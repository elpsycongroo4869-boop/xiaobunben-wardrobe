import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from render_open import render_card
from role_profile import validate_profile
from story_compiler import canonical, sha
from story_seal import assemble, json_data, prepare, read_zip, verify_archive
from wardrobe_version import VERSION
from world_cards import DEFAULT_DECK, select_cards

EXAMPLES = ROOT / 'examples'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


class Candidate(unittest.TestCase):
    def setUp(self):
        self.woman = load(EXAMPLES / 'role-new-woman.json')
        self.man = load(EXAMPLES / 'role-existing-gpt-man.json')
        self.brief = load(EXAMPLES / 'brief-woman.json')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)

    def seal(self, brief=None, profile=None, route='copy_only'):
        return assemble(brief or self.brief, profile or self.woman, {}, route, str(uuid4()))

    def test_new_woman_keeps_age_face_and_build(self):
        _, files, button, notes, status = self.seal()
        for value in (self.woman['appearance'], self.woman['build'], 'adult age 38'):
            self.assertIn(value, button['full_user_message'])
        self.assertEqual(len(notes['sections']), 6)
        self.assertEqual(len(json_data(files['english-details.json'])['fields']), 21)
        self.assertEqual(sha(files['photo-creation-message.txt']), button['source_message_sha256'])
        self.assertEqual(status['display_labels']['library_browsed'], '否')
        draw = json_data(files['draw.json'])
        self.assertEqual(draw['version'], VERSION)
        self.assertEqual(draw['role_profile_sha256'], sha(canonical(self.woman)))
        self.assertLessEqual(len(button['full_user_message']) * 10, draw['source_character_count'] * 7)

    def test_imported_existing_gpt_keeps_male_appearance(self):
        brief = load(EXAMPLES / 'brief-man.json')
        _, files, button, _, _ = self.seal(brief, self.man)
        role = json_data(files['role-profile.json'])
        self.assertEqual(role, self.man)
        self.assertEqual(role['source'], 'existing_gpt')
        message = button['full_user_message']
        expected_character = (
            f"Character: {self.man['identity']}, adult age {self.man['age']}. "
            f"{self.man['appearance']}"
        )
        lines = message.splitlines()
        self.assertEqual([line for line in lines if line.startswith('Character: ')], [expected_character])
        detail = brief['choice']['costume_plan']['visible_style_detail']
        self.assertEqual([line for line in lines if line.startswith('Outfit: ')],
                         [f"Outfit: {detail} {brief['scene_design']['wardrobe']}"])

    def test_hands_only_leaves_face_build_and_unseen_clothes_out(self):
        hands = load(Path(__file__).parent / 'fixtures' / 'hands-only.json')
        _, files, button, _, _ = self.seal(hands, self.man)
        message = button['full_user_message']
        self.assertNotIn(self.man['appearance'], message)
        self.assertNotIn(self.man['build'], message)
        self.assertNotIn('resoled brown boots', message)
        self.assertIn('About 0.45 m from the subject', message)
        self.assertIn('Close-up framing. The fingertips meeting the film edge', message)
        self.assertIn('Outfit: Buttoned cuffs pull the indigo sleeve', message)
        self.assertIn('resoled brown boots', files['photographer-selection.json'].decode())

    def test_kneeling_shot_keeps_camera_height_distance_and_crop_separate(self):
        camera = self.brief['camera_plan']
        camera.update(viewpoint='At knee height by the wall, looking across her braced arm',
                      subject_distance_m=2.8, frame_extent='knee')
        scene = self.brief['scene_design']
        scene['action_physics'] = (
            'Her right knee rests on the floor and her left palm braces on the sill as her right thumb holds the knob.'
        )
        self.brief['complete_world']['full_action'] += ' She lowers her right knee to the floor for support.'
        framing = 'Her braced knee and the thumb pressing the knob stay in the same frame.'
        self.brief['choice']['camera_style']['framing'] = framing
        _, files, button, _, _ = self.seal()
        lines = button['full_user_message'].splitlines()
        camera_line = next(line for line in lines if line.startswith('Camera: '))
        frame_line = next(line for line in lines if line.startswith('Frame: '))
        self.assertIn('At knee height by the wall', camera_line)
        self.assertIn('About 2.8 m from the subject', camera_line)
        self.assertNotIn('knee-level', camera_line)
        self.assertIn('Knee-up framing. ' + framing, frame_line)
        self.assertIn('Body mechanics: ' + scene['action_physics'], lines)
        fields = json_data(files['english-details.json'])['fields']
        self.assertIn(fields['shot_and_distance'], camera_line)
        self.assertIn(fields['framing'], frame_line)

    def test_unset_or_invalid_camera_distance_cannot_create_a_seal(self):
        camera = self.brief['camera_plan']
        del camera['subject_distance_m']
        pending = self.path / 'invalid'
        with self.assertRaisesRegex(ValueError, 'camera_plan.*subject_distance_m'):
            prepare(pending, self.brief, self.woman, DEFAULT_DECK, 'copy_only')
        self.assertFalse(pending.exists())
        for distance in (False, 0, -1, 'near', float('inf'), float('nan')):
            with self.subTest(distance=distance):
                camera['subject_distance_m'] = distance
                with self.assertRaisesRegex(ValueError, 'subject_distance_m'):
                    self.seal()

    def test_photographer_may_leave_entire_outfit_out(self):
        hands = load(Path(__file__).parent / 'fixtures' / 'hands-only.json')
        hands['scene_design']['wardrobe'] = ''
        hands['choice']['costume_plan']['material_anchors'] = []
        hands['choice']['costume_plan']['construction_anchors'] = []
        hands['choice']['costume_plan']['visible_style_detail'] = ''
        hands['choice']['camera_style']['texture'] = 'Translucent film edges and fine scratches on the glass'
        hands['choice']['camera_style']['lighting'] = 'The amber inspection plate lights the film; a tungsten bulb edges the fingers'
        _, _, button, _, _ = self.seal(hands, self.man)
        self.assertNotIn('Outfit:', button['full_user_message'])

    def test_photographer_need_not_invent_exclusions(self):
        self.brief['photographer_selection']['offscreen_not_requested'] = []
        self.seal()

    def test_offscreen_outfit_cannot_leak_through_light(self):
        self.brief['choice']['camera_style']['lighting'] += '; lights the black rubber waders'
        with self.assertRaisesRegex(ValueError, 'leaked'):
            self.seal()

    def test_visible_costume_anchors_stay_bound(self):
        self.brief['choice']['costume_plan']['construction_anchors'] = ['buttoned cuffs']
        with self.assertRaisesRegex(ValueError, 'construction missing'):
            self.seal()

    def test_selected_styling_opens_outfit_and_matches_sealed_scene(self):
        detail = self.brief['choice']['costume_plan']['visible_style_detail']
        expected = f"{detail} {self.brief['scene_design']['wardrobe']}"
        result = prepare(self.path / 'styling', self.brief, self.woman, DEFAULT_DECK, 'new_chat')
        _, files = verify_archive(result['pending_zip'], result['manifest_sha256'])
        self.assertIn('Outfit: ' + expected, files['photo-creation-message.txt'].decode().splitlines())
        self.assertEqual(json_data(files['scene-design.json'])['wardrobe'], expected)
        selected = json_data(files['photographer-selection.json'])['photographer_selection']
        self.assertEqual(selected['delivered_wardrobe'], expected)
        self.assertEqual(json_data(files['english-details.json'])['fields']['outfit_and_function'], expected)

    def test_visible_style_needs_a_construction_from_the_design(self):
        plan = self.brief['choice']['costume_plan']
        self.brief['scene_design']['wardrobe'] += ' The sleeves end in rolled cuffs.'
        plan['visible_style_detail'] = 'The jacket has a stylish and distinctive silhouette.'
        with self.assertRaisesRegex(ValueError, 'construction anchor from style_adaptation'):
            self.seal()

    def test_visible_outfit_can_leave_a_named_design_outside_the_crop(self):
        plan = self.brief['choice']['costume_plan']
        plan.update(visible_style_detail='', construction_anchors=['checked undershirt'],
                    style_adaptation='The narrow belt shapes the station jacket below the crop.')
        with self.assertRaisesRegex(ValueError, 'style adaptation is out of frame'):
            self.seal()
        self.brief['camera_plan']['frame_extent'] = 'close'
        self.brief['photographer_selection']['offscreen_not_requested'].append('narrow belt')
        _, _, button, _, _ = self.seal()
        self.assertIn('Outfit: A rust-red cotton station jacket', button['full_user_message'])
        self.assertNotIn('narrow belt', button['full_user_message'])

    def test_missing_or_duplicated_emotion_does_not_pass(self):
        missing = deepcopy(self.brief)
        del missing['emotion_review']
        with self.assertRaisesRegex(ValueError, 'creative brief'):
            self.seal(missing)
        self.brief['scene_design']['cue1'] += ' A sign repeats professional concentration.'
        with self.assertRaisesRegex(ValueError, 'Repeated emotional'):
            self.seal()

    def test_exact_six_notes_and_budget(self):
        oversized = deepcopy(self.brief)
        oversized['creative_notes']['story'] = '字' * 651
        with self.assertRaisesRegex(ValueError, 'creative_notes.story'):
            self.seal(oversized)
        self.brief['creative_notes'] = {key: '字' * 526 for key in self.brief['creative_notes']}
        with self.assertRaisesRegex(ValueError, '3150'):
            self.seal()

    def test_profile_is_explicitly_adult_and_reference_rights_are_required(self):
        for age in (True, 17, '43', 43.1):
            with self.subTest(age=age), self.assertRaises(ValueError):
                validate_profile({**self.man, 'age': age})
        with self.assertRaisesRegex(ValueError, 'rights'):
            validate_profile({**self.woman, 'reference_image': {'description': 'Example', 'rights_confirmed': False}})

    def test_original_draws_never_read_world_deck(self):
        with patch('world_cards.load_index', side_effect=AssertionError('world I/O')):
            result = prepare(self.path / 'new', self.brief, self.woman, self.path / 'missing.json', 'new_chat')
        self.assertTrue(result['verified'])
        self.assertFalse(result['image_generated'])
        self.assertIsNone(result['open_card'])

    def test_adopted_world_is_snapshotted_and_verifies_without_deck(self):
        audit = self.brief['creative_audit']
        audit.update(library_adopted=True, adopted_card_ids=['O002'],
                     adoption_note='The tide window becomes the mechanical station reading.')
        deck = self.path / 'cards.json'
        deck.write_bytes(DEFAULT_DECK.read_bytes())
        result = prepare(self.path / 'new', self.brief, self.woman, deck, 'copy_only')
        deck.unlink()
        _, files = verify_archive(result['pending_zip'], result['manifest_sha256'])
        self.assertEqual(list(json_data(files['cited-worlds.json'])), ['O002'])
        self.assertFalse(json_data(files['creative-status.json'])['audit']['library_browsed'])

    def test_unknown_world_is_rejected(self):
        audit = self.brief['creative_audit']
        audit.update(library_adopted=True, adopted_card_ids=['missing'], adoption_note='Specific idea went into scene.')
        with self.assertRaisesRegex(ValueError, 'Unknown world'):
            select_cards(audit)

    def test_byte_tampering_and_fake_manifest_are_detected(self):
        result = prepare(self.path / 'new', self.brief, self.woman, DEFAULT_DECK, 'copy_only')
        files = read_zip(result['pending_zip'])
        files['photo-creation-message.txt'] += b'changed'
        tampered = self.path / 'tampered.zip'
        with ZipFile(tampered, 'x') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            verify_archive(tampered)
        manifest = json_data(files['manifest.json'])
        manifest['files']['photo-creation-message.txt'] = sha(files['photo-creation-message.txt'])
        files['manifest.json'] = canonical(manifest)
        with ZipFile(tampered, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        with self.assertRaisesRegex(ValueError, 'separately recorded'):
            verify_archive(tampered, result['manifest_sha256'])
        with self.assertRaisesRegex(ValueError, 'does not match'):
            verify_archive(tampered)

    def test_archive_rejects_nonportable_paths(self):
        bad = self.path / 'bad.zip'
        with ZipFile(bad, 'x') as archive:
            archive.writestr('../external.txt', 'never read or written outside the ZIP')
        with self.assertRaises(ValueError):
            read_zip(bad)
        self.assertFalse((self.path.parent / 'external.txt').exists())

    def test_two_concurrent_writers_preserve_first_result(self):
        def create():
            try:
                return prepare(self.path / 'same', self.brief, self.woman, DEFAULT_DECK, 'copy_only')
            except FileExistsError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(sum(r is not None for r in attempts), 1)
        result = next(r for r in attempts if r is not None)
        verify_archive(result['pending_zip'], result['manifest_sha256'])

    def test_new_path_recompiles_once_and_binds_native_host_route(self):
        with patch('story_seal.compile_story', wraps=__import__('story_compiler').compile_story) as spy:
            result = prepare(self.path / 'new', self.brief, self.woman, DEFAULT_DECK, 'new_chat')
        self.assertEqual(spy.call_count, 1)
        _, files = verify_archive(result['pending_zip'])
        button = json_data(files['button_manifest.json'])
        self.assertEqual(button['action'], 'GenUI.issueNewTurn')
        self.assertEqual(button['full_user_message'].encode(), files['photo-creation-message.txt'])

    def test_card_escapes_untrusted_text_and_starts_closed(self):
        _, _, button, notes, status = self.seal()
        notes['sections']['story'] = '<img src=x onerror=alert(1)> __STATUS__'
        button['full_user_message'] = '</script><script>alert(1)</script>'
        html = render_card(button, notes, status)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;img', html)
        self.assertIn('__STATUS__', html)
        self.assertIn('<details><summary>创作思路</summary>', html)
        self.assertIn('type="button" disabled', html)

    def test_clean_cli_author_and_verify_from_different_working_directory(self):
        cli = ROOT / 'scripts' / 'story_start.py'
        profile = EXAMPLES / 'role-existing-gpt-man.json'
        brief = EXAMPLES / 'brief-man.json'
        def run(*args):
            result = subprocess.run([sys.executable, str(cli), *map(str, args)], cwd=self.path,
                                    check=True, capture_output=True, encoding='utf-8')
            return json.loads(result.stdout)
        self.assertEqual(run('profile', '--file', profile)['source'], 'existing_gpt')
        request = run('author', '--profile', profile, '--output', self.path / 'request.txt')
        self.assertIn(self.man['appearance'], Path(request['author_request']).read_text(encoding='utf-8'))
        result = run('prepare', '--profile', profile, '--creative-brief', brief, '--pending', 'one')
        self.assertTrue(run('verify', '--pending', 'one', '--pin', result['manifest_sha256'])['verified'])

    def test_json_requires_unique_keys(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            json_data(b'{"name":"one","name":"two"}')


if __name__ == '__main__':
    unittest.main()
