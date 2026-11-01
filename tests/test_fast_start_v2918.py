import sys, tempfile, json, hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fast_start import stage_draw,stage_finish
from photo_creation_relay import verify_from_pending, build_from_pending
from button_handoff import verify as verify_button
from english_relay import FIELDS
from visual_identity import FACE_EN,BODY_EN

assert len(FIELDS)==21
assert all(s not in FACE_EN.lower() for s in ('long hair','short hair','fringe','bangs','ponytail','black hair'))
assert len(FACE_EN)<560 and len(BODY_EN)<140
history=root/'references/history.jsonl'
count=0; sizes=[]; flavors={}
with tempfile.TemporaryDirectory() as base:
 base=Path(base)
 for lane in ('career','cosplay','fusion'):
  for i in range(12):
   pending=base/f'{lane}-{i}'
   draw=stage_draw(pending,history,lane=lane,seed=100+i*9)
   assert draw['lane']==lane
   assert draw['hosiery_style_hint'] in ('consider_sheer_black','leave_to_role_design')
   role=draw.get('role','professional')
   # Mechanical invariants only; random role / scene are semantically reviewed separately.
   design={
     'subject':'A clearly adult East Asian professional or role performer carrying out a specific working task inside a credible imagined world.',
     'setting':'A functioning worksite with genuine stone and metal structure, practical tools, route signs, warm window light and period-specific equipment carefully arranged for actual duties.',
     'action':'She carefully fastens a work tool, inspects its safety attachment and checks a service log against the nearby marked working surface before carrying out the next real assignment.',
     'cue1':'A legible specialist emblem on the tailored outer layer and one well-used professional instrument identify her working responsibility.',
     'cue2':'A second independent task prop, practical attachment and detailed work records clearly show her occupational responsibilities and purpose.',
     'wardrobe':'Coordinated navy and copper work layers, shaped waist, textured fabric and secure footwear with one matching signature emblem.',
     'composition':'Task-focused view frames her expressive face, working hands and tools.',
   }
   if draw['is_original']:design['role']='原创云港灯塔保养师'
   path=base/f'{lane}-{i}.json';path.write_text(json.dumps(design,ensure_ascii=False),encoding='utf-8')
   result=stage_finish(pending,path)
   actual=verify_from_pending(pending)
   verify_button(pending,'new_chat',pending/'button_manifest.json')
   assert actual['field_count']==21
   assert actual['message']==(pending/'photo-creation-message.txt').read_text()
   assert actual['message_sha256']==hashlib.sha256(actual['message'].encode()).hexdigest()
   assert 1450 <= len(actual['message']) <=3300
   assert FACE_EN in actual['message'] and BODY_EN in actual['message']
   assert actual['message'].index('Identity:') < actual['message'].index('Story and location:')
   assert all(s in FACE_EN.lower() for s in ('slim cheek contours','lower face','almond eyes','lower lids','nose','pink lips'))
   assert 'clear visual focus' in actual['message']
   assert 'about 20 years old' in actual['message']
   assert 'Wardrobe:' in actual['message']
   assert 'distinctly petite' in actual['message'].lower()
   assert 'Visible moment:' in actual['message'] and 'Two story clues:' in actual['message']
   assert 'protective workwear shaped by the real task' not in actual['message'].lower()
   assert 'natural facial catchlights' in actual['message']
   assert actual['success_sample_registration_enabled'] is False
   assert actual['message'].count('Story and location:') == 1
   assert actual['message'].count('Identity:') == 1
   assert actual['message'].count('Wardrobe:') == 1
   assert 'long hair with airy' not in actual['message'].lower()
   assert 'her eyes are blue' not in actual['message'].lower()
   manifest=json.loads((pending/'manifest.json').read_text())
   assert manifest['version']=='3.5' and manifest['pending_status']=='image_not_yet_generated'
   assert manifest['success_sample_registration_enabled'] is False
   assert result['image_generated'] is False
   sizes.append(len(actual['message']))
   flavors[draw['camera_pack_id']]=flavors.get(draw['camera_pack_id'],0)+1
   count+=1
 # Tamper test: never let an altered message verify.
 p=base/'career-0'/'photo-creation-message.txt'
 p.write_text(p.read_text()+' Altered.',encoding='utf-8')
 try:
  verify_from_pending(base/'career-0')
  raise AssertionError('Tampering was not blocked')
 except ValueError: pass
print(json.dumps({'passed_scenarios':count,'tamper_rejected':True,'prompt_characters_min':min(sizes),'prompt_characters_max':max(sizes),'prompt_characters_avg':round(sum(sizes)/len(sizes)),'distinct_camera_packs':len(flavors),'lanes_tested':['career','cosplay','fusion']},ensure_ascii=False))
