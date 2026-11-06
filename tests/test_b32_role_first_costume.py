"""B3.2 proves role/material first; protects old signed source compatibility in separate regression checks."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button
from role_first_costume import VERSION, validate_costume_plan

class RoleFirstWardrobeTests(unittest.TestCase):
    def test_two_distinct_costume_materials_and_climate(self):
        for name,material in [('winter-knight','steel'),('desert-pilot','nylon')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                brief=json.loads((ROOT/f'references/B3.2-{name}-fixture.json').read_text())
                stage_curate(Path(tmp)/'pending',ROOT/f'references/B3.2-{name}-fixture.json')
                stage_finish(Path(tmp)/'pending',Path(tmp)/'pending/scene-design.json')
                verify_from_pending(Path(tmp)/'pending')
                verify_button(Path(tmp)/'pending','new_chat',Path(tmp)/'pending/button_manifest.json')
                d=json.loads((Path(tmp)/'pending/draw.json').read_text())
                msg=(Path(tmp)/'pending/photo-creation-message.txt').read_text()
                self.assertEqual(d['version'],VERSION)
                self.assertNotIn('charm_index',d)
                self.assertNotIn('skin_exposure_boost_pct',d)
                self.assertNotIn('Charm 85/100',msg)
                self.assertNotIn('+50% skin-and-line',msg)
                self.assertIn(material,msg.lower())
                self.assertIn('Keep the role',msg)
                if name=='winter-knight':
                    self.assertIn('snow',msg.lower())
                    self.assertIn('armor',msg.lower())
                    self.assertNotIn('linen',msg.lower())
    def test_camera_cannot_invent_linen(self):
        b=json.loads((ROOT/'references/B3.2-winter-knight-fixture.json').read_text())
        plan=b['choice']['costume_plan']
        with self.assertRaisesRegex(ValueError,'camera texture introduces a material'):
            validate_costume_plan(plan,b['scene_design']['wardrobe'], 'damp linen folds, aged steel')
    def test_actual_outfit_must_include_material(self):
        b=json.loads((ROOT/'references/B3.2-winter-knight-fixture.json').read_text())
        with self.assertRaisesRegex(ValueError,'must actually name chosen garment material'):
            validate_costume_plan(b['choice']['costume_plan'],'Loose generic linen crop top and skirt',b['choice']['camera_style']['texture'])
    def test_hosiery_no_dice_or_mandate(self):
        b=json.loads((ROOT/'references/B3.2-desert-pilot-fixture.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            stage_curate(Path(tmp)/'p',ROOT/'references/B3.2-desert-pilot-fixture.json')
            d=json.loads((Path(tmp)/'p/draw.json').read_text())
            self.assertEqual(d['hosiery_style_hint'],'leave_to_role_design')
            self.assertNotIn('hosiery_dice',d)

if __name__=='__main__': unittest.main()
