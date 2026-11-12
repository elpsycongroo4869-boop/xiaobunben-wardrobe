"""The single P1.4 delivery gate, with a split fallback for basic hosts."""
import hashlib
import json
from pathlib import Path

from p13_prepare_handoff import prepare_handoff, prepare_local
from p13_verify_delivery import verify_bytes

CHAT_SCHEMA = "wardrobe2-p13-native-chat-v1"


def _check_payload(result, raw, *, studio):
    # Compare the full creative text, including the exact native click payload.
    work = json.loads(raw)["work"]
    job = work["job"]
    ui = result["chat_ui"]
    roles = job["roles"]
    expected_roles = {}
    for role in studio.MANDATORY:
        fields = studio.role_fields(job, role)
        expected_roles[role] = {key: roles[role][key] for key in fields}
    expected = {
        "producer": {key: job["producer"][key] for key in studio.PRODUCER_FIELDS},
        "roles": expected_roles,
        "render_instruction": work["render_instruction"],
    }
    if "chapter" in job:
        expected["chapter"] = job["chapter"]
    if "role_director" in ui["preview"]:
        if "role_director" not in job:
            raise ValueError("unsealed role director in native preview")
        expected["role_director"] = job["role_director"]
    if (ui["schema"], ui["state"], ui["work_id"], ui["seal_sha256"]) != (
        CHAT_SCHEMA, "ready", result["work_id"], result["seal_sha256"],
    ) or ui["preview"] != expected:
        raise ValueError("native preview differs from verified sealed work")


def _gate(result, *, verified):
    ui = result["chat_ui"]
    # P1.4 must also retain the verified action in the original session.
    ui = {**ui, "native_ui": {**ui["native_ui"], "show_open_button": False}}
    result = {**result, "chat_ui": ui}
    if verified:
        result["open_action"] = {
            "work_id": result["work_id"],
            "seal_sha256": result["seal_sha256"],
            "envelope_bytes_sha256": result["delivery"]["envelope_bytes_sha256"],
            "text": ui["preview"]["render_instruction"],
        }
    return result


def prepare(runtime, data_dir, job_file, *, studio=None, create_if_absent=None, read=None):
    if (create_if_absent is None) != (read is None):
        raise ValueError("supply both trusted store callbacks or neither")
    if create_if_absent is not None:
        if studio is None or not callable(create_if_absent) or not callable(read):
            raise ValueError("coalesced delivery requires the pinned studio and trusted callbacks")
        result = prepare_handoff(
            runtime, data_dir, job_file, studio=studio, create_if_absent=create_if_absent,
            read=read, validate_payload=lambda result, raw: _check_payload(result, raw, studio=studio),
        )
        return _gate(result, verified=True)

    prepared = prepare_local(runtime, data_dir, job_file)
    work_id = prepared["work_id"]
    pending = Path(data_dir) / "pending" / f"{work_id}.json"
    pin = hashlib.sha256(pending.read_bytes()).hexdigest()
    return _gate({
        "status": "awaiting_readback",
        "work_id": work_id,
        "seal_sha256": prepared["seal_sha256"],
        "chat_ui": prepared["chat_ui"],
        "resumed": prepared["resumed"],
        "pending_path": str(pending),
        "envelope_bytes_sha256": pin,
    }, verified=False)


def verify_delivery(prepared, *, studio, original, readback):
    if prepared.get("status") != "awaiting_readback" or prepared.get("open_action") is not None:
        raise ValueError("expected a P1.4 pending delivery")
    if hashlib.sha256(original).hexdigest() != prepared["envelope_bytes_sha256"]:
        raise ValueError("local envelope differs from the independently retained byte pin")
    delivery = verify_bytes(studio, original, readback, prepared["work_id"], prepared["seal_sha256"])
    _check_payload(prepared, readback, studio=studio)
    return _gate({
        "status": "handoff_verified",
        "work_id": prepared["work_id"],
        "seal_sha256": prepared["seal_sha256"],
        "chat_ui": prepared["chat_ui"],
        "delivery": delivery,
        "resumed": prepared["resumed"],
    }, verified=True)


def verify_open(readback, *, studio, work_id, seal_sha256, envelope_bytes_sha256,
                expected_action_text):
    if hashlib.sha256(readback).hexdigest() != envelope_bytes_sha256:
        raise ValueError("destination envelope differs from the original button byte pin")
    delivery = verify_bytes(studio, readback, readback, work_id, seal_sha256)
    instruction = json.loads(readback)["work"]["render_instruction"]
    if instruction != expected_action_text:
        raise ValueError("click payload differs from the sealed photography text")
    return {**delivery, "render_instruction": instruction}
