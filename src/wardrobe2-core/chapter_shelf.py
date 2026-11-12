"""Per-book chapter rotation. State changes belong to the successful receipt."""

CHAPTERS = (1, 2, 3, 4)
FREE_ORIGINS = ('autonomous_original', 'autonomous_spontaneous', 'autonomous_self')
CHAPTER_ZERO_WAIT = 5
OTHER_FREE_WAIT = 10


def free_story_remaining(state):
    """Remaining preset successes until the library-wide free entries can reopen."""
    return state['p13'].get('free_story_cd', {}).get('remaining_presets', OTHER_FREE_WAIT)


def chapter_zero_remaining(state):
    return max(0, free_story_remaining(state) - (OTHER_FREE_WAIT - CHAPTER_ZERO_WAIT))


def record_curated_success(state, origin, chapter_id):
    """Count only the first confirmed image of an autonomous work."""
    preset = origin == 'autonomous_library' and type(chapter_id) is int and chapter_id in CHAPTERS
    chapter_zero = origin == 'autonomous_library' and type(chapter_id) is int and chapter_id == 0
    if not preset and not chapter_zero and origin not in FREE_ORIGINS:
        return
    remaining = max(0, free_story_remaining(state) - 1) if preset else OTHER_FREE_WAIT
    state['p13'].setdefault('free_story_cd', {})['remaining_presets'] = remaining


def available_chapters(state, book_id):
    cycle = state['p13'].get('chapter_cycles', {}).get(book_id, {})
    used = cycle.get('used', ())
    return [chapter for chapter in CHAPTERS if chapter not in used] or list(CHAPTERS)


def record_chapter(state, book_id, chapter_id):
    if chapter_id not in CHAPTERS:
        return
    cycles = state['p13'].setdefault('chapter_cycles', {})
    used = cycles.get(book_id, {}).get('used', [])
    if len(used) == len(CHAPTERS):
        used = []
    if chapter_id not in used:
        used = [*used, chapter_id]
    cycles[book_id] = {'used': used, 'last': chapter_id}


def selected_point(card, chapter_id):
    if type(chapter_id) is not int or chapter_id not in (0, *CHAPTERS):
        raise ValueError('select chapter_id 0 to 4')
    if chapter_id == 0:
        return {'id': 0, 'title': '自由创作', 'point': None}
    chapter = next((row for row in card['chapters'] if row['id'] == chapter_id), None)
    if chapter is None:
        raise ValueError('chapter is missing from the verified book')
    return chapter
