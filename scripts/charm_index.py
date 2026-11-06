"""Controlled, subjective adult feminine styling index; no claim of a measurable beauty score."""

VERSION = '3.5.2-charm-index-candid-realism-framing-compact30-test'
DEFAULT_INDEX = 85


def normalize_index(index):
    if type(index) is not int or not 0 <= index <= 100:
        raise ValueError('charm_index must be an integer from 0 to 100, not a percentage of beauty')
    return index


def band(index):
    """Five art-direction bands; within a band, numeric display is more precise than the styling mapping."""
    index = normalize_index(index)
    if index < 25:
        return 'natural everyday'
    if index < 50:
        return 'soft charm'
    if index < 75:
        return 'noticeable allure'
    if index < 90:
        return 'strong allure'
    return 'intense allure'


def charm_note(index):
    """Alter only the Outfit emphasis; camera realism, story and cropping remain untouched."""
    index = normalize_index(index)
    direction = {
        'natural everyday': 'easy role-true clothing, relaxed posture and honest texture; no beauty posing.',
        'soft charm': 'flattering yet practical cuts, soft natural lines and easy confident posture; no polish.',
        'noticeable allure': 'fine waist-and-shoulder lines, flattering cuts and engaging natural posture; no gloss.',
        'strong allure': 'bolder role-true tailoring, natural waist curves, graceful neck and shoulders, confident unposed motion; allure without gloss or forced exposure.',
        'intense allure': 'striking role-true tailoring, expressive natural contours, neckline freedom and bold unposed body language; authentic and unforced.',
    }[band(index)]
    return f'Charm {index}/100 ({band(index)}): {direction}'
