"""Wardrobe 2 P0.2: a compact, deterministic library with a virtual Original entry.

Development-only Python core, not a requirement for public users. No model/tool calls.
The Creative Producer retains final choice; this module exposes eligible entries.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

ORIGINAL_ID = "ORIGINAL"
ORIGINAL_CD = 10  # number of subsequent successful autonomous photos


def new_state(original_cd: int = ORIGINAL_CD) -> dict[str, Any]:
    if not isinstance(original_cd, int) or isinstance(original_cd, bool) or original_cd < 0:
        raise ValueError("original_cd must be a nonnegative integer")
    return {
        "schema": "wardrobe2-shelf-state-v0.2",
        "auto_seq": 0,
        "book_stats": {},
        "original": {"auto_use_count": 0, "next_eligible_auto_seq": 1, "fixed_cd": original_cd},
        "renders": {},
        "work_books": {},
        "work_origins": {},
        "active_notes": [],
    }


def cd_for_use(n: int) -> int:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("use count must be positive integer")
    return 6 * n * (n + 1)


class Shelf:
    def __init__(self, book_index: dict[str, Any], state: dict[str, Any] | None = None) -> None:
        books = book_index["books"]
        ids = [b["id"] for b in books]
        if ORIGINAL_ID in ids or len(set(ids)) != len(ids):
            raise ValueError("duplicate/reserved book id")
        self.books = {b["id"]: b for b in books}
        self.state = state if state is not None else new_state()
        if self.state.get("schema") != "wardrobe2-shelf-state-v0.2":
            raise ValueError("unsupported state schema: explicitly migrate older prototypes")

    def _read_stat(self, book_id: str) -> dict[str, Any]:
        if book_id not in self.books:
            raise KeyError(f"unknown book: {book_id}")
        # Do not mutate state while just browsing; preparation has NO writes.
        return self.state["book_stats"].get(
            book_id, {"auto_use_count": 0, "next_eligible_auto_seq": 1, "active": True}
        )

    def _write_stat(self, book_id: str) -> dict[str, Any]:
        self._read_stat(book_id)  # validates book_id
        return self.state["book_stats"].setdefault(
            book_id, {"auto_use_count": 0, "next_eligible_auto_seq": 1, "active": True}
        )

    def original_available(self) -> bool:
        return self.state["auto_seq"] + 1 >= self.state["original"]["next_eligible_auto_seq"]

    def available_books(self) -> list[dict[str, Any]]:
        target_seq = self.state["auto_seq"] + 1
        out = []
        for book_id, book in self.books.items():
            stat = self._read_stat(book_id)
            if stat["active"] and target_seq >= stat["next_eligible_auto_seq"]:
                out.append({"id": book_id, "title": book["title"], "hook": book.get("hook", "")})
        return out

    def available_entries(self) -> list[dict[str, Any]]:
        """One single menu: fixed books plus the optional virtual Original book.

        No visit counts, cooldown scores, or instructions to choose underused books.
        The AI producer makes ONE entry choice, then deepens that one story.
        """
        entries = [{"kind": "fixed", **book} for book in self.available_books()]
        if self.original_available():
            entries.append({
                "kind": "original", "id": ORIGINAL_ID, "title": "原创",
                "hook": "自由发明一个此刻真正想拍的世界与事件",
            })
        return entries

    def remove_book(self, book_id: str) -> None:
        self._write_stat(book_id)["active"] = False

    def restore_book(self, book_id: str) -> None:
        self._write_stat(book_id)["active"] = True

    def live_notes(self, now: datetime) -> list[dict[str, Any]]:
        if now.tzinfo is None:
            raise ValueError("timezone-aware now required")
        return [n for n in self.state["active_notes"]
                if datetime.fromisoformat(n["expires_at"]) > now]

    def record_success(self, *, origin: str, work_id: str, render_id: str,
                       now: datetime, book_id: str | None = None,
                       event_signature: str | None = None,
                       deliberate_revisit_ref: str | None = None) -> bool:
        """Called only after image-success confirmation by host.

        user_directed: zero persistence, zero cooldown effects.
        autonomous_original: chosen from the visible Original menu entry.
        autonomous_spontaneous: an already-formed specific creative idea may
          bypass menu cooldown, but still restarts Original's fixed cooldown.
        """
        if origin == "user_directed":
            return False
        if origin not in {"autonomous_library", "autonomous_original", "autonomous_spontaneous"}:
            raise ValueError("unsupported origin")
        if not work_id or not render_id:
            raise ValueError("stable work_id and render_id required")
        if now.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        if render_id in self.state["renders"]:
            return False

        previous_origin = self.state["work_origins"].get(work_id)
        first_work_image = work_id not in self.state["work_origins"]
        previous_book = self.state["work_books"].get(work_id)
        if not first_work_image:
            if previous_origin != origin or previous_book != book_id:
                raise ValueError("same work cannot change origin or library book")

        stat = None
        if origin == "autonomous_library":
            if book_id is None:
                raise ValueError("library origin requires book_id")
            stat = self._read_stat(book_id)
            if first_work_image:
                if not stat["active"]:
                    raise ValueError("book is removed from active shelf")
                if self.state["auto_seq"] + 1 < stat["next_eligible_auto_seq"]:
                    prev_work = self.state["work_books"].get(deliberate_revisit_ref)
                    if not deliberate_revisit_ref or prev_work != book_id:
                        raise ValueError("cooling book requires a grounded prior work ref")
        else:
            if book_id is not None:
                raise ValueError("original cannot impersonate library book")
            if first_work_image and origin == "autonomous_original" and not self.original_available():
                raise ValueError("Original entry is cooling; choose a fixed book or bring a specific independent idea")

        # From here: only successful autonomous renders mutate state.
        seq = self.state["auto_seq"] + 1
        self.state["active_notes"] = self.live_notes(now)
        self.state["renders"][render_id] = {
            "work_id": work_id, "origin": origin, "book_id": book_id,
            "auto_seq": seq, "at": now.isoformat(),
        }
        self.state["auto_seq"] = seq
        if first_work_image:
            self.state["work_origins"][work_id] = origin
            self.state["work_books"][work_id] = book_id
            if origin == "autonomous_library":
                stat = self._write_stat(book_id)
                stat["auto_use_count"] += 1
                stat["next_eligible_auto_seq"] = seq + cd_for_use(stat["auto_use_count"]) + 1
            else:
                original = self.state["original"]
                original["auto_use_count"] += 1
                original["next_eligible_auto_seq"] = seq + original["fixed_cd"] + 1
                if event_signature and event_signature.strip():
                    sig = event_signature.strip()
                    if sig not in {n["signature"] for n in self.state["active_notes"]}:
                        self.state["active_notes"].append({
                            "signature": sig, "created_at": now.isoformat(),
                            "expires_at": (now + timedelta(hours=24)).isoformat(),
                        })
        return True

    def snapshot(self, now: datetime) -> dict[str, Any]:
        """Pure read: no mutations and no whole-history scan."""
        return {
            "auto_seq": self.state["auto_seq"],
            "available_entries": self.available_entries(),
            "active_notes": self.live_notes(now),
        }
