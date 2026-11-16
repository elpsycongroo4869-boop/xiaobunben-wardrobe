"""P1.5 Golden RC entry, using Stable's single-button signed full-text relay."""
import argparse
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import p13_fixed_entry as fixed
import p14_delivery as delivery
import p15_profile as owner
from p15_creative import INTERACTION, recent_moment_context
from p14_character import (card_from_file, director_from_card, render_contract_from_card,
                           validate_director_job, signed_render_request, verify_dispatch)

BASE = Path(__file__).resolve().parent
VERSION = '5.0.3'
SESSION_MARKER = '.p14-session.json'
SESSION_SCHEMA = 'wardrobe2-p14-action-narrative-session-v1'
VISUAL_INTENT_PROFILE = 'visual_intent_v1'
RENDER_POLICY = 'emotion_v1'
NATIVE_RESULT_LOCK = '.p14-native-result.lock'
WORK_ID = re.compile(r'[A-Za-z0-9_-]{1,96}')
BUTTON_COMMAND = re.compile(
    r'WARDROBE2_OPEN ([A-Za-z0-9][A-Za-z0-9_-]{0,95}) ([A-Za-z0-9_-]{1,96}) ([0-9a-f]{64})'
)


def start(ledger, session, persona_summary, *, cache=None, sessions=None,
          memory_available=False, candidate_count=30, bookshelf='stable',
          profile=None, overrides=()):
    """Return H1's complete pinned menu and isolated session in one call."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', session):
        raise ValueError('invalid P1.4 session ID')
    default = Path(tempfile.gettempdir()) / 'wardrobe2-public-v2'
    sessions = Path(sessions or default / 'sessions').resolve()
    target = sessions / session
    if target.is_symlink():
        raise ValueError('P1.4 session must not be a symlink')
    with fixed.file_lock(sessions / '.p14-start.lock'):
        if target.exists() and (
            not (target / SESSION_MARKER).is_file()
            or fixed.read_json(target / SESSION_MARKER).get('schema') != SESSION_SCHEMA
        ):
            raise ValueError('existing directory is not an isolated P1.4 session')
        pinned_profile = owner.session_profile(target, allow_missing=True)
        if pinned_profile is None and (profile is not None or overrides or bookshelf in ('golden', 'curated')):
            pinned_profile = owner.snapshot(profile, overrides)
        character = pinned_profile['character'] if pinned_profile is not None else None
        if character is not None:
            persona_summary = character['identity'] + ' ' + character['appearance']
        ready = fixed.ready(SimpleNamespace(
            entry=BASE / 'current.json', package=None, cache=cache or default / 'cache',
            sessions=sessions, ledger=ledger, session=session, persona_summary=persona_summary,
            memory_available=memory_available, force=False,
            candidate_count=candidate_count, bookshelf=bookshelf,
            creation_profile_sha256=owner.sha(pinned_profile) if pinned_profile is not None else None,
        ))
        expected = {'schema': SESSION_SCHEMA, 'session': session, 'runtime': ready['runtime']}
        marker = target / SESSION_MARKER
        if not marker.exists():
            fixed.write_atomic_json(marker, expected)
        if fixed.read_json(marker) != expected:
            raise ValueError('P1.4 session runtime identity changed')
        if pinned_profile is not None:
            profile_path = target / owner.SNAPSHOT
            if not profile_path.is_file():
                fixed.write_atomic_json(profile_path, pinned_profile)
            ready['creation_profile'] = owner.signed_settings(pinned_profile)
    menu = ready['prompt']['menu']
    ready['bookshelf_provenance'] = {
        'source': {'curated': 'pinned_curated_world_index', 'golden': 'pinned_golden_world_index',
                   'stable': 'pinned_R2_world_index'}[bookshelf],
        'catalog_books': menu['catalog_books'],
        'catalog_schema': 'wardrobe2-world-index-prototype-v1',
        'shelf_selection_source': 'the pinned menu in this session',
    }
    ready['engine_version'] = ready['version']
    ready['version'] = VERSION
    ready['suggested_next'] = 'use the pinned menu and prepare one Job with render_profile visual_intent_v1'
    return ready


def _guard_session(runtime, data_dir):
    data_dir, runtime = Path(data_dir).resolve(), Path(runtime).resolve()
    marker = data_dir / SESSION_MARKER
    if not marker.is_file() or fixed.read_json(marker) != {
        'schema': SESSION_SCHEMA, 'session': data_dir.name, 'runtime': str(runtime),
    }:
        raise ValueError('use runtime and data_dir returned by P1.4 start')
    return runtime, data_dir


def _call(runtime, data_dir, command, *args):
    prefix = [sys.executable, '-B', '-X', 'utf8', str(runtime / 'p13_cli.py'), '--data', str(data_dir)]
    return json.loads(subprocess.run(
        prefix + [command, *(str(arg) for arg in args)],
        cwd=runtime, check=True, capture_output=True, encoding='utf-8',
    ).stdout)


def production_prompt(runtime, data_dir, selection, persona, work_id, *, character_card=None):
    runtime, data_dir = _guard_session(runtime, data_dir)
    staged = _session_file(data_dir, 'character-director', work_id, suffix='-persona.json')
    selection_data = fixed.read_json(Path(selection).resolve())
    _check_menu_selection(data_dir, selection_data)
    persona_input = Path(persona).resolve()
    profile = owner.session_profile(data_dir)
    triptych = profile is not None and profile.get('outfit_triptych') is True
    framing = (
        'camera.plan 决定机位和景别。visible_frame 只交付可见画面，版式由程序处理。'
        if triptych else
        '本轮是单格。camera.plan 决定单张照片的机位和景别，visible_frame 直接交代镜头内可见画面。'
    )
    selected_card = _resolve_character(profile, character_card)
    director_extension = ''
    contract = None
    if selected_card is not None or profile is not None:
        draft = fixed.read_json(persona_input)
        if not isinstance(draft, dict):
            raise ValueError('authored persona is not a JSON object')
        if profile is not None:
            settings = profile['settings']
            configured = {row['role'] for row in settings}.union(profile['cleared_roles'])
            draft['preferences'] = [row for row in draft.get('preferences', [])
                                    if row['role'] not in configured] + settings
        if selected_card is not None:
            draft.update(adult=True, identity=selected_card['identity'], appearance=selected_card['appearance'],
                         identity_continuity=selected_card['continuity'])
        staged.parent.mkdir(parents=True, exist_ok=True)
        if staged.exists() and fixed.read_json(staged) != draft:
            raise ValueError('cannot change a staged character identity in one work')
        if not staged.exists():
            fixed.write_atomic_json(staged, draft)
        persona_input = staged
    if selected_card is not None:
        card = selected_card
        contract = render_contract_from_card(card)
        director_extension = ('\n【第六岗位：角色导演 Character Director】使用已确定的文字角色卡，'
            '用一句话说明主角如何适配本轮职业与处境，人物身份以已定角色卡为准。'
            '交稿时 role_director 只写 {"story_fit":"本轮角色适配"}，'
            'persona 只写 adult=true 和 story_role。由程序补齐稳定身份和 render_contract。'
            '本轮已确定的图像资产为 '+json.dumps(contract['image_assets'], ensure_ascii=False)+'。')
    options = ['--emotion-context']
    if selected_card is not None:
        options.append('--compact-character-draft')
    result = _call(runtime, data_dir, 'production-prompt',
                   Path(selection).resolve(), persona_input, work_id, *options)
    chapter = result.get('chapter')
    if chapter is not None:
        if (chapter['book_id'], chapter['id']) != (selection_data['book_id'], selection_data['chapter_id']):
            raise ValueError('chapter selection changed during handoff')
        pin = _session_file(data_dir, 'character-director', work_id, suffix='-chapter.json')
        with fixed.file_lock(pin.with_suffix('.lock')):
            if pin.is_file():
                if fixed.read_json(pin) != chapter:
                    raise ValueError('chapter differs from the pinned work')
            else:
                fixed.write_atomic_json(pin, chapter)
    result['selection_provenance'] = {
        'origin': selection_data.get('origin'),
        'book_id': selection_data.get('book_id'),
        'shelf_id': selection_data.get('shelf_id'),
        'disclosure': 'show the exact book only inside the collapsed creative section',
    }
    if chapter is not None and chapter['id'] != 0:
        guidance = (
            '\n【预设章节交稿】章节 Point 已锁定。不要重写 intent/context/event/moment/emotion 五栏。'
            'producer 可交 visual_decisions 与从既定 Point 逐字摘录的 performance_lock；没有新增就用 {}。'
            '程序将 Point 原文填入 producer.moment。'
            '只有用户明确要求或既定 Point 离不开在场配角时才拍入配角，主角仍是视觉中心。'
        )
    else:
        guidance = (
            '\n【制作人·单帧叙事】以本轮主角为画面中心。自行设计 Point 时写清观众要读懂的事件、必要行为及可见证据；'
            '书卡有标志定格时承接该定格，写入 producer.moment。故事必需的道具接触和职业技法写进 Point。'
            '默认仅主角入镜，只有用户明确要求同框才安排配角。动物、植物、小物件或幻想生物可自然参与。'
            '关键转折要有画面依据：暗号或画外信息可用可见线索承接；自由创作时也可换拍同一故事里更好读的瞬间。'
            '安静的画面可以只留一个有意味的状态，前因与余味可以留白。' + INTERACTION
        )
    result['prompt'] += guidance + (
        '\n一次交付可封签的 Job。摄影正文通常约 2 至 3 KiB UTF-8，保留必要视觉细节，同一事实写一次。'
        '\n' + framing +
        '\n在现有 Job 根级字段之外明确加入 "render_profile": "' + VISUAL_INTENT_PROFILE + '"。'
    )
    if chapter is not None:
        result['prompt'] += f"\nJob 保留选中的 chapter_id={chapter['id']}。程序封入书卡原文。"
    if chapter is None or chapter['id'] == 0:
        recent = recent_moment_context(fixed.read_json(data_dir / 'shelf-state.json'))
        if recent:
            result['prompt'] += '\n' + recent
    result['render_profile'] = VISUAL_INTENT_PROFILE
    if director_extension:
        result['prompt'] += director_extension
        result['character_director_enabled'] = True
        result['character_key'] = card['character_key']
    return result


def _normalize_preset_producer(job, chapter, *, new_emotion=False):
    """Expand a compact authored delta using the session-pinned chapter only.

    Do this before any seal or render compilation. Free chapter/other origins and
    historical full drafts remain unchanged. Never trust chapter text in the Job.
    """
    if chapter is None or chapter['id'] == 0:
        return job
    point = chapter.get('point')
    if not isinstance(point, str) or not point.strip():
        raise ValueError('pinned preset chapter Point is missing')
    draft = job.get('producer', {})
    if not isinstance(draft, dict):
        raise ValueError('producer must be an object')
    legacy = {'intent', 'context', 'event', 'moment', 'emotion'}
    if legacy.issubset(draft) and 'visual_decisions' not in draft:
        return {**job, 'producer': {**draft, 'moment': point}}
    allowed = {'visual_decisions', 'performance_lock'} if new_emotion else {'visual_decisions'}
    if set(draft) - allowed:
        raise ValueError('preset producer must use only visual_decisions or a complete legacy five-field draft')
    delta = draft.get('visual_decisions', '')
    if not isinstance(delta, str):
        raise ValueError('producer.visual_decisions must be a string')
    delta = delta.strip()
    chapter_name = chapter['title']
    resolved = {
        'intent': f'呈现预设章节《{chapter_name}》已经确定的故事瞬间',
        'context': f'已选定世界书 {chapter["book_id"]} 的第 {chapter["id"]} 章《{chapter_name}》；世界环境以本轮岗位定稿为准',
        'event': point + (f'\n本轮补充的画面决定：{delta}' if delta else ''),
        'moment': point,
        'emotion': ('沿用章节 Point 的情绪，具体演绎见情绪导演交稿。' if new_emotion
                    else '以章节 Point 的既定情绪与 performance.expression 的具体演绎为准'),
    }
    if 'performance_lock' in draft:
        resolved['performance_lock'] = draft['performance_lock']
    if delta:
        resolved['visual_decisions'] = delta
    return {**job, 'producer': resolved}


def _compact_host_result(command, result):
    """One producer menu or one full signed relay; no duplicated preview texts.

    Only compact a verified button delivery. Unverified handoffs keep the full
    prepared contract so they can still be passed to verify-delivery intact.
    """
    if command == 'start':
        return {
            'status': result['status'], 'version': result['version'],
            'runtime': result['runtime'], 'data_dir': result['data_dir'],
            'session_mode': result['session_mode'],
            'shelf_id': result['prompt']['menu']['shelf_id'],
            'catalog_books': result['prompt']['menu']['catalog_books'],
            'candidate_count': result['prompt']['menu']['candidate_count'],
            'selection_prompt': result['prompt']['prompt'],
            'next_step': 'select one book and chapter from selection_prompt; run production-prompt',
        }
    if command in ('prepare', 'verify-delivery'):
        ui = result.get('chat_ui', {})
        native = ui.get('native_ui', {})
        if result.get('status') == 'handoff_verified' and native.get('show_open_button') and native.get('open_button_message'):
            return {
                'status': result['status'], 'work_id': result['work_id'],
                'session_id': result['session_id'],
                'seal_sha256': result['seal_sha256'],
                'chat_ui': {
                    'native_ui': native,
                    'mode_card': ui.get('mode_card'),
                    'outfit_triptych': ui.get('outfit_triptych'),
                },
                'next_step': 'render the native Chat open button using chat_ui.native_ui.open_button_message; never call image generation before a click',
            }
    return result


def _resolve_character(profile, character_card):
    explicit = profile['character'] if profile is not None else None
    supplied = card_from_file(character_card) if character_card is not None else None
    if explicit is not None and supplied is not None and explicit != supplied:
        raise ValueError('supplied character differs from the session character')
    if explicit is not None or supplied is not None:
        return explicit or supplied
    return card_from_file(BASE.parent / 'defaults/character-example.json') if profile is not None else None


def prepare(runtime, data_dir, job_file, *, studio=None, create_if_absent=None, read=None,
            character_card=None, expected_render_profile=None, session_store=False):
    runtime, data_dir = _guard_session(runtime, data_dir)
    if session_store:
        if create_if_absent is not None or read is not None:
            raise ValueError('choose either the persistent session store or external store callbacks')
        studio = studio if studio is not None else _cli_studio(runtime)
        if Path(studio.__file__).resolve() != runtime / 'studio.py':
            raise ValueError('studio module does not match the verified runtime')
    job = fixed.read_json(Path(job_file).resolve())
    profile = owner.session_profile(data_dir)
    card = _resolve_character(profile, character_card)
    pending = _session_file(data_dir, 'pending', job.get('work_id'))
    sealed_job = fixed.read_json(pending)['work']['job'] if pending.is_file() else None
    if sealed_job is not None:
        cd_count = sealed_job.get('fixed_world_candidate_count')
    else:
        count = _check_menu_selection(data_dir, job)
        cd_count = count if count is not None and count < 30 else None
    if 'fixed_world_candidate_count' in job and (
        type(job['fixed_world_candidate_count']) is not int or job['fixed_world_candidate_count'] != cd_count
    ):
        raise ValueError('job cooldown count differs from the pinned session or seal')
    if expected_render_profile is not None and (
        expected_render_profile != VISUAL_INTENT_PROFILE or job.get('render_profile') != expected_render_profile
    ):
        raise ValueError('candidate Job must explicitly declare render_profile visual_intent_v1')
    if card is None and (
        expected_render_profile is not None or 'role_director' in job or 'render_contract' in job
    ):
        raise ValueError('character-card required for a directed job')
    normalized = job
    if card is not None:
        director = job.get('role_director')
        if (job.get('render_profile') == VISUAL_INTENT_PROFILE and isinstance(director, dict)
                and set(director) == {'story_fit'} and 'render_contract' not in job):
            job = {**job, 'role_director': director_from_card(card, director['story_fit']),
                   'render_contract': render_contract_from_card(card)}
        normalized = validate_director_job(job, card)
    if profile is not None:
        settings = owner.signed_settings(profile)
        if 'creation_profile' in job and job['creation_profile'] != settings:
            raise ValueError('job creation profile differs from the pinned session')
        normalized = {**normalized, 'creation_profile': settings}
    chapter = sealed_job.get('chapter') if sealed_job is not None else None
    if sealed_job is None and job.get('chapter_id') is not None:
        chapter_pin = _session_file(data_dir, 'character-director', job['work_id'], suffix='-chapter.json')
        if not chapter_pin.is_file():
            raise ValueError('prepare requires the original pinned chapter handoff')
        chapter = fixed.read_json(chapter_pin)
    if chapter is not None:
        if (type(job.get('chapter_id')) is not int or
                (chapter['book_id'], chapter['id']) != (job.get('book_id'), job['chapter_id']) or
                job.get('chapter', chapter) != chapter):
            raise ValueError('job chapter differs from the original pinned Point')
        normalized = {**normalized, 'chapter': chapter}
    elif 'chapter_id' in job or 'chapter' in job:
        raise ValueError('unbound chapter in job')
    if cd_count is not None:
        normalized = {**normalized, 'fixed_world_candidate_count': cd_count}
    policy = sealed_job.get('render_policy') if sealed_job is not None else RENDER_POLICY
    if chapter is not None and chapter['id'] != 0:
        normalized = _normalize_preset_producer(
            normalized, chapter, new_emotion=policy == RENDER_POLICY)
    if policy == RENDER_POLICY and job.get('render_profile') != VISUAL_INTENT_PROFILE:
        raise ValueError('new jobs require render_profile visual_intent_v1; refresh production-prompt')
    if 'render_policy' in job and job['render_policy'] != policy:
        raise ValueError('render policy differs from the original seal or this runtime')
    if policy is not None:
        normalized = {**normalized, 'render_policy': policy}
        if sealed_job is None:
            # Reject before pinning the normalized Job so the same draft can be repaired.
            if studio is None:
                studio = _cli_studio(runtime)
            if Path(studio.__file__).resolve() != runtime / 'studio.py':
                raise ValueError('studio module does not match the verified runtime')
            studio.compose_render(normalized)
    if card is not None or profile is not None or cd_count is not None or policy is not None:
        pinned_job = _session_file(data_dir, 'character-director', normalized['work_id'], suffix='-job.json')
        pinned_job.parent.mkdir(parents=True, exist_ok=True)
        if pinned_job.is_file() and fixed.read_json(pinned_job) != normalized:
            raise ValueError('character-directed job conflicts with prior snapshot')
        if not pinned_job.exists():
            fixed.write_atomic_json(pinned_job, normalized)
        job_file = pinned_job
    result = delivery.prepare(
        runtime, data_dir, job_file, studio=studio, create_if_absent=create_if_absent, read=read,
    )
    raw = _session_file(data_dir, 'pending', result['work_id']).read_bytes()
    if session_store:
        # prepare retained a byte pin before this fresh read of the actual session store.
        result = delivery.verify_delivery(result, studio=studio, original=raw, readback=raw)
        result['delivery']['store'] = 'persistent_session'
    return _finish_delivery(result, raw, data_dir, studio=studio)


def _session_file(data_dir, folder, work_id, *, suffix='.json'):
    if not isinstance(work_id, str) or not WORK_ID.fullmatch(work_id):
        raise ValueError('invalid work ID')
    parent = data_dir / folder
    path = parent / f'{work_id}{suffix}'
    if parent.resolve() != parent or path.resolve() != path:
        raise ValueError('work file leaves the isolated session')
    return path


def _check_menu_selection(data_dir, selection):
    origin = selection.get('origin')
    if origin not in ('autonomous_library', 'autonomous_original', 'autonomous_spontaneous', 'autonomous_self'):
        return
    source = data_dir / '.source.json'
    curated = source.is_file() and fixed.read_json(source).get('bookshelf') == 'curated'
    pin = data_dir / '.selection-pin.json'
    if origin != 'autonomous_library':
        if curated:
            if not pin.is_file():
                raise ValueError('autonomous free story requires a pinned menu')
            menu = fixed.read_json(pin)['payload']['menu']
            entry_id = selection.get('self_book_id') if origin == 'autonomous_self' else 'ORIGINAL'
            kind = 'self' if origin == 'autonomous_self' else 'original'
            if not any(row['kind'] == kind and row['id'] == entry_id for row in menu['available_entries']):
                raise ValueError('free story is outside the pinned menu')
        return
    book = selection.get('book_id')
    chapter = selection.get('chapter_id')
    if curated and (type(chapter) is not int or not 0 <= chapter <= 4):
        raise ValueError('curated fixed world requires chapter_id 0 to 4')
    revisit = selection.get('deliberate_revisit_ref')
    if isinstance(revisit, str) and revisit and not (curated and chapter == 0):
        ledger = fixed.read_json(data_dir / 'shelf-state.json')
        if isinstance(book, str) and ledger.get('work_books', {}).get(revisit) == book:
            return fixed.read_json(pin).get('candidate_count', 30) if pin.is_file() else 30
        raise ValueError('deliberate revisit does not reference a successful adoption of this book')
    if not pin.is_file():
        raise ValueError('autonomous fixed-world selection requires a pinned menu')
    pinned = fixed.read_json(pin)
    menu = pinned['payload']['menu']
    fallback_book = menu.get('fallback_book_id')
    if menu.get('shelf_selection_mode') == 'global_cooldown_fallback' and fallback_book is None:
        fallback_book = book
    if (selection.get('shelf_id') != menu['shelf_id']
            or selection.get('fallback_book_id') != fallback_book
            or not any(entry['kind'] == 'fixed' and entry['id'] == book
                       for entry in menu['available_entries'])):
        raise ValueError('fixed world is outside the pinned menu')
    if curated:
        entry = next(row for row in menu['available_entries'] if row['id'] == book)
        if not any(row['id'] == chapter for row in entry['chapters']):
            raise ValueError('chapter is outside the pinned menu')
    return pinned.get('candidate_count', 30)


def _attach_character(result, envelope, request, data_dir):
    if request is None:
        return result  # legacy unopened jobs remain compatible
    preview = result['chat_ui']['preview']
    director = envelope['work']['job']['role_director']
    if 'role_director' in preview and preview['role_director'] != director:
        raise ValueError('character director preview differs from signed work')
    preview['role_director'] = director
    job = envelope['work']['job']
    settings = job.get('creation_profile')
    triptych = isinstance(settings, dict) and settings.get('outfit_triptych') is True
    result['chat_ui']['outfit_triptych'] = triptych
    result['chat_ui']['mode_card'] = {
        'status': f"本轮 · 擦边模式{'开启（三格）' if triptych else '关闭（单格）'}",
        'commands': '输入「打开擦边模式」开启，输入「关闭擦边模式」关闭。设置从下一张生效。',
    }
    pin = data_dir / '.selection-pin.json'
    menu = fixed.read_json(pin)['payload']['menu'] if pin.is_file() else {}
    result['chat_ui']['bookshelf_provenance'] = {
        'catalog_books': menu.get('catalog_books'),
        'shelf_id': job.get('shelf_id'),
        'origin': job.get('origin'),
        'selected_book_inside_spoiler': job.get('book_id'),
        'source': 'R2_signed_job_and_pinned_book_catalog',
    }
    result['chat_ui']['character_director'] = {
        'character_key': director['character_key'],
        'identity_source': director['identity_source'],
        'story_fit': director['story_fit'],
        'signed_generation_inputs': request['image_assets'],
    }
    if result.get('open_action') is not None:
        result['open_action']['render_request'] = request
    return result


def _finish_delivery(result, raw, data_dir, *, studio):
    envelope = json.loads(raw)
    request = signed_render_request(envelope)
    result = _attach_character(result, envelope, request, data_dir)
    result['session_id'] = data_dir.name
    if request is None:
        result['native_open_status'] = 'missing_signed_generation_contract'
    action = result.get('open_action')
    if action is None:
        return result
    action['session_id'] = data_dir.name
    ui = result['chat_ui']['native_ui']
    if request is None:
        result['legacy_open_action'] = result.pop('open_action')
        return result

    work_id = action['work_id']
    seal = action['seal_sha256']
    command = f'WARDROBE2_OPEN {data_dir.name} {work_id} {seal}'
    pending = _session_file(data_dir, 'pending', work_id)
    saved = _session_file(data_dir, 'native-open', work_id)
    with studio.studio_lock(data_dir):
        if hashlib.sha256(raw).hexdigest() != action['envelope_bytes_sha256']:
            raise ValueError('retained readback does not match the verified byte pin')
        if (not (data_dir / 'shelf-state.json').is_file() or not pending.is_file()
                or pending.read_bytes() != raw or envelope.get('attempts')):
            raise ValueError('original unopened attempt state unavailable')
        if _session_file(data_dir, 'directed-receipts', work_id).exists():
            raise ValueError('work already completed')
        record = {'command': command, 'action': action, 'readback_utf8': raw.decode('utf-8')}
        if not saved.exists():
            fixed.write_atomic_json(saved, record)
        elif fixed.read_json(saved) != record:
            raise ValueError('saved native button differs from verified delivery')
    ui['open_button_command'] = command
    ui['open_button_message'] = (f'WARDROBE2_RELAY {data_dir.name} {work_id} {seal}'
                                 + '\n\n' + action['text'])
    ui['show_open_button'] = True
    return result


def verify_delivery(prepared, *, studio, original, readback, data_dir=None):
    """Finish H1 fallback using the bytes returned from the button's real store."""
    if data_dir is not None and Path(data_dir).name != prepared['session_id']:
        raise ValueError('delivery directory does not match the original session')
    result = delivery.verify_delivery(
        prepared, studio=studio, original=original, readback=readback,
    )
    if data_dir is None:
        data_dir = Path(prepared['pending_path']).parent.parent
    _, data_dir = _guard_session(Path(studio.__file__).resolve().parent, data_dir)
    if data_dir.name != prepared['session_id']:
        raise ValueError('delivery does not belong to the original session')
    return _finish_delivery(result, readback, data_dir, studio=studio)


def _verify_click(runtime, data_dir, action, readback, *, studio):
    runtime, data_dir = _guard_session(runtime, data_dir)
    if Path(studio.__file__).resolve() != runtime / 'studio.py':
        raise ValueError('studio module does not match the verified runtime')
    if action.get('session_id') != data_dir.name:
        raise ValueError('click action does not belong to this P1.4 session')
    work_id = action['work_id']
    if not isinstance(work_id, str) or not WORK_ID.fullmatch(work_id):
        raise ValueError('invalid work ID')
    verified = delivery.verify_open(
        readback, studio=studio, work_id=work_id, seal_sha256=action['seal_sha256'],
        envelope_bytes_sha256=action['envelope_bytes_sha256'], expected_action_text=action['text'],
    )
    sealed_request = signed_render_request(json.loads(readback))
    if sealed_request is not None and action.get('render_request') != sealed_request:
        raise ValueError('open action generation inputs differ from signed work')
    return runtime, data_dir, verified, sealed_request


def _open_verified(runtime, data_dir, action, readback, verified, sealed_request, *,
                   studio):
    work_id = action['work_id']
    pending = data_dir / 'pending' / f'{work_id}.json'
    with studio.studio_lock(data_dir):
        if not pending.resolve().is_relative_to(data_dir):
            raise ValueError('pending seal path leaves the isolated session')
        if not pending.exists():
            pending.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=pending.parent, delete=False) as staged:
                    temporary = Path(staged.name)
                    staged.write(readback)
                    staged.flush()
                    os.fsync(staged.fileno())
                os.replace(temporary, pending)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    result = _call(runtime, data_dir, 'open', work_id, '--seal-sha256', action['seal_sha256'])
    if result['render_instruction'] != verified['render_instruction']:
        raise ValueError('open result differs from the verified photography text')
    if sealed_request is not None:
        result['render_request'] = sealed_request
    return result


def open_seal(runtime, data_dir, action, readback, *, studio):
    """Open and return the verified sealed text, including historical seals."""
    runtime, data_dir, verified, sealed_request = _verify_click(
        runtime, data_dir, action, readback, studio=studio,
    )
    return _open_verified(runtime, data_dir, action, readback, verified, sealed_request,
                          studio=studio)


def _native_attempt_id(data_dir, work_id, seal):
    key = f'{data_dir.name}/{work_id}/{seal}'.encode('utf-8')
    return 'native-' + hashlib.sha256(key).hexdigest()


def _pending_for_seal(path, work_id, seal, *, studio):
    envelope = fixed.read_json(path)
    work = envelope['work']
    if (envelope.get('seal_sha256') != seal or studio.digest(work) != seal
            or work['job']['work_id'] != work_id):
        raise ValueError('local attempt state belongs to a different seal')
    return envelope


def _confirmed_generation(state, work_id, attempt_id):
    if work_id not in state['work_origins']:
        return None
    return next((generation_id for generation_id, render in state['renders'].items()
                 if render['work_id'] == work_id and render.get('attempt_id') == attempt_id), None)


def _reserve_native_attempt(data_dir, action, attempt_id, *, studio):
    work_id, seal = action['work_id'], action['seal_sha256']
    pending = _session_file(data_dir, 'pending', work_id)
    directed = _session_file(data_dir, 'directed-receipts', work_id)
    saved = _session_file(data_dir, 'native-open', work_id)
    dispatch = _session_file(data_dir, 'native-open', work_id, suffix='.attempt.json')
    success = _session_file(data_dir, 'native-success', work_id)
    ledger = data_dir / 'shelf-state.json'
    with studio.studio_lock(data_dir):
        if not saved.is_file():
            return {'status': 'state_unavailable'}
        record = fixed.read_json(saved)
        if (record['command'] != f'WARDROBE2_OPEN {data_dir.name} {work_id} {seal}'
                or record['action']['envelope_bytes_sha256'] != action['envelope_bytes_sha256']):
            raise ValueError('native attempt differs from the saved open action')
        dispatched = dispatch.is_file()
        if dispatched and fixed.read_json(dispatch) != {'attempt_id': attempt_id}:
            raise ValueError('native dispatch record belongs to a different attempt')
        if directed.is_file():
            row = fixed.read_json(directed)
            if row.get('attempt_id') == attempt_id:
                return {'status': 'already_confirmed', 'generation_id': row['render_id']}
            return {'status': 'prior_attempt'}
        if not ledger.is_file():
            return {'status': 'state_unavailable'}
        envelope = _pending_for_seal(pending, work_id, seal, studio=studio) if pending.is_file() else {}
        attempts = envelope.get('attempts', {})
        row = attempts.get(attempt_id)
        if row and row['status'] == 'confirmed':
            return {'status': 'already_confirmed', 'generation_id': row['render_id']}
        state = fixed.read_json(ledger)
        generation_id = _confirmed_generation(state, work_id, attempt_id)
        if generation_id is not None:
            return {'status': 'already_confirmed', 'generation_id': generation_id}
        if work_id in state['work_origins']:
            return {'status': 'prior_attempt'}
        if row and row['status'] == 'failed':
            return {'status': 'already_failed'}
        if success.is_file():
            receipt = fixed.read_json(success)
            if (receipt['work_id'], receipt['attempt_id'], receipt['seal_sha256'], receipt['status']) != (
                    work_id, attempt_id, seal, 'succeeded'):
                raise ValueError('retained success receipt belongs to a different attempt')
            return {'status': 'awaiting_confirmation', 'generation_id': receipt['generation_id'],
                    'receipt_path': str(success), 'image_file': receipt['image_file']}
        if not envelope:
            return {'status': 'state_unavailable'}
        if row is not None or dispatched:
            return {'status': 'awaiting_result'}
        if attempts or envelope.get('confirmed_images') or envelope['state'] != 'ready':
            # A previous version or an explicit legacy open may have consumed this action.
            return {'status': 'prior_attempt'}
        envelope['state'] = 'opened'
        envelope['attempts'] = {attempt_id: {'status': 'registered'}}
        studio.atomic_json(pending, envelope)
        # Keep this proof outside the mutable pending snapshot and the read-only button.
        fixed.write_atomic_json(dispatch, {'attempt_id': attempt_id})
        return {'status': 'ready_to_submit'}


def open_native(runtime, data_dir, action, readback, *, clicked_text, studio):
    """Return a render request only for the first verified native attempt."""
    if clicked_text != action.get('text'):
        raise ValueError('click text differs from the original button text')
    _, data_dir, _, sealed_request = _verify_click(
        runtime, data_dir, action, readback, studio=studio,
    )
    if sealed_request is None:
        raise ValueError('native execution requires a signed generation contract')
    work_id, seal = action['work_id'], action['seal_sha256']
    attempt_id = _native_attempt_id(data_dir, work_id, seal)
    request = {key: sealed_request[key] for key in ('text', 'image_assets', 'generation_options')}
    verify_dispatch(sealed_request, request)
    result = _reserve_native_attempt(data_dir, action, attempt_id, studio=studio)
    if result['status'] == 'ready_to_submit':
        result.update(render_request=request, seal_sha256=seal)
    return {'work_id': work_id, 'attempt_id': attempt_id, **result}


def open_native_from_button(runtime, data_dir, command, *, studio):
    runtime, data_dir = _guard_session(runtime, data_dir)
    match = BUTTON_COMMAND.fullmatch(command)
    if match is None or match[1] != data_dir.name:
        raise ValueError('invalid button command or original session mismatch')
    work_id, seal = match[2], match[3]
    saved = _session_file(data_dir, 'native-open', work_id)
    if not saved.is_file():
        return {'status': 'state_unavailable', 'work_id': work_id}
    record = fixed.read_json(saved)
    action = record['action']
    if (record['command'] != command or action['work_id'] != work_id
            or action['seal_sha256'] != seal):
        raise ValueError('button command does not match verified delivery')
    # The button only carries an identifier. The signed text comes from the saved action.
    return open_native(runtime, data_dir, action, record['readback_utf8'].encode('utf-8'),
                       clicked_text=action['text'], studio=studio)


def open_native_from_fulltext_relay(runtime, data_dir, clicked_message, *, studio):
    """Authorize the exact full-text user relay; never reopen a changed or replayed work."""
    runtime, data_dir = _guard_session(runtime, data_dir)
    if not isinstance(clicked_message, str):
        raise ValueError('fulltext relay must be a UTF-8 string')
    header, sep, body = clicked_message.partition('\n\n')
    match = re.fullmatch(
        r'WARDROBE2_RELAY ([A-Za-z0-9][A-Za-z0-9_-]{0,95}) ([A-Za-z0-9_-]{1,96}) ([0-9a-f]{64})', header
    )
    if not sep or match is None or match[1] != data_dir.name:
        raise ValueError('invalid fulltext relay header or session')
    work_id, seal = match[2], match[3]
    record_path = _session_file(data_dir, 'native-open', work_id)
    if not record_path.is_file():
        return {'status': 'state_unavailable', 'work_id': work_id}
    record = fixed.read_json(record_path)
    action = record['action']
    if (record['command'] != f'WARDROBE2_OPEN {data_dir.name} {work_id} {seal}'
            or action['seal_sha256'] != seal or action['work_id'] != work_id
            or body != action['text']
            or clicked_message != header + '\n\n' + action['text']):
        raise ValueError('fulltext relay differs from the verified signed work')
    return open_native(runtime, data_dir, action, record['readback_utf8'].encode('utf-8'),
                       clicked_text=body, studio=studio)


def attempt(runtime, data_dir, work_id, attempt_id, *, failed=False):
    runtime, data_dir = _guard_session(runtime, data_dir)
    if not isinstance(attempt_id, str) or not attempt_id:
        raise ValueError('valid attempt ID required')
    command = 'fail-attempt' if failed else 'start-attempt'
    native_failure = failed and attempt_id.startswith('native-')
    lock = fixed.file_lock(data_dir / NATIVE_RESULT_LOCK) if native_failure else nullcontext()
    with lock:
        if native_failure and _session_file(data_dir, 'native-success', work_id).is_file():
            raise ValueError('native success receipt already saved; retry confirmation')
        return _call(runtime, data_dir, command, work_id, attempt_id)


def _retain_native_success(data_dir, expected, image_file, *, studio):
    work_id, attempt_id = expected['work_id'], expected['attempt_id']
    seal, render_id = expected['seal_sha256'], expected['generation_id']
    if attempt_id != _native_attempt_id(data_dir, work_id, seal):
        raise ValueError('native success receipt does not match the signed attempt')
    saved = _session_file(data_dir, 'native-open', work_id)
    dispatch = _session_file(data_dir, 'native-open', work_id, suffix='.attempt.json')
    pending = _session_file(data_dir, 'pending', work_id)
    directed = _session_file(data_dir, 'directed-receipts', work_id)
    destination = _session_file(data_dir, 'native-success', work_id)
    with studio.studio_lock(data_dir):
        button = fixed.read_json(saved)
        if button['command'] != f'WARDROBE2_OPEN {data_dir.name} {work_id} {seal}':
            raise ValueError('native success receipt differs from the saved open action')
        dispatched = dispatch.is_file()
        if dispatched and fixed.read_json(dispatch) != {'attempt_id': attempt_id}:
            raise ValueError('native dispatch record belongs to a different attempt')
        previous = fixed.read_json(destination) if destination.is_file() else None
        if previous is not None and any(previous.get(key) != value for key, value in expected.items()):
            raise ValueError('native success receipt already bound to a different result')
        if directed.is_file():
            completed = fixed.read_json(directed)
            if (completed['attempt_id'], completed['render_id']) != (attempt_id, render_id):
                raise ValueError('native success receipt differs from the confirmed work')
        else:
            state = fixed.read_json(data_dir / 'shelf-state.json')
            committed = state['renders'].get(render_id)
            if committed is not None and (committed['work_id'], committed.get('attempt_id')) != (work_id, attempt_id):
                raise ValueError('generation ID is already bound to a different work or attempt')
            if work_id in state['work_origins'] and _confirmed_generation(state, work_id, attempt_id) != render_id:
                raise ValueError('work already confirmed with a different generation or attempt')
            envelope = _pending_for_seal(pending, work_id, seal, studio=studio)
            attempts = envelope.get('attempts', {})
            row = attempts.get(attempt_id)
            if (row is None and not attempts and envelope['state'] == 'ready'
                    and not envelope['confirmed_images']
                    and (dispatched or previous is not None or committed is not None)):
                # Recover the authorization for this callback without dispatching again.
                envelope.update(state='opened', attempts={attempt_id: {'status': 'registered'}})
                studio.atomic_json(pending, envelope)
            elif (row is None or row['status'] not in ('registered', 'confirmed')
                  or (row['status'] == 'confirmed' and row.get('render_id') != render_id)):
                raise ValueError('native success receipt requires the original registered attempt')
        if previous is None:
            fixed.write_atomic_json(destination, {**expected, 'image_file': str(image_file)})
    return destination


def confirm(runtime, data_dir, work_id, render_id, image_file, *, attempt_id, receipt):
    """Pass a real generation receipt to the original idempotent ledger code."""
    runtime, data_dir = _guard_session(runtime, data_dir)
    if (not isinstance(work_id, str) or not WORK_ID.fullmatch(work_id)
            or not isinstance(attempt_id, str) or not attempt_id
            or not isinstance(render_id, str) or not render_id.strip()):
        raise ValueError('valid work, attempt and generation IDs required')
    image_file, receipt = Path(image_file).resolve(), Path(receipt).resolve()
    native = attempt_id.startswith('native-')
    native_lock = fixed.file_lock(data_dir / NATIVE_RESULT_LOCK) if native else nullcontext()
    with native_lock:
        payload = fixed.read_json(receipt)
        pending = _session_file(data_dir, 'pending', work_id)
        studio = _cli_studio(runtime) if native else None
        expected = {'status': 'succeeded', 'work_id': work_id, 'attempt_id': attempt_id,
                    'generation_id': render_id,
                    'image_sha256': (studio.verify_image(image_file) if native else
                                     hashlib.sha256(image_file.read_bytes()).hexdigest())}
        if pending.is_file():
            expected['seal_sha256'] = fixed.read_json(pending)['seal_sha256']
        elif native:
            saved = _session_file(data_dir, 'native-open', work_id)
            expected['seal_sha256'] = fixed.read_json(saved)['action']['seal_sha256']
        if not isinstance(payload, dict) or any(payload.get(k) != v for k, v in expected.items()):
            raise ValueError('trusted success receipt does not match work, attempt or image')
        if native:
            receipt = _retain_native_success(data_dir, expected, image_file, studio=studio)
        result = _call(runtime, data_dir, 'confirm', work_id, render_id, image_file,
                       '--attempt-id', attempt_id)
        if native:
            result.update(generation_id=render_id, receipt_path=str(receipt))
        return result


def _cli_studio(runtime):
    runtime = Path(runtime).resolve()
    sys.path.insert(0, str(runtime))
    module = importlib.import_module('studio')
    if Path(module.__file__).resolve() != runtime / 'studio.py':
        raise ValueError('studio module does not match the verified runtime')
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-compact', action='store_true',
                        help='emit only the selection prompt or the verified single signed button message')
    sub = parser.add_subparsers(dest='command', required=True)
    entry = sub.add_parser('start')
    entry.add_argument('--ledger', type=Path, required=True)
    entry.add_argument('--session', required=True)
    entry.add_argument('--persona-summary', required=True)
    entry.add_argument('--cache', type=Path)
    entry.add_argument('--sessions', type=Path)
    entry.add_argument('--memory-available', action='store_true')
    entry.add_argument('--candidate-count', type=int, default=10)
    entry.add_argument('--bookshelf', choices=('stable', 'golden', 'curated'), default='curated')
    entry.add_argument('--profile', type=Path)
    entry.add_argument('--this-time', action='append', default=[])
    entry.add_argument('--this-time-request', type=Path, action='append', default=[])
    settings = sub.add_parser('configure')
    settings.add_argument('--profile', type=Path, required=True)
    settings_source = settings.add_mutually_exclusive_group(required=True)
    settings_source.add_argument('--utterance')
    settings_source.add_argument('--request', type=Path)
    commands = {name: sub.add_parser(name) for name in
                ('production-prompt', 'prepare', 'verify-delivery', 'open', 'open-native',
                 'start-attempt', 'fail-attempt', 'confirm', 'panel')}
    for name, command in commands.items():
        command.add_argument('--runtime', type=Path, required=True)
        command.add_argument('--data', type=Path, required=True)
    prod = commands['production-prompt']
    prod.add_argument('selection', type=Path)
    prod.add_argument('persona', type=Path)
    prod.add_argument('work_id')
    prod.add_argument('--character-card', type=Path)
    prep = commands['prepare']
    prep.add_argument('job', type=Path)
    prep.add_argument('--character-card', type=Path)
    prep.add_argument('--render-profile', choices=[VISUAL_INTENT_PROFILE],
                      help='require this explicit profile in a new candidate Job')
    prep.add_argument('--session-store', action='store_true',
                      help='verify in this session; requires its state to persist across chat turns')
    verify = commands['verify-delivery']
    verify.add_argument('prepared', type=Path)
    verify.add_argument('--original', type=Path, required=True)
    verify.add_argument('--readback', type=Path, required=True)
    legacy = commands['open']
    legacy.add_argument('action', type=Path)
    legacy.add_argument('--readback', type=Path, required=True)
    native = commands['open-native']
    native.add_argument('action', type=Path, nargs='?')
    native.add_argument('--readback', type=Path)
    native.add_argument('--clicked-text', type=Path)
    native.add_argument('--relay-message', type=Path)
    native.add_argument('--button-command')
    for name in ('start-attempt', 'fail-attempt'):
        commands[name].add_argument('work_id')
        commands[name].add_argument('attempt_id')
    done = commands['confirm']
    done.add_argument('work_id')
    done.add_argument('render_id')
    done.add_argument('image', type=Path)
    done.add_argument('--attempt-id', required=True)
    done.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'start':
            result = start(args.ledger, args.session, args.persona_summary, cache=args.cache,
                           sessions=args.sessions, memory_available=args.memory_available,
                           candidate_count=args.candidate_count, bookshelf=args.bookshelf,
                           profile=args.profile,
                           overrides=([owner.parse_utterance(text) for text in args.this_time]
                                      + [fixed.read_json(path) for path in args.this_time_request]))
        elif args.command == 'configure':
            request = (owner.parse_utterance(args.utterance) if args.utterance is not None
                       else fixed.read_json(args.request))
            result = owner.configure(args.profile, request)
        else:
            runtime, data_dir = _guard_session(args.runtime, args.data)
            if args.command == 'production-prompt':
                result = production_prompt(runtime, data_dir, args.selection, args.persona, args.work_id, character_card=args.character_card)
            elif args.command == 'prepare':
                result = prepare(runtime, data_dir, args.job, character_card=args.character_card,
                                 expected_render_profile=args.render_profile, session_store=args.session_store)
            elif args.command == 'verify-delivery':
                prepared = fixed.read_json(args.prepared)
                if prepared.get('session_id') != data_dir.name:
                    raise ValueError('pending delivery does not belong to this P1.4 session')
                result = verify_delivery(prepared, studio=_cli_studio(runtime), original=args.original.read_bytes(), readback=args.readback.read_bytes(),
                                         data_dir=data_dir)
            elif args.command == 'open':
                result = open_seal(runtime, data_dir, fixed.read_json(args.action), args.readback.read_bytes(),
                                   studio=_cli_studio(runtime))
            elif args.command == 'open-native':
                files = (args.action, args.readback, args.clicked_text)
                studio = _cli_studio(runtime)
                if args.relay_message is not None and args.button_command is None and not any(files):
                    result = open_native_from_fulltext_relay(runtime, data_dir, args.relay_message.read_bytes().decode('utf-8'),
                                                             studio=studio)
                elif args.button_command is not None and args.relay_message is None and not any(files):
                    result = open_native_from_button(runtime, data_dir, args.button_command,
                                                     studio=studio)
                elif args.button_command is None and args.relay_message is None and all(files):
                    result = open_native(
                        runtime, data_dir, fixed.read_json(args.action), args.readback.read_bytes(),
                        clicked_text=args.clicked_text.read_bytes().decode('utf-8'),
                        studio=studio,
                    )
                else:
                    raise ValueError('supply a button command or the three original open files')
                if result['status'] == 'ready_to_submit':
                    result = {
                        'native_image_instruction': (
                            '同一封签已有出图记录时，只处理原图和原回执。'
                            '确认此前未出图后，在同一回合调用 ChatGPT 原生图片工具一次，按摄影正文新生成一张图。'
                            '工具可选操作时选择新建图像。画面内的照片、相纸、画作和屏幕是场景道具。'
                            '当 image_assets 为空时，本轮没有输入图片，直接从文字生成。'
                            '本次 render_request.text 是唯一的摄影正文，保留全部字符和换行。'
                            '有显式 prompt 字段时直接填入整个字符串。仅能使用上下文时，'
                            '以本次返回的完整原文作为生图输入，实际派发待核验。'
                            '禁止概括、润色、缩写、翻译或拼接摄影正文。'
                            '参考图只取 image_assets，空数组表示无参考图。'
                            '按工具协议使用 generation_options，签内 size 为 null 时采用默认画幅。'
                            '无法交付全文或沿用签内参数时，停止派发并报告。'
                            '图片工具真实成功后，用返回的生成 ID、原图 SHA-256 与本次 work_id、'
                            'attempt_id、seal_sha256 保存成功回执，立即执行 confirm。'
                            '生成结果或回执暂不可取得时保留待核实状态。'
                        ),
                        **result,
                    }
                elif result['status'] == 'awaiting_confirmation':
                    result['confirmation_instruction'] = '使用已保存回执和原图重试 confirm。'
            elif args.command in ('start-attempt', 'fail-attempt'):
                result = attempt(runtime, data_dir, args.work_id, args.attempt_id,
                                 failed=args.command == 'fail-attempt')
            else:
                result = confirm(runtime, data_dir, args.work_id, args.render_id, args.image,
                                 attempt_id=args.attempt_id, receipt=args.receipt)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            sys.stderr.write(error.stderr or '')
        parser.exit(2, f'{VERSION}: {error}\n')
    if args.host_compact:
        result = _compact_host_result(args.command, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
