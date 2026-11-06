"""Exercise real sealing/delivery and role-clothing preservation; generate no images."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from button_handoff import verify as verify_button
from fast_start import stage_curate, stage_draw, stage_finish
from photo_creation_relay import verify_from_pending
from role_costume import REVISION, validate_plan


CASES = {
    'knight': {
        'context': 'A sheltered castle gate at the end of a cool evening patrol.',
        'foundation': 'Articulated metal armor, secured by leather straps, establishes the knight before feminine tailoring.',
        'wardrobe': 'Etched steel cuirass with a fitted waist, articulated pauldrons, leather straps and asymmetric segmented tassets; a narrow side opening above a dark fitted undersuit.',
        'materials': ['steel', 'leather'],
        'structures': ['articulated pauldrons', 'segmented tassets'],
        'adaptation': 'Fit the waist and shape asymmetric armor panels while retaining articulated protective construction.',
        'action': 'She holds the gate latch while checking that the portcullis chain has settled securely.',
        'cues': ['A lowered portcullis and guard banner frame the stone entry.', 'A shield bearing the castle crest rests beside the gatepost.'],
    },
    'airline pilot': {
        'context': 'An aircraft cockpit in cool morning light while preparing for departure.',
        'foundation': 'A pilot jacket with rank epaulettes and a cotton shirt establishes the uniform before tailoring.',
        'wardrobe': 'Navy wool-blend pilot jacket with gold epaulettes, a cotton shirt and tapered waist; high-waist pencil skirt and a silk neck scarf.',
        'materials': ['wool-blend', 'cotton', 'silk'],
        'structures': ['pilot jacket', 'gold epaulettes'],
        'adaptation': 'Refine the jacket waist and scarf drape while retaining the pilot uniform and its rank markings.',
        'action': 'She checks a heading selector with her right hand while watching the runway ahead.',
        'cues': ['Flight instruments glow in front of their seated operator.', 'The runway centerline recedes beyond the cockpit windscreen.'],
    },
    'winter ranger': {
        'context': 'Inside a heated ranger hut beside a snowy forest trail during a cold winter patrol.',
        'foundation': 'A lined parka with storm cuffs and gloves establishes cold-weather field clothing before feminine styling.',
        'wardrobe': 'Forest-green waxed-canvas parka with a fitted belt, wool lining and storm cuffs; leather gloves and a narrow fur-trimmed hood, slightly unfastened inside the heated hut.',
        'materials': ['waxed-canvas', 'wool', 'leather'],
        'structures': ['parka', 'storm cuffs'],
        'adaptation': 'Use a fitted belt and layered collar to shape the figure, with a slightly open outer layer in the warm hut.',
        'action': 'She holds the hut latch while checking the trail marker beyond the frost-edged window.',
        'cues': ['Snow-covered pines and a marked forest trail appear outside.', 'A ranger route map hangs beside the hut door facing its user.'],
    },
    'lavender distiller': {
        'context': 'A warm rural distillery during the lavender harvest, with open workshop doors.',
        'foundation': 'A work apron over a cotton-sleeved dress belongs to the harvest workshop and protects clothing during distillation.',
        'wardrobe': 'Linen work apron with a shaped waist, brass buckles and rolled cotton sleeves over a fitted violet dress.',
        'materials': ['Linen', 'cotton'],
        'structures': ['work apron', 'brass buckles'],
        'adaptation': 'Shape the apron waist and contrast the violet dress with natural linen, keeping the working layers intact.',
        'action': 'She rests a gloved hand on a copper valve while watching the first drops enter a flask.',
        'cues': ['A copper still feeds a glass receiver through a narrow tube.', 'Fresh lavender bundles lie beside the open workshop doorway.'],
    },
}


def make_brief(role):
    case = CASES[role]
    brief = json.loads((ROOT / 'references/candid-realism-creative-fixture.json').read_text('utf-8'))
    choice, design = brief['choice'], brief['scene_design']
    choice.update(world=case['context'], role=role, scene=case['context'],
                  creative_intent=f'Create a distinctive {role} portrait through role-specific clothing and feminine design.',
                  moment='Checking a small but meaningful detail near the end of her task.',
                  moment_english='checking a small detail near the end of her task',
                  emotion_tone='Quiet concentration, with a small trace of satisfaction after a demanding shift.',
                  shot='An eye-level waist-up candid focused on her face, role clothing and actual task.',
                  shot_english='Eye-level waist-up candid, with incidental objects naturally cropped.',
                  frame_extent='waist',
                  frame_intent='Keep the face, visible costume construction and working gesture readable within a waist-up crop.')
    choice['camera_style'] = {
        'name': 'Location-specific working portrait',
        'medium': 'Candid natural-light editorial photography',
        'optics': 'Natural 50mm portrait perspective',
        'lighting': 'Uneven ambient light across her face',
        'palette': 'Muted colors from this outfit and setting',
        'texture': 'Natural skin, worn surfaces and fine grain',
        'framing': 'Waist-up crop with incidental objects outside frame',
    }
    choice['costume_plan'] = {
        'context_and_climate': case['context'],
        'role_foundation': case['foundation'],
        'material_anchors': case['materials'],
        'construction_anchors': case['structures'],
        'feminine_adaptation': case['adaptation'],
    }
    design.update(subject=f'A clearly adult East Asian {role} attending to a meaningful detail of her work.',
                  setting=case['context'], action=case['action'],
                  cue1=case['cues'][0], cue2=case['cues'][1], wardrobe=case['wardrobe'],
                  composition='Waist-up candid; face, role clothing and task carry the story.',
                  expression='She watches her task with focused eyes and a faint, tired trace of satisfaction.',
                  action_physics='Her right elbow bends as her gloved fingers hold the control; her left hand rests at her waist.')
    return brief


def prepare(folder, brief, *, active=True):
    brief = copy.deepcopy(brief)
    if not active:
        brief['choice']['role_first_costume_design'] = False
    folder.mkdir()
    path = folder / 'brief.json'
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding='utf-8')
    pending = folder / 'pending'
    stage_curate(pending, path, role_costume_first=active)
    result = stage_finish(pending, pending / 'scene-design.json')
    record = verify_from_pending(pending)
    verify_button(pending, 'new_chat', pending / 'button_manifest.json')
    return pending, result, record


class RoleCostumeTests(unittest.TestCase):
    def test_distinct_roles_keep_materials_structures_and_styling(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for index, role in enumerate(CASES):
                with self.subTest(role=role):
                    brief = make_brief(role)
                    pending, result, record = prepare(folder / str(index), brief)
                    message = record['message']
                    draw = json.loads((pending / 'draw.json').read_text('utf-8'))
                    manifest = json.loads((pending / 'manifest.json').read_text('utf-8'))
                    details = json.loads((pending / 'english-details.json').read_text('utf-8'))
                    self.assertEqual(draw['art_direction_revision'], REVISION)
                    self.assertTrue(manifest['role_costume_first'])
                    self.assertEqual(record['costume_plan'], brief['choice']['costume_plan'])
                    self.assertEqual(len(details['fields']), 21)
                    self.assertIn(brief['scene_design']['wardrobe'], message)
                    for anchor in CASES[role]['materials'] + CASES[role]['structures']:
                        self.assertIn(anchor.casefold(), message.casefold())
                    self.assertIn('feminine tailoring', message)
                    self.assertNotIn('Charm 85/100', message)
                    self.assertNotIn('+50%', message)
                    self.assertNotIn('sheer lace/stockings', message)
                    self.assertNotIn('no bust', message)
                    self.assertIn('Body mechanics:', message)
                    self.assertFalse(record['image_generated'])
                    self.assertFalse(record['success_sample_registration_enabled'])
                    self.assertLessEqual(len(message), 2300)
                    self.assertGreaterEqual(len(message), 1100)
                    print(f'ROLE PASS: {role}, {len(message)} chars, anchors and 21 sources verified')

    def test_only_outfit_direction_changes_for_same_scene(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            brief = make_brief('airline pilot')
            _, _, active = prepare(folder / 'active', brief)
            _, _, legacy = prepare(folder / 'legacy', brief, active=False)
            left, right = active['message'].split('\n\n'), legacy['message'].split('\n\n')
            self.assertEqual(len(left), len(right))
            changed = [a.split(':', 1)[0] for a, b in zip(left, right) if a != b]
            self.assertEqual(changed, ['Outfit'])

    def test_missing_plan_blocks_new_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            brief = make_brief('knight')
            del brief['choice']['costume_plan']
            with self.assertRaisesRegex(ValueError, 'costume_plan'):
                prepare(Path(temporary) / 'case', brief)

    def test_dropped_material_or_structure_is_rejected(self):
        brief = make_brief('knight')
        for token in ('steel', 'articulated pauldrons'):
            with self.subTest(token=token):
                altered = brief['scene_design']['wardrobe'].replace(token, 'plain cloth')
                with self.assertRaisesRegex(ValueError, 'missing from wardrobe'):
                    validate_plan(brief['choice']['costume_plan'], altered)

    def test_new_clothing_budget_and_no_silent_truncation(self):
        self.assertGreater(len(make_brief('knight')['scene_design']['wardrobe']), 155)
        with tempfile.TemporaryDirectory() as temporary:
            brief = make_brief('knight')
            brief['scene_design']['wardrobe'] += ' ' + 'long textile description ' * 12
            brief['scene_design']['wardrobe'] = brief['scene_design']['wardrobe'].strip()
            with self.assertRaisesRegex(ValueError, 'exceeds 280'):
                prepare(Path(temporary) / 'case', brief)

    def test_camera_texture_cannot_invent_a_textile(self):
        with tempfile.TemporaryDirectory() as temporary:
            brief = make_brief('knight')
            brief['choice']['camera_style']['texture'] = 'Damp linen folds with natural skin texture and fine grain'
            with self.assertRaisesRegex(ValueError, 'Camera texture introduces a material'):
                prepare(Path(temporary) / 'case', brief)

    def test_random_entry_requires_a_designed_costume_before_finish(self):
        with tempfile.TemporaryDirectory() as temporary:
            pending = Path(temporary) / 'pending'
            draw = stage_draw(pending, ROOT / 'references/history.jsonl', seed=19,
                              role_costume_first=True)
            self.assertTrue(draw['role_costume_first'])
            design = Path(temporary) / 'design.json'
            design.write_text(json.dumps(make_brief('knight')['scene_design']), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'costume_plan'):
                stage_finish(pending, design)

    def test_cli_starts_and_verifies_current_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / 'brief.json'
            path.write_text(json.dumps(make_brief('winter ranger')), encoding='utf-8')
            pending = folder / 'pending'
            entry = [sys.executable, str(ROOT / 'scripts/role_first_start.py')]
            for command in (
                    ['curate', '--pending', str(pending), '--creative-brief', str(path), '--art-direction', 'role-first'],
                    ['finish', '--pending', str(pending), '--scene-design', str(pending / 'scene-design.json')],
                    ['verify', '--pending', str(pending)]):
                result = subprocess.run(entry + command, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['art_direction_revision'], REVISION)

    def test_delivered_message_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pending, _, record = prepare(Path(temporary) / 'case', make_brief('knight'))
            path = pending / 'photo-creation-message.txt'
            path.write_text(record['message'].replace('steel', 'linen'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'message was changed'):
                verify_from_pending(pending)


if __name__ == '__main__':
    unittest.main(verbosity=2)
