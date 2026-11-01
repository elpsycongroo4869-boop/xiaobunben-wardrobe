"""v3.4: one refined small oval adult face, fixed face topology.

A stable original adult face and slim figure persist across draws; all hair,
costumes, lighting setups and cameras remain draw-specific.
"""
# v3.4: use one narrow, refined small oval face as the sole active identity.
# Expressions and hairstyles can vary; the shape itself is no longer a range.
# Text-only facial guidance does not guarantee exact photo likeness.
FACE_EN = (
    'A clearly adult East Asian woman, about 20 years old, with a distinctly petite, fine-boned, slender oval face. '
    'Delicately slim cheek contours and a gently tapered jaw form an elegant, compact facial outline; '
    'the lower face is short, ending in a small softly pointed chin. '
    'Bright clear dark almond eyes with subtly lifted outer corners and delicate lower lids; '
    'fine natural brows, a petite straight nose with a small tip, and softly shaped rose-pink lips. '
    'Refined, youthful-adult sweetness with harmonious natural proportions.'
)
# For verifying sealed v3.3 designs, use exactly their original face anchor.
FACE_EN_V33 = (
    'A clearly adult East Asian woman, about 20 years old: a very petite, fine-boned soft oval face with '
    'gently rounded upper cheeks, a slim softly tapered jaw, a compact short lower face and a small delicate chin. '
    'Clear dark almond eyes with softly rounded lower lids, their outer corners level or lightly lifted; '
    'fine natural brows, a dainty straight nose with a small tip, and soft naturally pink lips. '
    'Harmonious adult features and a fresh, sweet expression, from playful, lively charm to gentle, quiet tenderness.'
)
# Historical relay messages must retain their original face wording for hash verification.
FACE_EN_V32 = (
    'A clearly adult East Asian woman, about 20 years old: a very petite, fine-boned soft oval face, '
    'slightly narrower through the cheeks and jaw, gently rounded upper cheeks, a compact short lower face '
    'and a small softly tapered chin; bright open dark almond eyes with softly rounded lower lids, '
    'delicate natural brows, a dainty straight nose and naturally pink lips. '
    'A sweet, fresh, lively expression with balanced adult facial proportions.'
)
BODY_EN = (
    'Healthy, gracefully slender adult build, narrow shoulders, a neat waist, '
    'slim arms and long, fine legs with realistic adult proportions.'
)
# The four mode probabilities are unchanged. These fragments express different
# costume art-direction treatments, never realism-first safety conditions.
FINISH_BY_MODE = {
 'practical': 'A polished heroine version of the work outfit: clean fitted lines, a visible waist and graceful coordinated styling.',
 'refined': 'Elegant feminine uniform design with a shaped waist, beautiful upper-to-lower proportions and coordinated footwear.',
 'game_feminine': 'Game-heroine tailoring with a striking waistline, artful hems or fitted shorts, expressive accents and unified styling.',
 'bespoke': 'A one-of-a-kind femininely art-directed character wardrobe, designed for this specific identity, world and story.',
 'fantasy': 'An imaginative heroine costume with sculpted shape, distinctive layered pieces, role motifs and expressive footwear.',
}
SCENE_HIERARCHY = (
 'She is the nearest, largest and sharpest recognizable person; soft facial fill and natural eye catchlights '
 'flatter her in the chosen lighting. Other people stay small, distant and visually quiet.'
)
