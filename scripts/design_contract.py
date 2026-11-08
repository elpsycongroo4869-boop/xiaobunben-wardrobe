"""Shared story, camera, wardrobe and creative-note validation.

The limits and anchors originated in v4.4. The calling protocol supplies the
role styling key and decides whether clothing is visible in the photograph.
"""
from copy import deepcopy
import re

FRAME_EXTENTS = {'close', 'waist', 'mid_thigh', 'knee', 'full'}
EXTENDED_SECTION_MAX = 650
EXTENDED_TOTAL_MAX = 3150
COSTUME_FIELDS = ('context_and_climate', 'role_foundation', 'material_anchors',
                  'construction_anchors')
MATERIALS = ('linen','cotton','silk','velvet','satin','brocade','leather','suede','wool',
             'fur','denim','nylon','polyester','canvas','steel','metal','chainmail',
             'chiffon','organza','lace','latex','neoprene','rubber','tweed','knit')
SECTIONS = (
    ('story', '故事瞬间'),
    ('emotion_action', '情绪与动作'),
    ('outfit', '衣装设计'),
    ('camera', '摄影选择'),
    ('visible_clues', '画面线索'),
    ('review_focus', '看图时可以对照'),
)


def visual_text(value, name, minimum, maximum):
    if not isinstance(value, str) or value != value.strip() or not minimum <= len(value) <= maximum:
        raise ValueError(f'{name} needs {minimum}..{maximum} characters of specific English prose')
    if sum('\u3400' <= c <= '\u9fff' for c in value) > 2:
        raise ValueError(name + ' needs English visual wording')
    return value


def validate_plans(story, camera):
    if not isinstance(story, dict):
        raise ValueError('4.0 begins with story_plan, before identity and clothing')
    visual_text(story.get('moment'), 'story_plan.moment', 40, 200)
    visual_text(story.get('meaning'), 'story_plan.meaning', 25, 220)
    if not isinstance(camera, dict):
        raise ValueError('4.0 needs a fresh camera_plan for this story')
    visual_text(camera.get('viewpoint'), 'camera_plan.viewpoint', 20, 145)
    visual_text(camera.get('optics'), 'camera_plan.optics', 12, 150)
    visual_text(camera.get('reason'), 'camera_plan.reason', 25, 220)
    if camera.get('frame_extent') not in FRAME_EXTENTS:
        raise ValueError('camera_plan.frame_extent needs close/waist/mid_thigh/knee/full')


def validate_notes(notes, *, extended=False):
    if not isinstance(notes, dict) or set(notes) != {key for key, _ in SECTIONS}:
        raise ValueError('4.x creative_notes needs the six public design-explanation sections')
    ceiling = EXTENDED_SECTION_MAX if extended else 500
    for key, _ in SECTIONS:
        value = notes[key]
        if not isinstance(value, str) or value != value.strip() or not 8 <= len(value) <= ceiling:
            raise ValueError(f'creative_notes.{key} needs 8..{ceiling} characters of design explanation')
    if extended and sum(len(notes[key]) for key, _ in SECTIONS) > EXTENDED_TOTAL_MAX:
        raise ValueError('4.4 r3 creative_notes combined maximum is 3150 characters (old 3000 + 150)')
    return deepcopy(notes)


def validate_costume_plan(plan, wardrobe, styling_field, *, visible=True):
    """Check explicit decisions and delivery fidelity, not artistic correctness."""
    required = (*COSTUME_FIELDS, styling_field)
    if not isinstance(plan, dict) or any(key not in plan for key in required):
        raise ValueError('Role-first design requires costume_plan: ' + ', '.join(required))
    if not isinstance(wardrobe, str):
        raise ValueError('Role-first wardrobe needs concrete English clothing')
    for key, minimum, maximum in (
            ('context_and_climate', 12, 220),
            ('role_foundation', 24, 300),
            (styling_field, 20, 260)):
        value = plan[key]
        if (not isinstance(value, str) or value != value.strip()
                or not minimum <= len(value) <= maximum):
            raise ValueError(f'costume_plan.{key} needs {minimum}..{maximum} characters')
        if sum('\u3400' <= c <= '\u9fff' for c in value) > 2:
            raise ValueError('Costume plan needs English visual wording: ' + key)
    for key in ('material_anchors', 'construction_anchors'):
        anchors = plan[key]
        if not isinstance(anchors, list) or not int(visible) <= len(anchors) <= 5:
            raise ValueError('costume_plan.' + key + f' needs {int(visible)}..5 chosen visible anchors')
        for anchor in anchors:
            if (not isinstance(anchor, str) or anchor != anchor.strip()
                    or not 2 <= len(anchor) <= 80 or '\n' in anchor):
                raise ValueError('Invalid visible costume anchor: ' + key)
            if anchor.casefold() not in wardrobe.casefold():
                raise ValueError('Selected role material/construction missing from wardrobe: ' + anchor)
    return deepcopy(plan)


def validate_texture(wardrobe, texture):
    """Catch familiar fabric substitutions without creating a material whitelist."""
    for material in MATERIALS:
        pattern = r'(?<![a-z])' + re.escape(material) + r'(?![a-z])'
        if re.search(pattern, texture, re.I) and not re.search(pattern, wardrobe, re.I):
            raise ValueError('Camera texture introduces a material absent from outfit: ' + material)


def validate_physics(note):
    if not isinstance(note, str) or not 50 <= len(note) <= 170 or note != note.strip():
        raise ValueError('action_physics needs 50..170 characters of precise English body mechanics')
    low = note.lower()
    joints=('hand','finger','wrist','elbow','arm','shoulder','torso','hip','knee','foot','feet','leg')
    contacts=('hold','grip','rest','touch','press','pin','support','steady','bend','plant','brace','release','reach','balance','place','turn','shift')
    if not any(s in low for s in joints) or not any(s in low for s in contacts):
        raise ValueError('action_physics must specify joints, physical supports and real contact/movement')
    if sum('\u3400'<=c<='\u9fff' for c in note)>2:
        raise ValueError('action_physics needs English wording')
    return note
