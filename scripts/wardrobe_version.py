"""Version labels for newly sealed v4.5 photographs."""

VERSION = '4.5.0'
LEGACY_CAMERA_VERSIONS = {'4.5.0-rc.1', '4.5.0-rc.2', '4.5.0-rc.3'}
LEGACY_OUTFIT_VERSIONS = LEGACY_CAMERA_VERSIONS | {'4.5.0-rc.4'}
SEAL_VERSIONS = LEGACY_OUTFIT_VERSIONS | {'4.5.0-rc.5', VERSION}
SEAL_SCHEMA = 'wardrobe-seal-v4.5'
OBSERVATION_SCHEMA = 'wardrobe-photographer-selection-v4.5'
