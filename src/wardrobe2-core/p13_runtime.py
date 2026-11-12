"""P1.3 candidate: 30-book shelves + shared SELF shelf, single durable ledger.

Creative jobs and sealed render instructions still belong to the original Studio.
All new book/SELF CD information lives in `shelf-state.json['p13']`, under the
same Studio file lock and atomic ledger replacement as render receipts.
This runtime neither retrieves memories nor generates images: those operations
require an authorized ChatGPT host and a real successful provider callback.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import random

from bookshelf_local_cd import (
    bootstrap_from_legacy, read_shelf_entries, choose, eligible as cd_eligible,
    eligible_by_shelf, new_local_state, record_success as record_local_success,
)
from bookshelf_nav import BASE, catalog, load_selected_card, selection_prompt_for_shelf
from chapter_shelf import (FREE_ORIGINS, available_chapters, chapter_zero_remaining,
                           free_story_remaining, record_chapter, record_curated_success)
from studio import Studio, read_json, atomic_json, studio_lock
from wardrobe2_core import Shelf, new_state, cd_for_use

VERSION = 'wardrobe2-p13-integrated-v1'
SELF_BOOKS = ('SELF_FREE', 'SELF_ECHO')
SELF_CD = (3, 4, 5, 8)
try:
    SHANGHAI = ZoneInfo('Asia/Shanghai')
except ZoneInfoNotFoundError:
    SHANGHAI = timezone(timedelta(hours=8), name='Asia/Shanghai')


def day_for(now: datetime) -> str:
    if now.tzinfo is None:
        raise ValueError('timezone-aware timestamp required')
    return now.astimezone(SHANGHAI).date().isoformat()


def create_p13_state(legacy: dict, book_catalog: dict, now: datetime) -> dict:
    if 'p13' in legacy:
        raise ValueError('already P1.3; do not migrate twice')
    result = deepcopy(legacy)
    result['p13'] = {
        'schema': VERSION,
        'local_cd': bootstrap_from_legacy(legacy, book_catalog),
        'self': {
            'timezone': 'Asia/Shanghai', 'day_key': day_for(now),
            'uses_today': 0, 'remaining_other_successes': 0,
            'self_work_ids': {}, 'other_render_ids': [],
        },
    }
    return result


class P13Shelf(Shelf):
    p13_enabled = True

    def __init__(self, index, state, *, book_catalog=None, chapter_priority=False):
        super().__init__(index, state)
        self.book_catalog = book_catalog if book_catalog is not None else catalog()
        self.chapter_priority = chapter_priority
        if self.state.get('p13', {}).get('schema') != VERSION:
            raise ValueError('P1.3 state not enabled; migrate explicitly first')

    def local_eligible(self, book_id: str) -> bool:
        return cd_eligible(book_id, self.state['p13']['local_cd'], self.book_catalog, self.state)

    def local_all_cooling(self) -> bool:
        e = eligible_by_shelf(self.state['p13']['local_cd'], self.book_catalog, self.state)
        return not any(e.values())

    def has_active_books(self) -> bool:
        stats = self.state['book_stats']
        return any(stats.get(book, {}).get('active', True) for book in self.books)

    def original_available(self) -> bool:
        # Keep an escape hatch when the user explicitly deactivates the whole shelf.
        return super().original_available() or (self.chapter_priority and not self.has_active_books())

    def _self_data(self, now: datetime, *, commit: bool) -> dict:
        d = self.state['p13']['self']
        today = day_for(now)
        if d['day_key'] < today:
            if commit:
                d.update(day_key=today, uses_today=0, remaining_other_successes=0)
                return d
            temp = dict(d)
            temp.update(day_key=today, uses_today=0, remaining_other_successes=0)
            return temp
        # A late callback must never rewind a newer day's state.
        return d

    def self_eligible(self, now: datetime) -> bool:
        return self._self_data(now, commit=False)['remaining_other_successes'] == 0

    def _other_success(self, render_id: str, now: datetime) -> None:
        d = self._self_data(now, commit=True)
        # Other successes are counted once, even for directed works that do not
        # enter the global autonomous ledger. Stale callbacks from an earlier
        # Shanghai day never decrease the current day's cooldown.
        if render_id in d['other_render_ids']:
            return
        d['other_render_ids'].append(render_id)
        if day_for(now) < d['day_key']:
            return
        d['remaining_other_successes'] = max(0, d['remaining_other_successes'] - 1)

    def record_directed_other(self, render_id: str, now: datetime, *, is_self: bool) -> None:
        if not is_self:
            self._other_success(render_id, now)

    def record_success(self, *, origin: str, work_id: str, render_id: str,
                       now: datetime, book_id: str | None = None,
                       event_signature: str | None = None,
                       deliberate_revisit_ref: str | None = None,
                       self_book_id: str | None = None,
                       fallback_book_id: str | None = None,
                       fixed_world_candidate_count: int = 30,
                       chapter_id: int | None = None) -> bool:
        if render_id in self.state['renders']:
            if self.state['renders'][render_id]['work_id'] != work_id:
                raise ValueError('render_id belongs to another work')
            return False
        first = work_id not in self.state['work_origins']
        if origin == 'autonomous_self':
            if book_id is not None or self_book_id not in SELF_BOOKS:
                raise ValueError('invalid SELF entry')
            if day_for(now) < self.state['p13']['self']['day_key']:
                raise ValueError('stale SELF completion timestamp; confirm using trusted current receipt time')
            if not first:
                if self.state['work_origins'][work_id] != 'autonomous_self' or self.state['p13']['self']['self_work_ids'].get(work_id) != self_book_id:
                    raise ValueError('SELF work identity conflict')
            elif not self.self_eligible(now):
                raise ValueError('SELF shelf cooling')
            d = self._self_data(now, commit=True)
            seq = self.state['auto_seq'] + 1
            self.state['auto_seq'] = seq
            self.state['renders'][render_id] = {
                'work_id': work_id, 'origin': origin, 'book_id': None,
                'self_book_id': self_book_id, 'auto_seq': seq, 'at': now.isoformat(),
            }
            if first:
                self.state['work_origins'][work_id] = origin
                self.state['work_books'][work_id] = None
                d['self_work_ids'][work_id] = self_book_id
                d['uses_today'] += 1
                d['remaining_other_successes'] = SELF_CD[min(d['uses_today']-1, 3)]
                if self.chapter_priority:
                    record_curated_success(self.state, origin, None)
            return True

        if origin == 'autonomous_library':
            if book_id is None:
                raise ValueError('book_id required')
            local = self.state['p13']['local_cd']
            # All updates are on the staged copy, never a published ledger.
            record_local_success(local, self.book_catalog, self.state,
                                 work_id=work_id, render_id=render_id, book_id=book_id,
                                 fallback_book_id=fallback_book_id,
                                 deliberate_revisit_ref=deliberate_revisit_ref,
                                 candidate_count=fixed_world_candidate_count)
            if not first and (self.state['work_origins'][work_id] != origin or
                              self.state['work_books'].get(work_id) != book_id):
                raise ValueError('work origin/book cannot change')
            # Preserve a legacy-global-CD shadow for rollback/reporting, but
            # ONLY the local P1.3 CD decides whether a fixed book is eligible.
            seq = self.state['auto_seq'] + 1
            self.state['active_notes'] = self.live_notes(now)
            self.state['auto_seq'] = seq
            self.state['renders'][render_id] = {
                'work_id':work_id,'origin':origin,'book_id':book_id,
                'auto_seq':seq,'at':now.isoformat(),
            }
            if first:
                self.state['work_origins'][work_id] = origin
                self.state['work_books'][work_id] = book_id
                if self.chapter_priority:
                    record_curated_success(self.state, origin, chapter_id)
                record_chapter(self.state, book_id, chapter_id)
                legacy_stat = self._write_stat(book_id)
                legacy_stat['auto_use_count'] += 1
                legacy_stat['next_eligible_auto_seq'] = seq + cd_for_use(legacy_stat['auto_use_count']) + 1
            self._other_success(render_id,now)
            return True
        result = super().record_success(
            origin=origin, work_id=work_id, render_id=render_id,
            now=now, book_id=book_id, event_signature=event_signature,
            deliberate_revisit_ref=deliberate_revisit_ref,
        )
        if result:
            if first and self.chapter_priority:
                record_curated_success(self.state, origin, chapter_id)
            self._other_success(render_id, now)
        return result


def world_paths(runtime, data_dir):
    provenance = Path(data_dir) / '.source.json'
    library = Path(runtime)
    if provenance.is_file():
        bookshelf = read_json(provenance).get('bookshelf')
        if bookshelf in ('golden', 'curated'):
            library /= bookshelf
    return library / 'world_index.json', library / 'bookshelf_extension'


class P13Studio(Studio):
    def __init__(self, root: Path, index_path: Path, *, shelf_root: Path = BASE):
        self.shelf_root = Path(shelf_root)
        self.chapter_priority = self.shelf_root.parent.name == 'curated'
        self.book_catalog = catalog(self.shelf_root)
        super().__init__(root, index_path)
        from bookshelf_local_cd import group_map
        if set(group_map(self.book_catalog)) != set(self.shelf.books):
            raise ValueError('catalog membership differs from world index')

    def _new_shelf(self, state) -> P13Shelf:
        if state is None:
            state = create_p13_state(new_state(), self.book_catalog, datetime.now(timezone.utc))
        return P13Shelf(self.index, state, book_catalog=self.book_catalog,
                        chapter_priority=self.chapter_priority)

    def menu(self, now: datetime, *, memory_available: bool = False, rng=None, candidate_count=30) -> dict:
        if type(candidate_count) is not int or candidate_count < 1:
            raise ValueError('candidate_count must be a positive integer')
        self.shelf = self._read_shelf()
        local = self.shelf.state['p13']['local_cd']
        picked = choose(local, self.book_catalog, self.shelf.state, rng=rng,
                        shelf_fallback=self.chapter_priority)
        spines = (read_shelf_entries(picked['shelf_id'], self.book_catalog, self.shelf_root)
                  if picked['shelf_id'] else [])
        available = set(picked['available_ids'])
        remaining = free_story_remaining(self.shelf.state) if self.chapter_priority else None
        zero_remaining = chapter_zero_remaining(self.shelf.state) if self.chapter_priority else None
        free_open = remaining in (None, 0)
        original = self.shelf.original_available() and (free_open or picked['mode'] == 'no_active_fixed_books')
        self_open = self.shelf.self_eligible(now) and free_open
        entries = [dict(kind='fixed', **e) for e in spines if e['id'] in available]
        if len(entries) > candidate_count:
            indices = sorted((rng or random.SystemRandom()).sample(range(len(entries)), candidate_count))
            entries = [entries[index] for index in indices]
        for entry in entries:
            if 'chapters' in entry:
                allowed = available_chapters(self.shelf.state, entry['id'])
                entry['chapters'] = [row for row in entry['chapters'] if row['id'] in allowed]
                if zero_remaining == 0:
                    entry['chapters'].append({'id': 0, 'title': '自由创作'})
        fixed_count = len(entries)
        if original:
            entries.append({'kind':'original','id':'ORIGINAL','title':'原创','intro':'自主创造此刻真正想拍的全新世界'})
        if self_open:
            entries.append({'kind':'self','id':'SELF_FREE','title':'主角自己',
                            'intro':'完全由创作者自主决定表达什么，不强制依赖记忆'})
            if memory_available:
                entries.append({'kind':'self','id':'SELF_ECHO','title':'主角的灵感回声',
                                'intro':'从本轮确实可访问的近期记忆选择线索，转化为新的摄影故事'})
        return {'auto_seq':self.shelf.state['auto_seq'], 'shelf_id':picked['shelf_id'],
                'shelf_selection_mode':picked['mode'], 'fallback_book_id':picked['override_book_id'],
                 'shelf_total':fixed_count, 'candidate_count':candidate_count,
                 'catalog_books':len(self.index['books']),
                'available_entries':entries, 'memory_available':memory_available,
                'self_eligible':self_open, 'original_eligible':original,
                 'p13_schema':VERSION, 'free_story_remaining':remaining,
                 'chapter_zero_remaining':zero_remaining}

    def prepare(self, job, *, now=None):
        origin = job.get('origin')
        chapter_zero = origin == 'autonomous_library' and job.get('chapter_id') == 0
        if self.chapter_priority and (chapter_zero or origin in FREE_ORIGINS) and not self._path(job['work_id']).is_file():
            shelf = self._read_shelf()
            fallback = origin in ('autonomous_original', 'autonomous_spontaneous') and not shelf.has_active_books()
            remaining = (chapter_zero_remaining(shelf.state) if chapter_zero
                         else free_story_remaining(shelf.state))
            if remaining and not fallback:
                raise ValueError('free story cooldown: finish the required preset works first')
        if job.get('origin') == 'autonomous_library':
            from bookshelf_local_cd import group_map
            actual = group_map(self.book_catalog).get(job.get('book_id'))
            if actual is None or job.get('shelf_id') != actual:
                raise ValueError('P1.3 fixed book must specify its actual selected shelf_id')
            if self.chapter_priority:
                chapter = job.get('chapter')
                if (not isinstance(chapter, dict) or chapter.get('book_id') != job['book_id']
                        or type(job.get('chapter_id')) is not int
                        or chapter.get('id') != job['chapter_id']):
                    raise ValueError('curated work requires a bound chapter')
        return super().prepare(job, now=now)

    def selection_prompt(self, persona_summary: str, now: datetime, *, memory_available=False, rng=None,
                         candidate_count=30) -> dict:
        menu = self.menu(now, memory_available=memory_available, rng=rng, candidate_count=candidate_count)
        brief = {'available_books':menu['available_entries'], 'original_entry':None, 'shelf_id':menu['shelf_id']}
        # Original and SELF are already present in available_entries, so avoid duplication.
        prompt = selection_prompt_for_shelf(brief, persona_summary)
        prompt = prompt.replace('独立30本书架实验', 'P1.3 万卷故事整合版')
        origins = ['autonomous_library'] if not self.chapter_priority or menu['shelf_total'] else []
        if not self.chapter_priority or menu['original_eligible']:
            origins.extend(('autonomous_original', 'autonomous_spontaneous'))
        if not self.chapter_priority or menu['self_eligible']:
            origins.append('autonomous_self')
        prompt = prompt.replace('"autonomous_library|autonomous_original|autonomous_spontaneous"',
                                '"' + '|'.join(origins) + '"')
        prompt += ('\n实际输出选择 JSON 时：固定书要包含 shelf_id、本次所选书 ID；SELF 要包含 self_book_id；'
                   '灵感回声仅在确实访问了来源后才选择，并提交 memory_source_verified=true、memory_source_type、memory_inspiration。'
                   '\n固定书 job 必须写本轮选中书的 shelf_id=' + str(menu['shelf_id']) + '；'
                   'SELF 与 ORIGINAL 不写固定书架编号。'
                   '\nSELF_FREE/SELF_ECHO 的 origin 为 autonomous_self，book_id=null；'
                   'SELF_ECHO 必须有可访问来源，创作不等于聊天摘要。'
                   '\n如选择自主SELF，job 必须保留 self_book_id。')
        if menu['shelf_selection_mode'] == 'global_cooldown_fallback':
            prompt += '\n本轮启用书架保底。选择固定书时，选择 JSON 和 Job 的 fallback_book_id 均填写选中书的 ID。'
        if self.chapter_priority:
            prompt = prompt.replace('如果你已经有具体明确的独立原创灵感，可以按原规则使用 autonomous_spontaneous。\n', '')
            prompt += ('\n从可选章节中自主选择。只有本轮出现原创入口时才可使用书架原创或独立灵感。'
                       '固定书的 chapter_id 只选列出的编号，显示 0 时才可选该书自由创作。选定后读取 Point。')
            if menu['shelf_total'] and menu['free_story_remaining']:
                prompt += f"\n原创冷却中，尚需 {menu['free_story_remaining']} 个预设作品成功确认。"
        return {'menu':menu, 'prompt':prompt}


def migrate_ledger(old: dict, index_path: Path, book_root: Path, *, now: datetime) -> dict:
    """Explicit, side-effect-free migration transform; host chooses destination."""
    from wardrobe2_core import Shelf
    Shelf(read_json(index_path), deepcopy(old))  # Validate legacy schema.
    return create_p13_state(old, catalog(book_root), now)
