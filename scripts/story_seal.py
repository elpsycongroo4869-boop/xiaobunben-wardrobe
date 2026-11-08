"""Create and verify portable wardrobe archives. Historical archives stay read-only."""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
import json
import os
import re
import subprocess
import sys
import time
import zipfile

from creative_audit import display_labels, fragment as render_status
from design_contract import SECTIONS
from render_open import notes_fragment, render_card
from story_compiler import canonical, compile_story, sha
from wardrobe_version import SEAL_SCHEMA, SEAL_VERSIONS, VERSION
from world_cards import select_cards

ROUTES = {'new_chat': 'GenUI.issueNewTurn', 'copy_only': 'GenUI.copy'}
MAX_ENTRY_BYTES = 512 * 1024
MAX_FILES = 24


def json_data(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=unique)


def notes_markdown(notes):
    return '# 本次创作思路\n\n' + '\n\n'.join(
        f'## {label}\n\n{notes[key]}' for key, label in SECTIONS
    ) + '\n'


def assemble(brief, profile, cards, route, draw_id, *, version=VERSION):
    if route not in ROUTES:
        raise ValueError('Unsupported button route')
    if version not in SEAL_VERSIONS:
        raise ValueError('Unsupported v4.5 seal version')
    if str(UUID(draw_id, version=4)) != draw_id:
        raise ValueError('Draw ID must be a canonical UUID4')
    draw, selection, fields, message = compile_story(brief, profile, cards, draw_id, version=version)
    source = {'source_draw_id': draw_id, 'source_photo_message_sha256': draw['message_sha256']}
    notes = {'schema': 'wardrobe-creative-notes-v4.5', **source, 'sections': draw['creative_notes'],
             'source_draw_sha256': sha(canonical(draw)), 'initially_collapsed': True,
             'written_stage': 'before_image_generation'}
    status = {'schema': 'wardrobe-creative-status-v4.5', **source, 'audit': draw['creative_audit'],
              'display_labels': display_labels(draw['creative_audit']), 'status_kind': 'creator_self_report'}
    button = {
        'schema': 'wardrobe-button-handoff-v4.5', 'status': 'prepared_not_clicked',
        'source_draw_id': draw_id, 'source_message_sha256': draw['message_sha256'],
        'route': route, 'action': ROUTES[route],
        'button_label': '打开衣橱' if route == 'new_chat' else '开箱并复制出图指令',
        'source_field_count': len(fields), 'full_user_message': message,
        'creative_notes': {'record_file': 'creative-notes.json', 'record_sha256': sha(canonical(notes)),
                           'button_fragment': 'creative-notes-button.html', 'initially_collapsed': True},
        'creative_status': {'record_file': 'creative-status.json', 'record_sha256': sha(canonical(status)),
                            'fragment_file': 'creative-status.html', 'status_labels': status['display_labels']},
    }
    records = {
        'creative-brief.json': brief, 'role-profile.json': profile,
        'cited-worlds.json': cards, 'draw.json': draw,
        'scene-design.json': {
            **brief['scene_design'], 'wardrobe': fields['outfit_and_function'],
            'expression': draw['emotion_review']['visible_expression'],
        },
        'photographer-selection.json': selection,
        'english-details.json': {'schema': 'wardrobe-visual-fields-v4.5', **source, 'fields': fields},
        'creative-notes.json': notes, 'creative-status.json': status, 'button_manifest.json': button,
    }
    files = {name: canonical(value) for name, value in records.items()}
    files.update({
        'photo-creation-message.txt': message.encode('utf-8'),
        'creative-notes.md': notes_markdown(notes['sections']).encode('utf-8'),
        'creative-notes-button.html': notes_fragment(notes).encode('utf-8'),
        'creative-status.html': render_status(status).encode('utf-8'),
    })
    manifest = {
        'schema': SEAL_SCHEMA, 'version': version, 'draw_id': draw_id, 'route': route,
        'message_sha256': draw['message_sha256'],
        'files': {name: sha(data) for name, data in files.items()},
    }
    return manifest, files, button, notes, status


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (len(names) > MAX_FILES or len(set(names)) != len(names)
                or any(not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}', name) for name in names)
                or any(entry.file_size > MAX_ENTRY_BYTES for entry in entries)):
            raise ValueError('Unexpected, duplicate or oversized files in the seal archive')
        return {entry.filename: archive.read(entry) for entry in entries}


def checked_payload(files, pin=None):
    files = dict(files)
    manifest_bytes = files.pop('manifest.json')
    manifest = json_data(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get('schema') != SEAL_SCHEMA:
        raise ValueError('Use the v4.4 verifier for a historical seal')
    if manifest.get('files') != {name: sha(data) for name, data in files.items()}:
        raise ValueError('Archive files or SHA-256 values changed after sealing')
    if pin is not None and sha(manifest_bytes) != pin:
        raise ValueError('The manifest does not match the separately recorded SHA-256')
    return manifest, files


def verify_archive(path, pin=None):
    manifest, files = checked_payload(read_zip(path), pin)
    expected, expected_files, *_ = assemble(
        json_data(files['creative-brief.json']), json_data(files['role-profile.json']),
        json_data(files['cited-worlds.json']), manifest['route'], manifest['draw_id'],
        version=manifest['version'],
    )
    if manifest != expected or files != expected_files:
        raise ValueError('The archived photograph does not match the role, reviewed story and button payload')
    return manifest, files


def prepare(pending, brief, profile, deck, route):
    started = time.perf_counter()
    cards = select_cards(brief.get('creative_audit'), deck)
    deck_finished = time.perf_counter()
    manifest, files, button, notes, status = assemble(brief, profile, cards, route, str(uuid4()))
    compiled = time.perf_counter()
    manifest_bytes = canonical(manifest)
    pin = sha(manifest_bytes)
    pending = Path(pending).absolute()
    pending.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive directory reservation prevents two draws or retries from writing
    # into the same location. The ZIP is the last file published.
    pending.mkdir()
    archive = pending / f"wardrobe-v{VERSION}-pending-{manifest['draw_id']}.zip"
    created = []
    try:
        with TemporaryDirectory(prefix='.sealing-', dir=pending) as folder:
            staged = Path(folder) / archive.name
            with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED) as output:
                for name, data in {**files, 'manifest.json': manifest_bytes}.items():
                    output.writestr(name, data)
            packed = time.perf_counter()
            disk_manifest, disk_files = checked_payload(read_zip(staged), pin)
            if disk_manifest != manifest or disk_files != files:
                raise ValueError('The archived bytes differ from the verified in-memory photograph')
            verified = time.perf_counter()
            artifacts = {'button_manifest.json': disk_files['button_manifest.json']}
            if route == 'copy_only':
                artifacts['open.html'] = render_card(button, notes, status).encode('utf-8')
            for name, data in artifacts.items():
                path = pending / name
                with path.open('xb') as stream:
                    created.append(path)
                    stream.write(data)
            os.replace(staged, archive)
        finished = time.perf_counter()
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        if not archive.exists() and not any(pending.iterdir()):
            pending.rmdir()
        raise
    times = {'world_lookup': deck_finished - started, 'compile_review': compiled - deck_finished,
             'pack': packed - compiled, 'verify_archive': verified - packed,
             'card_files': finished - verified, 'total': finished - started}
    return {
        'verified': True, 'draw_id': manifest['draw_id'], 'version': VERSION, 'route': route,
        'pending_zip': str(archive), 'manifest_sha256': pin, 'message_sha256': manifest['message_sha256'],
        'message_chars': len(button['full_user_message']),
        'manifest_path': str(pending / 'button_manifest.json'),
        'open_card': str(pending / 'open.html') if route == 'copy_only' else None,
        'image_generated': False, 'timings_seconds': {key: round(value, 6) for key, value in times.items()},
    }


def verify_legacy(path, engine, route=None):
    """Execute a supplied historical verifier against an isolated, temporary copy."""
    path = Path(path)
    if not engine.is_file():
        raise ValueError('Give --legacy-engine the path to the unpacked official v4.4 scripts/story_start.py')
    with TemporaryDirectory(prefix='wardrobe-history-') as folder:
        copy = Path(folder)
        if path.is_dir():
            for item in path.iterdir():
                if item.is_file() and not item.is_symlink():
                    (copy / item.name).write_bytes(item.read_bytes())
        else:
            for name, data in read_zip(path).items():
                (copy / name).write_bytes(data)
        actual_route = json_data((copy / 'button_manifest.json').read_bytes())['route']
        if route is not None and actual_route != route:
            raise ValueError('Requested route differs from the historical button route')
        run = subprocess.run(
            [sys.executable, str(engine.resolve()), 'verify', '--pending', str(copy), '--route', actual_route],
            check=False, capture_output=True, text=True, encoding='utf-8',
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8'},
        )
        if run.returncode:
            raise ValueError(run.stderr.strip() or 'Historical verification failed')
        return json_data(run.stdout)
