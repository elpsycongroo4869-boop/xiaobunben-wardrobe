"""Verify a host-supplied readback against an independently retained seal pin."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def _verify_snapshot(studio, snapshot: bytes, work_id: str, expected_seal: str) -> dict:
    envelope = json.loads(snapshot.decode("utf-8"))
    if not isinstance(envelope, dict):
        raise ValueError("readback must be a seal object")
    work = envelope.get("work")
    if not isinstance(work, dict) or work.get("protocol") != studio.PROTOCOL:
        raise ValueError("invalid sealed work protocol")
    job = work.get("job")
    if not isinstance(job, dict) or job.get("work_id") != work_id:
        raise ValueError("readback work ID mismatch")
    if envelope.get("state") != "ready" or envelope.get("confirmed_images") != []:
        raise ValueError("readback is not an unopened ready seal")
    if envelope.get("seal_sha256") != expected_seal or studio.digest(work) != expected_seal:
        raise ValueError("readback seal does not match the expected SHA-256")
    render = work.get("render_instruction")
    if not isinstance(render, str) or not render.strip():
        raise ValueError("sealed render instruction is missing")
    return {
        "status": "readback_verified",
        "work_id": work_id,
        "seal_sha256": expected_seal,
        "render_payload_sha256": hashlib.sha256(render.encode("utf-8")).hexdigest(),
    }


def verify_readback(studio, path, work_id, expected_seal):
    return _verify_snapshot(studio, path.read_bytes(), work_id, expected_seal)


def verify_bytes(studio, original: bytes, readback: bytes, work_id: str, expected_seal: str) -> dict:
    """Verify exact outer bytes and canonical work against one immutable snapshot."""
    if original != readback:
        raise ValueError("readback differs byte-for-byte from original pending envelope")
    result = _verify_snapshot(studio, readback, work_id, expected_seal)
    result["envelope_bytes_sha256"] = hashlib.sha256(readback).hexdigest()
    result["envelope_bytes_identical"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True, help="already verified R2 runtime directory")
    parser.add_argument("--readback", type=Path, required=True, help="host-retrieved seal file")
    parser.add_argument("--original", type=Path, help="local sealed envelope retained from prepare; require byte-identical readback")
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--seal-sha256", required=True, help="independently retained local prepare pin")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{64}", args.seal_sha256):
        parser.error("--seal-sha256 must be a lowercase SHA-256 hex digest")
    runtime = args.runtime.resolve()
    studio_file = runtime / "studio.py"
    if not studio_file.is_file() or studio_file.resolve() != studio_file:
        parser.error("--runtime must contain the verified runtime's studio.py")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime))
    try:
        import studio

        if Path(studio.__file__).resolve() != studio_file:
            raise ValueError("studio was loaded from outside the specified runtime")
        if args.original is None:
            result = verify_readback(studio, args.readback, args.work_id, args.seal_sha256)
        else:
            result = verify_bytes(studio, args.original.read_bytes(), args.readback.read_bytes(),
                                  args.work_id, args.seal_sha256)
    except (ImportError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
