"""V3.2 creative hosiery details are preserved when chosen, optional when not."""
from pathlib import Path
import json, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fast_start import stage_curate,stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button

choice={
 'world':'romantic vintage railway','role':'night flower courier',
 'scene':'art-deco luxury sleeper-train corridor','lane':'story',
 'shot':'eye-level environmental three-quarter portrait',
 'shot_english':'Eye-level three-quarter portrait with face, hands and outfit comfortably readable.',
 'moment':'last ribbon before delivering flowers','moment_english':'finishing the last ribbon before the delivery',
 'costume_mode':'bespoke','camera_intensity':'medium',
 'camera_style':{
   'name':'train night 35mm photograph','medium':'fine-grain 35mm color film',
   'optics':'a natural 50mm portrait lens','lighting':'soft brass lamps and cool rainy window light',
   'palette':'deep teal, oxblood red and warm amber','texture':'realistic velvet grain and soft glass reflections',
   'framing':'an intimate carriage corridor environmental portrait'},
 'creative_intent':'A tender night-train flower delivery with refined coordinated fashion.'
}
scene={
 'subject':'A clearly adult East Asian night flower courier prepares a special bouquet for a passenger traveling aboard an elegant old sleeper train.',
 'setting':'The vintage train has polished wooden corridors, gold brass lamps, compartment numbers and indigo rain beyond tall windows.',
 'action':'She finishes a burgundy satin bow around white flowers, then looks up in gentle delight at someone approaching along the corridor.',
 'cue1':'A wicker flower carrier beside her holds individually tagged bouquets with wax-paper wrappings and soft pink ribbons.',
 'cue2':'A leather satchel tucked against her hip carries handwritten message cards, compartment labels, and a neatly organized delivery notebook.',
 'wardrobe':'Teal velvet jacket, cream bow blouse, oxblood mini skirt, fine 20-denier smoky-black tights with a subtle back seam, and lace-up boots.',
 'composition':'Natural three-quarter portrait, clear face, hands and outfit.'
}
with tempfile.TemporaryDirectory() as tmp:
 for label,wardrobe,has_hosiery in [
  ('fine',scene['wardrobe'],True),
  ('other','Teal velvet jacket, cream bow blouse, oxblood pleated skirt, polished leather boots and small pearl earrings.',False)]:
  pending=Path(tmp)/label
  scene2=dict(scene,wardrobe=wardrobe)
  brief=Path(tmp)/(label+'.json');brief.write_text(json.dumps({'choice':choice,'scene_design':scene2},ensure_ascii=False),encoding='utf-8')
  stage_curate(pending,brief)
  stage_finish(pending,pending/'scene-design.json','new_chat')
  response=verify_from_pending(pending)
  verify_button(pending,'new_chat',pending/'button_manifest.json')
  message=response['message']
  assert wardrobe in message
  assert ('20-denier smoky-black tights with a subtle back seam' in message)==has_hosiery
  assert message.count('Wardrobe:')==1
  assert 'Eye-level three-quarter portrait' in message
  assert 1450 <= len(message) <= 3300
  assert json.loads((pending/'manifest.json').read_text())['version']=='3.5'
 print('PASS: refined hosiery kept in full, optional otherwise; 21-field seal + original camera + button verified')
