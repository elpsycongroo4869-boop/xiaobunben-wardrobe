"""Validate and present the three independent, creator-reported statuses."""
from copy import deepcopy
from html import escape

KEYS = {'focus_review', 'focus_evidence', 'library_browsed', 'browsing_scope',
        'browsed_card_ids', 'library_adopted', 'adopted_card_ids', 'adoption_note'}


def unknown_audit():
    """Compatibility fallback is visibly unknown, never silently a success."""
    return {'focus_review': 'uncertain',
            'focus_evidence': 'No confirmed focus-process review was supplied for this draw.',
            'library_browsed': None, 'browsing_scope': 'unknown', 'browsed_card_ids': [],
            'library_adopted': None, 'adopted_card_ids': [], 'adoption_note': ''}


def validate_audit(audit, *, known_ids):
    if audit is None:
        return unknown_audit()
    if not isinstance(audit, dict) or set(audit) != KEYS:
        raise ValueError('creative_audit must contain eight explicit status/evidence fields')
    result = deepcopy(audit)
    if result['focus_review'] not in ('completed', 'not_completed', 'uncertain'):
        raise ValueError('focus_review must be completed, not_completed or uncertain')
    proof = result['focus_evidence']
    if not isinstance(proof, str) or not (12 <= len(proof) <= 400) or proof != proof.strip():
        raise ValueError('focus_evidence must explain the creator self-review, not just repeat a success label')
    browsed, adopted = result['library_browsed'], result['library_adopted']
    if type(browsed) not in (bool, type(None)) or type(adopted) not in (bool, type(None)):
        raise ValueError('library_browsed and library_adopted must be true, false or null')
    scope = result['browsing_scope']
    if scope not in ('cards', 'index', 'none', 'unknown'):
        raise ValueError('browsing_scope must be cards, index, none or unknown')
    if browsed is True and scope not in ('cards', 'index'):
        raise ValueError('browsed=true requires index or cards scope')
    if browsed is False and scope != 'none':
        raise ValueError('browsed=false requires scope=none')
    if browsed is None and scope != 'unknown':
        raise ValueError('unknown browsing requires scope=unknown')
    for field in ('browsed_card_ids', 'adopted_card_ids'):
        ids = result[field]
        if not isinstance(ids, list) or len(ids) > 20 or any(not isinstance(i, str) for i in ids):
            raise ValueError(field + ' must be a small list of card IDs')
        if len(set(ids)) != len(ids) or (ids and not set(ids) <= known_ids):
            raise ValueError(field + ' contains duplicated or unknown card IDs')
    if scope == 'cards' and not result['browsed_card_ids']:
        raise ValueError('A cards-level browsing claim needs consulted card IDs')
    if scope != 'cards' and result['browsed_card_ids']:
        raise ValueError('Only cards-level browsing may claim consulted card IDs')
    note = result['adoption_note']
    if not isinstance(note, str) or note != note.strip() or len(note) > 400:
        raise ValueError('adoption_note must be concise text')
    if adopted is True:
        if len(note) < 12 or not result['adopted_card_ids']:
            raise ValueError('adopted=true requires a specific influence note and referenced world card ID')
    elif result['adopted_card_ids'] or note:
        raise ValueError('Unconfirmed/unadopted inspiration cannot claim adopted card IDs or a use note')
    # Browsing and adoption are INDEPENDENT. Recalling a previously known card without
    # reading it this time may truthfully result in browsed=false, adopted=true.
    return result


def display_labels(a):
    f = {'completed':'已完成（创作者自检）', 'not_completed':'未完成', 'uncertain':'未确认'}[a['focus_review']]
    yesno = {True:'是', False:'否', None:'未确认'}
    return {'focus':f, 'library_browsed':yesno[a['library_browsed']],
            'library_adopted':yesno[a['library_adopted']]}


def fragment(record):
    d = record['display_labels']
    return ('<section class="wardrobe-creative-status" aria-label="本次创作实录">\n'
            + '<p>专注创作：'+escape(d['focus'])+'</p>\n'
            + '<p>万卷故事 · 本次浏览：'+escape(d['library_browsed'])+'</p>\n'
            + '<p>万卷故事 · 采用灵感：'+escape(d['library_adopted'])+'</p>\n'
            + '</section>\n')
