"""Wardrobe 2 P1 studio: role handoffs, sealed snapshots and verifiable render commit.

This is an offline prototype. It does NOT call an LLM or generate images.
A ChatGPT/other-host adapter supplies a coherent authored job and validates real image output.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager, suppress
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from wardrobe2_core import Shelf
from emotion_director import RENDER_POLICY_EMOTION_V1, render_performance

PROTOCOL = 'wardrobe2-studio-p1'
VISUAL_INTENT_PROFILE = 'visual_intent_v1'
OUTFIT_TRIPTYCH_NOTE = (
    '第 1 格是你最保守的穿搭，每往右一格，你就把她的穿搭往更大胆、更显身材的方向推一步，'
    '第3 格是你能出到的上限，到哪你自己决定。每格底下用很小的手写字标上 1 到 3，再写一句你给这一格的你想说的话。'
)
RENDER_POLICY_RC7 = 'rc7_v1'
RENDER_POLICY_RC8_R1 = 'rc8_r1'
RENDER_POLICY_RC9_2 = 'rc9_2'
RENDER_POLICY_RC9_5 = 'rc9_5'
RENDER_POLICY_EMOTION_V1 = 'emotion_v1'
BOUNDED_RENDER_POLICIES = (RENDER_POLICY_RC7, RENDER_POLICY_RC8_R1, RENDER_POLICY_RC9_2, RENDER_POLICY_RC9_5, RENDER_POLICY_EMOTION_V1)
MAX_RENDER_BYTES = 6144
RECENT_STORY_MOMENTS = 'recent_story_moments'
SINGLE_OUTPUT_EN = re.compile(
    r'(?im)^[ \t]*(?:(?:create|generate|render|make)\s+|(?:this|it)\s+is\s+)(?:one|a single|a|1)\b'
    r'[^.\n!?;。！？]{0,150}?\b(?:photograph|photo|cinematic still|image)'
    r'(?=[ \t]*(?:[,.!?;]|$))[ \t]*(?:[,.!?;][ \t]*)?'
)
SINGLE_OUTPUT_ZH = re.compile(
    r'(?m)(?:^|(?<=[。；！？]))[ \t]*(?:请)?(?:只)?(?:生成|制作|输出|拍摄)?'
    r'(?:一张|单张|一幅)[ \t]*(?:全新|高质量|独立|单独|写实|照片级|电影感|电影级|电影|静态|摄影|的|[ \t])*'
    r'(?:照片|剧照|摄影图|静帧|画面)(?=[ \t]*(?:[，。；！？]|$))[ \t]*[，。；！？]?[ \t]*'
)
LAYOUT_EN = r'(?:collage|triptych|split[ -]screen|multi[ -]panel(?: layout)?)'
SINGLE_LAYOUT_ONLY_EN = re.compile(
    r'\b(?:never an edit|do not edit an existing image|'
    rf'(?:no|without)\s+{LAYOUT_EN}(?:[ \t]*(?:,|or|and)\s*(?:no\s+)?{LAYOUT_EN})*)'
    r'\b(?=[ \t]*(?:[,.;!?]|\n|$))[ \t]*[,.;!?]?[ \t]*', re.IGNORECASE,
)
SINGLE_LAYOUT_ONLY_ZH = re.compile(
    r'(?:不要|禁止|请勿|不采用|不做)(?:使用|采用)?[ \t]*(?:三联画|三联图|三格|多格|拼图|分屏)(?:构图|排版|画面)?'
    r'(?:[、或和](?:三联画|三联图|三格|多格|拼图|分屏)(?:构图|排版|画面)?)*'
    r'(?=[ \t]*(?:[，。；！？]|\n|$))[ \t]*[，。；！？]?[ \t]*'
)
ROLES = ('scene', 'wardrobe', 'performance', 'lighting', 'camera')
MANDATORY = {
    'scene': ('plan', 'props'),
    'wardrobe': ('full_outfit', 'visible_outfit'),
    'performance': ('action', 'expression'),
    'lighting': ('plan',),
    'camera': ('plan', 'visible_frame'),
}
PRODUCER_FIELDS = ('intent', 'context', 'event', 'moment', 'emotion')
ORIGINS = {'autonomous_library', 'autonomous_original', 'autonomous_spontaneous', 'autonomous_self', 'user_directed'}


def canon(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.writing')
    try:
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        with suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def required_text(d: dict[str, Any], field: str, scope: str) -> str:
    val = d.get(field)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f'{scope}.{field} must be nonempty text')
    return val.strip()


def role_fields(job: dict[str, Any], role: str) -> tuple[str, ...]:
    if role == 'performance' and job.get('render_policy') == RENDER_POLICY_EMOTION_V1:
        if set(job['roles'][role]) != {'emotional_context'}:
            raise ValueError('performance must contain only emotional_context')
        return ('emotional_context',)
    if role == 'performance' and job.get('render_policy') == RENDER_POLICY_RC9_5:
        if set(job['roles'][role]) != {'expression'}:
            raise ValueError('RC9.5 performance must contain only expression')
        return ('expression',)
    if (role == 'performance' and job.get('render_profile') == VISUAL_INTENT_PROFILE
            and 'action' not in job['roles'][role]):
        return ('expression',)
    return MANDATORY[role]


def validate_job(job: dict[str, Any], shelf: Shelf, *, now: datetime | None = None) -> None:
    work_id = required_text(job, 'work_id', 'job')
    if not work_id.replace('_', '').replace('-', '').isalnum() or len(work_id) > 96:
        raise ValueError('work_id must be simple letters/digits/dashes/underscores')
    origin = job.get('origin')
    if origin not in ORIGINS:
        raise ValueError('unsupported job origin')
    book_id = job.get('book_id')
    if origin == 'autonomous_library':
        if book_id not in shelf.books:
            raise ValueError('unknown fixed book')
        stat = shelf._read_stat(book_id)
        if not stat['active']:
            raise ValueError('removed book cannot be selected from shelf')
        if hasattr(shelf, 'local_eligible'):
            allowed = shelf.local_eligible(book_id)
            fallback = job.get('fallback_book_id') == book_id and shelf.local_all_cooling()
        else:
            allowed = shelf.state['auto_seq'] + 1 >= stat['next_eligible_auto_seq']
            fallback = False
        if not (allowed or fallback):
            ref = job.get('deliberate_revisit_ref')
            if not ref or shelf.state['work_books'].get(ref) != book_id:
                raise ValueError('book cooling, no grounded deliberate_revisit_ref')
    elif origin == 'autonomous_original':
        if book_id is not None:
            raise ValueError('original entry must not have a fixed book_id')
        if not shelf.original_available():
            raise ValueError('Original virtual book is cooling')
    elif origin == 'autonomous_spontaneous':
        if book_id is not None:
            raise ValueError('spontaneous idea must not impersonate a fixed book')
    elif origin == 'autonomous_self':
        if book_id is not None or not hasattr(shelf, 'self_eligible'):
            raise ValueError('SELF requires P1.3 runtime without a fixed book_id')
        if job.get('self_book_id') not in {'SELF_FREE', 'SELF_ECHO'}:
            raise ValueError('unknown SELF book')
        if not shelf.self_eligible(now or datetime.now(timezone.utc)):
            raise ValueError('SELF shelf is cooling')
        if job['self_book_id'] == 'SELF_ECHO':
            if not isinstance(job.get('memory_inspiration'), str) or not job['memory_inspiration'].strip():
                raise ValueError('SELF_ECHO requires a nonempty creative memory inspiration')
            if job.get('memory_source_verified') is not True or job.get('memory_source_type') not in {'current_chat', 'retrieved_chat', 'library', 'memory', 'user_shared'}:
                raise ValueError('SELF_ECHO requires host-verified accessible memory source')
    else:
        if book_id is not None and book_id not in shelf.books:
            raise ValueError('unknown referenced book')
        if job.get('self_book_id') is not None and job.get('self_book_id') not in {'SELF_FREE', 'SELF_ECHO'}:
            raise ValueError('invalid user-directed SELF book')

    persona = job.get('persona')
    if not isinstance(persona, dict):
        raise ValueError('persona must be object')
    required_text(persona, 'identity', 'persona')
    required_text(persona, 'appearance', 'persona')
    if persona.get('adult') is not True:
        raise ValueError('human persona must be explicitly adult')
    producer = job.get('producer')
    if not isinstance(producer, dict):
        raise ValueError('producer must be object')
    for field in PRODUCER_FIELDS:
        required_text(producer, field, 'producer')
    roles = job.get('roles')
    if not isinstance(roles, dict) or set(roles) != set(ROLES):
        raise ValueError('roles must contain exactly scene, wardrobe, performance, lighting, camera')
    for role in MANDATORY:
        if not isinstance(roles[role], dict):
            raise ValueError(f'{role} must be object')
        for f in role_fields(job, role):
            required_text(roles[role], f, role)
    if origin in {'autonomous_original', 'autonomous_spontaneous'}:
        required_text(job, 'event_signature', 'job')
    # Technical validation only: do not run aesthetic review or force model re-decisions.


def triptych_frame(frame: str) -> str:
    for conflict in (SINGLE_OUTPUT_EN, SINGLE_OUTPUT_ZH, SINGLE_LAYOUT_ONLY_EN, SINGLE_LAYOUT_ONLY_ZH):
        frame = conflict.sub('', frame)
    frame = frame.strip()
    if not frame:
        raise ValueError('三格摄影正文需要保留共同的可见画面')
    return frame


def _without_exact_identity_lines(frame: str, persona: dict[str, Any], identity_line: str) -> str:
    """Drop standalone copies of stable identity; leave visual descriptions intact."""
    def normalized(line: str) -> str:
        return ' '.join(line.split()).rstrip('.。')

    stable = {normalized(line) for line in (
        identity_line, persona['identity'], persona['appearance'],
        persona.get('identity_continuity', ''),
    ) if line.strip()}
    lines = frame.split('\n')
    retained = [line for line in lines if normalized(line) not in stable]
    return required_text({'visible_frame': '\n'.join(retained)}, 'visible_frame', 'camera')


def compose_render(job: dict[str, Any]) -> str:
    """Only describe what photographer chose to expose; do not force off-screen outfit."""
    persona = job['persona']
    story_role = persona.get('story_role', '').strip()
    continuity = persona.get('identity_continuity', '').strip()
    parts = [
        'Create ONE new high-quality photorealistic cinematic still photograph. Do not edit an existing image.',
        'Adult character: ' + persona['identity'].strip() + '; appearance: ' + persona['appearance'].strip() + '.' + ((' Story identity: ' + story_role + '.') if story_role else '') + ((' Identity continuity: ' + continuity) if continuity else ''),
    ]
    profile = job.get('creation_profile')
    triptych = isinstance(profile, dict) and profile.get('outfit_triptych') is True
    policy = job.get('render_policy')
    if policy is not None and policy not in BOUNDED_RENDER_POLICIES:
        raise ValueError('unsupported render policy')
    if 'render_profile' in job or triptych:
        if job.get('render_profile', VISUAL_INTENT_PROFILE) != VISUAL_INTENT_PROFILE:
            raise ValueError('unsupported job render_profile')
        frame = required_text(job['roles']['camera'], 'visible_frame', 'camera')
        if policy in (RENDER_POLICY_RC9_5, RENDER_POLICY_EMOTION_V1):
            performance = job['roles'].get('performance')
            if not isinstance(performance, dict):
                raise ValueError('performance must be object')
            for field in role_fields(job, 'performance'):
                required_text(performance, field, 'performance')
            frame = _without_exact_identity_lines(frame, persona, parts[1])
        if policy == RENDER_POLICY_EMOTION_V1:
            parts.extend(render_performance(job))
        if triptych:
            if policy in (RENDER_POLICY_RC8_R1, RENDER_POLICY_RC9_2, RENDER_POLICY_RC9_5, RENDER_POLICY_EMOTION_V1):
                frame = triptych_frame(frame)
            if policy in (RENDER_POLICY_RC9_2, RENDER_POLICY_RC9_5, RENDER_POLICY_EMOTION_V1):
                parts[0] = 'Create a new high-quality photorealistic cinematic image. Do not edit an existing image.'
            else:
                parts[0] = ('Create ONE new high-quality photorealistic cinematic image with three equal panels side by side. '
                            'Do not edit an existing image.')
                if policy == RENDER_POLICY_RC8_R1:
                    parts.append('横排三格。同一位成年主角在同一故事瞬间展示三套穿搭。'
                                 '下方摄影定稿中的机位、景别、场景、动作和光线分别应用到每一格，按每格边界完整取景。'
                                 '人物身份保持一致，服装从左至右变化。')
                else:
                    parts.append('三格为同一位成年主角的时装摄影。沿用下方摄影定稿的场景、动作、光影和取景。'
                                 '人物身份与镜头保持一致，服装从左到右变化。每格下方各留一小行字。')
            note = (OUTFIT_TRIPTYCH_NOTE.replace('她的穿搭', '本轮主角的穿搭')
                    if policy in BOUNDED_RENDER_POLICIES else OUTFIT_TRIPTYCH_NOTE)
            parts.extend((frame, note))
        else:
            parts.append(frame)
        rendered = '\n'.join(parts)
        if policy in BOUNDED_RENDER_POLICIES:
            byte_count = len(rendered.encode('utf-8'))
            if byte_count > MAX_RENDER_BYTES:
                raise ValueError(f'摄影正文共 {byte_count} 字节，超出 RC7 的 {MAX_RENDER_BYTES} 字节试拍保护线。'
                                 '本轮尚未封签，暂停开箱。')
        return rendered

    if policy == RENDER_POLICY_EMOTION_V1:
        raise ValueError('emotion_v1 requires visual_intent_v1')
    producer, roles = job['producer'], job['roles']
    parts += [
        'World and narrative: ' + producer['context'].strip() + '. ' + producer['event'].strip() + '.',
        'Key photographed moment: ' + producer['moment'].strip() + '.',
        'Emotion: ' + producer['emotion'].strip() + '.',
        'Environment and necessary props: ' + roles['scene']['plan'].strip() + '; ' + roles['scene']['props'].strip() + '.',
        'Visible clothing and styling: ' + roles['wardrobe']['visible_outfit'].strip() + '.',
        'Performance: ' + roles['performance']['action'].strip() + '; expression: ' + roles['performance']['expression'].strip() + '.',
        'Lighting: ' + roles['lighting']['plan'].strip() + '.',
        'Camera: ' + roles['camera']['plan'].strip() + '.',
        'Visible frame: ' + roles['camera']['visible_frame'].strip() + '.',
        'Natural physical coherence; credible anatomy and hands; preserve the character and story moment.',
    ]
    return '\n'.join(parts)


def remember_story_moment(state: dict[str, Any], job: dict[str, Any]) -> None:
    if job.get('render_policy') in BOUNDED_RENDER_POLICIES:
        saved = state.get(RECENT_STORY_MOMENTS, [])
        recent = [row for row in saved[-3:] if isinstance(row, dict)] if isinstance(saved, list) else []
        work_id = job['work_id']
        if any(row.get('work_id') == work_id for row in recent):
            return
        chapter_point = job.get('chapter', {}).get('point')
        moment = ' '.join((chapter_point or job['producer']['moment']).split())[:180]
        state[RECENT_STORY_MOMENTS] = [*recent[-2:], {'work_id': work_id, 'moment': moment}]


@contextmanager
def studio_lock(root: Path):
    """An OS lock shared by P1.2.1 writers using the same local data directory."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.studio.lock').open('a+b') as lock:
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        # Closing the handle also releases the lock after exceptions or process exit.
        yield


def verify_image(image_file: Path) -> str:
    image_file = Path(image_file)
    if not image_file.is_file():
        raise ValueError('cannot verify image file')
    image_bytes = image_file.read_bytes()
    magic = image_bytes[:16]
    if not (magic.startswith(b'\x89PNG\r\n\x1a\n') or magic.startswith(b'\xff\xd8\xff')
            or (magic.startswith(b'RIFF') and magic[8:12] == b'WEBP')):
        raise ValueError('file does not look like PNG/JPEG/WebP')
    if len(image_bytes) < 32:
        raise ValueError('image file is too small')
    try:
        from PIL import Image  # Optional developer-side integrity check, not a runtime requirement
    except ImportError:
        pass
    else:
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                if image.width < 1 or image.height < 1:
                    raise ValueError('image dimensions must be positive')
                image.verify()
        except Exception as exc:
            raise ValueError('image file is not decodable') from exc
    return hashlib.sha256(image_bytes).hexdigest()


def valid_attempt_id(attempt_id: str) -> None:
    if (not isinstance(attempt_id, str) or not attempt_id.isascii() or len(attempt_id) > 96
            or not attempt_id.replace('_', '').replace('-', '').isalnum()):
        raise ValueError('attempt_id must be simple ASCII letters/digits/dashes/underscores')


class Studio:
    def __init__(self, root: Path, index_path: Path):
        self.root = Path(root)
        self.index = read_json(Path(index_path))
        if not isinstance(self.index.get('books'), list) or not self.index['books']:
            raise ValueError('a nonempty verified world index is required')
        self.state_path = self.root / 'shelf-state.json'
        self.shelf = self._read_shelf()

    def _new_shelf(self, state) -> Shelf:
        if state is not None and 'p13' in state:
            raise ValueError('P1.3 ledger requires p13_cli.py; old Studio cannot write it')
        return Shelf(self.index, state)

    def _read_shelf(self) -> Shelf:
        try:
            state = read_json(self.state_path)
        except FileNotFoundError:
            state = None
        return self._new_shelf(state)

    def menu(self, now: datetime) -> dict[str, Any]:
        self.shelf = self._read_shelf()
        return self.shelf.snapshot(now)  # pure read; no filesystem write

    def _path(self, work_id: str) -> Path:
        key = required_text({'work_id': work_id}, 'work_id', 'job')
        if not key.replace('_', '').replace('-', '').isalnum() or len(key) > 96:
            raise ValueError('work_id must be simple letters/digits/dashes/underscores')
        return self.root / 'pending' / f'{work_id}.json'

    def _directed_receipt(self, work_id: str) -> Path:
        return self.root / 'directed-receipts' / self._path(work_id).name

    def prepare(self, job: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        with studio_lock(self.root):
            latest = self._read_shelf()
            self.shelf = latest
            path = self._path(job['work_id'])
            if self._directed_receipt(job['work_id']).exists():
                raise ValueError('work_id already completed; use a new work ID')
            # A retry must not re-run the creative process or be blocked by a
            # CD advanced *after* this work was first sealed. Reconstruct the
            # immutable creative work using its signed render profile, verify
            # the persisted seal, and only resume if the content is identical.
            if path.exists():
                _, envelope = self._get(job['work_id'])
                candidate = {
                    'protocol': PROTOCOL, 'job': job, 'render_instruction': compose_render(job),
                }
                if digest(candidate) != envelope['seal_sha256'] or candidate != envelope['work']:
                    raise ValueError('work_id conflict: existing seal has different content')
                if envelope['state'] not in {'ready', 'opened', 'rendered'}:
                    raise ValueError('existing work cannot be resumed from this state')
                resumed = True
            else:
                validate_job(job, latest, now=now)
                work = {
                    'protocol': PROTOCOL, 'job': job, 'render_instruction': compose_render(job),
                }
                envelope = {
                    'work': work, 'seal_sha256': digest(work), 'state': 'ready', 'confirmed_images': [],
                }
                resumed = False
            if not resumed:
                atomic_json(path, envelope)
        return {'work_id': job['work_id'], 'state': envelope['state'], 'seal_sha256': envelope['seal_sha256'],
                'teaser': job['producer']['intent'], 'next_step': 'open', 'resumed': resumed}

    def _get(self, work_id: str) -> tuple[Path, dict[str, Any]]:
        path = self._path(work_id)
        env = read_json(path)
        if env['seal_sha256'] != digest(env['work']):
            raise ValueError('sealed snapshot altered: checksum mismatch')
        if env['work']['job']['work_id'] != work_id:
            raise ValueError('sealed work_id does not match requested work')
        if env['work']['job']['origin'] == 'user_directed' and self._directed_receipt(work_id).exists():
            raise ValueError('directed work already completed')
        return path, env

    def open(self, work_id: str, *, expected_seal: str | None = None) -> dict[str, Any]:
        with studio_lock(self.root):
            if self._directed_receipt(work_id).exists():
                raise ValueError('directed work already completed')
            path, env = self._get(work_id)
            if expected_seal is not None and env['seal_sha256'] != expected_seal:
                raise ValueError('seal does not match the expected SHA-256')
            if env['state'] not in {'ready', 'opened', 'rendered'}:
                raise ValueError('work not ready for opening')
            if env['state'] == 'ready':
                env['state'] = 'opened'
                atomic_json(path, env)
        return {'work_id': work_id, 'state': env['state'], 'render_instruction': env['work']['render_instruction'],
                'seal_sha256': env['seal_sha256']}

    def start_attempt(self, work_id: str, attempt_id: str) -> dict[str, Any]:
        """Reserve a trusted host attempt after opening, before provider dispatch."""
        valid_attempt_id(attempt_id)
        with studio_lock(self.root):
            if self._directed_receipt(work_id).exists():
                raise ValueError('directed work already completed')
            path, env = self._get(work_id)
            if env['state'] not in {'opened', 'rendered'}:
                raise ValueError('user must open the sealed work before starting generation')
            attempts = env.setdefault('attempts', {})
            current = attempts.get(attempt_id)
            if current is not None:
                if current['status'] != 'registered':
                    raise ValueError('attempt is already terminal')
            else:
                if any(attempt['status'] == 'registered' for attempt in attempts.values()):
                    raise ValueError('a different attempt is already registered')
                attempts[attempt_id] = {'status': 'registered'}
                atomic_json(path, env)
        return {'work_id': work_id, 'attempt_id': attempt_id, 'status': 'registered', 'created': current is None}

    def fail_attempt(self, work_id: str, attempt_id: str) -> dict[str, Any]:
        valid_attempt_id(attempt_id)
        with studio_lock(self.root):
            if self._directed_receipt(work_id).exists():
                raise ValueError('directed work already completed')
            path, env = self._get(work_id)
            attempt = env.get('attempts', {}).get(attempt_id)
            if attempt is None:
                raise ValueError('attempt_id does not match this work')
            if attempt['status'] == 'confirmed':
                raise ValueError('attempt already confirmed')
            if attempt['status'] == 'registered':
                self.shelf = self._read_shelf()
                if any(row['work_id'] == work_id and row.get('attempt_id') == attempt_id
                       for row in self.shelf.state['renders'].values()):
                    raise ValueError('attempt has a committed image; retry its success callback')
                attempt['status'] = 'failed'
                atomic_json(path, env)
        return {'work_id': work_id, 'attempt_id': attempt_id, 'status': 'failed'}

    def confirm_image(self, work_id: str, render_id: str, image_file: Path,
                      now: datetime | None = None, *, attempt_id: str | None = None) -> dict[str, Any]:
        if not isinstance(render_id, str) or not render_id.strip():
            raise ValueError('render_id is required')
        if attempt_id is not None:
            valid_attempt_id(attempt_id)

        with studio_lock(self.root):
            latest = self._read_shelf()
            self.shelf = latest
            result = {'status': 'duplicate', 'counted': False, 'auto_seq': latest.state['auto_seq']}
            if attempt_id is not None:
                result.update(work_id=work_id, attempt_id=attempt_id)

            receipt_path = self._directed_receipt(work_id)
            if receipt_path.exists():
                receipt = read_json(receipt_path)
                if receipt['render_id'] != render_id or receipt['attempt_id'] != attempt_id:
                    raise ValueError('callback does not match the completed directed work')
                self._path(work_id).unlink(missing_ok=True)
                return result

            path, env = self._get(work_id)
            if env['state'] not in {'opened', 'rendered'}:
                raise ValueError('user must open the sealed work before image confirmation')
            attempts = env.get('attempts', {})
            attempt = attempts.get(attempt_id)
            if attempt_id is not None and attempt is None:
                raise ValueError('attempt_id does not match this work')
            if attempts and attempt_id is None:
                raise ValueError('attempt_id is required for this tracked work')

            record = latest.state['renders'].get(render_id)
            if record is not None and (record['work_id'] != work_id or record.get('attempt_id') != attempt_id):
                raise ValueError('render_id is already bound to a different work or attempt')
            if attempt is not None and attempt['status'] != 'registered':
                if attempt['status'] == 'confirmed' and attempt['render_id'] == render_id:
                    return result
                raise ValueError('attempt is already terminal')
            if render_id in env['confirmed_images']:
                if attempt is not None:
                    raise ValueError('render_id is already confirmed by another callback')
                return result

            if record is None:
                image_sha256 = verify_image(image_file)
                now = now or datetime.now(timezone.utc)
                if now.tzinfo is None:
                    raise ValueError('timestamp must include timezone')
                job = env['work']['job']
                result.update(status='confirmed', image_sha256=image_sha256)
                if job['origin'] == 'user_directed':
                    # A minimal retry receipt is separate from autonomous exploration and CD.
                    if hasattr(latest, 'record_directed_other'):
                        special = self._new_shelf(deepcopy(latest.state))
                        special.record_directed_other(render_id, now, is_self=bool(job.get('self_book_id')))
                        remember_story_moment(special.state, job)
                        atomic_json(self.state_path, special.state)
                        self.shelf = special
                    atomic_json(receipt_path, {'render_id': render_id, 'attempt_id': attempt_id})
                    path.unlink()
                    return result
                staged = self._new_shelf(deepcopy(latest.state))
                kw = dict(origin=job['origin'], work_id=work_id, render_id=render_id,
                          now=now, book_id=job.get('book_id'), event_signature=job.get('event_signature'),
                          deliberate_revisit_ref=job.get('deliberate_revisit_ref'))
                if hasattr(staged, 'p13_enabled'):
                    kw.update(self_book_id=job.get('self_book_id'), fallback_book_id=job.get('fallback_book_id'),
                              fixed_world_candidate_count=job.get('fixed_world_candidate_count', 30),
                              chapter_id=job.get('chapter_id'))
                counted = staged.record_success(**kw)
                if counted and not env['confirmed_images']:
                    remember_story_moment(staged.state, job)
                if attempt_id is not None:
                    staged.state['renders'][render_id]['attempt_id'] = attempt_id
                # Publish the in-memory state only after the durable replacement succeeds.
                atomic_json(self.state_path, staged.state)
                self.shelf = staged
                result.update(counted=counted, auto_seq=staged.state['auto_seq'])

            # An existing matching row repairs a prior ledger-first commit, even without the image file.
            env['confirmed_images'].append(render_id)
            env['state'] = 'rendered'
            if attempt is not None:
                attempt.update(status='confirmed', render_id=render_id)
            atomic_json(path, env)
            return result


def role_contract(*, emotion_only: bool = False, emotional_context: bool = False) -> dict[str, Any]:
    performance = ({'fields': ['expression'], 'owns': 'inner state, emotional layers, facial expression'}
                   if emotion_only else
                   {'fields': list(MANDATORY['performance']), 'owns': 'action, expression, gaze'})
    if emotional_context:
        performance = {'fields': ['emotional_context'], 'owns': 'story experience and whole emotional performance'}
    return {
        'producer': {'fields': list(PRODUCER_FIELDS), 'owner': 'current AI creative producer',
                     'rule': ('One moment; only producer may lock exact story performance with performance_lock.'
                              if emotional_context else 'One story, one moment; no preselected camera/costume.')},
        'scene': {'fields': list(MANDATORY['scene']), 'owns': 'environment, prop materials, physical layout'},
        'wardrobe': {'fields': list(MANDATORY['wardrobe']), 'owns': 'complete costume vs camera-visible details'},
        'performance': performance,
        'lighting': {'fields': list(MANDATORY['lighting']), 'owns': 'light origin, direction, material response'},
        'camera': {'fields': list(MANDATORY['camera']), 'owns': 'lens, framing, perspective, final visible frame'},
        'method': 'Logical role sequence in one AI creation pass if feasible; not six model/API calls.',
        'cinematography': 'Shared craft knowledge; not a genmedia CLI/API execution dependency.',
    }
