"""Delivery audit for three detailed, heroine-first role descriptions, without image generation."""
import sys,json,tempfile,hashlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fast_start import stage_draw,stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button
from visual_identity import FINISH_BY_MODE

# These are synthetic sample designs, not user lottery outcomes or actual photographs.
DESIGNS=[
 dict(subject='A clearly adult East Asian mountain snow rescue driver checking a recovery rig in a dramatic contemporary highland dispatch bay.',
 setting='A remote rescue garage overlooking a blizzard road; amber worklamps, icy guardrails, a marked red tracked recovery vehicle and practical metal benches reveal the scene.',
 action='She steadies a forged steel recovery shackle beside the workbench with one gloved hand while testing the indicator of a wired winch-control handset with the other.',
 cue1='A mountain-rescue badge on her cropped outer layer identifies the heroine as the dedicated snow road recovery driver.',
 cue2='The clearly marked tracked rescue truck and a steel recovery shackle with coiled line show the unmistakable rescue duty.',
 wardrobe='Cropped teal rescue jacket, nipped waist, feminine pleated skort, slim thermal shorts, tall snow boots and coral mountain badge.',
 composition='Face, silhouette and equipment clearly lead the scene.'),
 dict(subject='A clearly adult East Asian female engineer adjusting a fantastical coastal observatory signal lens during an emergency night shift.',
 setting='In an active high-tech tidal beacon station above the sea, holographic tide charts shine beside polished brass tools, curved glass and salt-sprayed windows.',
 action='She rotates a calibrated optical collar with her left hand while checking its alignment against the etched tide-bearing chart on the illuminated console.',
 cue1='An enamel lighthouse crest with a technician identification plate on the elegant jacket establishes her observatory duty.',
 cue2='A specialized optical lens calibrator and a live tide-bearing projection reveal her skilled technical work.',
 wardrobe='Artfully belted midnight-blue jacket over a fitted tailored skort, pearl-gold piping, ankle boots and a luminous beacon insignia.',
 composition='Youthful face, fine costume and tools lead the scene.'),
 dict(subject='A clearly adult East Asian fantasy-world botanical field scholar cataloguing magical flowers inside an ancient cliffside greenhouse.',
 setting='A vaulted glass greenhouse clings to a misty mountain cliff, with carved botanical plaques, seed cabinets and old bronze irrigation channels.',
 action='She identifies a glowing petal with a brass magnifier while sketching its veins in a field log on the wooden potting bench.',
 cue1='An embroidered field-scholar crest and botanical classification ledger identify her professional mission.',
 cue2='The calibrated specimen magnifier and tagged magical seed tray communicate active research.',
 wardrobe='Cream cropped scholar vest, cinched olive waist, flowing layered short overskirt, fitted shorts and elegant lace-up field boots.',
 composition='Her face leads beside tagged flowers and magnifying tools.')
]
with tempfile.TemporaryDirectory() as base:
 base=Path(base)
 for i,design in enumerate(DESIGNS):
  lane=('career','cosplay','fusion')[i]
  pending=base/f'shot-{i}'
  draw=stage_draw(pending,ROOT/'references/history.jsonl',lane=lane,seed=567+i)
  if draw.get('is_original'): design['role']='原创光谱设备管理员'
  path=base/f'art-{i}.json'
  path.write_text(json.dumps(design,ensure_ascii=False),encoding='utf-8')
  result=stage_finish(pending,path)
  photo=verify_from_pending(pending)
  verify_button(pending,'new_chat',pending/'button_manifest.json')
  msg=photo['message']
  assert len(msg)<=3650
  assert 'about 20 years old' in msg and 'almond eyes' in msg
  assert 'Wardrobe:' in msg and 'tailor' not in msg.lower()[:35]
  assert any(x in msg for x in ('skort','overskirt'))
  assert 'Story and location:' in msg and 'Visible moment:' in msg and 'Two story clues:' in msg
  assert photo['field_count']==21 and photo['image_generated'] is False
  assert Path(result['pending_zip']).is_file() and zipfile.is_zipfile(result['pending_zip'])
  print(f'{lane}: {len(msg)} characters, {photo["message_sha256"][:12]}, 21 sources verified')
print('3 detailed role trials passed (no photos created)')
