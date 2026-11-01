#!/usr/bin/env python3
"""v3.5 assistant-led startup (or optional v2.9 random): real draw -> 7-field English art direction -> verified 21-field relay.

Never generates an image or registers success samples. Legacy history is read-only for random diversity.
No network/upload dependency. The caller uploads the portable pending zip before displaying the button.
"""
import argparse
import hashlib
import json
import random
import secrets
import uuid
import sys
import zipfile
from pathlib import Path

from roll_wardrobe import draw as roll, load_history
from prepare_shoot import compile_shot
from dispatch_shoot import seal, verify as verify_seal
from english_relay import FIELDS, canonical, build as english_build
from photo_creation_relay import build_from_pending, verify_from_pending
from button_handoff import build as button_build, verify as button_verify

ROOT = Path(__file__).resolve().parents[1]
CAMERA_EN = json.loads((ROOT/'references/camera-packs-en.json').read_text(encoding='utf-8'))
MAX_SCENE_CHARS={'subject':170,'setting':245,'action':270,'cue1':220,'cue2':220,'wardrobe':155,'composition':70}
MOMENTS = (
 'preparing before the task begins', 'executing the decisive work action',
 'explaining the work to a colleague or student', 'having just solved a sudden problem',
 'taking a brief rest while work evidence remains visible', 'making an on-site work record',
 'checking tools and professional equipment', 'glancing back after completing the task',
 'continuing to work despite demanding conditions', 'interacting with the subject of the work',
 'discovering something unexpected at the location', 'preparing to travel to the next assignment',
)
SHOT_EN = (
 'Wide environmental portrait: she is legible within the world.',
 'Medium work candid: expressive, task-directed body language.',
 'Full-body action: natural weight, movement and coherent outfit.',
 'Waist-up work portrait: attentive face, hands and role clues.',
 'Slightly low cinematic angle: confident presence at the worksite.',
 'Shoulder-follow view: readable face, work target and hands.',
 'Candid street view: a lively but believable working moment.',
 'Broad worksite portrait: one clear visual heroine and task.',
 'After-task candid: expressive face and visible work evidence.',
 'Live performance shot: dynamic, role-appropriate movement.',
 'Environmental close-up: face and two clear role cues.',
 'Elevated work view: working hands, task evidence and recognizable face.',
 'Backlit side portrait: face and equipment still clear.',
 'Walking follow shot: natural stride and meaningful destination.',
)
INTENSITY = {'subtle':'Restrained camera styling: the job remains foremost and fully legible.',
 'medium':'Distinct camera texture, natural face and readable career cues.',
 'strong':'Bold camera style with readable face, action and career cues.'}
MODE = {
 'practical':'Art-directed, fitted work-inspired outfit with a flattering feminine silhouette.',
 'refined':'Elegant, feminine role uniform with attractive proportions and signature colors.',
 'game_feminine':'Bold game-heroine role costume, beautifully tailored beyond everyday workwear.',
 'fantasy':'Fantasy heroine costume with expressive silhouette and distinctive role motifs.',
 'bespoke':'A one-off art-directed character costume, uniquely designed for this role and story.'
}
MANDATORY = ('subject','setting','action','cue1','cue2','wardrobe','composition')

def write_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def stage_draw(pending, history, lane=None, seed=None):
 pending=Path(pending).resolve()
 pending.mkdir(parents=True,exist_ok=False) # never silently replace an existing draw
 rng=random.Random(seed) if seed is not None else secrets.SystemRandom()
 d=roll(load_history(Path(history)),rng,lane)
 d['decision_owner']='assistant'
 d['delivery_version']='3.5'  # reference-first handoff; legacy random draw stays unchanged
 d['decision_method']='assistant_chose_randomization'
 # Cosmetic suggestion only, drawn after the locked occupation/camera/costume lottery.
 # A positive suggestion means: add fine dark hosiery only when the scene's
 # outfit, original character and natural frame suit it. Never force or reframe.
 d['hosiery_style_hint']='consider_sheer_black' if rng.randrange(2)==0 else 'leave_to_role_design'
 write_json(pending/'draw.json',d)
 return d

def stage_curate(pending, creative_brief_path):
 """V3: assistant makes a creative decision; lottery is optional, not default."""
 pending=Path(pending).resolve()
 pending.mkdir(parents=True,exist_ok=False)
 brief=json.loads(Path(creative_brief_path).read_text(encoding='utf-8'))
 choice=brief.get('choice')
 design=brief.get('scene_design')
 if not isinstance(choice,dict) or not isinstance(design,dict):
  raise ValueError('Creative brief must have explicit choice and scene_design objects')
 for k in ('world','role','scene','shot','moment'):
  if not isinstance(choice.get(k),str) or len(choice[k].strip())<3:
   raise ValueError('Missing assistant-created decision: '+k)
 lane=choice.get('lane','career')
 if lane not in ('career','cosplay','fusion','story'):raise ValueError('Unsupported role type')
 costume=choice.get('costume_mode','bespoke')
 if costume not in MODE:raise ValueError('Invalid wardrobe approach')
 intensity=choice.get('camera_intensity','medium')
 if intensity not in INTENSITY:raise ValueError('Invalid photographic intensity')
 pack_id=choice.get('camera_pack_id')
 if pack_id is not None:
  packs=json.loads((ROOT/'references/camera-packs.json').read_text(encoding='utf-8'))['camera_packs']
  pack=next((v for v in packs if v['id']==pack_id),None)
  if pack is None:raise ValueError('Unknown camera pack; use camera_style for original photography')
 elif isinstance(choice.get('camera_style'),dict):
  original=choice['camera_style']
  for k in ('name','medium','optics','lighting','palette','texture','framing'):
   if not isinstance(original.get(k),str) or len(original[k].strip())<8:
    raise ValueError('Original camera art direction needs '+k)
  pack_id='original-'+hashlib.sha256(canonical(original)).hexdigest()[:12]
  pack={'id':pack_id,**{k:original[k].strip() for k in ('name','medium','optics','lighting','palette','texture','framing')}}
 else:raise ValueError('Choose a photographic approach or write a bespoke camera_style')
 cosplay_fields={'cosplay_id':None,'cosplay_character':None}
 if lane in ('cosplay','fusion'):
  info=choice.get('character')
  if not isinstance(info,dict) or not all(info.get(k) for k in ('name','source','visual_cues')) or not isinstance(info['visual_cues'],list) or len(info['visual_cues'])<2:
   raise ValueError('Cos/fusion requires named character with recognizable visual cues')
  cp_id=hashlib.sha256(canonical(info)).hexdigest()[:16]
  cosplay_fields={'cosplay_id':cp_id,'cosplay_character':{'id':cp_id,'name':info['name'],'source':info['source'],'visual_cues':info['visual_cues'],'suggested_action':choice['moment'],'fusion_style':info.get('fusion_style','recognizable artistic motifs')}}
 draw={'version':'3.5','draw_id':str(uuid.uuid4()),'mode':'chosen','decision_owner':'assistant',
       'decision_method':'direct_art_direction','creative_intent':str(choice.get('creative_intent','')).strip(),
       'lane':lane,'category':choice['world'].strip(),'category_id':'v3-original-world',
       'role':choice['role'].strip(),'is_original':False,'suggested_scene':choice['scene'].strip(),
       'story_moment':choice['moment'].strip(),'story_moment_english':choice.get('moment_english',''),
       'suggested_camera':choice['shot'].strip(),'shot_description':choice.get('shot_english',''),
       'camera_pack':pack,'camera_pack_id':pack_id,'camera_intensity':intensity,
       'camera_intensity_description':intensity,'costume_mode':costume,
       'hosiery_style_hint':'leave_to_role_design', **cosplay_fields,
       'status':'artist_decision_locked','requires_preflight':True}
 validate_design(design,draw)
 if lane in ('career','fusion','story') and not (choice['role'].lower() in design['subject'].lower() or all(x in design['subject'].lower() for x in choice['role'].lower().split() if len(x)>3)):
  # Semantic mapping from Chinese role names to English must be manually reviewed.
  draw['role_translation_review_required']=True
 write_json(pending/'draw.json',draw)
 write_json(pending/'scene-design.json',design)
 return {'decision_method':draw['decision_method'],'decision_owner':'assistant','draw_id':draw['draw_id'],
         'role':draw['role'],'camera_pack_id':draw['camera_pack_id'],'pending':str(pending),
         'next_command':'finish --pending ... --scene-design '+str(pending/'scene-design.json')}

def validate_design(design, draw):
 for key in MANDATORY:
  v=design.get(key)
  if not isinstance(v,str) or len(v.strip())<22 or v!=v.strip():
   raise ValueError('The original 7-field scene design requires specific English prose for: '+key)
  if sum('\u3400'<=c<='\u9fff' for c in v)>2:
   raise ValueError('Scene field must be in English: '+key)
  if len(v)>MAX_SCENE_CHARS[key]:
   raise ValueError(f'Scene field {key} exceeds {MAX_SCENE_CHARS[key]} chars: keep all key visual evidence within the short delivery budget')
 if draw.get('is_original') and (not design.get('role') or len(design['role'])<5):
  raise ValueError('An original occupation must be named explicitly in scene design')
 # The assistant must check role/scene semantics against the draw. Hashes cannot validate translation.

def build_fields(d,s,design):
 camera=CAMERA_EN.get(d['camera_pack_id'])
 if camera is None and d.get('mode')=='chosen':
  pk=d['camera_pack']
  camera=[pk['medium'],pk['optics'],pk['lighting'],pk['palette'],pk['texture'],pk['framing']]
 if camera is None:raise ValueError('Camera package has no faithful English translation')
 pack=d['camera_pack']
 pose=(d.get('shot_description') or SHOT_EN[__import__('roll_wardrobe').SHOT_POOL.index(d['suggested_camera'])]) if d.get('mode')=='random' else (d.get('shot_description') or 'A considered portrait camera angle highlighting the heroine and this work.')
 moment=MOMENTS[__import__('roll_wardrobe').MOMENT_POOL.index(d['story_moment'])] if d.get('mode')=='random' else (d.get('story_moment_english') or 'carrying out her chosen task in a meaningful story moment')
 medium,lens,lighting,color,texture,framing=camera
 if d['camera_pack_id']=='front-phone' and any(t in d['suggested_camera'] for t in ('全身','远景','环境','跟拍','高位')):
  medium='a fixed-position smartphone-style wide-angle field recording'
  framing='a supported phone-wide frame with the woman standing back in her workplace'
 char=d.get('cosplay_character') if d['lane'] in ('cosplay','fusion') else None
 character=('The clearly adult East Asian heroine plays a live-action version of '+char['name'].split(' ')[-1]+
            ' with instantly recognizable signature appearance and professionally believable activity.' if char and d['lane']=='cosplay'
            else ('A clearly adult East Asian fictional heroine with a coherent personal identity and expressive role-specific presence.' if d.get('mode')=='chosen' else 'A clearly adult East Asian female professional, with a composed and lively presence in her occupational world.'))
 body='Healthy, slender adult proportions and natural movement suited to the profession.'
 detail=(f"She is seen {moment}; the chosen story moment is expressed in her action and environment." if d.get('mode')=='chosen' else f"She is seen {moment}; the work unfolds during an authentic, specific local event, with her action visibly underway.")
 light_extra=design.get('lighting_detail','')
 if light_extra and (len(light_extra)<20 or len(light_extra)>160):raise ValueError('lighting_detail is out of bounds')
 shot=f'{pose} Keep her visible story action and two independent role clues readable.' if d.get('mode')=='chosen' else f'{pose} Keep her actual task and its two independent occupational cues readable.'
 field={
  'world_and_role': design['subject'],
  'environment': design['setting'],
  'work_action': design['action'],
  'career_evidence_1': design['cue1'],
  'career_evidence_2': design['cue2'],
  'character_identity': character,
  'body_proportions':body,
  'outfit_and_function':design['wardrobe'],
  'outfit_design_mode':MODE[d['costume_mode']],
  'shot_and_distance':shot,
  'story_moment':detail,
  'camera_medium':f'Photographed with {medium}, capturing her chosen story moment.' if d.get('mode')=='chosen' else f'Photographed with {medium}, as a naturally observed professional moment.',
  'camera_lens':f'Use {lens}.',
  'lighting':f'The photographic light is {lighting}.'+((' '+light_extra) if light_extra else ''),
  'color':f'Palette: {color}; harmonize the visible outfit and setting.',
  'texture_depth':f'Capture {texture}, respecting the original camera package and plausible depth of field.',
  'framing':f'Keep {framing}, retaining the identity, task and spatial context.',
  'intensity':INTENSITY[d['camera_intensity']],
  'composition':design['composition'],
  'in_world_writing':'Any writing or signage belongs naturally to her world and story.' if d.get('mode')=='chosen' else 'Any signage naturally uses the language of this setting.',
  'feminine_presence':'Her sweet youthful-adult expression, bright gaze, gentle face lighting and artfully tailored feminine costume make her the visual star of this role.'
 }
 assert set(field)==set(FIELDS)
 return field

def stage_finish(pending, design_path, route='new_chat'):
 pending=Path(pending).resolve()
 d=json.loads((pending/'draw.json').read_text(encoding='utf-8'))
 design=json.loads(Path(design_path).read_text(encoding='utf-8'))
 validate_design(design,d)
 # Respect already-specified coordinated legwear; no inserted camera request.
 hosiery_requested=any(token in design['wardrobe'].lower() for token in
     ('black tights','black stockings','black thigh-high stockings','dark sheer tights','sheer black hosiery'))
 natural_lower_frame=any(token in d['suggested_camera'] for token in
     ('全身','远景','步行','街拍','舞台','三分之四'))
 s=compile_shot(d,design['action'],design['cue1'],design['cue2'],
     role_override=design.get('role'),hosiery_fitting=hosiery_requested and natural_lower_frame)
 write_json(pending/'scene-design.json',design)
 write_json(pending/'shoot.json',s)
 h=seal(pending/'draw.json',pending/'shoot.json','context_inferred')
 write_json(pending/'handoff.json',h)
 verify_seal(h)
 fields=build_fields(d,s,design)
 e={'draw_id':d['draw_id'],'original_prompt_sha256':h['prompt_sha256'],
    'lane':s['lane'],'costume_mode':s['costume_mode'], 'camera_pack_id':s['camera_pack_id'],
    'camera_intensity':d['camera_intensity'],'feminine_presence_mode':s['feminine_presence_mode'],
    'fields':fields}
 write_json(pending/'english-details.json',e)
 english_build(pending/'handoff.json',pending/'english-details.json')
 p=build_from_pending(pending)
 write_json(pending/'photo-creation-relay.json',p)
 (pending/'photo-creation-message.txt').write_text(p['message'],encoding='utf-8')
 verify_from_pending(pending)
 button=button_build(pending,route)
 write_json(pending/'button_manifest.json',button)
 button_verify(pending,route,pending/'button_manifest.json')
 m={'version':('3.5' if d.get('version')=='3.5' or d.get('delivery_version')=='3.5' else '3.4' if d.get('version')=='3.4' or d.get('delivery_version')=='3.4' else '3.3' if d.get('version')=='3.3' or d.get('delivery_version')=='3.3' else '3.2' if d.get('version')=='3.2' or d.get('delivery_version')=='3.2' else '3.1' if d.get('version')=='3.1' or d.get('delivery_version')=='3.1' else '3.0' if d.get('version')=='3.0' else '2.9.19'),'source_version':'2.9.19', 'draw_id':d['draw_id'],
    'decision_owner':d.get('decision_owner','assistant'),'decision_method':d.get('decision_method','assistant_chose_randomization'),
    'original_21_fields_verified':True,'button_verified':True,'route':route,
    'pending_status':'image_not_yet_generated',
    'message_sha256':p['message_sha256'],'reference_asset_sha256':'245c7aa75aa8f077b0f6352414d800cc955a287b6ecb95583ab955aaaa42e4f1',
    'semantic_review_required':True,'success_sample_registration_enabled':False,
    'hosiery_style_hint':d.get('hosiery_style_hint','leave_to_role_design'),
    'hosiery_selected_in_wardrobe':hosiery_requested}
 write_json(pending/'manifest.json',m)
 zip_path=pending.parent/(f'wardrobe-v{m["version"]}-pending-{d["draw_id"][:8]}.zip')
 with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for item in sorted(pending.iterdir()):
   if item.is_file():z.write(item,item.name)
 return {'draw_id':d['draw_id'],'lane':d['lane'], 'role':s['role'], 'camera_pack_id':d['camera_pack_id'],
         'button_label':button['button_label'],'route':route,'message_sha256':p['message_sha256'],
         'message_chars':len(p['message']),'pending_zip':str(zip_path),'message_path':str(pending/'photo-creation-message.txt'),
         'needs_library_upload':True,'image_generated':False}

def main():
 parser=argparse.ArgumentParser(description='v3.5 assistant-directed wardrobe, with optional randomness and full verification')
 sub=parser.add_subparsers(dest='command',required=True)
 u=sub.add_parser('curate');u.add_argument('--pending',type=Path,required=True);u.add_argument('--creative-brief',type=Path,required=True)
 a=sub.add_parser('draw');a.add_argument('--pending',type=Path,required=True);a.add_argument('--history',type=Path,default=ROOT/'references/history.jsonl');a.add_argument('--lane',choices=('career','cosplay','fusion'));a.add_argument('--seed',type=int,help='tests only, never for genuine random draw')
 b=sub.add_parser('finish');b.add_argument('--pending',type=Path,required=True);b.add_argument('--scene-design',type=Path,required=True);b.add_argument('--route',choices=('new_chat','copy_only'),default='new_chat')
 c=sub.add_parser('verify');c.add_argument('--pending',type=Path,required=True);c.add_argument('--route',choices=('new_chat','copy_only'),default='new_chat')
 args=parser.parse_args()
 if args.command=='draw': out=stage_draw(args.pending,args.history,args.lane,args.seed)
 elif args.command=='curate':out=stage_curate(args.pending,args.creative_brief)
 elif args.command=='finish':out=stage_finish(args.pending,args.scene_design,args.route)
 else:
  verify_from_pending(args.pending);button_verify(args.pending,args.route,args.pending/'button_manifest.json')
  out={'verified':True,'draw_id':json.loads((args.pending/'draw.json').read_text('utf-8'))['draw_id']}
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,KeyError,TypeError,OSError,AssertionError,IndexError,json.JSONDecodeError) as exc:
  print('FAST START BLOCKED: '+str(exc),file=sys.stderr)
  sys.exit(2)
