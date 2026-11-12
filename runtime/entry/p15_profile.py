"""Small, local owner configuration with explicit work-scoped overrides."""
from copy import deepcopy
from pathlib import Path
import re

from p13_fixed_entry import file_lock, read_json, write_atomic_json
from p14_character import sha, validate_card

SCHEMA = 'wardrobe2-owner-profile-v1'
SNAPSHOT = '.golden-profile.json'
ALIASES = {
    '服装负责人': 'wardrobe', '服装指导': 'wardrobe', '服装': 'wardrobe',
    '情绪导演': 'performance.expression', '表情导演': 'performance.expression', '表情指导': 'performance.expression',
    '摄影师': 'camera', '摄影': 'camera', '灯光': 'lighting',
    '场景': 'scene',
}
ROLES = set(ALIASES.values())
ROLE_TEXT = '|'.join(map(re.escape, ALIASES))


def text(value, field, limit=400):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f'invalid {field}')
    return value.strip()


def read_profile(path):
    if path is None or not Path(path).is_file():
        return dict(schema=SCHEMA, revision=0, roles={}, characters={}, active_character=None)
    profile = read_json(Path(path))
    if (not isinstance(profile, dict) or profile.get('schema') != SCHEMA
            or type(profile.get('revision')) is not int
            or profile['revision'] < 0 or not isinstance(profile.get('roles'), dict)
            or not isinstance(profile.get('characters'), dict)):
        raise ValueError('invalid owner profile')
    for role, note in profile['roles'].items():
        if role not in ROLES and role != 'performance':
            raise ValueError('unknown role in owner profile')
        text(note, 'preference')
    for key, entry in profile['characters'].items():
        if validate_card(entry['card'])['character_key'] != key:
            raise ValueError('character library key differs from card')
        if not isinstance(entry['aliases'], list):
            raise ValueError('invalid character aliases')
        for alias in entry['aliases']:
            text(alias, 'character alias', 100)
    if profile['active_character'] is not None and profile['active_character'] not in profile['characters']:
        raise ValueError('active character is missing from owner profile')
    if 'outfit_triptych' in profile and type(profile['outfit_triptych']) is not bool:
        raise ValueError('invalid 擦边模式 setting')
    return profile


def parse_utterance(utterance):
    phrase = text(utterance, 'preference utterance').rstrip('。！!')
    scope = 'this_time' if phrase.startswith('这次') else 'long_term'
    phrase = phrase.removeprefix('这次').strip()
    outfit_mode = re.fullmatch(r'(打开|开启|关闭|关掉)\s*擦边模式|擦边模式\s*(打开|开启|关闭|关掉)', phrase)
    if outfit_mode:
        return dict(op='set_outfit_triptych', value=(outfit_mode[1] or outfit_mode[2]) in ('打开', '开启'),
                    scope=scope)
    choice = re.fullmatch(r'(?:角色导演[，,:： ]*)?(?:换成|改用|使用|选择|换回)(?:我保存的)?(.+)', phrase)
    if choice:
        return dict(op='choose_character', value=choice[1], scope=scope)
    if phrase in {'角色导演恢复默认', '选角恢复默认', '恢复默认角色'}:
        return dict(op='choose_character', value='默认角色', scope=scope)
    phrase = phrase.removeprefix('把')
    role = re.fullmatch(rf'({ROLE_TEXT})\s*(.+)', phrase)
    if role:
        detail = role[2].strip('，,:： ')
        if detail in {'恢复默认', '清空偏好', '重置'}:
            return dict(op='set_role', role=ALIASES[role[1]], value=None, scope=scope)
        note = re.sub(r'^(?:以后|从现在起)?\s*(?:偏向|偏|更|喜欢|希望|倾向于|倾向)?\s*', '', detail)
        return dict(op='set_role', role=ALIASES[role[1]], value=text(note, 'preference'), scope=scope)
    raise ValueError('unrecognized utterance; translate the explicit request to a supported structured operation')


def apply(profile, request):
    op = request['op']
    value = request.get('value')
    if op == 'set_role':
        role = request.get('role')
        if role not in ROLES:
            raise ValueError('unknown role')
        if value is None:
            profile['roles'].pop(role, None)
        else:
            profile['roles'][role] = text(value, 'preference')
    elif op == 'set_outfit_triptych':
        if type(value) is not bool:
            raise ValueError('擦边模式 must be enabled or disabled')
        profile['outfit_triptych'] = value
    elif op == 'choose_character':
        if value in (None, '默认角色', '默认'):
            profile['active_character'] = None
            return
        name = text(value, 'character name', 100)
        if name in profile['characters']:
            profile['active_character'] = name
            return
        matches = [key for key, entry in profile['characters'].items()
                   if name in (entry['card']['display_name'], *entry['aliases'])]
        if len(matches) != 1:
            raise ValueError('character alias is missing or ambiguous; specify the character key')
        profile['active_character'] = matches[0]
    elif op == 'save_character':
        card = validate_card(request.get('card'))
        aliases = request.get('aliases', [])
        if not isinstance(aliases, list) or len(aliases) > 12:
            raise ValueError('invalid character aliases')
        profile['characters'][card['character_key']] = dict(
            card=card, aliases=[text(alias, 'character alias', 100) for alias in aliases])
    else:
        raise ValueError('unknown configuration operation')


def configure(path, request):
    path = Path(path).resolve()
    if not isinstance(request, dict):
        raise ValueError('configuration request must be an object')
    scope = request.get('scope', 'long_term')
    if scope not in {'long_term', 'this_time'}:
        raise ValueError('unknown preference scope')
    if scope == 'this_time':
        preview = read_profile(path)
        if request['op'] == 'save_character':
            raise ValueError('save a character before selecting it for one work')
        apply(preview, request)
        return {'status': 'this_time_override', 'override': request}
    with file_lock(path.with_name(path.name + '.lock')):
        profile = read_profile(path)
        original = deepcopy(profile)
        apply(profile, request)
        if original != profile:
            profile['revision'] += 1
            write_atomic_json(path, profile)
    return {'status': 'saved', 'revision': profile['revision'],
            'roles': profile['roles'], 'active_character': profile['active_character'],
            'outfit_triptych': profile.get('outfit_triptych', True)}


def snapshot(path, overrides=()):
    profile = read_profile(path)
    prior_roles = dict(profile['roles'])
    scoped_roles = set()
    for request in overrides:
        if request.get('scope') != 'this_time' or request['op'] not in {
            'choose_character', 'set_role', 'set_outfit_triptych'
        }:
            raise ValueError('this_time role, character or outfit mode override required')
        apply(profile, request)
        if request['op'] == 'set_role':
            scoped_roles.add(request['role'])
    active = profile['active_character']
    card = profile['characters'][active]['card'] if active else None
    settings = [{'role': role, 'note': note, 'strength': 'this_time' if role in scoped_roles else 'soft'}
                for role, note in sorted(profile['roles'].items())]
    cleared = sorted(scoped_roles.intersection(prior_roles).difference(profile['roles']))
    return dict(schema=SCHEMA, revision=profile['revision'], settings=settings,
                cleared_roles=cleared, character=card,
                outfit_triptych=profile.get('outfit_triptych', True))


def session_profile(data_dir, *, allow_missing=False):
    file = data_dir / SNAPSHOT
    pin = data_dir / '.selection-pin.json'
    expected = read_json(pin).get('creation_profile_sha256') if pin.is_file() else None
    if not file.is_file():
        if expected is not None and not allow_missing:
            raise ValueError('pinned creation profile is missing')
        return None
    profile = read_json(file)
    if expected != sha(profile):
        raise ValueError('creation profile differs from the session pin')
    return profile


def signed_settings(profile):
    card = profile['character']
    settings = dict(schema=SCHEMA, revision=profile['revision'], settings=profile['settings'],
                    cleared_roles=profile['cleared_roles'], profile_sha256=sha(profile),
                    character_key=card['character_key'] if card else None,
                    character_card_sha256=sha(card) if card else None)
    if 'outfit_triptych' in profile:
        settings['outfit_triptych'] = profile['outfit_triptych']
    return settings
