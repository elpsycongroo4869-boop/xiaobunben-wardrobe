"""Compile one reviewed v4.5 photograph from its world and the selected frame.

This module has no file, network, rendering or image-generation side effects.
"""

import hashlib
import json

from creative_audit import validate_audit
from design_contract import (
    COSTUME_FIELDS, validate_costume_plan, validate_notes, validate_physics, validate_plans,
    validate_texture, visual_text,
)
from emotion_consistency import REVISION as EMOTION_REVISION, validate_message, validate_review
from photographer_selection_v44 import selected
from role_profile import validate_profile
from wardrobe_version import LEGACY_CAMERA_VERSIONS, LEGACY_OUTFIT_VERSIONS, OBSERVATION_SCHEMA, VERSION
from world_cards import cited_ids

QUALITY = '杰作，顶级品质，超高清8K照片级写实艺术摄影，电影般质感，绝佳的光影效果。'
INTRO = QUALITY + '\n((请创建一张照片))\nCreate ONE NEW photorealistic photograph, not an edit.'
CROPS = {'close': 'close-up', 'waist': 'waist-up', 'mid_thigh': 'mid-thigh',
         'knee': 'knee-up', 'full': 'full-length or environmental'}
IDENTITY_VISIBILITY = {'face', 'build', 'face_and_build', 'none'}
SCENE_LIMITS = {'subject': 170, 'setting': 245, 'action': 270, 'cue1': 220,
                'cue2': 220, 'wardrobe': 280, 'composition': 70}
CAMERA_LIMITS = {'medium': 85, 'lighting': 230, 'palette': 110, 'texture': 150, 'framing': 140}
WRITING = 'Any writing belongs naturally to this scene. No poster title or watermark.'
FRAME_POLICY = 'Keep the chosen observational crop and credible perspective.'
RED_FLAGS = (
    'edit this image', 'edit the photo', 'modify the photo', 'retouch the photo',
    'use the provided image', 'change the existing picture', 'same photo as before',
    'replace the background of the image',
)
BRIEF_SECTIONS = {
    'story_plan', 'camera_plan', 'choice', 'scene_design', 'emotion_review',
    'creative_notes', 'creative_audit', 'complete_world', 'photographer_selection',
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _shape(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{name} needs these fields: ' + ', '.join(sorted(keys)))
    return value


def _visual(value, name, minimum, maximum):
    text = visual_text(value, name, minimum, maximum)
    if '\n' in text or '\r' in text:
        raise ValueError(name + ' must be single-line text')
    return text


def compile_story(brief, profile, cards, draw_id, *, version=VERSION):
    """Normalize aliases for v4.4 validators, then deliver only the selected photograph."""
    validate_profile(profile)
    _shape(brief, BRIEF_SECTIONS, 'creative brief')
    choice = _shape(brief['choice'], ('world', 'role', 'camera_style', 'costume_plan'), 'choice')
    story = _shape(brief['story_plan'], ('moment', 'meaning'), 'story_plan')
    legacy_camera = version in LEGACY_CAMERA_VERSIONS
    legacy_outfit = version in LEGACY_OUTFIT_VERSIONS
    camera_fields = ('viewpoint', 'optics', 'frame_extent', 'reason')
    if not legacy_camera:
        camera_fields += ('subject_distance_m',)
    camera = _shape(brief['camera_plan'], camera_fields, 'camera_plan')
    scene = _shape(brief['scene_design'], (*SCENE_LIMITS, 'action_physics'), 'scene_design')
    style = _shape(choice['camera_style'], CAMERA_LIMITS, 'choice.camera_style')
    world = _shape(brief['complete_world'], ('full_wardrobe', 'full_action', 'offscreen_context'), 'complete_world')
    shot = _shape(brief['photographer_selection'],
                  ('intentionally_unshown', 'offscreen_not_requested', 'identity_visibility'),
                  'photographer_selection')

    validate_plans(story, camera)
    viewpoint = camera['viewpoint']
    framing = style['framing']
    crop = CROPS[camera['frame_extent']]
    if not legacy_camera:
        distance = camera['subject_distance_m']
        if type(distance) not in (int, float) or not 0 < distance < float('inf'):
            raise ValueError('camera_plan.subject_distance_m needs a finite positive number in meters')
        viewpoint = f"{viewpoint.removesuffix('.')}. About {distance} m from the subject"
        framing = f'{crop.capitalize()} framing. {framing}'
    for key, maximum in SCENE_LIMITS.items():
        minimum = 0 if key == 'wardrobe' and (not legacy_outfit or scene[key] == '') else 22
        _visual(scene[key], 'scene_design.' + key, minimum, maximum)
    for key, maximum in CAMERA_LIMITS.items():
        _visual(style[key], 'choice.camera_style.' + key, 8, maximum)
    _visual(choice['world'], 'choice.world', 12, 220)
    _visual(choice['role'], 'choice.role', 3, 80)
    physics = validate_physics(scene['action_physics'])

    costume = choice['costume_plan']
    detail = ''
    if not legacy_outfit:
        _shape(costume, (*COSTUME_FIELDS, 'style_adaptation', 'visible_style_detail'),
               'choice.costume_plan')
        detail = costume['visible_style_detail']
        _visual(detail, 'costume_plan.visible_style_detail', 0 if detail == '' else 20, 150)
        if detail:
            detail = detail.removesuffix('.')
            if detail.casefold() in scene['wardrobe'].casefold():
                raise ValueError('Write the selected visible styling only once, in visible_style_detail')
            wardrobe = ' '.join(part for part in (detail + '.', scene['wardrobe']) if part)
            scene = {**scene, 'wardrobe': wardrobe}
        _visual(scene['wardrobe'], 'compiled visible wardrobe',
                22 if scene['wardrobe'] else 0, SCENE_LIMITS['wardrobe'])

    plan = validate_costume_plan(costume, scene['wardrobe'], 'style_adaptation',
                                 visible=bool(scene['wardrobe']))
    adaptation = plan['style_adaptation'].casefold()
    if detail and not any(anchor.casefold() in detail.casefold() and anchor.casefold() in adaptation
                          for anchor in plan['construction_anchors']):
        raise ValueError('visible_style_detail needs a construction anchor from style_adaptation')
    # Texture may be the texture of a prop or surrounding set. The wardrobe
    # anchors above bind the actual visible garment, including when it is absent.
    if scene['wardrobe']:
        validate_texture(scene['wardrobe'], style['texture'])
    if shot['identity_visibility'] not in IDENTITY_VISIBILITY:
        raise ValueError('Choose face, build, face_and_build or none for the visible identity details')

    review = brief['emotion_review']
    _shape(review, ('final_tone', 'visible_expression', 'review_note'), 'emotion_review')
    _visual(review['final_tone'], 'emotion_review.final_tone', 22, 120)
    _visual(review['visible_expression'], 'emotion_review.visible_expression', 22, 130)
    visible_scene = {**scene, 'expression': review['visible_expression']}
    normalized = {
        **brief, 'scene_design': visible_scene,
        'choice': {**choice, 'emotion_tone': review['final_tone']},
        'photographer_selection': {
            **shot, 'why_this_frame': camera['reason'],
            'delivered_wardrobe': scene['wardrobe'], 'delivered_action': scene['action'],
        },
    }
    selection = selected(normalized, schema=OBSERVATION_SCHEMA)
    if not legacy_outfit and scene['wardrobe'] and not detail:
        if not any(phrase.casefold() in adaptation for phrase in shot['offscreen_not_requested']):
            raise ValueError('Choose a visible_style_detail or record which style adaptation is out of frame')
    review = validate_review(review, normalized)
    notes = validate_notes(brief['creative_notes'], extended=True)
    if set(cards) != cited_ids(brief['creative_audit']):
        raise ValueError('Cited world cards disagree with the frozen card references')
    for key, value in cards.items():
        if not isinstance(value, dict) or value.get('id') != key:
            raise ValueError('Cited card ID differs from its source')
    audit = validate_audit(brief['creative_audit'], known_ids=cards.keys())

    # All 21 v4.4 source dimensions remain represented. The legacy
    # feminine_presence slot is named visible_expression in the new schema.
    character = f"{profile['identity']}, adult age {profile['age']}. {profile['appearance']}"
    fields = {
        'world_and_role': scene['subject'],
        'environment': scene['setting'],
        'work_action': scene['action'],
        'career_evidence_1': scene['cue1'],
        'career_evidence_2': scene['cue2'],
        'character_identity': character,
        'body_proportions': profile['build'],
        'outfit_and_function': scene['wardrobe'],
        'outfit_design_mode': plan['style_adaptation'],
        'shot_and_distance': viewpoint,
        'story_moment': story['moment'],
        'camera_medium': style['medium'],
        'camera_lens': camera['optics'],
        'lighting': style['lighting'],
        'color': style['palette'],
        'texture_depth': style['texture'],
        'framing': framing,
        'intensity': 'Use believable contrast and natural material response to make the selected story action legible.',
        'composition': scene['composition'],
        'in_world_writing': WRITING,
        'visible_expression': review['visible_expression'],
    }
    identity = shot['identity_visibility']
    visible_identity = []
    if identity in ('face', 'face_and_build'):
        visible_identity.append(character)
    if identity in ('build', 'face_and_build'):
        visible_identity.append(profile['build'])
    paragraphs = [INTRO, 'Story moment: ' + story['moment']]
    if visible_identity:
        paragraphs.append('Character: ' + ' '.join(visible_identity))
    paragraphs.extend((
        'Scene: ' + scene['subject'] + ' ' + scene['setting'],
        'Emotional tone: ' + review['final_tone'],
        'Action: ' + scene['action'],
        'Expression: ' + review['visible_expression'],
        'Clues: ' + scene['cue1'] + ' ' + scene['cue2'],
        'Body mechanics: ' + physics,
    ))
    if scene['wardrobe']:
        paragraphs.append('Outfit: ' + scene['wardrobe'])
    camera_details = [style['medium'], viewpoint, camera['optics'], style['lighting'],
                      style['palette'], style['texture']]
    if legacy_camera:
        # Older seals must recompile to their original text, including this label.
        camera_details.append('knee-level' if camera['frame_extent'] == 'knee' else crop)
    paragraphs.extend((
        'Camera: ' + '; '.join(camera_details) + '.',
        'Frame: ' + scene['composition'] + ' ' + framing + ' ' + FRAME_POLICY + ' ' + WRITING,
    ))
    message = '\n\n'.join(paragraphs)
    folded = message.casefold()
    if any(flag in folded for flag in RED_FLAGS) or message.count(QUALITY) != 1:
        raise ValueError('The photograph needs a single creation preamble and new-image language')
    for phrase in shot['offscreen_not_requested']:
        if phrase.casefold() in folded:
            raise ValueError('A detail excluded by the photographer leaked into the image: ' + phrase)
    validate_message({'emotion_review_revision': EMOTION_REVISION, 'emotion_review': review}, message)

    # The comparison text is a stable expansion of the actual 21 dimensions and
    # the full world, story rationale, observed action, review and camera logic.
    # It contains no repeated padding or filler to force a percentage.
    full = '\n\n'.join([
        INTRO, *(f"{key.replace('_', ' ')}: {value}" for key, value in fields.items()),
        'World and role: ' + choice['world'] + ' / ' + choice['role'],
        'Story meaning: ' + story['meaning'],
        'World wardrobe: ' + world['full_wardrobe'],
        'World action: ' + world['full_action'],
        'World offscreen context: ' + world['offscreen_context'],
        'Clothing conditions: ' + plan['context_and_climate'],
        'Clothing foundation: ' + plan['role_foundation'],
        'Body mechanics: ' + physics,
        'Emotional tone: ' + review['final_tone'],
        'Editorial review: ' + review['review_note'],
        'Camera rationale: ' + camera['reason'],
        'Out of frame: ' + shot['intentionally_unshown'],
    ])
    target = min(2500, len(full) * 7 // 10)
    if not 1100 <= len(message) <= target:
        raise ValueError(f'Photograph has {len(message)} characters. Use 1100–{target} from the {len(full)}-character full design; refine wording without dropping story evidence.')
    draw = {
        'draw_id': draw_id, 'version': version, 'wardrobe_version': version,
        'art_direction_revision': '4.5-story-first-observer-reviewed',
        'status': 'prepared_not_clicked', 'decision_owner': 'creator',
        'story_plan': story, 'camera_plan': camera, 'costume_plan': plan,
        'emotion_review': review, 'creative_notes': notes, 'creative_audit': audit,
        'role_profile_sha256': sha(canonical(profile)),
        'photographer_selection_schema': OBSERVATION_SCHEMA,
        'photographer_selection_sha256': sha(canonical(selection)),
        'visual_fields_sha256': sha(canonical(fields)),
        'source_character_count': len(full), 'message_character_count': len(message),
        'message_sha256': sha(message.encode('utf-8')),
    }
    return draw, selection, fields, message
