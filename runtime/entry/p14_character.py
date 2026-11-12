"""P1.4.2 character director: authored text identity + sealed generation input contract.

This is an outer-host adapter; the original five-role R2 compiler is unchanged.
The sixth role lives in job['role_director'], which R2 signs with the entire job.
No runtime image lookup or implicit assets: inputs are taken from the character card.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

CARD_SCHEMA = 'wardrobe2-character-card-v1'
DIRECTOR_SCHEMA = 'wardrobe2-character-director-v1'
RENDER_SCHEMA = 'wardrobe2-generation-contract-v1'
KEY = re.compile(r'^[a-zA-Z0-9_-]{1,96}$')


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(canon(value)).hexdigest()


def _str(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 5000:
        raise ValueError('invalid character field: '+name)
    return value.strip()


def card_from_file(path):
    card = json.loads(Path(path).read_text(encoding='utf-8'))
    return validate_card(card)


def validate_card(card):
    if not isinstance(card, dict) or card.get('schema') != CARD_SCHEMA:
        raise ValueError('invalid character card schema')
    if not isinstance(card.get('character_key'), str) or not KEY.fullmatch(card['character_key']):
        raise ValueError('invalid character key')
    if card.get('identity_source') != 'text_profile':
        raise ValueError('this character adapter requires an explicit text identity source')
    if card.get('adult') is not True:
        raise ValueError('current character engine requires an adult character')
    for name in ('identity','appearance','continuity','display_name'):
        _str(card.get(name), name)
    for name in ('stable_traits','flexible_traits'):
        items = card.get(name)
        if not isinstance(items, list) or len(items) > 30 or not all(isinstance(v, str) and v.strip() for v in items):
            raise ValueError('invalid '+name)
    inputs = card.get('generation_inputs')
    if not isinstance(inputs, dict) or set(inputs) != {'image_assets'}:
        raise ValueError('generation_inputs must declare exact image_assets')
    assets = inputs['image_assets']
    if not isinstance(assets, list) or len(assets) > 3 or not all(isinstance(x, str) and x for x in assets):
        raise ValueError('invalid image asset list')
    if len(set(assets)) != len(assets):
        raise ValueError('duplicate image assets')
    if card.get('notes') is not None and not isinstance(card['notes'], str):
        raise ValueError('invalid notes')
    return deepcopy(card)


def director_from_card(card, story_fit):
    card = validate_card(card)
    return {
        'schema': DIRECTOR_SCHEMA,
        'character_key': card['character_key'],
        'identity_source': card['identity_source'],
        'identity': card['identity'],
        'appearance': card['appearance'],
        'continuity': card['continuity'],
        'stable_traits': card['stable_traits'],
        'flexible_traits': card['flexible_traits'],
        'story_fit': _str(story_fit,'story_fit'),
        'card_sha256': sha(card),
    }


def render_contract_from_card(card):
    card = validate_card(card)
    return {
        'schema': RENDER_SCHEMA,
        'prompt_source': 'work.render_instruction',
        'image_assets': deepcopy(card['generation_inputs']['image_assets']),
        'generation_options': {'size': None, 'transparent_background': False},
        'character_card_sha256': sha(card),
    }


def validate_director_job(job, card):
    """Enforce the approved text identity before sealing."""
    card = validate_card(card)
    result = deepcopy(job)
    role = result.get('role_director')
    if not isinstance(role, dict) or not isinstance(role.get('story_fit'), str):
        raise ValueError('character director story_fit is required in authored job')
    expected = director_from_card(card, role['story_fit'])
    if role != expected:
        raise ValueError('authored character director differs from approved character card')
    persona = result.get('persona')
    if not isinstance(persona, dict):
        raise ValueError('job persona missing')
    if persona.get('adult') is not True:
        raise ValueError('character must be adult')
    # The producer may author story_role, but stable identity comes from this card.
    persona['identity'] = card['identity']
    persona['appearance'] = card['appearance']
    persona['identity_continuity'] = card['continuity']
    expected_render = render_contract_from_card(card)
    if result.get('render_contract') != expected_render:
        raise ValueError('authored render contract differs from character card')
    return result


def signed_render_request(envelope):
    """Derive the *entire* requested model input from the R2 signed work."""
    work = envelope['work']
    job = work['job']
    director = job.get('role_director')
    contract = job.get('render_contract')
    if not isinstance(director, dict) or director.get('schema') != DIRECTOR_SCHEMA:
        return None  # Compatibility with pre-1.4.2 sealed work.
    if not isinstance(contract, dict) or contract.get('schema') != RENDER_SCHEMA:
        raise ValueError('signed work is missing its render contract')
    if (contract.get('prompt_source') != 'work.render_instruction' or
        contract.get('character_card_sha256') != director.get('card_sha256')):
        raise ValueError('signed render contract conflicts with character director')
    options = contract.get('generation_options')
    if options != {'size': None, 'transparent_background': False}:
        raise ValueError('invalid signed generation options for current P1.4.2 host')
    ids = contract.get('image_assets')
    if (not isinstance(ids, list) or len(ids) > 3 or
        not all(isinstance(x, str) and x for x in ids) or len(set(ids)) != len(ids)):
        raise ValueError('invalid signed image asset list')
    return {'schema': RENDER_SCHEMA,
            'text': work['render_instruction'],
            'image_assets': ids,
            'generation_options': deepcopy(options),
            'character_key': director['character_key'],
            'character_card_sha256': director['card_sha256'],
            'work_id': job['work_id'],
            'seal_sha256': envelope['seal_sha256']}


def verify_dispatch(sealed_request, submitted_request):
    """Pure host-side gate: reject changed prompt, altered or appended image inputs."""
    if not isinstance(sealed_request, dict) or not isinstance(submitted_request, dict):
        raise ValueError('generation request missing')
    if sealed_request.get('schema') != RENDER_SCHEMA:
        raise ValueError('not a P1.4.2 signed request')
    # This is deliberately an allowlist, not a negative prompt about reference images.
    expected = {'text': sealed_request['text'],
                'image_assets': sealed_request['image_assets'],
                'generation_options': sealed_request['generation_options']}
    if submitted_request != expected:
        raise ValueError('generation inputs do not match the signed request')
    return True
