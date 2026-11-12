"""Verified sealed content -> native ChatGPT UI data. No HTML or UI files.

The host controls native expansion buttons and the actual Open click. This module
is read-only: it neither re-authors the creative job nor mutates the seal or CD.
"""
from __future__ import annotations
from studio import MANDATORY as ROLE_FIELDS, PRODUCER_FIELDS, role_fields

CHAT_SCHEMA = 'wardrobe2-p13-native-chat-v1'


def native_chat_payload(studio, work_id: str, *, expected_seal: str) -> dict:
    # _get verifies canonical SHA and the work_id before exposing any content.
    _,envelope=studio._get(work_id)
    if envelope['seal_sha256'] != expected_seal:
        raise ValueError('seal does not match requested SHA-256')
    if envelope['state'] not in ('ready','opened','rendered'):
        raise ValueError('work is not available for native preview')
    work=envelope['work']
    job=work['job']
    producer=job['producer']
    roles=job['roles']
    # Enforce the COMPLETE fields, not a generated summary of them.
    for field in PRODUCER_FIELDS:
        if not isinstance(producer.get(field),str) or not producer[field].strip():
            raise ValueError('missing producer field: '+field)
    preview_roles = {}
    for key in ROLE_FIELDS:
        fields = role_fields(job, key)
        for field in fields:
            if not isinstance(roles[key].get(field),str) or not roles[key][field].strip():
                raise ValueError('missing role field: '+key+'.'+field)
        preview_roles[key] = {field: roles[key][field] for field in fields}
    preview = {
        'producer': {k: producer[k] for k in PRODUCER_FIELDS},
        'roles': preview_roles,
        'render_instruction': work['render_instruction'],
    }
    if 'chapter' in job:
        preview['chapter'] = job['chapter']
    return {
        'schema':CHAT_SCHEMA, 'work_id':work_id, 'seal_sha256':expected_seal,
        'state':envelope['state'],
        'preview':preview,
        'native_ui':{
            'show_open_button':envelope['state']=='ready',
            'spoilers_collapsed_by_default':True,
            'show_full_text_inside_chat':True,
            'generate_html':False,
            'show_separate_photo_after_image_tool':False,
            'ask_for_rating_after_photo':False,
            'create_acceptance_notes':False,
        },
    }
