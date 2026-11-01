"""v3.5 reference-first handoff, no claims of actual image injection."""
import sys,json,tempfile,hashlib,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fast_start import stage_curate, stage_finish
from button_handoff import verify as verify_button
from photo_creation_relay import verify_from_pending,REFERENCE_FACE_PATH
from visual_identity import FACE_EN
# Private assets are optional in a fresh clone; never include them in Git.
original = ROOT/'assets/xiaobunben-selected-reference-2026-11-01.jpg'
crop = ROOT/'assets/xiaobunben-standard-face-crop-2026-11-01.jpg'
if original.exists() != crop.exists():
 raise AssertionError('Provide both private reference images, or neither')
if original.exists():
 from image_integrity import fingerprint
 fingerprint(original)
 fingerprint(crop)
else:
 print('SKIP: private reference image integrity (assets not installed)')
tree=ast.parse((ROOT/'tests/test_compact_v31.py').read_text())
data={}
for n in tree.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('scene','choice'):
  data[n.targets[0].id]=ast.literal_eval(n.value)
with tempfile.TemporaryDirectory() as td:
 t=Path(td); brief=t/'brief.json'; brief.write_text(json.dumps({'choice':data['choice'],'scene_design':data['scene']},ensure_ascii=False),encoding='utf-8')
 pending=t/'fresh'
 stage_curate(pending,brief)
 r=stage_finish(pending,pending/'scene-design.json')
 verify_button(pending,'new_chat',pending/'button_manifest.json')
 msg=verify_from_pending(pending)['message']
 assert json.loads((pending/'manifest.json').read_text())['version']=='3.5'
 assert 'look up the original reference image in ChatGPT Library' in msg
 assert REFERENCE_FACE_PATH in msg
 assert 'If the image cannot be accessed' in msg
 assert msg.count(FACE_EN)==1
 assert all(x in msg for x in data['scene'].values())
 assert 1450<=len(msg)<=3300
 assert json.loads((pending/'photo-creation-relay.json').read_text())['reference_image_attached_to_request'] is False
 assert r['image_generated'] is False
 print(json.dumps({'version':'3.5','button_verified':True,'reference_lookup':True,'original_21_fields_preserved':True,'identity_anchor_once':True,'image_attachment_not_claimed':True,'prompt_chars':len(msg)}))
