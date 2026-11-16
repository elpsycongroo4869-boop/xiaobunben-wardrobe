"""Public regression tests for Story/Point performance authority."""
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'src/wardrobe2-core'
sys.path.insert(0, str(CORE))
from ai_bridge import production_prompt
from studio import Studio, compose_render, digest, role_contract

CHAPTER = {
    'book_id': 'B199',
    **json.loads((CORE / 'curated/bookshelf_extension/cards/B199.json').read_bytes())['chapters'][2],
}
WINK = '演员向镜头眨了一下媚眼'
TEARS = '一滴眼泪从左眼滑落，右眼始终紧闭'
OLD_CONTEXT = '细眉轻抬，眼神明亮又带一点不可置信，唇间稍稍分开；不用夸张张嘴'
POINT = CHAPTER['point']
CONTEXT = '她发现两份海图有关键差异，知道这可能影响船员的安全，正在安静地确认自己的发现。'


def cartographer():
    return {
        'work_id': 'cartographer', 'origin': 'user_directed', 'book_id': 'B199',
        'render_profile': 'visual_intent_v1', 'render_policy': 'emotion_v1',
        'persona': {'adult': True, 'identity': 'Adult chartmaker',
                    'appearance': 'Brown eyes, arched eyebrows and a narrow nose'},
        'producer': dict(intent='Chart error', context='Port', event='Discovery',
                         moment=POINT, emotion='Quiet discovery'),
        'roles': {
            'scene': {'plan': 'Rain against the window', 'props': 'Two sea charts'},
            'wardrobe': {'full_outfit': 'Linen coat', 'visible_outfit': 'Linen sleeve'},
            'performance': {'emotional_context': CONTEXT},
            'lighting': {'plan': 'Light through wet paper'},
            'camera': {'plan': 'Medium framing', 'visible_frame': '她看向透光的两张海图，眉眼有柔和的窗光。'},
        },
    }


def lock(job, instruction, source='producer'):
    job['producer']['performance_lock'] = {
        'type': 'precise_local_action', 'instruction': instruction, 'source': source,
    }


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.job = cartographer()

    def test_t01_b199_context_and_prompt(self):
        job = self.job
        text = compose_render(job)
        self.assertIn(POINT, text)
        self.assertIn(CONTEXT, text)
        self.assertNotIn('眉梢微抬', text)
        selection = dict(origin='autonomous_library', book_id='B199', initial_intent='海图')
        prompt = production_prompt(selection, job['persona'], job['work_id'], emotional_context=True,
                                   selected_book={'title': '文艺复兴制图坊', 'world_logic': '以海图导航'},
                                   chapter=CHAPTER)
        self.assertIn(POINT, prompt)
        self.assertIn('performance{emotional_context}', prompt)
        self.assertIn('producer.performance_lock', prompt)
        self.assertIn('眉、眼、口、鼻', prompt)
        self.assertEqual(role_contract(emotional_context=True)['performance']['fields'], ['emotional_context'])
        job['roles']['performance']['emotional_context'] = OLD_CONTEXT
        with self.assertRaisesRegex(ValueError, 'performance.emotional_context'):
            compose_render(job)

    def test_t02_producer_wink(self):
        lock(self.job, WINK)
        self.assertIn(WINK, compose_render(self.job))

    def test_t03_shyness_without_generated_face_instructions(self):
        self.job['roles']['performance']['emotional_context'] = '她感到羞涩，担心被看穿，又盼对方明白。'
        result = compose_render(self.job)
        for action in ('脸红', '咬唇', '低头'):
            self.assertNotIn(action, result)

    def test_t04_producer_tear(self):
        line = '她流下了一滴眼泪'
        lock(self.job, line)
        self.assertIn(line, compose_render(self.job))

    def test_t05_camera_and_other_roles_cannot_add_local_directions(self):
        for role, field, line in (
            ('camera', 'visible_frame', '她眉梢微抬，唇微张'),
            ('camera', 'plan', '要求主角抬头'),
            ('camera', 'visible_frame', '鼻翼轻轻翕动'),
            ('camera', 'visible_frame', 'She studies the chart. Her lips are slightly parted.'),
            ('scene', 'plan', '让她伸手'),
            ('wardrobe', 'visible_outfit', '必须抬手'),
            ('lighting', 'plan', '使左眉上扬'),
        ):
            with self.subTest(role=role, field=field, line=line):
                job = deepcopy(self.job)
                job['roles'][role][field] = line
                with self.assertRaisesRegex(ValueError, rf'{role}\.{field}'):
                    compose_render(job)
        self.assertIn('Brown eyes, arched eyebrows and a narrow nose', compose_render(self.job))
        self.job['role_director'] = {'story_fit': '主角左眉上扬'}
        with self.assertRaisesRegex(ValueError, 'role_director.story_fit'):
            compose_render(self.job)

    def test_t06_no_inferred_lock(self):
        self.assertNotIn('Required performance:', compose_render(self.job))
        self.assertNotIn('performance_lock', self.job['producer'])

    def test_t07_keep_original_point(self):
        self.job['chapter'] = CHAPTER
        self.job['producer']['moment'] = 'Wrong replacement moment'
        text = compose_render(self.job)
        self.assertIn(POINT, text)
        self.assertNotIn('Wrong replacement moment', text)

    def test_t08_legacy_recompile_and_reopen(self):
        job = self.job
        job['render_policy'] = 'rc9_5'
        job['roles']['performance'] = {'expression': OLD_CONTEXT}
        expected = ('Create ONE new high-quality photorealistic cinematic still photograph. Do not edit an existing image.\n'
                    'Adult character: Adult chartmaker; appearance: Brown eyes, arched eyebrows and a narrow nose.\n'
                    + job['roles']['camera']['visible_frame'])
        work = {'protocol': 'wardrobe2-studio-p1', 'job': job, 'render_instruction': expected}
        envelope = dict(work=work, seal_sha256=digest(work), state='ready', confirmed_images=[])
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pending').mkdir()
            seal = root / 'pending/cartographer.json'
            seal.write_text(json.dumps(envelope, ensure_ascii=False), encoding='utf-8')
            original = seal.read_bytes()
            studio = Studio(root, CORE / 'world_index.json')
            self.assertTrue(studio.prepare(job)['resumed'])
            self.assertEqual(seal.read_bytes(), original)
            self.assertEqual(studio.open(job['work_id'], expected_seal=envelope['seal_sha256'])
                             ['render_instruction'], expected)

    def test_t09_strong_emotion(self):
        self.job['roles']['performance']['emotional_context'] = '她见到失散多年的亲人，激动得放声大哭。'
        self.assertIn('放声大哭', compose_render(self.job))

    def test_t10_unauthorized_tear_placement(self):
        self.job['roles']['performance']['emotional_context'] = TEARS
        with self.assertRaisesRegex(ValueError, 'unauthorized local performance'):
            compose_render(self.job)

    def test_t11_preset_producer_lock_and_conflict(self):
        point = '她终于等到回信。' + TEARS + '。'
        self.job['chapter'] = {**CHAPTER, 'point': point}
        lock(self.job, TEARS)
        self.assertEqual(compose_render(self.job).count(TEARS), 1)
        self.job['roles']['camera']['visible_frame'] = '右眼落泪，左眼紧闭'
        with self.assertRaisesRegex(ValueError, 'camera.visible_frame'):
            compose_render(self.job)
        lock(self.job, '右眼落泪')
        with self.assertRaisesRegex(ValueError, 'quote the original Point'):
            compose_render(self.job)

    def test_t12_exaggerated_mischief(self):
        self.job['roles']['performance']['emotional_context'] = '恶作剧成功，她露出夸张、狡黠而顽皮的神态。'
        self.assertIn('夸张、狡黠而顽皮的神态', compose_render(self.job))

    def test_t13_whole_emotional_performances(self):
        for phrase in ('开怀大笑', '痛哭失声', '惊恐失措', '她带着狡黠的神态看着对方'):
            with self.subTest(phrase=phrase):
                self.job['roles']['performance']['emotional_context'] = phrase
                self.assertIn(phrase, compose_render(self.job))

    def test_t14_local_direction_and_authority(self):
        line = '左眉上扬、右眼闭合'
        for direction in (line, '不要张嘴', '头部向左倾斜十五度', '某根手指伸出',
                          '眼睛保持自然睁开', '泪珠沿她的左颊滑落'):
            self.job['roles']['performance']['emotional_context'] = direction
            with self.subTest(direction=direction), self.assertRaisesRegex(ValueError, 'emotional_context'):
                compose_render(self.job)
        self.job['roles']['performance']['emotional_context'] = line
        lock(self.job, line, 'performance')
        with self.assertRaisesRegex(ValueError, 'from producer'):
            compose_render(self.job)
        lock(self.job, line)
        self.assertIn(line, compose_render(self.job))

    def test_single_and_triptych_keep_their_own_layout(self):
        self.assertTrue(compose_render(self.job).startswith('Create ONE new '))
        self.assertNotIn('第 1 格', compose_render(self.job))
        self.job['creation_profile'] = {'outfit_triptych': True}
        text = compose_render(self.job)
        self.assertIn('本轮主角的穿搭', text)
        self.assertIn(POINT, text)


class EntryTests(unittest.TestCase):
    def test_prepare_verify_exact_relay_and_success_receipt(self):
        # No host calls. Exercise the same CLI paths used by the Chat run book.
        bundle = Path(os.environ.get('WARDROBE_TEST_RELEASE', ROOT))
        entry = bundle / 'runtime/entry/p14.py'
        with TemporaryDirectory() as folder:
            root = Path(folder)

            def write(name, data):
                path = root / name
                path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                return path

            def invoke(command, *args, fail=None):
                result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(entry), command,
                                         *map(str, args)], capture_output=True, encoding='utf-8')
                if fail:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(fail, result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return json.loads(result.stdout)

            profile = root / 'profile.json'
            invoke('configure', '--profile', profile, '--utterance', '关闭擦边模式')
            ledger = bundle / 'runtime/defaults/empty-ledger.json'
            state = json.loads(ledger.read_bytes())
            index = json.loads((CORE / 'curated/world_index.json').read_bytes())
            state['book_stats'] = {book['id']: {'active': False}
                                   for book in index['books'] if book['id'] != 'B199'}
            ledger = write('ledger.json', state)
            ready = invoke('start', '--cache', root / 'cache', '--sessions', root / 'sessions',
                           '--ledger', ledger,
                           '--session', 'emotion-test', '--persona-summary', 'Adult',
                           '--profile', profile, '--candidate-count', 30)
            runtime, data = Path(ready['runtime']), Path(ready['data_dir'])
            args = ('--runtime', runtime, '--data', data)
            menu = ready['prompt']['menu']
            selected = dict(origin='autonomous_library', book_id='B199', chapter_id=3,
                            shelf_id=menu['shelf_id'], initial_intent='Compare the charts')
            choice = write('choice.json', selected)
            handoff = invoke('production-prompt', *args, choice,
                             bundle / 'runtime/defaults/persona.json', 'cartographer')
            self.assertEqual(handoff['chapter'], CHAPTER)
            self.assertIn('performance{emotional_context}', handoff['prompt'])
            job = {**cartographer(), **selected}
            job.pop('render_policy')
            job['persona'] = {'adult': True, 'story_role': 'Chartmaker'}
            job['role_director'] = {'story_fit': 'An adult cartographer'}
            job['producer'] = {}
            # Force the original preset through normalization. A fabricated
            # producer lock for this chapter must fail before any seal is saved.
            fabricated = deepcopy(job)
            lock(fabricated, WINK)
            invoke('prepare', *args, write('fabricated.json', fabricated),
                   fail='quote the original Point')
            draft = write('job.json', job)
            wrong = deepcopy(job)
            wrong['roles']['camera']['visible_frame'] = '她张开嘴巴，双眼睁大。'
            invoke('prepare', *args, write('wrong.json', wrong), fail='camera.visible_frame')
            self.assertFalse((data / 'pending/cartographer.json').exists())
            staged = invoke('prepare', *args, draft)
            seal_path = Path(staged['pending_path'])
            original = seal_path.read_bytes()
            envelope = json.loads(original)
            self.assertIn(POINT, envelope['work']['render_instruction'])
            self.assertNotIn('performance_lock', envelope['work']['job']['producer'])
            self.assertEqual(invoke('prepare', *args, draft)['seal_sha256'], staged['seal_sha256'])
            self.assertEqual(seal_path.read_bytes(), original)
            verified = invoke('verify-delivery', *args, write('prepare.json', staged),
                              '--original', seal_path, '--readback', seal_path)
            uri = root / 'relay.txt'
            message = verified['chat_ui']['native_ui']['open_button_message']
            uri.write_bytes(message.encode('utf-8'))
            opened = invoke('open-native', *args, '--relay-message', uri)
            self.assertEqual(opened['status'], 'ready_to_submit')
            self.assertEqual(opened['render_request']['text'], envelope['work']['render_instruction'])
            self.assertEqual(invoke('open-native', *args, '--relay-message', uri)['status'], 'awaiting_result')
            image = root / 'mock.png'
            image.write_bytes(base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=='))
            receipt = write('receipt.json', {
                'status': 'succeeded', 'work_id': job['work_id'], 'attempt_id': opened['attempt_id'],
                'generation_id': 'simulated-image', 'seal_sha256': envelope['seal_sha256'],
                'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            })
            confirmed = invoke('confirm', *args, job['work_id'], 'simulated-image', image,
                               '--attempt-id', opened['attempt_id'], '--receipt', receipt)
            self.assertTrue(confirmed['counted'])
            saved = json.loads((data / 'shelf-state.json').read_bytes())
            self.assertEqual(saved['p13']['chapter_cycles']['B199']['used'], [3])
            self.assertEqual(invoke('open-native', *args, '--relay-message', uri)['status'], 'already_confirmed')
