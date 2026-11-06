"""Independent role-costume skin reveal and honest mechanical-action experiment."""
VERSION = '3.5.2-charm85-role-exposure50-handphysics-compact30-test'
DEFAULT_EXPOSURE_BOOST = 50

def normalize_exposure_pct(uplift):
    if type(uplift) is not int or not 0 <= uplift <= 100:
        raise ValueError('skin_exposure_boost_pct must be integer 0..100')
    return uplift

def exposure_note(score, uplift=DEFAULT_EXPOSURE_BOOST, sheer_lines=False, anatomy_neutral_mode=False):
    normalize_exposure_pct(uplift)
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError('charm_index must be integer 0..100')
    # Preserve the existing five-tier charm index: intensity and reveal are separate.
    moods=('relaxed','softly feminine','flattering','strong graceful allure','bold graceful allure')
    tier=0 if score<25 else 1 if score<50 else 2 if score<75 else 3 if score<90 else 4
    if uplift == 0:
        ending = 'role-true lines and unposed poise.' if anatomy_neutral_mode else 'role-true lines and unposed poise; no bust emphasis.'
        return f'Charm {score}/100: {moods[tier]}, {ending}'
    if sheer_lines:
        ending = 'hosiery optional, no forced pose.' if anatomy_neutral_mode else 'hosiery optional, no bust focus or forced pose.'
        return (f'Charm {score}/100: {moods[tier]}, game-heroine rolewear; '
                f'+{uplift}% skin-and-line reveal through bare skin OR sheer lace/stockings; '+ending)
    ending = 'no forced pose.' if anatomy_neutral_mode else 'no bust focus or forced pose.'
    return (f'Charm {score}/100: {moods[tier]}, game-heroine rolewear, '
            f'+{uplift}% natural skin reveal at shoulder, waist or leg; '+ending)

def validate_physics(note):
    if not isinstance(note, str) or not 50 <= len(note) <= 170 or note != note.strip():
        raise ValueError('action_physics needs 50..170 characters of precise English body mechanics')
    low = note.lower()
    joints=('hand','finger','wrist','elbow','arm','shoulder','torso','hip','knee','foot','feet','leg')
    contacts=('hold','grip','rest','touch','press','pin','support','steady','bend','plant','brace','release','reach','balance','place','turn','shift')
    if not any(s in low for s in joints) or not any(s in low for s in contacts):
        raise ValueError('action_physics must specify joints, physical supports and real contact/movement')
    if sum('\u3400'<=c<='\u9fff' for c in note)>2:
        raise ValueError('action_physics needs English wording')
    return note
