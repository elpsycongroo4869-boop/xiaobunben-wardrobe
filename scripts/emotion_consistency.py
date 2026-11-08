"""Final emotional-direction review for new 4.1 photograph briefs.

This is an editorial checkpoint, not a sentiment classifier: mixed feelings are
welcome. Mechanical checks catch misplaced snapshots and verbatim stacking;
semantic alignment still requires the artist's own review.
"""
from copy import deepcopy
import re

REVISION = '4.1-final-emotion-review-r1'
EMOTION_LABEL = 'Emotional tone: '
EXPRESSION_LABEL = 'Expression: '
# Only grammar words are ignored in repeat checks; NO emotional word blacklist.
GRAMMAR = frozenset('a an the and or but for from into with while through that this there then than onto upon after before when where which who whose them their his her she he they you your it its is are was were to of in on at as by not just very little once now one'.split())


def _words(text):
    return [w for w in re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())]


def _meaningful_pairs(text):
    tokens = _words(text)
    return {' '.join((a, b)) for a, b in zip(tokens, tokens[1:])
            if len(a) >= 4 and len(b) >= 4 and a not in GRAMMAR and b not in GRAMMAR}


def echo_report(brief):
    """Only exact adjacent content-word repetition; synonyms require human judgment."""
    tone = brief['choice']['emotion_tone']
    tone_pairs = _meaningful_pairs(tone)
    camera = brief['choice']['camera_style']
    sections = {
        'story_plan.moment': brief['story_plan']['moment'],
        'scene_design.action': brief['scene_design']['action'],
        'scene_design.expression': brief['scene_design']['expression'],
        'scene_design.cue1': brief['scene_design']['cue1'],
        'scene_design.cue2': brief['scene_design']['cue2'],
        'scene_design.wardrobe': brief['scene_design']['wardrobe'],
        'camera_plan.viewpoint': brief['camera_plan']['viewpoint'],
        'camera_style': ' '.join(str(v) for v in camera.values()),
    }
    matches = {}
    for field, value in sections.items():
        overlap = tone_pairs & _meaningful_pairs(value)
        if overlap:
            matches[field] = sorted(overlap)
    return matches


def validate_review(review, brief):
    """Called after the story and expression are written; preserve complex emotion."""
    if not isinstance(review, dict) or set(review) != {'final_tone', 'visible_expression', 'review_note'}:
        raise ValueError('Final emotion review needs final_tone, visible_expression and review_note')
    for key, lower, upper in (('final_tone', 22, 120), ('visible_expression', 22, 130), ('review_note', 25, 400)):
        item = review[key]
        if not isinstance(item, str) or item != item.strip() or not lower <= len(item) <= upper:
            raise ValueError('emotion_review.' + key + ' needs a specific, nonempty editorial decision')
    if review['final_tone'] != brief['choice']['emotion_tone']:
        raise ValueError('Final emotion differs from choice.emotion_tone; reconcile the two instead of stacking')
    if review['visible_expression'] != brief['scene_design']['expression']:
        raise ValueError('Final visible expression differs from scene_design.expression; reconcile before sealing')
    echoes = echo_report(brief)
    if echoes:
        details = '; '.join(f"{field}: {', '.join(pairs)}" for field, pairs in echoes.items())
        raise ValueError('Repeated emotional wording across fields; revise redundancies and re-review: ' + details)
    return deepcopy(review)


def mark_review(draw, brief):
    review = validate_review(brief.get('emotion_review'), brief)
    draw['emotion_review_revision'] = REVISION
    draw['emotion_review'] = review


def is_reviewed(draw):
    return draw.get('emotion_review_revision') == REVISION


def validate_locked(draw, scene):
    if 'emotion_review' not in draw and 'emotion_review_revision' not in draw:
        # Historical 4.0/4.1 sealed pending remains readable, not retrofitted.
        return
    if not is_reviewed(draw):
        raise ValueError('Unknown or incomplete final emotion review revision')
    review = draw['emotion_review']
    if not isinstance(review, dict) or review.get('final_tone') != draw.get('emotion_tone'):
        raise ValueError('Final emotion review changed after the editorial decision')
    if review.get('visible_expression') != scene.get('expression'):
        raise ValueError('Visible expression changed after the final emotion review')
    # Complete cross-field scan on the *delivered* draft, not just the initial brief.
    audit = {'story_plan': draw['story_plan'], 'camera_plan': draw['camera_plan'],
             'choice': {'emotion_tone': draw['emotion_tone'], 'camera_style': draw['camera_pack']},
             'scene_design': scene}
    echoes = echo_report(audit)
    if echoes:
        raise ValueError('A later scene change reintroduced emotional repetition: ' + str(echoes))


def validate_message(draw, message):
    if not is_reviewed(draw):
        return
    tone = draw['emotion_review']['final_tone']
    expression = draw['emotion_review']['visible_expression']
    if message.count(EMOTION_LABEL) != 1 or message.count(EXPRESSION_LABEL) != 1:
        raise ValueError('Final prompt must have one emotional direction and one visible expression')
    if EMOTION_LABEL + tone not in message or EXPRESSION_LABEL + expression not in message:
        raise ValueError('The final reviewed emotion or expression did not reach the actual photo prompt')
    if draw['emotion_review']['review_note'] in message:
        raise ValueError('The private editorial review must not become another emotional prompt')
