"""P1.2.3a PROTOTYPE ONLY: per-shelf cooldown and safe fixed-book fallback.

The official Studio/Shelf and Library ledgers are NOT modified by this module.
A sidecar local-CD state can be bootstrapped by replaying legacy confirmed
first-work renders; production integration is explicitly out of scope.

CD: fixed book after its nth successful distinct-work adoption waits
2 / 4 / 6 / 8 *other* successful book adoptions on the same shelf,
with an adaptive cap of active_shelf_books - 1.
Only a confirmed distinct-work first render advances a shelf counter.
A shelf with exactly one active physical book has no book cooldown.
When no fixed book globally is eligible, one active book is chosen uniformly
and explicitly marked as a one-time override.
"""
from __future__ import annotations

import copy
import random
import secrets
from typing import Any

SCHEMA = 'wardrobe2-local-cd-sidecar-prototype-v1'
CD_LENGTHS = (2, 4, 6, 8)
CD_REFERENCE_CANDIDATE_COUNT = 30


def cd_length(auto_use_count: int, candidate_count: int = CD_REFERENCE_CANDIDATE_COUNT) -> int:
    if type(auto_use_count) is not int or auto_use_count < 1:
        raise ValueError('positive integer use count expected')
    if type(candidate_count) is not int or candidate_count < 1:
        raise ValueError('positive integer candidate count expected')
    base = CD_LENGTHS[min(auto_use_count - 1, len(CD_LENGTHS) - 1)]
    width = min(candidate_count, CD_REFERENCE_CANDIDATE_COUNT)
    scaled = (base * width + CD_REFERENCE_CANDIDATE_COUNT - 1) // CD_REFERENCE_CANDIDATE_COUNT
    return max(base // 2, scaled)


def group_map(catalog: dict) -> dict[str, str]:
    mapping = {}
    for group in catalog['groups']:
        for book in group['ids']:
            if book in mapping:
                raise ValueError('duplicate book in shelves')
            mapping[book] = group['id']
    return mapping


def new_local_state(catalog: dict) -> dict:
    return {'schema': SCHEMA,
            'shelf_visits': {g['id']: 0 for g in catalog['groups']},
            'book_stats': {}, 'work_books': {}, 'render_ids': {}}


def check_state(state: dict, catalog: dict) -> None:
    if state.get('schema') != SCHEMA:
        raise ValueError('unsupported local-CD sidecar state')
    expected = {g['id'] for g in catalog['groups']}
    if set(state['shelf_visits']) != expected:
        raise ValueError('sidecar shelf mapping mismatch: explicit migration required')


def _active(book: str, legacy_state: dict) -> bool:
    return legacy_state.get('book_stats', {}).get(book, {}).get('active', True)


def active_ids(shelf_id: str, catalog: dict, legacy_state: dict) -> list[str]:
    group = next((g for g in catalog['groups'] if g['id'] == shelf_id), None)
    if group is None:
        raise ValueError(f'unknown shelf group: {shelf_id}')
    return [b for b in group['ids'] if _active(b, legacy_state)]


def eligible(book: str, local_state: dict, catalog: dict, legacy_state: dict) -> bool:
    check_state(local_state, catalog)
    shelf_id = group_map(catalog).get(book)
    if shelf_id is None or not _active(book, legacy_state):
        return False
    ids = active_ids(shelf_id, catalog, legacy_state)
    if len(ids) == 1:  # A single-book shelf must never be deadlocked by CD.
        return True
    next_visit = local_state['shelf_visits'][shelf_id] + 1
    next_eligible = local_state['book_stats'].get(book, {}).get('next_eligible_visit', 1)
    return next_visit >= next_eligible


def eligible_by_shelf(local_state: dict, catalog: dict, legacy_state: dict) -> dict[str, list[str]]:
    check_state(local_state, catalog)
    group_map(catalog)
    result = {}
    stats = local_state['book_stats']
    for group in catalog['groups']:
        shelf_id = group['id']
        active = [book for book in group['ids'] if _active(book, legacy_state)]
        visit = local_state['shelf_visits'][shelf_id] + 1
        result[shelf_id] = (active if len(active) == 1 else
                            [book for book in active
                             if stats.get(book, {}).get('next_eligible_visit', 1) <= visit])
    return result


def _random_index(upper: int, rng=None) -> int:
    if upper <= 0:
        raise ValueError('empty random choice')
    return rng.randrange(upper) if rng is not None else secrets.randbelow(upper)


def choose(local_state: dict, catalog: dict, legacy_state: dict, rng=None, *, shelf_fallback=False) -> dict[str, Any]:
    """Weighted by eligible-book count; fallback only if *every* shelf cooling.

    Does not read full world cards, does not mutate either ledger, and never
    returns deactivated books. The override is a selection receipt, not a CD reset.
    """
    available = eligible_by_shelf(local_state, catalog, legacy_state)
    count = sum(map(len, available.values()))
    if count:
        draw = _random_index(count, rng)
        for group in catalog['groups']:
            candidates = available[group['id']]
            if draw < len(candidates):
                return {'shelf_id': group['id'], 'mode': 'normal',
                        'available_ids': candidates, 'override_book_id': None}
            draw -= len(candidates)
        raise AssertionError('unreachable')
    active = [(g['id'], bid) for g in catalog['groups'] for bid in g['ids']
              if _active(bid, legacy_state)]
    if not active:
        return {'shelf_id': None, 'mode': 'no_active_fixed_books',
                'available_ids': [], 'override_book_id': None}
    shelf_id, bid = active[_random_index(len(active), rng)]
    candidates = [book for sid, book in active if sid == shelf_id] if shelf_fallback else [bid]
    return {'shelf_id': shelf_id, 'mode': 'global_cooldown_fallback',
            'available_ids': candidates, 'override_book_id': bid if len(candidates) == 1 else None}


def _mark_work(state: dict, book_id: str, work_id: str, catalog: dict, active_count: int,
               candidate_count: int = CD_REFERENCE_CANDIDATE_COUNT) -> None:
    shelf_id = group_map(catalog)[book_id]
    stat = state['book_stats'].get(book_id, {'auto_use_count': 0, 'next_eligible_visit': 1})
    adoption = stat['auto_use_count'] + 1
    # Smaller menus shorten CD, with a floor that preserves all four repeat tiers.
    effective_cd = min(cd_length(adoption, candidate_count), max(active_count - 1, 0))
    state['shelf_visits'][shelf_id] += 1
    seq = state['shelf_visits'][shelf_id]
    stat['auto_use_count'] = adoption
    stat['next_eligible_visit'] = seq + effective_cd + 1
    state['book_stats'][book_id] = stat
    state['work_books'][work_id] = book_id


def record_success(local_state: dict, catalog: dict, legacy_state: dict, *,
                   work_id: str, render_id: str, book_id: str | None,
                   origin: str = 'autonomous_library',
                   fallback_book_id: str | None = None,
                   deliberate_revisit_ref: str | None = None,
                   candidate_count: int = CD_REFERENCE_CANDIDATE_COUNT) -> bool:
    """Simulation of success callback; DO NOT use as a replacement for Studio.confirm_image.

    Caller must have confirmed the real render and hold an appropriate common
    writer lock. In production, sidecar and global ledger must commit atomically.
    This module intentionally does not write either file.
    """
    check_state(local_state, catalog)
    if origin == 'user_directed':
        return False
    if origin in {'autonomous_original', 'autonomous_spontaneous'}:
        return False  # Original retains existing independent global policy.
    if origin != 'autonomous_library':
        raise ValueError('unsupported origin')
    if not work_id or not render_id or not book_id:
        raise ValueError('ids are required')
    if render_id in local_state['render_ids']:
        if (local_state['render_ids'][render_id] != work_id or
                local_state['work_books'].get(work_id) != book_id):
            raise ValueError('render_id is already bound to another work')
        return False
    old_book = local_state['work_books'].get(work_id)
    if old_book is not None and old_book != book_id:
        raise ValueError('work ID conflicts with another world')
    if book_id not in group_map(catalog) or not _active(book_id, legacy_state):
        raise ValueError('book not active or not in catalog')
    if old_book is None:
        allowed = eligible(book_id, local_state, catalog, legacy_state)
        if not allowed:
            fallback_valid = (fallback_book_id == book_id and
                              sum(map(len, eligible_by_shelf(local_state, catalog, legacy_state).values())) == 0)
            revisit_valid = (deliberate_revisit_ref is not None and
                             local_state['work_books'].get(deliberate_revisit_ref) == book_id)
            if not (fallback_valid or revisit_valid):
                raise ValueError('cooling book requires validated global fallback or grounded revisit')
        shelf_id = group_map(catalog)[book_id]
        _mark_work(local_state, book_id, work_id, catalog, len(active_ids(shelf_id, catalog, legacy_state)),
                   candidate_count)
    local_state['render_ids'][render_id] = work_id
    return True


def bootstrap_from_legacy(legacy_state: dict, catalog: dict) -> dict:
    """NON-WRITING migration preview using confirmed historical renders only.

    Replays each work once at its earliest successful autonomous fixed render.
    Historical CD is not re-enforced during replay because the new mechanism is
    a *new* policy. No file is written, and current global state is not mutated.
    """
    state = new_local_state(catalog)
    mapping = group_map(catalog)
    work_events = {}
    for render_id, receipt in legacy_state.get('renders', {}).items():
        if receipt.get('origin') != 'autonomous_library':
            continue
        bid, wid = receipt.get('book_id'), receipt.get('work_id')
        if bid not in mapping or not wid:
            continue
        prev = work_events.get(wid)
        if prev is None or receipt['auto_seq'] < prev[0]:
            work_events[wid] = (receipt['auto_seq'], bid)
        state['render_ids'][render_id] = wid
    for wid, (_, bid) in sorted(work_events.items(), key=lambda x: (x[1][0], x[0])):
        sid = mapping[bid]
        _mark_work(state, bid, wid, catalog, len(active_ids(sid, catalog, legacy_state)))
    return state


def read_shelf_entries(group_id: str, catalog: dict, root) -> list[dict]:
    """Read and verify only the selected shelf's spines."""
    from pathlib import Path
    import hashlib
    import json
    group = next((g for g in catalog['groups'] if g['id'] == group_id), None)
    if group is None:
        raise ValueError('unknown shelf')
    raw = (Path(root) / group['path']).read_bytes()
    if group.get('sha256') and hashlib.sha256(raw).hexdigest() != group['sha256']:
        raise ValueError('curated shelf differs from catalog')
    data = json.loads(raw)
    if data.get('id') != group_id or [e['id'] for e in data['entries']] != group['ids']:
        raise ValueError('group IDs and shelf file disagree')
    return data['entries']


def browse_local(group_id: str, local_state: dict, catalog: dict, legacy_state: dict,
                 root, *, override_book_id: str | None = None) -> dict:
    """Inspect one shelf, optionally using a legacy single-book fallback."""
    entries = read_shelf_entries(group_id, catalog, root)
    available = eligible_by_shelf(local_state, catalog, legacy_state)
    allowed = available[group_id]
    if override_book_id is not None:
        if override_book_id not in active_ids(group_id, catalog, legacy_state):
            raise ValueError('override book is inactive or not in chosen shelf')
        if any(available.values()):
            raise ValueError('global override is allowed only when ALL fixed books cool')
        allowed = [override_book_id]
    return {'shelf_id': group_id, 'shelf_total': len(entries),
            'available_books': [row for row in entries if row['id'] in allowed],
            'override_book_id': override_book_id,
            'cd_mode': 'local-successful-adoptions-2-4-6-8-adaptive-prototype'}
