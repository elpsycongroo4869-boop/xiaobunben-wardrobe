"""Optional 30-book bookshelf navigator. Never mutates the legacy global CD ledger.

The publisher catalog contains only group IDs and book IDs. Browse reads exactly
one shelf brief; selected-world detail reads exactly one standalone card.
No creative/model requests are performed here.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
from pathlib import Path

BASE = Path(__file__).resolve().parent / 'bookshelf_extension'


def _read(path: Path) -> dict:
    with Path(path).open('r', encoding='utf-8') as stream:
        return json.load(stream)


def catalog(root: Path = BASE) -> dict:
    d = _read(Path(root) / 'catalog.json')
    if d.get('schema') != 'wardrobe2-bookshelf-catalog-v1':
        raise ValueError('unsupported bookshelf catalog')
    return d


def eligible(book_id: str, state: dict) -> bool:
    """Same global successful-auto-photo CD eligibility as legacy Shelf."""
    if state.get('schema') != 'wardrobe2-shelf-state-v0.2':
        raise ValueError('unsupported CD ledger; do not migrate implicitly')
    stat = state.get('book_stats', {}).get(book_id, {})
    return stat.get('active', True) and state['auto_seq'] + 1 >= stat.get('next_eligible_auto_seq', 1)


def choose_shelf(state: dict, root: Path = BASE, rng=None) -> str | None:
    """Weights shelves by available book count, so a 12-book tail isn't favored.

    Uses only catalog's compact IDs and state stats, no shelf blurbs or full cards.
    Returns None if all fixed books are cooling or disabled.
    """
    groups = catalog(root)['groups']
    weights = [sum(bool(eligible(b, state)) for b in g['ids']) for g in groups]
    total = sum(weights)
    if not total:
        return None
    # Production: system randomness. Tests can pass deterministic random.Random.
    draw = rng.randrange(total) if rng is not None else secrets.randbelow(total)
    for group, weight in zip(groups, weights):
        if draw < weight:
            return group['id']
        draw -= weight
    raise AssertionError('unreachable')


def browse_shelf(group_id: str, state: dict, root: Path = BASE) -> dict:
    d = catalog(root)
    group = next((g for g in d['groups'] if g['id'] == group_id), None)
    if group is None:
        raise ValueError(f'unknown shelf group: {group_id}')
    shelf = _read(Path(root) / group['path'])
    expected_ids = group['ids']
    entries = shelf.get('entries', [])
    if shelf.get('id') != group_id or [v['id'] for v in entries] != expected_ids:
        raise ValueError('shelf file mismatch with catalog')
    available = [e for e in entries if eligible(e['id'], state)]
    original_state = state['original']
    original_available = state['auto_seq'] + 1 >= original_state['next_eligible_auto_seq']
    return {
        'shelf_id': group_id,
        'shelf_total': len(entries),
        'available_books': available,
        'original_entry': ({'id':'ORIGINAL','title':'原创','intro':'自由创造此刻真正想拍的世界与事件'}
                           if original_available else None),
        'cd_mode': d['cd_mode'],
    }


def load_selected_card(book_id: str, root: Path = BASE) -> dict:
    """Read one complete original world card after selection, never the 102-card file."""
    if not re.fullmatch(r'B\d{3,}', book_id):
        raise ValueError('invalid fixed-world ID')
    c = catalog(root)
    if not any(book_id in g['ids'] for g in c['groups']):
        raise ValueError('world ID is not in bookshelf catalog')
    path = Path(root) / 'cards' / f'{book_id}.json'
    hashes = c.get('card_sha256')
    if hashes is None:
        book = _read(path)
    else:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != hashes[book_id]:
            raise ValueError('curated chapter card differs from catalog')
        book = json.loads(raw)
    if book.get('id') != book_id:
        raise ValueError('world card ID mismatch')
    return book


def selection_prompt_for_shelf(bookshelf: dict, persona_summary: str) -> str:
    entries = bookshelf['available_books'][:]
    if bookshelf['original_entry'] is not None:
        entries.append(bookshelf['original_entry'])
    lines = ['- '+e['id']+' '+e['title']+'：'+(
        ' / '.join(f"{row['id']} {row['title']}" for row in e['chapters'])
        if 'chapters' in e else e['intro']) for e in entries]
    shelf = bookshelf['shelf_id']
    return '\n'.join([
        '# 小笨笨衣橱二号 · 制作人一次选题（独立30本书架实验）',
        '当前角色：' + persona_summary,
        ('这一次已走进 '+shelf+' 书架。仅浏览本书架当前可选的书脊简介，其他书架不读取。'
         if shelf is not None else '本轮没有可用的固定世界，使用下列可用入口或已有的明确原创灵感。'),
        ('只看本架书名和可选章名。选定章节后再读取完整 Point。'
         if any('chapters' in entry for entry in entries)
         else '简介只帮助认识世界，不是指定剧情；选中后再读取完整世界卡，深化一个有独特瞬间的故事。'),
        '请从当前可选条目选择你真正想创作的世界。不要因历史使用次数排名，也不要同时提出多个故事。',
        '如果你已经有具体明确的独立原创灵感，可以按原规则使用 autonomous_spontaneous。',
        '输出仅一份 JSON：{"origin":"autonomous_library|autonomous_original|autonomous_spontaneous",'
        '"book_id":"B010或null","initial_intent":"本次想拍什么"}。',
        '\n'.join(lines),
    ])
