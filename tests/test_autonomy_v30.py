"""End-to-end artist choice, optional genuine lottery, and button hashes."""
import json, tempfile, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fast_start import stage_curate,stage_draw,stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button

scene={
'subject':'A clearly adult East Asian tideglass archival conservator, carefully restoring a rare flooded coastal map in a near-future library.',
'setting':'An inhabited floating archival library on a dawnlit inlet, with shelved atlases, brass hinge clamps, soft lamps and restoration trays along a weathered workbench.',
'action':'She eases a damp parchment map onto a fine mesh support, touching the margin with her left hand as she gently coaxes an old water stain apart using a soft brush.',
'cue1':'A conservation workbench carries specialized paper repair brushes, handmade blotter sheets and weights protecting the old cartographic artifact.',
'cue2':'A discreet archive keeper insignia sewn onto her fitted jacket and an inventory seal on the map case identify a trained preservation specialist.',
'wardrobe':'Pale seafoam fitted bolero, ink-blue pleated skirt, silk waist sash, pearl fasteners and elegant low boots designed as a unique guardian costume.',
'composition':'Close, affectionate portrait balancing clear face and archival task.',
}
choice={
'world':'near-future floating coastal archive','role':'tideglass archival conservator',
'scene':'floating coastal archival library at dawn','lane':'career',
'shot':'intimate medium documentary portrait','shot_english':'Intimate waist-up portrait with the heroine, hands and fragile map in focus.',
'moment':'在晨光中抢救浸水古地图','moment_english':'saving a delicate artifact during the first morning sunlight',
'costume_mode':'bespoke','camera_intensity':'medium',
'camera_style':{'name':'bespoke salt-light documentary','medium':'an archival medium-format digital camera',
  'optics':'a 50mm lens with soft spatial falloff','lighting':'low sunrise through clear boat windows',
  'palette':'pearl seafoam and soft amber','texture':'fine paper fibers and warm skin detail',
  'framing':'a restrained human-scale documentary frame'},
'creative_intent':'A quiet, intimate scene about preservation rather than a forced statistical genre.',
}
with tempfile.TemporaryDirectory() as tmp:
 base=Path(tmp)
 brief=base/'brief.json';brief.write_text(json.dumps({'choice':choice,'scene_design':scene},ensure_ascii=False),encoding='utf-8')
 chosen=base/'chosen'; result=stage_curate(chosen,brief)
 d=json.loads((chosen/'draw.json').read_text(encoding='utf-8'))
 assert d['mode']=='chosen' and d['decision_owner']=='assistant' and d['costume_mode']=='bespoke'
 assert d['camera_pack_id'].startswith('original-')
 out=stage_finish(chosen,chosen/'scene-design.json')
 relay=verify_from_pending(chosen)
 verify_button(chosen,'new_chat',chosen/'button_manifest.json')
 assert relay['field_count']==21 and 1450<=len(relay['message'])<=3300
 assert 'tideglass archival conservator' in relay['message']
 assert out['image_generated']==False
 assert json.loads((chosen/'manifest.json').read_text())['version']=='3.5'
 # Story-first creation without a job is a first-class choice in v3.
 story_choice=dict(choice,role='dawn ferry letter keeper',lane='story',
                   moment='黎明时分将一封未寄出的信收回口袋',
                   moment_english='putting an unsent letter gently back into her coat at dawn',
                   creative_intent='One small story about hesitation rather than a profession.')
 story_scene=dict(scene,
  subject='A clearly adult East Asian dawn ferry letter keeper quietly deciding whether to mail a handwritten note on a calm sunrise crossing.',
  setting='A small wooden river ferry in the pink morning mist, with folded tickets, a worn rail, a weathered wooden seat and distant shore lanterns.',
  action='She folds a handwritten letter on her lap, hesitates by the ferry rail and places the unsealed envelope back into her jacket pocket.',
  cue1='A pale blue envelope bearing a tiny pressed flower and an unbroken wax seal sits half-visible by her coat cuff.',
  cue2='A single unused boarding receipt and a softly glowing lantern beside the ferry seat reinforce the early-morning decision.',
  wardrobe='Soft dove-blue short coat, embroidered ivory waistcoat, pleated skirt, delicate scarf and matte boots in a cohesive romantic silhouette.')
 b2=base/'story-brief.json';b2.write_text(json.dumps({'choice':story_choice,'scene_design':story_scene},ensure_ascii=False),encoding='utf-8')
 sd=base/'story';stage_curate(sd,b2)
 stage_finish(sd,sd/'scene-design.json')
 m2=verify_from_pending(sd)
 assert 'Visible moment:' in m2['message'] and 'Two story clues:' in m2['message']
 assert 'Dawn' in m2['message'] or 'dawn' in m2['message']
 assert len(m2['message'])<=3650
 verify_button(sd,'new_chat',sd/'button_manifest.json')
 # A second test verifies that a deliberate assistant decision to use randomness
 # remains supported without imposing it on every artistic choice.
 random_dir=base/'random';roll=stage_draw(random_dir,root/'references/history.jsonl',seed=123)
 assert roll['mode']=='random' and roll['decision_method']=='assistant_chose_randomization'
 assert roll['version']=='2.5'
 print(json.dumps({'chosen_mode':'PASS','optional_random':'PASS','full_21_field_seal':'PASS',
   'button':'PASS','story_first_nonprofessional':'PASS','delivered_characters':len(relay['message']),
   'reference_face':'PRESENT','image_generated':False},ensure_ascii=False))
