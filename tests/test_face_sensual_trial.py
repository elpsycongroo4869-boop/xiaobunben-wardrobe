"""Current adult face and global sensual-costume redesign, without image generation."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_role_costume_first import make_brief
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button
from face_sensual_trial import REVISION, FACE_ZH, FACE_EN, QUALITY_PREFIX, FACE_SOURCE_NOTE


OUTFITS = {
    'knight': (
        'Etched steel cuirass with corset-seamed waist, articulated pauldrons, leather straps and open side-waist panels; asymmetric segmented tassets over fitted shorts.',
        ['corset-seamed waist', 'open side-waist panels'],
        'Redesign the armor with corset seams and open side-waist panels while retaining steel plates and articulated shoulder protection.'),
    'airline pilot': (
        'Navy wool-blend cropped pilot jacket with gold epaulettes, sculpted waist and open side-waist panels; cotton wrap shirt, high-waist slit skirt and silk neck scarf.',
        ['cropped pilot jacket', 'open side-waist panels', 'high-waist slit skirt'],
        'Shorten and sculpt the flight jacket, open its side-waist panels and shape the skirt slit while retaining uniform rank details.'),
    'winter ranger': (
        'Forest-green waxed-canvas short parka with corset-seamed waist, open front and storm cuffs; high-cut wool bodysuit, leather gloves and fur-trimmed hood inside the heated hut.',
        ['corset-seamed waist', 'high-cut wool bodysuit'],
        'Retain the field parka and winter materials, but shape its waist and open its front over a high-cut fitted layer inside the heated hut.'),
    'lavender distiller': (
        'Linen work apron with corset-seamed waist, open sides, brass buckles and a high curved hem over a fitted violet cotton dress with an open back.',
        ['open sides', 'high curved hem', 'open back'],
        'Redesign the apron with an open-sided waist and curved hem over an open-back dress, keeping the linen work apron and brass buckles.'),
}


def make_trial_brief(role):
    brief = make_brief(role)
    wardrobe, anchors, adaptation = OUTFITS[role]
    brief['scene_design']['wardrobe'] = wardrobe
    brief['choice']['costume_plan']['sensual_design_anchors'] = anchors
    brief['choice']['costume_plan']['feminine_adaptation'] = adaptation
    return brief


def prepare(folder, brief, *, current=True):
    folder.mkdir()
    path = folder / 'brief.json'
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding='utf-8')
    pending = folder / 'pending'
    stage_curate(pending, path, role_costume_first=True, face_sensual_trial=current)
    stage_finish(pending, pending / 'scene-design.json')
    record = verify_from_pending(pending)
    verify_button(pending, 'new_chat', pending / 'button_manifest.json')
    return pending, record


class FaceSensualTrialTests(unittest.TestCase):
    def test_new_face_and_concrete_designs_across_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            for index, role in enumerate(OUTFITS):
                with self.subTest(role=role):
                    brief = make_trial_brief(role)
                    pending, record = prepare(Path(temporary) / str(index), brief)
                    draw = json.loads((pending / 'draw.json').read_text('utf-8'))
                    manifest = json.loads((pending / 'manifest.json').read_text('utf-8'))
                    details = json.loads((pending / 'english-details.json').read_text('utf-8'))
                    message = record['message']
                    self.assertTrue(message.startswith(QUALITY_PREFIX + '\n((请创建一张照片))\n'))
                    self.assertEqual(message.count(QUALITY_PREFIX), 1)
                    self.assertEqual(manifest['quality_prompt_prefix'], QUALITY_PREFIX)
                    self.assertEqual(manifest['face_delivery_mode'], 'text_only')
                    self.assertNotIn(FACE_SOURCE_NOTE, message)
                    self.assertNotIn('Face reference', message)
                    self.assertNotIn('ChatGPT Library', message)
                    self.assertNotIn('xiaobunben-selected-reference', (pending / 'shoot.json').read_text('utf-8'))
                    self.assertNotIn('xiaobunben-standard-face-crop', (pending / 'shoot.json').read_text('utf-8'))
                    self.assertEqual(draw['face_profile_zh'], FACE_ZH)
                    self.assertEqual(draw['face_profile_status'], 'provisional_user_setting')
                    self.assertEqual(manifest['art_direction_revision'], REVISION)
                    self.assertEqual(manifest['version'], REVISION)
                    self.assertEqual(record['art_direction_revision'], REVISION)
                    self.assertIn(FACE_EN, message)
                    self.assertIn('age 20', message)
                    self.assertIn('high nasal bridge', message)
                    self.assertIn('lower-eyelid rolls', message)
                    self.assertIn('pointed chin and thin lips', message)
                    self.assertNotIn('small straight nose', message)
                    self.assertNotIn('rose lips', message)
                    self.assertNotIn('xiaobunben-standard-face-crop', message)
                    self.assertIsNone(record['reference_asset'])
                    self.assertIsNone(record['reference_library_path'])
                    self.assertIsNone(manifest['reference_asset_sha256'])
                    self.assertIn(brief['scene_design']['wardrobe'], message)
                    for anchor in brief['choice']['costume_plan']['sensual_design_anchors']:
                        self.assertIn(anchor, message)
                    self.assertIn('sexy feminine version of the role costume', message)
                    self.assertIn('tools face their actual user, not the camera', message)
                    self.assertNotIn('Charm 85/100', message)
                    self.assertNotIn('+50%', message)
                    self.assertEqual(len(details['fields']), 21)
                    self.assertFalse(record['image_generated'])
                    self.assertFalse(record['success_sample_registration_enabled'])
                    self.assertLessEqual(len(message), 2300)
                    print(f'TRIAL PASS: {role}, {len(message)} chars, face and garment anchors delivered')

    def test_story_expression_physics_and_camera_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            brief = make_trial_brief('knight')
            _, current = prepare(folder / 'current', brief)
            _, original = prepare(folder / 'original', brief, current=False)
            def sections(message):
                return {part.split(':', 1)[0]: part for part in message.split('\n\n') if ':' in part}
            new, old = sections(current['message']), sections(original['message'])
            for label in ('Scene', 'Emotional tone', 'Action', 'Expression', 'Clues', 'Body mechanics', 'Camera'):
                self.assertEqual(new[label], old[label], label)
            self.assertIn('Face reference (face only)', original['message'])

    def test_current_entry_requires_a_concrete_sensual_redesign(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'sensual_design_anchors'):
                prepare(Path(temporary) / 'missing', make_brief('knight'))
            generic = make_trial_brief('knight')
            generic['choice']['costume_plan']['sensual_design_anchors'] = ['sexy outfit']
            with self.assertRaisesRegex(ValueError, 'specific garment construction'):
                prepare(Path(temporary) / 'generic', generic)

    def test_previous_trial_without_delivery_snapshot_keeps_original_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / 'brief.json'
            path.write_text(json.dumps(make_trial_brief('knight')), encoding='utf-8')
            pending = folder / 'pending'
            stage_curate(pending, path, role_costume_first=True, face_sensual_trial=True)
            draw_path = pending / 'draw.json'
            draw = json.loads(draw_path.read_text('utf-8'))
            for key in ('delivery_style_revision', 'quality_prompt_prefix', 'face_delivery_mode'):
                draw.pop(key)
            draw['face_reference_policy'] = 'provisional_text_only_old_photo_inactive'
            draw_path.write_text(json.dumps(draw, ensure_ascii=False), encoding='utf-8')
            stage_finish(pending, pending / 'scene-design.json')
            record = verify_from_pending(pending)
            verify_button(pending, 'new_chat', pending / 'button_manifest.json')
            self.assertTrue(record['message'].startswith('((请创建一张照片))\n'))
            self.assertIn(FACE_SOURCE_NOTE, record['message'])
            self.assertNotIn(QUALITY_PREFIX, record['message'])
            self.assertNotIn('delivery_style_revision', record)

    def test_redesign_must_be_present_in_actual_outfit(self):
        with tempfile.TemporaryDirectory() as temporary:
            brief = make_trial_brief('knight')
            brief['scene_design']['wardrobe'] = brief['scene_design']['wardrobe'].replace('open side-waist panels', 'solid side panels')
            with self.assertRaisesRegex(ValueError, 'sensual costume design missing'):
                prepare(Path(temporary) / 'case', brief)

    def test_default_cli_uses_current_face_and_costume_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / 'brief.json'
            path.write_text(json.dumps(make_trial_brief('winter ranger')), encoding='utf-8')
            pending = folder / 'pending'
            entry = [sys.executable, str(ROOT / 'scripts/role_first_start.py')]
            for command in (
                    ['curate', '--pending', str(pending), '--creative-brief', str(path)],
                    ['finish', '--pending', str(pending), '--scene-design', str(pending / 'scene-design.json')],
                    ['verify', '--pending', str(pending)]):
                result = subprocess.run(entry + command, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['art_direction_revision'], REVISION)


if __name__ == '__main__':
    unittest.main(verbosity=2)
