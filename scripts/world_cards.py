"""Optional world-card discovery. A draw with zero cited cards does no deck I/O."""

from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECK = ROOT / 'references' / 'original-worlds.json'


@lru_cache(maxsize=8)
def _index(path, version):
    data = json.loads(path.read_text(encoding='utf-8'))
    entries = data['entries']
    if not isinstance(entries, list) or len(entries) != data.get('count'):
        raise ValueError('World deck count disagrees with its entries')
    indexed = {}
    for card in entries:
        for key in ('id', 'title', 'category', 'world_logic'):
            if not isinstance(card.get(key), str) or not card[key].strip():
                raise ValueError('World card is missing ' + key)
        if card['id'] in indexed:
            raise ValueError('Duplicate world-card ID: ' + card['id'])
        indexed[card['id']] = card
    return indexed


def load_index(path=DEFAULT_DECK):
    path = Path(path).resolve()
    info = path.stat()
    return _index(path, (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns, info.st_size))


def cited_ids(audit):
    if not isinstance(audit, dict):
        return set()
    ids = set()
    for field in ('browsed_card_ids', 'adopted_card_ids'):
        values = audit.get(field, [])
        if not isinstance(values, list) or len(values) > 20 or any(not isinstance(value, str) for value in values):
            raise ValueError(field + ' must be a small list of card IDs')
        ids.update(values)
    return ids


def select_cards(audit, path=DEFAULT_DECK):
    ids = cited_ids(audit)
    if not ids:
        return {}
    index = load_index(path)
    missing = ids - index.keys()
    if missing:
        raise ValueError('Unknown world-card IDs: ' + ', '.join(sorted(missing)))
    return {key: index[key] for key in sorted(ids)}
