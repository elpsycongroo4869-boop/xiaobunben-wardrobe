"""Exercise the actual story/camera handoff, versioning and free legwear choices."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button
from face_sensual_trial import FACE_EN, QUALITY_PREFIX
from story_first import VERSION, REVISION


def brief():
    return json.loads((ROOT / 'references/story-first-creative-fixture.json').read_text('utf-8'))


def prepare(folder, data):
    folder.mkdir()
    source = folder / 'brief.json'
    source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    pending = folder / 'pending'
    stage_curate(pending, source, role_costume_first=True, face_sensual_trial=True, story_first=True)
    stage_finish(pending, pending / 'scene-design.json')
    record = verify_from_pending(pending)
    verify_button(pending, 'new_chat', pending / 'button_manifest.json')
    return pending, record


class StoryFirstTests(unittest.TestCase):
    def test_story_and_selected_camera_reach_the_actual_button_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = brief()
            pending, record = prepare(Path(tmp) / 'current', data)
            message = record['message']
            manifest = json.loads((pending / 'manifest.json').read_text('utf-8'))
            draw = json.loads((pending / 'draw.json').read_text('utf-8'))
            button = json.loads((pending / 'button_manifest.json').read_text('utf-8'))
            self.assertEqual(draw['version'], VERSION)
            self.assertEqual(manifest['version'], VERSION)
            self.assertEqual(record['version'], VERSION)
            self.assertEqual(record['art_direction_revision'], REVISION)
            self.assertTrue(message.startswith(QUALITY_PREFIX + '\n((请创建一张照片))'))
            self.assertLess(message.index('Story moment:'), message.index('Character:'))
            for value in (FACE_EN, data['story_plan']['moment'], data['camera_plan']['viewpoint'],
                          data['camera_plan']['optics'], data['scene_design']['wardrobe'],
                          data['scene_design']['cue1'], data['scene_design']['cue2']):
                self.assertIn(value, message)
            self.assertEqual(button['full_user_message'], message)
            self.assertEqual(record['field_count'], 21)
            self.assertTrue(manifest['hosiery_selected_in_wardrobe'])
            self.assertIsNone(record['reference_asset'])
            self.assertFalse(record['image_generated'])
            self.assertTrue(1100 <= len(message) <= 2300)
            self.assertNotIn('85/100', message)
            self.assertNotIn('+50%', message)

    def test_low_high_side_and_overhead_choices_survive_without_a_fixed_camera(self):
        cameras = (
            ('Low diagonal beside the bench, looking up toward her attentive profile', 'An 85mm lens with soft compression and a credible focus plane', 'knee'),
            ('High view from behind her left shoulder toward the violin case and her partial profile', 'A 35mm lens with environmental depth and natural perspective', 'waist'),
            ('Side-on view across the shelter, with her profile and the case at different depths', 'A 105mm lens compressing the distant tram lights', 'mid_thigh'),
            ('Near-overhead view into the shelter, with her upward-turned face and the open case', 'A 28mm lens with controlled wide-angle perspective', 'full'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, (viewpoint, optics, extent) in enumerate(cameras):
                with self.subTest(viewpoint=viewpoint):
                    data = brief()
                    data['camera_plan'].update(viewpoint=viewpoint, optics=optics, frame_extent=extent)
                    data['choice']['camera_style']['framing'] = 'A considered crop joining the heroine, violin case and tram lights'
                    data['scene_design']['composition'] = 'Join her face, the open case and the approaching tram lamps.'
                    _, record = prepare(Path(tmp) / str(index), data)
                    camera = next(p for p in record['message'].split('\n\n') if p.startswith('Camera:'))
                    self.assertIn(viewpoint, camera)
                    self.assertIn(optics, camera)
                    self.assertEqual(record['camera_plan']['frame_extent'], extent)

    def test_story_and_camera_decisions_are_required_before_starting(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index, key in enumerate(('story_plan', 'camera_plan')):
                data = brief()
                data.pop(key)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                    prepare(Path(tmp) / str(index), data)
            data = brief()
            data['camera_plan'].pop('optics')
            with self.assertRaisesRegex(ValueError, 'camera_plan.optics'):
                prepare(Path(tmp) / 'no-lens', data)

    def test_conflicting_lens_is_rejected_instead_of_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = brief()
            data['choice']['camera_style']['optics'] = 'A different 55mm lens copied from another camera'
            with self.assertRaisesRegex(ValueError, 'conflicts'):
                prepare(Path(tmp) / 'conflict', data)

    def test_hosiery_can_be_colored_or_freely_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index, (substitute, selected) in enumerate((('sheer deep-navy stockings with tiny embroidered stars', True), ('bare legs', False))):
                data = brief()
                data['scene_design']['wardrobe'] = data['scene_design']['wardrobe'].replace('sheer smoky-black stockings with fine floral jacquard and lace tops', substitute)
                pending, record = prepare(Path(tmp) / str(index), data)
                manifest = json.loads((pending / 'manifest.json').read_text('utf-8'))
                self.assertEqual(manifest['hosiery_selected_in_wardrobe'], selected)
                self.assertIn(substitute, record['message'])
                self.assertEqual(record['camera_plan'], data['camera_plan'])

    def test_story_and_viewpoint_snapshots_are_protected_by_the_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending, _ = prepare(Path(tmp) / 'sealed', brief())
            path = pending / 'draw.json'
            original = path.read_text('utf-8')
            for key, field in (('story_plan', 'moment'), ('camera_plan', 'viewpoint')):
                draw = json.loads(original)
                draw[key][field] += ' Changed after sealing.'
                path.write_text(json.dumps(draw), encoding='utf-8')
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_from_pending(pending)
                path.write_text(original, encoding='utf-8')

    def test_current_cli_verifies_a_sealed_version_four_without_upgrading_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pending, _ = prepare(folder / 'legacy', brief())
            entry = [sys.executable, str(ROOT / 'scripts/story_start.py')]
            for args in (['verify', '--pending', str(pending)],):
                result = subprocess.run(entry + args, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['version'], VERSION)


if __name__ == '__main__':
    unittest.main(verbosity=2)
