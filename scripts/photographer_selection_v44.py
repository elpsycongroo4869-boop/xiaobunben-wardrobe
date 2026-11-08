"""4.4 observer release: a full world exists independently of the chosen photograph.

The original 4.3.4 signed pipeline is preserved. This module validates an
additional creator-authored full-world vs photographed-detail distinction and
saves the original creative choices inside the pending before the ZIP is sealed.
"""
import hashlib
import json
from pathlib import Path

SCHEMA = 'wardrobe-photographer-selection-v4.4-preview-r2'


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def _proper(value, name, minimum=15, maximum=1200):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum or value != value.strip():
        raise ValueError(f'{name} must contain specific prose between {minimum} and {maximum} characters')
    return value


def selected(brief, *, schema=SCHEMA):
    historical = schema == SCHEMA
    world = brief.get('complete_world')
    shot = brief.get('photographer_selection')
    if not isinstance(world, dict) or not isinstance(shot, dict):
        raise ValueError('4.4 observer preview requires complete_world and photographer_selection')
    for k in ('full_wardrobe', 'full_action', 'offscreen_context'):
        _proper(world.get(k), 'complete_world.'+k)
    for k in ('why_this_frame','intentionally_unshown','delivered_wardrobe','delivered_action'):
        minimum = 0 if k == 'delivered_wardrobe' and not historical else 15
        _proper(shot.get(k), 'photographer_selection.'+k, minimum)
    scene,cam=brief.get('scene_design'),brief.get('camera_plan')
    if not isinstance(scene,dict) or not isinstance(cam,dict):
        raise ValueError('4.4 needs existing scene_design and camera_plan')
    if shot['delivered_wardrobe'] != scene.get('wardrobe') or shot['delivered_action'] != scene.get('action'):
        raise ValueError('Photographer-selected visible outfit/action must match delivered scene exactly')
    exclusions=shot.get('offscreen_not_requested')
    if not isinstance(exclusions, list) or not int(historical) <= len(exclusions) <= 12:
        raise ValueError('Declare up to 12 concrete complete-world details left out of this shot')
    world_text = ' '.join(world[key] for key in ('full_wardrobe', 'full_action', 'offscreen_context')).casefold()
    relevant = ' '.join((scene.get('wardrobe',''),scene.get('action',''),scene.get('cue1',''),scene.get('cue2',''),scene.get('composition',''),cam.get('viewpoint',''),cam.get('optics',''))).casefold()
    for phrase in exclusions:
        _proper(phrase,'offscreen_not_requested detail',4,90)
        if phrase.casefold() not in world_text:
            raise ValueError('Missing complete-world detail to be left outside the shot: '+phrase)
        if phrase.casefold() in relevant:
            raise ValueError('Offscreen-only detail is mistakenly required in image request: '+phrase)
    if len({phrase.casefold() if not historical else phrase for phrase in exclusions}) != len(exclusions):
        raise ValueError('Offscreen details must not repeat')
    if historical and len(world['full_wardrobe']) <= len(scene['wardrobe']):
        raise ValueError('Complete outfit must meaningfully exceed photographically selected outfit')
    return {'schema':schema,'complete_world':world,'photographer_selection':shot,
            'selected_scene_sha256':hashlib.sha256(canonical(scene)).hexdigest(),
            'selected_camera_sha256':hashlib.sha256(canonical(cam)).hexdigest(),
            'selected_costume_sha256':hashlib.sha256(canonical(brief['choice']['costume_plan'])).hexdigest()}


def write_snapshot(pending, brief):
    record=selected(brief)
    p=Path(pending)/'photographer-selection.json'
    if p.exists():raise ValueError('Photographer selection already exists in pending')
    p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # The existing 4.3.4 source seal includes draw.json. Tie the extra record
    # to that sealed source rather than relying on an unbound extra ZIP file.
    draw_path=Path(pending)/'draw.json'
    draw=json.loads(draw_path.read_text('utf-8'))
    draw['photographer_selection_schema']=SCHEMA
    draw['photographer_selection_sha256']=hashlib.sha256(canonical(record)).hexdigest()
    draw_path.write_text(json.dumps(draw,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def verify_snapshot(pending):
    pending=Path(pending)
    p=pending/'photographer-selection.json'
    if not p.exists():raise ValueError('4.4 observer preview missing photographer decision snapshot')
    record=json.loads(p.read_text('utf-8'))
    if record.get('schema')!=SCHEMA:raise ValueError('Wrong photographer decision schema')
    draw=json.loads((pending/'draw.json').read_text('utf-8'))
    if draw.get('photographer_selection_schema')!=SCHEMA or draw.get('photographer_selection_sha256')!=hashlib.sha256(canonical(record)).hexdigest():
        raise ValueError('Photographer decision is not tied to sealed draw source')
    scene=json.loads((pending/'scene-design.json').read_text('utf-8'))
    if hashlib.sha256(canonical(scene)).hexdigest()!=record['selected_scene_sha256']:
        raise ValueError('Photographer-selected visible scene drifted')
    if hashlib.sha256(canonical(draw['camera_plan'])).hexdigest()!=record['selected_camera_sha256']:
        raise ValueError('Photographer camera decision drifted')
    if hashlib.sha256(canonical(draw['costume_plan'])).hexdigest()!=record['selected_costume_sha256']:
        raise ValueError('Visible outfit structure drifted')
    selection=record['photographer_selection']
    message=(pending/'photo-creation-message.txt').read_text('utf-8')
    if selection['delivered_wardrobe'] not in message or selection['delivered_action'] not in message:
        raise ValueError('Photographer-selected visible parts did not reach image request')
    for phrase in selection['offscreen_not_requested']:
        if phrase.casefold() in message.casefold():
            raise ValueError('Full-world-only detail leaked into requested photograph: '+phrase)
    return {'schema':SCHEMA,'offscreen_details_excluded':len(selection['offscreen_not_requested']),
            'selected_photo_sha256':hashlib.sha256(message.encode('utf-8')).hexdigest(),
            'full_world_recorded':True}
