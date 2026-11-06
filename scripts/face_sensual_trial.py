"""Fictional adult character face and redesigned role clothing, without personal records."""

from copy import deepcopy

REVISION = '3.5.3-face-sensual-trial'
FACE_ZH = '20岁成年女性，精致东亚混血脸型，拥有自然且极具辨识度的高颜值；脸型小巧精致、轮廓流畅，五官漂亮但不过分锐利；高鼻梁、饱满卧蚕、尖下巴、薄唇。'
FACE_EN = ('Adult woman, age 20, with naturally striking, highly distinctive beauty and a petite, '
           'refined East Asian mixed-heritage face; smooth contours and beautiful features without '
           'overly sharp angles; high nasal bridge, softly full lower-eyelid rolls just beneath the lashes, '
           'pointed chin and thin lips.')
OUTFIT_NOTE = 'Emphasize this explicitly redesigned, sexy feminine version of the role costume.'
FACE_SOURCE_NOTE = 'Use the provisional adult facial specification in Character for this new photo.'
DELIVERY_STYLE_REVISION = 'quality-prefix-text-face-v1'
QUALITY_PREFIX_V1 = '杰作，顶级品质，超高清8K照片级写实艺术摄影，电影般质感。'
QUALITY_PREFIX = '杰作，顶级品质，超高清8K照片级写实艺术摄影，电影般质感，绝佳的光影效果。'
GENERIC_ANCHORS = {'sexy', 'sexier', 'sexy outfit', 'more sexy', 'sensual',
                   'feminine', 'more feminine', 'beautiful', 'alluring', 'attractive'}


def is_trial(draw):
    return draw.get('face_sensual_trial_revision') == REVISION


def is_text_face_delivery(draw):
    return is_trial(draw) and draw.get('delivery_style_revision') == DELIVERY_STYLE_REVISION


def mark_trial(draw):
    draw.update(face_sensual_trial_revision=REVISION, art_direction_revision=REVISION,
                face_profile_zh=FACE_ZH, face_profile_en=FACE_EN,
                face_profile_status='provisional_user_setting',
                costume_styling_note=OUTFIT_NOTE,
                face_reference_policy='text_face_only_no_reference_image',
                face_delivery_mode='text_only',
                delivery_style_revision=DELIVERY_STYLE_REVISION,
                quality_prompt_prefix=QUALITY_PREFIX)


def validate_trial(draw, wardrobe):
    plan = draw.get('costume_plan') or {}
    anchors = plan.get('sensual_design_anchors')
    if not isinstance(anchors, list) or not 1 <= len(anchors) <= 5:
        raise ValueError('Current trial needs sensual_design_anchors naming concrete visible garment redesigns')
    for anchor in anchors:
        if (not isinstance(anchor, str) or anchor != anchor.strip()
                or not 4 <= len(anchor) <= 100 or '\n' in anchor
                or anchor.casefold() in GENERIC_ANCHORS):
            raise ValueError('Sensual design anchor must describe a specific garment construction, not a beauty label')
        if anchor.casefold() not in wardrobe.casefold():
            raise ValueError('Concrete sensual costume design missing from wardrobe: ' + anchor)
    for key in ('face_profile_zh', 'face_profile_en', 'costume_styling_note'):
        if not isinstance(draw.get(key), str) or not draw[key].strip():
            raise ValueError('Current trial is missing its signed styling snapshot: ' + key)


def validate_message(draw, wardrobe, message):
    validate_trial(draw, wardrobe)
    if draw['face_profile_en'] not in message:
        raise ValueError('Provisional face description was not delivered intact')
    if 'xiaobunben-standard-face-crop-2026-11-01.jpg' in message:
        raise ValueError('The old face photo must not override the provisional adult face')
    if is_text_face_delivery(draw):
        prefix = draw.get('quality_prompt_prefix')
        if prefix not in (QUALITY_PREFIX_V1, QUALITY_PREFIX) or draw.get('face_delivery_mode') != 'text_only':
            raise ValueError('Current delivery needs the exact quality prefix and text-only face setting')
        if not message.startswith(prefix + '\n((请创建一张照片))\n') or message.count(prefix) != 1:
            raise ValueError('The exact quality prefix must appear once at the absolute beginning')
        if any(note in message.casefold() for note in ('face reference', 'reference image', 'chatgpt library')):
            raise ValueError('Current text-only delivery must not request a reference image')


def metadata(draw):
    if not is_trial(draw):
        return {}
    keys = ('face_sensual_trial_revision', 'face_profile_zh', 'face_profile_en',
            'face_profile_status', 'face_reference_policy', 'costume_styling_note')
    optional = ('delivery_style_revision', 'quality_prompt_prefix', 'face_delivery_mode')
    return {key: deepcopy(draw[key]) for key in (*keys, *optional) if key in draw}
