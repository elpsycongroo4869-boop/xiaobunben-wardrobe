"""Wardrobe 2 fixed entry; no image generation or remote Library writes.

Pinned package validation happens once per cache installation, with a brief
manifest/critical-file check on warm runs. Always stage the caller-supplied
fresh ledger, never reuse a cached CD state.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

SCHEMA = "wardrobe2-fixed-entry-v1"
REQUIRED_RUNTIME_FILES = ("studio.py", "p13_cli.py", "p13_runtime.py", "ai_bridge.py", "world_index.json", "bookshelf_extension/catalog.json")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding='utf-8'))


def write_atomic_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.write-', dir=p.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, p)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def manifest(p: Path) -> dict:
    v = read_json(p)
    if v.get('schema') != SCHEMA or v.get('slot') != 'public-wardrobe2':
        raise ValueError('invalid fixed-entry manifest')
    arc = v.get('archive',{})
    if not isinstance(arc.get('sha256'),str) or len(arc['sha256']) != 64:
        raise ValueError('missing pinned archive sha256')
    if v.get('runtime_schema') != 'wardrobe2-p13-integrated-v1':
        raise ValueError('unexpected runtime schema')
    import re
    if not re.fullmatch(r'P1\.3-R[1-9][0-9]*', str(v.get('version',''))):
        raise ValueError('unsupported P1.3-RN version')
    if v.get('runtime_dir_name') != 'wardrobe2-core':
        raise ValueError('unsafe runtime root')
    return v


def package_path(entry: Path, m: dict, override: Path | None) -> Path:
    return (override or entry.parent / m['archive']['path']).resolve()


def internal_sha_list(root: Path) -> dict:
    items = {}
    for line in (root / 'MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest, rel = line.split('  ',1)
        if len(digest)!=64 or rel.startswith('/') or '..' in Path(rel).parts or rel in items:
            raise ValueError('unsafe internal manifest')
        items[rel]=digest
    return items


def verify_runtime(root: Path, *, full: bool) -> dict:
    if not root.is_dir(): raise ValueError('runtime directory missing')
    manifest_file = root / 'MANIFEST.sha256'
    expected = internal_sha_list(root)
    paths = expected.keys() if full else {
        *REQUIRED_RUNTIME_FILES,
        *(name for name in expected if name.endswith('.py') and '/' not in name
          and not name.startswith('test_')),
    }
    if not full and "curated/world_index.json" in expected:
        paths.update(("curated/world_index.json", "curated/bookshelf_extension/catalog.json"))
    for rel in paths:
        if rel not in expected: raise ValueError(f'critical file not listed: {rel}')
        p = root / rel
        if not p.is_file() or sha256_file(p) != expected[rel]:
            raise ValueError(f'runtime tampered or incomplete: {rel}')
    return {"file_count":len(expected), "manifest_sha256":sha256_file(manifest_file)}


@contextmanager
def file_lock(path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        if os.name == 'nt':
            import msvcrt
            f.seek(0);f.write(b'0');f.flush();f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            try: yield
            finally:
                f.seek(0);msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(f.fileno(),fcntl.LOCK_UN)


def install_runtime(entry: Path, m: dict, cache: Path, override: Path|None = None, *, force=False) -> tuple[Path,str]:
    package = package_path(entry,m,override)
    fingerprint = m['archive']['sha256']
    cache.mkdir(parents=True,exist_ok=True)
    ver_dir = cache / ('runtime-' + fingerprint[:16])
    marker_path = ver_dir / '.activation.json'
    root = ver_dir / m['runtime_dir_name']
    with file_lock(cache/'.install.lock'):
        if not force and marker_path.is_file() and root.is_dir():
            a = read_json(marker_path)
            if a.get('package_sha256') == fingerprint and a.get('version') == m['version']:
                info = verify_runtime(root,full=False)
                if a.get('internal_manifest_sha256') == info['manifest_sha256']:
                    return root,'warm_verified'
            # Cache is suspect: fail closed; never use untrusted code.
            raise ValueError('cached runtime marker/critical files mismatch; explicitly clean cache or reinstall')
        if ver_dir.exists():
            if not force: raise ValueError('incomplete installation; explicitly retry activation with --force')
            shutil.rmtree(ver_dir)
        if not package.is_file(): raise FileNotFoundError('pinned ZIP unavailable; host must provide or materialize it')
        actual=sha256_file(package)
        if actual!=fingerprint: raise ValueError(f'package SHA mismatch: {actual}')
        tmp=Path(tempfile.mkdtemp(prefix='.runtime-',dir=cache))
        try:
            with zipfile.ZipFile(package) as z:
                names=z.namelist()
                if not names or any((not n.startswith(m['runtime_dir_name']+'/')) or n.startswith('/') or '..' in Path(n).parts for n in names):
                    raise ValueError('unsafe runtime archive layout')
                z.extractall(tmp)
            info=verify_runtime(tmp/m['runtime_dir_name'],full=True)
            write_atomic_json(tmp/'.activation.json',{
                'schema':'wardrobe2-pinned-activation-v1', 'version':m['version'],
                'package_sha256':fingerprint,'internal_manifest_sha256':info['manifest_sha256'],
                'verified_at_utc':datetime.now(timezone.utc).isoformat(),
                'files':info['file_count']})
            os.replace(tmp,ver_dir)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
        return root,'cold_verified'


def read_ledger(p: Path, schema: str) -> tuple[dict, bytes]:
    if not p.is_file(): raise FileNotFoundError('fresh P1.3 candidate ledger required')
    raw = p.read_bytes()
    data = json.loads(raw)
    if data.get('p13',{}).get('schema')!=schema:
        raise ValueError('not a migrated P1.3 ledger; never auto-migrate at 4869')
    if not isinstance(data.get('auto_seq'),int): raise ValueError('invalid auto_seq')
    if not isinstance(data.get('renders'),dict): raise ValueError('invalid render receipts')
    return {'auto_seq':data['auto_seq'],'recorded_images':len(data['renders']),
            'sha256':hashlib.sha256(raw).hexdigest()}, raw


def selection_prompt(runtime: Path, data_dir: Path, persona: str, memory_available: bool,
                     candidate_count=30) -> dict:
    # In-process import avoids a second Python interpreter and one additional
    # host tool round-trip. The engine itself is imported unmodified.
    from importlib import import_module
    prev = list(sys.path)
    try:
        sys.path.insert(0,str(runtime))
        module=import_module('p13_runtime')
        index, shelf_root = module.world_paths(runtime, data_dir)
        studio=module.P13Studio(data_dir,index,shelf_root=shelf_root)
        return studio.selection_prompt(persona,datetime.now(timezone.utc),memory_available=memory_available,
                                       candidate_count=candidate_count)
    finally: sys.path[:] = prev


def expand_ledger(runtime, ledger_bytes):
    ledger = json.loads(ledger_bytes)
    visits = ledger['p13']['local_cd']['shelf_visits']
    legacy = read_json(runtime / 'bookshelf_extension/catalog.json')
    golden = read_json(runtime / 'golden/bookshelf_extension/catalog.json')
    old_groups = {group['id'] for group in legacy['groups']}
    new_groups = {group['id'] for group in golden['groups']}
    if not old_groups <= new_groups or set(visits) not in (old_groups, new_groups):
        raise ValueError('ledger group mapping is neither Stable nor Golden')
    if set(visits) == new_groups:
        return ledger_bytes
    visits.update({group: 0 for group in sorted(new_groups - old_groups)})
    return json.dumps(ledger, ensure_ascii=False).encode('utf-8')


def ready(args) -> dict:
    candidate_count = getattr(args, 'candidate_count', 30)
    bookshelf = getattr(args, 'bookshelf', 'stable')
    profile_sha = getattr(args, 'creation_profile_sha256', None)
    if bookshelf not in ('stable', 'golden', 'curated'):
        raise ValueError('unknown bookshelf')
    if type(candidate_count) is not int or candidate_count < 1:
        raise ValueError('candidate_count must be a positive integer')
    entry=Path(args.entry).resolve();m=manifest(entry)
    root,mode=install_runtime(entry,m,Path(args.cache).resolve(),
                               Path(args.package) if args.package else None,force=args.force)
    ledger_info, ledger_bytes = read_ledger(Path(args.ledger), m['runtime_schema'])
    if bookshelf in ('golden', 'curated'):
        ledger_info['bookshelf'] = bookshelf
        ledger_bytes = expand_ledger(root, ledger_bytes)
    sessions=Path(args.sessions).resolve();sessions.mkdir(parents=True,exist_ok=True)
    if not args.session or '/' in args.session or '\\' in args.session or args.session in ('.','..'):
        raise ValueError('use safe --session id')
    data_dir=sessions/args.session
    # The first selected shelf is frozen for this session. A retry may not
    # silently sample a second shelf and invalidate the creator's choice.
    chosen=None
    selection_source='not_requested'
    with file_lock(sessions/'.session.lock'):
        if data_dir.exists():
            prev=data_dir/'.source.json'
            if not prev.is_file() or read_json(prev) != ledger_info:
                raise ValueError('session ID already exists with different ledger')
            session_mode='same-session-resumed'
        else:
            data_dir.mkdir()
            (data_dir/'shelf-state.json').write_bytes(ledger_bytes)
            write_atomic_json(data_dir/'.source.json',ledger_info)
            session_mode='fresh-session'
        if args.persona_summary is not None:
            pin_path=data_dir/'.selection-pin.json'
            persona_sha=hashlib.sha256(args.persona_summary.encode('utf-8')).hexdigest()
            if pin_path.is_file():
                pin=read_json(pin_path)
                if (pin.get('schema')!='wardrobe2-r3-selection-pin-v1' or
                        pin.get('ledger_sha256')!=ledger_info['sha256'] or
                        pin.get('persona_sha256')!=persona_sha or
                        pin.get('memory_available') is not bool(args.memory_available) or
                        pin.get('candidate_count', 30) != candidate_count or
                        pin.get('creation_profile_sha256') != profile_sha):
                    raise ValueError('selection pin conflict: session/persona/memory changed; start a fresh session')
                chosen=pin.get('payload')
                if not isinstance(chosen,dict) or not isinstance(chosen.get('prompt'),str) or not isinstance(chosen.get('menu'),dict):
                    raise ValueError('damaged session selection pin')
                selection_source='pinned_reused'
            else:
                chosen=selection_prompt(root,data_dir,args.persona_summary,args.memory_available,
                                        candidate_count=candidate_count)
                write_atomic_json(pin_path,{
                    'schema':'wardrobe2-r3-selection-pin-v1',
                    'ledger_sha256':ledger_info['sha256'],
                    'persona_sha256':persona_sha,
                    'memory_available':bool(args.memory_available),
                    'candidate_count':candidate_count,
                    'creation_profile_sha256':profile_sha,
                    'payload':chosen,
                })
                selection_source='generated_and_pinned'
    result={"status":"ready","version":m['version'],"runtime":str(root),"runtime_mode":mode,
            "data_dir":str(data_dir),"session_mode":session_mode,"selection_source":selection_source,"ledger":ledger_info,
            "suggested_next":"use P1.3-R2 unmodified studio and seal; persist/check work SHA before button",
            "prompt":chosen}
    return result
