"""Exercise saved design explanations, real disclosure markup and historical verification."""
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
from creative_notes import VERSION, REVISION, verify_bundle
from photo_creation_relay import verify_from_pending
from button_handoff import verify as verify_button


def brief():
    data = json.loads((ROOT / 'references/story-first-creative-fixture.json').read_text('utf-8'))
    data['creative_notes'] = json.loads((ROOT / 'references/creative-notes-example-v4.1.json').read_text('utf-8'))
    return data


def prepare(folder, data=None, route='new_chat'):
    folder.mkdir()
    source = folder / 'brief.json'
    source.write_text(json.dumps(data or brief(), ensure_ascii=False), encoding='utf-8')
    pending = folder / 'pending'
    stage_curate(pending, source, role_costume_first=True, face_sensual_trial=True, story_first=True)
    result = stage_finish(pending, pending / 'scene-design.json', route)
    return pending, result


class CreativeNotesTests(unittest.TestCase):
    def test_saved_before_generation_and_kept_out_of_the_image_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending, result = prepare(Path(tmp) / 'new')
            notes = verify_bundle(pending)
            photo = verify_from_pending(pending)
            button = json.loads((pending / 'button_manifest.json').read_text('utf-8'))
            manifest = json.loads((pending / 'manifest.json').read_text('utf-8'))
            self.assertEqual(photo['version'], VERSION)
            self.assertEqual(photo['art_direction_revision'], REVISION)
            self.assertEqual(manifest['version'], VERSION)
            self.assertEqual(notes['source_draw_id'], photo['draw_id'])
            self.assertEqual(notes['source_photo_message_sha256'], photo['message_sha256'])
            self.assertFalse(notes['image_observed'])
            self.assertEqual(notes['written_stage'], 'before_image_generation')
            self.assertEqual(button['full_user_message'], photo['message'])
            self.assertNotIn(brief()['creative_notes']['story'], photo['message'])
            self.assertEqual(button['creative_notes']['action'], 'local_reveal')
            self.assertFalse(button['creative_notes']['post_image_callback_available'])
            self.assertTrue(Path(result['creative_notes_button']).is_file())
            self.assertTrue(1100 <= len(photo['message']) <= 2300)
            verify_button(pending, 'new_chat', pending / 'button_manifest.json')

    def test_different_photographs_cannot_exchange_their_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, _ = prepare(Path(tmp) / 'first')
            second, _ = prepare(Path(tmp) / 'second')
            (second / 'creative-notes.json').write_bytes((first / 'creative-notes.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'source binding changed'):
                verify_bundle(second)

    def test_modified_notes_source_and_presentation_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending, _ = prepare(Path(tmp) / 'sealed')
            for filename in ('creative-notes.json', 'creative-notes.md', 'creative-notes-button.html', 'draw.json'):
                path = pending / filename
                original = path.read_bytes()
                if filename.endswith('.json'):
                    data = json.loads(original)
                    if filename == 'draw.json':
                        data['creative_notes']['story'] += ' changed'
                    else:
                        data['sections']['story'] += ' changed'
                    path.write_text(json.dumps(data), encoding='utf-8')
                else:
                    path.write_text(original.decode('utf-8') + '\nchanged', encoding='utf-8')
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    verify_bundle(pending)
                path.write_bytes(original)

    def test_hidden_local_disclosure_escapes_authored_text_and_supports_copy_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = brief()
            data['creative_notes']['story'] += ' <img src=x onerror=alert(1)>'
            pending, _ = prepare(Path(tmp) / 'safe', data, route='copy_only')
            markup = (pending / 'creative-notes-button.html').read_text('utf-8')
            self.assertIn('aria-expanded="false"', markup)
            self.assertIn('data-notes-content hidden', markup)
            self.assertIn('&lt;img src=x onerror=alert(1)&gt;', markup)
            self.assertNotIn('<img ', markup)
            self.assertNotIn('issueNewTurn', markup)
            verify_button(pending, 'copy_only', pending / 'button_manifest.json')

    def test_current_cli_requires_notes_and_prepares_all_saved_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / 'brief.json'
            pending = folder / 'pending'
            entry = [sys.executable, str(ROOT / 'scripts/story_start.py')]
            incomplete = brief()
            incomplete.pop('creative_notes')
            source.write_text(json.dumps(incomplete), encoding='utf-8')
            failed = subprocess.run(entry + ['curate', '--pending', str(pending), '--creative-brief', str(source)], capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(pending.exists())
            source.write_text(json.dumps(brief(), ensure_ascii=False), encoding='utf-8')
            for args in (
                ['curate', '--pending', str(pending), '--creative-brief', str(source)],
                ['finish', '--pending', str(pending), '--scene-design', str(pending / 'scene-design.json')],
                ['verify', '--pending', str(pending)],
            ):
                result = subprocess.run(entry + args, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['version'], VERSION)
            self.assertEqual(verify_bundle(pending)['version'], VERSION)


if __name__ == '__main__':
    unittest.main(verbosity=2)
