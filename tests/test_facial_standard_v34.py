"""v3.4 single-face prompt regression: one adult face anchor, existing scene untouched.

This is structural verification, not a visual similarity test.
"""
import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from visual_identity import FACE_EN, FACE_EN_V33, FACE_EN_V32, BODY_EN
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button

assert FACE_EN!=FACE_EN_V32 and FACE_EN!=FACE_EN_V33
assert 'distinctly petite' in FACE_EN and 'fine-boned' in FACE_EN
assert all(x in FACE_EN for x in ('slim cheek contours','lower face is short','almond eyes','lower lids','nose','pink lips'))
assert 'subtly lifted outer corners' in FACE_EN
assert not any(x in FACE_EN.lower() for x in ('rounded cheeks','full cheeks','round face','playful, lively charm to gentle'))
assert 400<=len(FACE_EN)<560
assert not any(x in FACE_EN.lower() for x in ('bangs','fringe','long hair','short hair','ponytail','black hair','stockings','tights'))
# Load test's structured source without executing its test runner.
tree=ast.parse((ROOT/'tests/test_compact_v31.py').read_text())
fixture={}
for n in tree.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('scene','choice'):
  fixture[n.targets[0].id]=ast.literal_eval(n.value)
with tempfile.TemporaryDirectory() as d:
 base=Path(d)
 brief=base/'brief.json'
 brief.write_text(json.dumps({'choice':fixture['choice'],'scene_design':fixture['scene']},ensure_ascii=False),encoding='utf-8')
 pending=base/'current'
 stage_curate(pending,brief)
 historical=json.loads((pending/'draw.json').read_text())
 historical['version']='3.4'
 (pending/'draw.json').write_text(json.dumps(historical,ensure_ascii=False,indent=2))
 result=stage_finish(pending,pending/'scene-design.json')
 verified=verify_from_pending(pending)
 verify_button(pending,'new_chat',pending/'button_manifest.json')
 msg=verified['message']
 assert json.loads((pending/'manifest.json').read_text())['version']=='3.4'
 assert FACE_EN in msg and FACE_EN_V32 not in msg and FACE_EN_V33 not in msg and BODY_EN in msg
 assert msg.count(FACE_EN)==1 and msg.count('Identity:')==1
 assert all(v in msg for v in fixture['scene'].values())
 assert 1450<=len(msg)<=3000
 assert hashlib.sha256(msg.encode()).hexdigest()==verified['message_sha256']
 assert result['image_generated'] is False
 print(json.dumps({'version':'3.4','face_chars':len(FACE_EN),'full_prompt_chars':len(msg),'signed_fields':verified['field_count'],'face_anchor_once':True,'scene_untouched':True,'button_verified':True,'image_generated':False},ensure_ascii=False))
