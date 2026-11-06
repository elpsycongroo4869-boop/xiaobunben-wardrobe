"""Story-led art direction and deliberate camera choices for fictional adult photographs."""

from copy import deepcopy
import re

VERSION = '4.0'
REVISION = '4.0-story-first'
SUPPORTED_REVISIONS = {REVISION: VERSION, '4.1-story-first-creative-notes': '4.1'}
FRAME_EXTENTS = {'close', 'waist', 'mid_thigh', 'knee', 'full'}
OUTFIT_NOTE = 'Express her personality and feminine allure through this redesigned outfit, preserving its chosen materials and signature structure.'


def is_story_first(draw):
    return draw.get('story_first_revision') in SUPPORTED_REVISIONS


def _text(value, name, minimum, maximum):
    if not isinstance(value, str) or value != value.strip() or not minimum <= len(value) <= maximum:
        raise ValueError(f'{name} needs {minimum}..{maximum} characters of specific English prose')
    if sum('\u3400' <= c <= '\u9fff' for c in value) > 2:
        raise ValueError(name + ' needs English visual wording')
    return value


def validate_plans(story, camera):
    if not isinstance(story, dict):
        raise ValueError('4.0 begins with story_plan, before identity and clothing')
    _text(story.get('moment'), 'story_plan.moment', 40, 200)
    _text(story.get('meaning'), 'story_plan.meaning', 25, 220)
    if not isinstance(camera, dict):
        raise ValueError('4.0 needs a fresh camera_plan for this story')
    _text(camera.get('viewpoint'), 'camera_plan.viewpoint', 20, 145)
    _text(camera.get('optics'), 'camera_plan.optics', 12, 150)
    _text(camera.get('reason'), 'camera_plan.reason', 25, 220)
    if camera.get('frame_extent') not in FRAME_EXTENTS:
        raise ValueError('camera_plan.frame_extent needs close/waist/mid_thigh/knee/full')


def prepare_brief(brief):
    """Resolve the selected story and camera into legacy source slots without defaults."""
    brief = deepcopy(brief)
    story, camera = brief.get('story_plan'), brief.get('camera_plan')
    validate_plans(story, camera)
    choice = brief.get('choice')
    if not isinstance(choice, dict):
        raise ValueError('4.0 needs choice and scene_design after the story plan')
    resolved = {'moment': story['moment'], 'moment_english': story['moment'],
                'shot': camera['viewpoint'], 'shot_english': camera['viewpoint'],
                'frame_extent': camera['frame_extent'], 'frame_intent': camera['reason']}
    for key, value in resolved.items():
        if key in choice and choice[key] != value:
            raise ValueError('4.0 story/camera conflicts with choice.' + key)
        choice[key] = value
    style = choice.get('camera_style')
    if not isinstance(style, dict) or choice.get('camera_pack_id') is not None:
        raise ValueError('Write this shoot in camera_style; existing packs may inspire it, without a preset viewpoint or lens')
    if 'optics' in style and style['optics'] != camera['optics']:
        raise ValueError('camera_style.optics conflicts with the selected camera_plan')
    style['optics'] = camera['optics']
    return brief


def mark_story(draw, brief):
    validate_plans(brief['story_plan'], brief['camera_plan'])
    draw.update(delivery_version=draw.get('delivery_version', draw['version']),
                version=VERSION, wardrobe_version=VERSION, art_direction_revision=REVISION,
                story_first_revision=REVISION, story_first=True,
                story_plan=deepcopy(brief['story_plan']), camera_plan=deepcopy(brief['camera_plan']),
                costume_styling_note=OUTFIT_NOTE,
                hosiery_style_hint='active_outfit_design_free_choice')


def validate_draw(draw):
    story, camera = draw.get('story_plan'), draw.get('camera_plan')
    validate_plans(story, camera)
    version = SUPPORTED_REVISIONS.get(draw.get('story_first_revision'))
    if not version or draw.get('version') != version or draw.get('wardrobe_version') != version:
        raise ValueError('4.0 needs the current story-first version snapshot')
    if draw.get('story_moment_english') != story['moment'] or draw.get('story_moment') != story['moment']:
        raise ValueError('The selected story moment changed after the creative decision')
    if draw.get('shot_description') != camera['viewpoint'] or draw.get('suggested_camera') != camera['viewpoint']:
        raise ValueError('The selected viewpoint changed after the creative decision')
    if draw.get('frame_extent') != camera['frame_extent'] or draw.get('frame_intent') != camera['reason']:
        raise ValueError('The selected crop or its story motivation changed')
    if draw.get('camera_pack', {}).get('optics') != camera['optics']:
        raise ValueError('The delivered optics differ from the selected story camera')


def validate_message(draw, message):
    validate_draw(draw)
    for value in (draw['story_plan']['moment'], draw['camera_plan']['viewpoint'], draw['camera_plan']['optics']):
        if value not in message:
            raise ValueError('Story moment, viewpoint and optics must reach the actual image message intact')


def hosiery_selected(wardrobe):
    """Describe an artist's actual choice; never select hosiery or alter the camera."""
    return bool(re.search(r'(?<![a-z])(tights|stockings|pantyhose|hosiery|thigh-highs)(?![a-z])', wardrobe, re.I))


def metadata(draw):
    if not is_story_first(draw):
        return {}
    keys = ('wardrobe_version', 'art_direction_revision', 'story_first_revision',
            'story_first', 'story_plan', 'camera_plan')
    return {key: deepcopy(draw[key]) for key in keys}
