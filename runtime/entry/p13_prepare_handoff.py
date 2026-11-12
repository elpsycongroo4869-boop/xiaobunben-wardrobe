"""Prepare once and require exact readback from the selected store."""

import json
import subprocess
import sys
from pathlib import Path

from p13_verify_delivery import verify_bytes


def prepare_local(runtime, data_dir, job_file):
    runtime = Path(runtime).resolve()
    command = [
        sys.executable, '-B', '-X', 'utf8', str(runtime / 'p13_cli.py'),
        '--data', str(Path(data_dir).resolve()), 'prepare', str(Path(job_file).resolve()),
    ]
    prepared = subprocess.run(command, cwd=runtime, check=True, capture_output=True, encoding='utf-8')
    result = json.loads(prepared.stdout)
    chat_ui = result['chat_ui']
    if (chat_ui['work_id'], chat_ui['seal_sha256'], chat_ui['state']) != (
        result['work_id'], result['seal_sha256'], 'ready',
    ):
        raise ValueError('prepare UI does not match an unopened seal')
    return result


def prepare_handoff(runtime, data_dir, job_file, *, studio, create_if_absent, read,
                    validate_payload=None):
    """Use trusted callbacks for the exact store used by the button."""
    runtime = Path(runtime).resolve()
    if Path(studio.__file__).resolve() != runtime / 'studio.py':
        raise ValueError('studio module does not match the verified runtime')
    data_dir = Path(data_dir).resolve()
    result = prepare_local(runtime, data_dir, job_file)
    work_id, seal_sha256 = result['work_id'], result['seal_sha256']
    original = (data_dir / 'pending' / f'{work_id}.json').read_bytes()
    verify_bytes(studio, original, original, work_id, seal_sha256)
    if validate_payload is not None:
        validate_payload(result, original)

    readback = read(work_id) if result['resumed'] else None
    if readback is None:
        create_if_absent(work_id, original)
        readback = read(work_id)
    if readback is None:
        raise ValueError('destination seal is missing after create')
    delivery = verify_bytes(studio, original, readback, work_id, seal_sha256)
    return {
        'status': 'handoff_verified',
        'work_id': work_id,
        'seal_sha256': seal_sha256,
        'chat_ui': result['chat_ui'],
        'delivery': delivery,
        'resumed': result['resumed'],
    }
