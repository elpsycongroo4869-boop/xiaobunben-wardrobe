"""An explicit adult role, kept separate from the selected story and lens."""

from design_contract import visual_text

SCHEMA = 'wardrobe-role-v1'
PREFERENCES = ('personality', 'wardrobe_preferences', 'aesthetic_preferences',
               'world_preferences', 'photo_preferences', 'continuity')
REQUIRED = {'schema', 'source', 'name', 'age', 'identity', 'appearance', 'build'}
ALLOWED = REQUIRED | set(PREFERENCES) | {'reference_image'}


def validate_profile(profile):
    if not isinstance(profile, dict) or not REQUIRED <= profile.keys() or profile.keys() - ALLOWED:
        raise ValueError('Use a wardrobe-role-v1 profile with name, age, identity, appearance and build')
    if profile['schema'] != SCHEMA or profile['source'] not in ('custom', 'existing_gpt'):
        raise ValueError('Role profile needs wardrobe-role-v1 and source custom or existing_gpt')
    if type(profile['age']) is not int or profile['age'] < 18:
        raise ValueError('Role age must be an integer of at least 18')
    name = profile['name']
    if not isinstance(name, str) or not 1 <= len(name) <= 80 or name != name.strip() or '\n' in name or '\r' in name:
        raise ValueError('Role name must be a single line of 1–80 characters')
    for key, low, high in (('identity', 2, 80), ('appearance', 12, 460), ('build', 12, 180)):
        value = visual_text(profile[key], 'role.' + key, low, high)
        if '\n' in value or '\r' in value:
            raise ValueError('Role visual fields must fit on one line')
    for key in PREFERENCES:
        value = profile.get(key, '')
        if not isinstance(value, str) or value != value.strip() or len(value) > 1500:
            raise ValueError('Invalid role preference: ' + key)
    reference = profile.get('reference_image')
    if reference is not None:
        if (not isinstance(reference, dict) or set(reference) != {'description', 'rights_confirmed'}
                or reference['rights_confirmed'] is not True
                or not isinstance(reference['description'], str)
                or not 1 <= len(reference['description'].strip()) <= 300):
            raise ValueError('Reference image metadata requires a description and explicit rights confirmation')
    return profile
