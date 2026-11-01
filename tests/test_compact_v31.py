"""V3.1 end-to-end checks: concise relay, face anchor, narrative cues, sealed button.

These are structural tests only: they do not claim actual image quality.
"""
import json
import hashlib
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button
from visual_identity import FACE_EN, BODY_EN

scene={
 'subject':'A clearly adult East Asian seaside traveler welcoming someone she cherishes at the first coastal train arrival at dawn.',
 'setting':'A rain-washed old coastal railway platform; beyond its iron canopy are a misty harbor, amber station lamps and a vintage local train easing in.',
 'action':'She ties a fine burgundy velvet ribbon around a tiny bouquet of wildflowers, then looks up at the arriving train with a delighted smile.',
 'cue1':'A hand-picked bouquet with slightly crinkled paper wrapping rests between her fingers as she finishes its burgundy velvet ribbon.',
 'cue2':'Two vintage rail tickets peek from her small leather satchel; the arriving carriage and old station clock mark a long-awaited meeting.',
 'wardrobe':'Fitted navy cropped jacket, ivory bow-neck blouse, burgundy A-line short skirt, sheer charcoal tights, elegant ankle boots and pearls.',
 'composition':'Eye-level three-quarter portrait, face and hands visibly clear.',
}
choice={
 'world':'nostalgic maritime railway town','role':'seaside traveler',
 'scene':'coastal railway platform at dawn','lane':'story',
 'shot':'intimate medium-full three-quarter environmental portrait',
 'shot_english':'Eye-level medium-full three-quarter environmental portrait with a clearly recognizable face and graceful hands.',
 'moment':'拥抱期待重逢的清晨','moment_english':'just as the first dawn train arrives',
 'costume_mode':'bespoke','camera_intensity':'medium',
 'camera_style':{
  'name':'harbor dawn medium format','medium':'a modern medium-format digital camera',
  'optics':'a natural 65mm portrait lens','lighting':'luminous early-morning skylight and warm station lamps',
  'palette':'misty sea blue, honeyed amber, ivory and burgundy',
  'texture':'fine grain, natural wet-stone reflections and realistic fabric texture',
  'framing':'an environmental three-quarter portrait with natural face scale'},
 'creative_intent':'Her emotional return, not a job or an obligatory draw.',
}
with tempfile.TemporaryDirectory() as tmp:
 folder=Path(tmp)
 brief=folder/'brief.json'
 brief.write_text(json.dumps({'choice':choice,'scene_design':scene},ensure_ascii=False),encoding='utf-8')
 pending=folder/'story'
 stage_curate(pending,brief)
 result=stage_finish(pending,pending/'scene-design.json')
 photo=verify_from_pending(pending)
 verify_button(pending,'new_chat',pending/'button_manifest.json')
 msg=photo['message']
 assert photo['schema'].endswith('v3.1') and photo['field_count']==21
 assert all(s in msg for s in scene.values())
 assert FACE_EN in msg and BODY_EN in msg
 assert msg.count('Identity:')==1 and msg.count('Wardrobe:')==1
 assert msg.count('Visible moment:')==1 and msg.count('Two story clues:')==1
 assert msg.count('one-of-a-kind')==0 and '65mm portrait lens' in msg
 assert msg.count('original photorealistic photograph')==1
 assert 1450<=len(msg)<=3300
 assert photo['message_sha256']==hashlib.sha256(msg.encode()).hexdigest()
 assert json.loads((pending/'manifest.json').read_text())['version']=='3.5'
 assert result['button_label']=='打开小笨笨衣橱' and result['image_generated'] is False
 # Any tampering to the final button message should be detected.
 button_file=pending/'button_manifest.json'
 button=json.loads(button_file.read_text())
 assert button['full_user_message']==msg
 button['full_user_message']='tampered'
 button_file.write_text(json.dumps(button),encoding='utf-8')
 try:verify_button(pending,'new_chat',button_file)
 except ValueError:pass
 else:raise AssertionError('Button tampering not detected')
 # Structural validation only: no permanent example enters the creative library.
 print(json.dumps({'scenario':'dawn coastal reunion','signed_fields':photo['field_count'],
   'output_chars':len(msg),'role_cues_survive':True,'wardrobe_exact':True,
   'button_verified':True,'tamper_detected':True,'image_generated':False},ensure_ascii=False))
