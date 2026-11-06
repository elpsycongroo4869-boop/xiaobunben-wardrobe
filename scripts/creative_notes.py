"""Save a concise, source-bound design explanation before a photograph is generated."""
from copy import deepcopy
import hashlib
from html import escape
import json
from pathlib import Path

VERSION = '4.1'
REVISION = '4.1-story-first-creative-notes'
SCHEMA = 'wardrobe-creative-notes-v4.1'
SECTIONS = (
    ('story', '故事瞬间'),
    ('emotion_action', '情绪与动作'),
    ('outfit', '衣装设计'),
    ('camera', '摄影选择'),
    ('visible_clues', '画面线索'),
    ('review_focus', '看图时可以对照'),
)
ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def is_notes(draw):
    return draw.get('creative_notes_revision') == REVISION


def validate_notes(notes):
    if not isinstance(notes, dict) or set(notes) != {key for key, _ in SECTIONS}:
        raise ValueError('4.1 creative_notes needs the six public design-explanation sections')
    for key, _ in SECTIONS:
        value = notes[key]
        if not isinstance(value, str) or value != value.strip() or not 8 <= len(value) <= 500:
            raise ValueError('creative_notes.' + key + ' needs 8..500 characters of concise design explanation')
    return deepcopy(notes)


def mark_notes(draw, brief):
    notes = validate_notes(brief.get('creative_notes'))
    draw.update(version=VERSION, wardrobe_version=VERSION, art_direction_revision=REVISION,
                story_first_revision=REVISION, creative_notes_revision=REVISION,
                creative_notes=notes)


def build_record(draw, photo, fields):
    if not is_notes(draw) or draw.get('wardrobe_version') != VERSION:
        raise ValueError('This photograph has no saved 4.1 design explanation')
    if photo['draw_id'] != draw['draw_id']:
        raise ValueError('Creative notes belong to another photograph')
    snapshot = {
        'story_plan': draw['story_plan'], 'emotion_tone': draw['emotion_tone'],
        'camera_plan': draw['camera_plan'], 'costume_plan': draw['costume_plan'],
        'visual_fields': fields,
    }
    return {
        'schema': SCHEMA, 'version': VERSION, 'source_draw_id': draw['draw_id'],
        'source_photo_message_sha256': photo['message_sha256'],
        'source_snapshot_sha256': sha(canonical(snapshot)),
        'source_snapshot': deepcopy(snapshot),
        'sections': validate_notes(draw.get('creative_notes')),
        'written_stage': 'before_image_generation',
        'content_kind': 'public_design_explanation',
        'image_observed': False,
        'button_label': '创作思路', 'initially_collapsed': True,
        'placement': 'alongside_draw_button_with_optional_post_image_redisplay',
    }


def markdown(record):
    parts = ['# 本次创作思路', '拍摄前保存的设计说明，可与成片对照。']
    for key, label in SECTIONS:
        parts.extend(['## ' + label, record['sections'][key]])
    return '\n\n'.join(parts) + '\n'


def fragment(record):
    template = (ROOT / 'assets/creative-notes-button.html').read_text('utf-8')
    root_id = 'wardrobe-notes-' + sha(record['source_draw_id'].encode('utf-8'))[:20]
    sections = '\n'.join('<div><dt>' + escape(label) + '</dt><dd>' +
                         escape(record['sections'][key]) + '</dd></div>'
                         for key, label in SECTIONS)
    return template.replace('__ROOT_ID__', root_id).replace('__SECTIONS__', sections)


def write_bundle(pending, draw, photo, fields):
    pending = Path(pending)
    record = build_record(draw, photo, fields)
    (pending / 'creative-notes.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (pending / 'creative-notes.md').write_text(markdown(record), encoding='utf-8')
    (pending / 'creative-notes-button.html').write_text(fragment(record), encoding='utf-8')
    return record


def button_contract(draw, photo, fields):
    record = build_record(draw, photo, fields)
    return {
        'button_label': '创作思路', 'action': 'local_reveal',
        'source_draw_id': draw['draw_id'],
        'record_sha256': sha(canonical(record)),
        'record_file': 'creative-notes.json',
        'button_fragment': 'creative-notes-button.html',
        'initially_collapsed': True, 'written_before_image_generation': True,
        'post_image_callback_available': False,
    }


def verify_bundle(pending):
    # Verify the sealed source first; never reconstruct a lost explanation from an image.
    from photo_creation_relay import verify_from_pending
    pending = Path(pending)
    photo = verify_from_pending(pending)
    draw = json.loads((pending / 'draw.json').read_text('utf-8'))
    fields = json.loads((pending / 'english-details.json').read_text('utf-8'))['fields']
    expected = build_record(draw, photo, fields)
    actual = json.loads((pending / 'creative-notes.json').read_text('utf-8'))
    if canonical(actual) != canonical(expected):
        raise ValueError('Saved creative notes or their source binding changed')
    for name, content in (('creative-notes.md', markdown(expected)),
                          ('creative-notes-button.html', fragment(expected))):
        if (pending / name).read_text('utf-8') != content:
            raise ValueError('Creative notes presentation changed: ' + name)
    return expected
