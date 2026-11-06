"""Preserve artist-selected role clothing before applying feminine styling."""

from copy import deepcopy
import re
from role_first_costume import MATERIALS

REVISION = '3.5.3-role-costume-first'
MAX_WARDROBE_CHARS = 280
PLAN_FIELDS = ('context_and_climate', 'role_foundation', 'material_anchors',
               'construction_anchors', 'feminine_adaptation')


def is_role_first(draw):
    return draw.get('role_costume_first') is True


def validate_plan(plan, wardrobe):
    """Check explicit decisions and delivery fidelity, not artistic correctness."""
    if not isinstance(plan, dict) or any(key not in plan for key in PLAN_FIELDS):
        raise ValueError('Role-first design requires costume_plan: ' + ', '.join(PLAN_FIELDS))
    if not isinstance(wardrobe, str):
        raise ValueError('Role-first wardrobe needs concrete English clothing')
    for key, minimum, maximum in (
            ('context_and_climate', 12, 220),
            ('role_foundation', 24, 300),
            ('feminine_adaptation', 20, 260)):
        value = plan[key]
        if (not isinstance(value, str) or value != value.strip()
                or not minimum <= len(value) <= maximum):
            raise ValueError(f'costume_plan.{key} needs {minimum}..{maximum} characters')
        if sum('\u3400' <= c <= '\u9fff' for c in value) > 2:
            raise ValueError('Costume plan needs English visual wording: ' + key)
    for key in ('material_anchors', 'construction_anchors'):
        anchors = plan[key]
        if not isinstance(anchors, list) or not 1 <= len(anchors) <= 5:
            raise ValueError('costume_plan.' + key + ' needs 1..5 chosen visible anchors')
        for anchor in anchors:
            if (not isinstance(anchor, str) or anchor != anchor.strip()
                    or not 2 <= len(anchor) <= 80 or '\n' in anchor):
                raise ValueError('Invalid visible costume anchor: ' + key)
            if anchor.casefold() not in wardrobe.casefold():
                raise ValueError('Selected role material/construction missing from wardrobe: ' + anchor)
    return deepcopy(plan)


def attach_plan(draw, plan, wardrobe):
    draw['costume_plan'] = validate_plan(plan, wardrobe)
    draw['role_costume_first'] = True
    draw['art_direction_revision'] = REVISION


def styling_note():
    return ('Give this role outfit bold, graceful feminine tailoring and expressive lines, '
            'keeping its signature structure, chosen materials and climate context.')


def validate_texture(wardrobe, texture):
    """Catch familiar fabric substitutions without creating a material whitelist."""
    for material in MATERIALS:
        pattern = r'(?<![a-z])' + re.escape(material) + r'(?![a-z])'
        if re.search(pattern, texture, re.I) and not re.search(pattern, wardrobe, re.I):
            raise ValueError('Camera texture introduces a material absent from outfit: ' + material)


def validate_delivery(draw, wardrobe, message):
    validate_plan(draw.get('costume_plan'), wardrobe)
    validate_texture(wardrobe, draw.get('camera_pack', {}).get('texture', ''))
    if wardrobe not in message:
        raise ValueError('Role-first outfit was altered during delivery')
    if len(message) > 2300:
        raise ValueError('Role-first delivery exceeds 2300 characters; refine prose without dropping role clothing')
