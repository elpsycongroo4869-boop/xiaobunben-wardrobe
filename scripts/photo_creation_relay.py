#!/usr/bin/env python3
"""v3.1 concise delivery with legacy v2.9.18/v3.0 pending verification.

No backend image-mode override is claimed. The goal is to reduce text ambiguity
while preserving all 21 visual dimensions, the original draw, and all task cues.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
from dispatch_shoot import seal, canonical as source_canonical, digest
from pathlib import Path
from english_relay import build as verify_english_source, FIELDS, canonical
from visual_identity import FACE_EN, FACE_EN_V33, FACE_EN_V32, BODY_EN, FINISH_BY_MODE, SCENE_HIERARCHY, FACE_EN_COMPACT, BODY_EN_COMPACT
from charm_index import VERSION as CHARM_INDEX_VERSION, DEFAULT_INDEX, normalize_index, charm_note, band
from exposure_physics import VERSION as EXPOSURE_PHYSICS_VERSION, DEFAULT_EXPOSURE_BOOST, exposure_note, validate_physics
from role_costume import REVISION as ROLE_COSTUME_REVISION, is_role_first, styling_note, validate_delivery
from role_first_costume import VERSION as B32_VERSION, COSTUME_DIRECTION, validate_costume_plan
from face_sensual_trial import FACE_SOURCE_NOTE, is_trial, is_text_face_delivery, validate_message as validate_trial_message, metadata as trial_metadata

SCHEMA='wardrobe-compact-photo-creation-relay-v2.9.18'
SCHEMA_V31='wardrobe-story-first-concise-photo-relay-v3.1'
REFERENCE_FACE_PATH='/小笨笨衣橱/xiaobunben-standard-face-crop-2026-11-01.jpg'
REFERENCE_INSTRUCTION=(
    'Before generating, look up the original reference image in ChatGPT Library at '+REFERENCE_FACE_PATH+'. '
    'Use the pictured adult woman as the facial-identity reference only; create a new photograph with the story below. '
    'If the image cannot be accessed, use the facial description as a best-effort guide.\n\n'
)
LABELS={
 'world_and_role':'Subject and profession',
 'environment':'Location and setting',
 'work_action':'Work in progress',
 'career_evidence_1':'First visible professional evidence',
 'career_evidence_2':'Second visible professional evidence',
 'character_identity':'Fictional adult character',
 'body_proportions':'Adult physique and proportions',
 'outfit_and_function':'Professional wardrobe and materials',
 'outfit_design_mode':'Wardrobe styling and construction',
 'shot_and_distance':'Framing and camera position',
 'story_moment':'Documentary moment',
 'camera_medium':'Photographic approach',
 'camera_lens':'Lens and optics',
 'lighting':'Location lighting',
 'color':'Color and atmosphere',
 'texture_depth':'Texture and depth of field',
 'framing':'Scene composition',
 'intensity':'Visual intensity',
 'composition':'Overall photographic result',
 'in_world_writing':'Signs and interface text',
 'feminine_presence':'Natural expression and presence',
}
INTRO=(
    '((请创建一张照片))\n'
    'Create exactly ONE new photorealistic photograph of a fictional adult woman performing a recognizable role-specific task. '
    'Prioritize her sweet young-adult face and beautiful game-heroine costume over literal uniform realism; '
    'her specific work action, distinctive role evidence and setting establish her role.\n\n'
)
INTRO_V3=(
    '((请创建一张照片))\n'
    'Create exactly ONE entirely new, original photorealistic photograph of a fictional adult heroine in a specific story moment. '
    'Her recognizable personal face and expressive, feminine role styling lead the image; '
    'her chosen action, two visible role details and meaningful setting tell this particular story.\n\n'
)
GROUPS_V3=tuple((('Story in progress' if heading=='Work in progress' else 'Two recognizable role clues' if heading=='Two visible career cues' else heading),keys) for heading,keys in (
    ('Her face and figure', ('character_identity','body_proportions')),
    ('Role and setting', ('world_and_role','environment')),
    ('Work in progress', ('work_action','story_moment')),
    ('Two visible career cues', ('career_evidence_1','career_evidence_2')),
    ('Wardrobe', ('outfit_and_function','outfit_design_mode')),
    ('Photographic framing', ('shot_and_distance','camera_medium','camera_lens','framing')),
    ('Light and photographic texture', ('lighting','color','texture_depth','intensity')),
    ('Composition, signage and presence', ('composition','in_world_writing','feminine_presence')),
))
# Ambiguous continuity/edit language is changed at delivery time only.  The
# full signed English field source remains intact for inspection and audit.
LANGUAGE_CLARITY_REPLACEMENTS={
    'She is recognizably the same recurring adult fictional heroine, adapted to this entirely new role and moment.':
        'Her face, expression, proportions, and styling form a consistent, original fictional adult person in this scene.',
    'Preserve these meaningful tools rather than cropping to beauty details.':
        'Frame her face, specific work action, and distinctive occupational evidence together.',
    'rather than replacing the herbalist with a combat character.':
        'while maintaining the herbalist as the clear professional identity.',
}
def normalize_scene_text(value):
    for old,new in LANGUAGE_CLARITY_REPLACEMENTS.items():
        value=value.replace(old,new)
    return value
OUTRO=('\n\nOutput one coherent, beautiful, on-location photograph. Any writing belongs naturally to the world; no poster title or watermark.')
RED_FLAGS=(
 'edit this image','edit the photo','modify the photo','retouch the photo',
 'use the provided image','change the existing picture','same photo as before', 'same recurring adult fictional heroine', 'preserving the',
 'make this image','replace the background of the image',
)
# This direction is added to the existing composition field (21 total), not
# a competing 22nd demand. The actor/patient/pilgrim may still be present when
# their presence is necessary evidence of the heroine's occupation.
SUBJECT_HIERARCHY_EN = (
    'The heroine is the single unmistakable visual protagonist, with emphasis on her face, working hands and task. '
    'Other people may appear naturally for work interactions or city atmosphere, visually quieter in scale, placement and contrast.'
)

# Compact delivery groups all 21 verified source dimensions into eight natural
# paragraphs. Source details are NEVER shortened or rewritten on disk.
# Human review must ensure that task/cues/lens survive each particular draw.
BUDGETS={
    'world_and_role':170, 'environment':245, 'work_action':270,
    'career_evidence_1':220, 'career_evidence_2':220,
    'character_identity':85, 'body_proportions':75,
    'outfit_and_function':155, 'outfit_design_mode':80,
    'shot_and_distance':130, 'story_moment':70,
    'camera_medium':80, 'camera_lens':70, 'lighting':105,
    'color':110, 'texture_depth':65, 'framing':75,
    'intensity':60, 'composition':70, 'in_world_writing':60,
    'feminine_presence':150,
}
# This is a visual anchor distilled from the adult character reference the user
# explicitly selected on 2026-11-01. The photograph remains in assets/ and the
# text-only delivery can guide but cannot guarantee facial likeness without a true image reference.
# Identity is a compact stable template; hair is intentionally absent.
# Role-specific hair is supplied by career evidence, cosplay cues and wardrobe.
REFERENCE_FACE_EN=FACE_EN
REFERENCE_BODY_EN=BODY_EN
CHARM_ACCENTS=FINISH_BY_MODE
SUBJECT_HIERARCHY_EN=SCENE_HIERARCHY

GROUPS=(
    ('Her face and figure', ('character_identity','body_proportions')),
    ('Role and setting', ('world_and_role','environment')),
    ('Work in progress', ('work_action','story_moment')),
    ('Two visible career cues', ('career_evidence_1','career_evidence_2')),
    ('Wardrobe', ('outfit_and_function','outfit_design_mode')),
    ('Photographic framing', ('shot_and_distance','camera_medium','camera_lens','framing')),
    ('Light and photographic texture', ('lighting','color','texture_depth','intensity')),
    ('Composition, signage and presence', ('composition','in_world_writing','feminine_presence')),
)

def _clause_trim(text, limit):
    """Extract a readable first visual clause, with no mechanical midword cut."""
    text=' '.join(text.strip().split())
    if len(text)<=limit: return text
    # First sentence is favored; semantically dense first sentences are shortened
    # only at punctuation/clause joins, not arbitrarily after a word count.
    first=re.split(r'(?<=[.!?])\s+',text)[0]
    if len(first)<=limit: return first
    best=[]
    for pattern in (r'[,;:]\s+',r'\s+(?:and|while|with|which|where|including|that)\s+'):
        for match in re.finditer(pattern,first,re.I):
            if limit*.52 <= match.start()<=limit*1.13:
                best.append(match.start())
    if best:
        return first[:max(best)].rstrip(' ,;:.')+'.'
    # When one single unbroken sentence holds critical constraints, return it
    # instead of silently losing the tool/action. The final length gate then
    # catches pathological cases for human simplification.
    if len(first)<=int(limit*3.5):return first
    raise ValueError('Field needs human semantic editing for short delivery')

def compact_field(key, value):
    return _clause_trim(normalize_scene_text(value),BUDGETS[key])

def photographic_field(key,text,costume_mode):
    return compact_field(key,text)

def _clean_sentence(value):
    return ' '.join(value.strip().split()).strip(' .;')


def _remove_ending(value, patterns):
    text=_clean_sentence(value)
    for pattern in patterns:
        text=re.sub(pattern, '', text, flags=re.I).strip(' ,.;')
    return text


def compose_v31(fields, draw, costume_mode, reference_face, image_ref_hint=False, skip_size_check=False):
    """Six brief, ordered visual paragraphs; every critical scene field is kept verbatim.

    Twenty-one fields remain in the signed internal audit, but repetitive helper
    sentences do not enter the user-facing image request. No image similarity is
    inferred from text or hashes. Source fields stay unchanged on disk.
    """
    for k in ('world_and_role','environment','work_action','career_evidence_1',
              'career_evidence_2','outfit_and_function'):
        if not fields[k].strip():
            raise ValueError('V3.1 lacks required visual evidence: '+k)
    if fields['career_evidence_1']==fields['career_evidence_2']:
        raise ValueError('Distinct role clues required')
    # Story logic and all seven user-designed scene values retain their original
    # wording. Their per-field caps were validated by fast_start.validate_design.
    paras=[
        'Identity: '+reference_face+' '+REFERENCE_BODY_EN,
        'Story and location: '+fields['world_and_role']+' '+fields['environment'],
        'Visible moment: '+fields['work_action'],
        'Two story clues: '+fields['career_evidence_1']+' '+fields['career_evidence_2'],
    ]
    if draw.get('cosplay_character') and draw.get('lane') in ('cosplay','fusion'):
        character=draw['cosplay_character']
        cues=character.get('visual_cues',[])
        motif='; '.join(str(v) for v in cues)
        if len(motif)>420:
            raise ValueError('Cosplay cues need human semantic condensation')
        paras.append('Character styling: '+character['name']+' ('+character['source']+'); '+motif+'.')
    mode_notes={
        'practical':'Feminine task-inspired tailoring.',
        'refined':'Refined feminine styling.',
        'game_feminine':'Expressive game-heroine tailoring.',
        'fantasy':'Imaginative heroine detailing.',
        'bespoke':'',
    }
    outfit_note=mode_notes[costume_mode]
    paras.append('Wardrobe: '+fields['outfit_and_function']+((' '+outfit_note) if outfit_note else ''))

    # Separate one meaningful camera/lighting passage from story and wardrobe.
    # Do not repeat the full source's "chosen story moment", role cue reminders,
    # repeated heroine praise, and "harmonize" directions.
    shot=_remove_ending(fields['shot_and_distance'],
         [r'\s+Keep her (?:visible story action|actual task).*$', r'\s+Keep the .*?$'])
    medium=_remove_ending(fields['camera_medium'],
         [r',\s*capturing her chosen story moment$',r',\s*as a naturally observed professional moment$'])
    lens=_clean_sentence(fields['camera_lens'])
    lighting=_remove_ending(fields['lighting'], [])
    color=_remove_ending(fields['color'], [r';\s*harmonize the visible outfit and setting$'])
    texture=_remove_ending(fields['texture_depth'],
         [r',\s*respecting the original camera package.*$'])
    # Short, concrete camera language, each facet once.
    camera=' '.join(x+'.' for x in (shot,medium,lens,lighting,color,texture) if x)
    if draw.get('camera_intensity')=='strong':
        camera+=' Bold but natural cinematic contrast.'
    paras.append('Photography: '+camera)
    paras.append('Composition: '+fields['composition']+' '
                 'She is the clear visual focus; other people, if present, remain unobtrusive. '
                 'Flattering natural facial catchlights, believable skin and material texture. '
                 'In-world signage only; no poster title or watermark.')
    message=('((请创建一张照片))\n'
             + (REFERENCE_INSTRUCTION if image_ref_hint else '')
             + 'Create exactly ONE entirely new original photorealistic photograph of a fictional adult heroine in a meaningful moment.\n\n'
             +'\n\n'.join(paras))
    # This is a readability budget, not a reason to remove narrative or identity.
    if not skip_size_check and not 1450<=len(message)<=(3300 if image_ref_hint else 3000):
        raise ValueError(f'V3.1 brief needs human semantic review: {len(message)} characters')
    return message


# v3.5.2: only the user-facing delivery is condensed. The original seven
# scene-design fields and all 21 signed visual audit fields remain unchanged.
# Historical pending v3.5/v3.5.1 always uses compose_v31, so its SHA remains valid.
CHARM_TEST_VERSION='3.5.2-charm30-expression-test'
B3_VERSION='3.5.2-charm30-emotion-tone-test'
B31_VERSION='3.5.2-charm70-natural-props-emotion-test'
FRAMING_VERSION='3.5.2-charm70-framing-sovereignty-test'
CHARM100_FRAMING_VERSION='3.5.2-charm100-framing-sovereignty-test'
COMPACT100_VERSION='3.5.2-charm100-framing-compact30-test'
SENSUAL100_VERSION='3.5.2-charm100-sensual-framing-compact30-test'
REAL100_VERSION='3.5.2-charm100-candid-realism-framing-compact30-test'
FRAMING_CROP_NAMES={'close':'close-up','waist':'waist-up','mid_thigh':'mid-thigh','knee':'knee-level','full':'full-length'}
FRAMING_BODY_NOTE='Healthy slim adult figure with narrow shoulders and a naturally defined waist where visible.'
FRAMING_CAMERA_NOTE=('choose the deliberately selected crop over literal head-to-toe coverage; use a natural portrait perspective without compressing the figure')
FRAMING_FRAME_NOTE=('The story does not require the complete body, shoes, full costume, or entire props in view. Allow the outfit, tools and environment to extend naturally beyond the photograph; do not zoom out merely to fit everything.')
PREVIOUS_CHARM_TEST_VERSION='3.5.2-charm30-test'
CHARM_TEST_OUTFIT_NOTE=(
    'Charm +30% experiment: subtly flatter the adult heroine with a defined waist and elegant neckline or apron-framed back where suitable; ' 
    'retain credible workwear, action and framing.'
)
CHARM100_CHARM_NOTE=(
    'Charm +100% artistic experiment vs original baseline: craft an exceptionally magnetic clearly adult heroine through exquisite face-framing hair, luminous facial lighting, refined makeup, beautiful feminine tailoring and a naturally graceful waist-and-shoulder line within the chosen crop. '
    'Let her presence command the portrait while she genuinely performs her task; no forced exposure, smile, full-body view or costume repetition.'
)
B31_CHARM_NOTE=(
    'Charm +70% experimental direction vs original baseline: give this clearly adult heroine magnetic visual presence through exquisitely face-framing styling, an elegantly sculpted waist, beautiful outfit proportions, '
    'assured yet emotionally truthful bearing, refined textures and striking feminine tailoring; choose neckline, drape or legwear details only when natural. Preserve action and story, not obligatory exposure.'
)
B31_NATURAL_PROPS=(
    'Natural observer view: notebooks, papers, maps, screens and tools face their actual user; do not rotate them toward '
    'the camera just to show text. Writing need not be legible; let someone display an item only when the story calls for it.'
)
REFERENCE_INSTRUCTION_COMPACT = (
    'Before generating, find the face reference in ChatGPT Library: '+REFERENCE_FACE_PATH+'. '
    'Use its adult face only; create a NEW photo. If unavailable, follow the description.\n\n'
)

def compose_v352_compact30(fields, draw, costume_mode, expression_test=False):
    """External message only: compact all sections, preserve every signed scene phrase."""
    if draw.get('frame_extent') not in FRAMING_CROP_NAMES:
        raise ValueError('Compact branch requires a deliberate crop')
    pack=draw.get('camera_pack') or {}
    for k in ('optics','lighting','palette','texture'):
        if not pack.get(k):
            raise ValueError('Compact branch needs the original camera visual: '+k)
    face=('Adult East Asian woman (~20), petite narrow oval face, slim cheeks, short jaw, '
          'soft pointed chin, slightly upturned dark almond eyes, fine brows, small '
          'straight nose, rose lips; healthy slim adult build.')
    face_ref=('Face reference (face only) in ChatGPT Library: '+REFERENCE_FACE_PATH+
              '. Look up if available; otherwise use Character.')
    if is_trial(draw):
        face=draw['face_profile_en']+' Healthy slim adult build.'
        face_ref=FACE_SOURCE_NOTE
    charm=('Charm +100% art direction: exquisite face-framing hair, luminous makeup and '
           'face light, elegant posture, flattering waistline and sculpted feminine '
           'tailoring. Magnetic yet believable in action; no forced exposure.')
    if draw.get('version')==SENSUAL100_VERSION or draw.get('delivery_version')==SENSUAL100_VERSION:
        charm=('Charm +100%, sensuality enhanced: compelling adult eyes and softly lit lips, '
               'graceful neck and shoulders, confident natural posture, a beautifully '
               'fitted waist and alluring silk drape. Elegant, role-true, never forced exposure.')
    if draw.get('version')==REAL100_VERSION or draw.get('delivery_version')==REAL100_VERSION:
        charm=('Charm +100%, natural adult sensuality: expressive eyes, graceful neck and fitted waist, '
               'relaxed confidence, believable clothing and candid movement; genuine allure, not gloss.')
    if draw.get('version')==CHARM_INDEX_VERSION or draw.get('delivery_version')==CHARM_INDEX_VERSION:
        charm = charm_note(normalize_index(draw.get('charm_index')))
    exposure_test=draw.get('version')==EXPOSURE_PHYSICS_VERSION or draw.get('delivery_version')==EXPOSURE_PHYSICS_VERSION
    if exposure_test:
        charm=exposure_note(normalize_index(draw.get('charm_index')), draw.get('skin_exposure_boost_pct',DEFAULT_EXPOSURE_BOOST), sheer_lines=bool(draw.get('sheer_lines_art_direction')), anatomy_neutral_mode=bool(draw.get('anatomy_neutral_mode')))
        validate_physics(draw.get('action_physics'))
    is_b32=draw.get('version')==B32_VERSION or draw.get('delivery_version')==B32_VERSION
    if is_b32:
        validate_physics(draw.get('action_physics'))
        validate_costume_plan(draw.get('costume_plan'),fields['outfit_and_function'],pack['texture'])
        charm=COSTUME_DIRECTION
    if is_role_first(draw):
        charm=draw['costume_styling_note'] if is_trial(draw) else styling_note()
    extent=FRAMING_CROP_NAMES[draw['frame_extent']]
    camera=('Candid editorial photo; '+pack['optics']+'; '+pack['lighting']+'; '+
            pack['palette']+'; '+pack['texture']+'; '+extent+' crop, no distortion.')
    if draw.get('version') in (REAL100_VERSION, CHARM_INDEX_VERSION, EXPOSURE_PHYSICS_VERSION, B32_VERSION) or draw.get('delivery_version') in (REAL100_VERSION, CHARM_INDEX_VERSION, EXPOSURE_PHYSICS_VERSION, B32_VERSION):
        camera+=' Real pores and skin tone, subtle asymmetry, uneven light and fabric creases; no retouch.'
    frame=('Show her face and story-defining action; partial props suffice. Keep '
           'papers and tools naturally facing their user. Let clothing, body and '
           'props crop naturally; never widen just to show all. No watermark.')
    paras=[
        '((请创建一张照片))\nCreate ONE NEW photorealistic photograph, not an edit.\n'+face_ref,
        'Character: '+face,
        'Scene: '+fields['world_and_role']+' '+fields['environment'],
        'Emotional tone: '+draw['emotion_tone'],
        'Action: '+fields['work_action'],
        *(['Expression: '+fields['feminine_presence']] if expression_test else []),
        'Clues: '+fields['career_evidence_1']+' '+fields['career_evidence_2'],
    ]
    if draw.get('cosplay_character') and draw.get('lane') in ('cosplay','fusion'):
        c=draw['cosplay_character'];paras.append('Cosplay: '+c['name']+'; '+', '.join(c['visual_cues'])+'.')
    if exposure_test or is_b32:
        paras.append('Body mechanics: '+draw['action_physics'])
    paras.extend([
        'Outfit: '+fields['outfit_and_function']+' '+charm,
        'Camera: '+camera,
        'Frame: '+fields['composition']+' '+frame,
    ])
    if exposure_test or is_b32:
        # Preserve face/role/plot/photo intent while removing duplicated stock microcopy.
        paras[-2]=paras[-2].replace(' Real pores and skin tone, subtle asymmetry, uneven light and fabric creases; no retouch.',
                ' Real skin texture, uneven light, natural creases; unretouched.')
        paras[-1]='Frame: '+fields['composition']+' Face and action primary; partial user-facing tools and natural crop. No watermark.'
        if draw.get('sheer_lines_art_direction'):
            paras[-2]=paras[-2].replace(' Real skin texture, uneven light, natural creases; unretouched.', ' Skin texture, candid light.')
    if is_trial(draw):
        paras[-1]=('Frame: '+fields['composition']+' Face and action primary; tools face their actual user, '
                   'not the camera. Natural crop. No watermark.')
    if is_text_face_delivery(draw):
        paras[0]=(draw['quality_prompt_prefix']+'\n((请创建一张照片))\n'
                  'Create ONE NEW photorealistic photograph, not an edit.')

    msg='\n\n'.join(paras)
    if is_role_first(draw):
        validate_delivery(draw, fields['outfit_and_function'], msg)
    if is_trial(draw):
        validate_trial_message(draw, fields['outfit_and_function'], msg)
    baseline_draw={**draw,'version':CHARM100_FRAMING_VERSION,'delivery_version':CHARM100_FRAMING_VERSION}
    baseline=compose_v352(fields,baseline_draw,costume_mode,charm_test=True,expression_test=expression_test)
    target=int(len(baseline)*0.70)
    if not 1100<=len(msg)<=target:
        raise ValueError(f'Compact30 message {len(msg)} chars exceeds <=70% of original {len(baseline)} chars ({target}). Refine design wording; do not truncate signed fields.')
    return msg

def compose_v352(fields, draw, costume_mode, charm_test=False, expression_test=False):
    """Short new-photo request; never trim seven signed scene-design phrases."""
    if draw.get('version') in (COMPACT100_VERSION,SENSUAL100_VERSION,REAL100_VERSION,CHARM_INDEX_VERSION,EXPOSURE_PHYSICS_VERSION,B32_VERSION) or draw.get('delivery_version') in (COMPACT100_VERSION,SENSUAL100_VERSION,REAL100_VERSION,CHARM_INDEX_VERSION,EXPOSURE_PHYSICS_VERSION,B32_VERSION):
        return compose_v352_compact30(fields,draw,costume_mode,expression_test=expression_test)
    is_charm100=draw.get('version')==CHARM100_FRAMING_VERSION or draw.get('delivery_version')==CHARM100_FRAMING_VERSION
    is_framing=is_charm100 or draw.get('version')==FRAMING_VERSION or draw.get('delivery_version')==FRAMING_VERSION
    is_b31=is_framing or draw.get('version')==B31_VERSION or draw.get('delivery_version')==B31_VERSION
    is_tone=is_b31 or draw.get('version')==B3_VERSION or draw.get('delivery_version')==B3_VERSION
    for k in ('world_and_role','environment','work_action','career_evidence_1',
              'career_evidence_2','outfit_and_function','composition'):
        if not fields[k].strip():
            raise ValueError('v3.5.2 missing scene detail: '+k)
    if fields['career_evidence_1']==fields['career_evidence_2']:
        raise ValueError('Distinct story cues required')
    paras=[
        'Character: '+FACE_EN_COMPACT+' '+(FRAMING_BODY_NOTE if is_framing and draw.get('frame_extent')!='full' else BODY_EN_COMPACT),
        'Scene: '+fields['world_and_role']+' '+fields['environment'],
        *(['Emotional tone: '+draw['emotion_tone']] if is_tone else []),
        'Action: '+fields['work_action'],
        *(['Expression: '+fields['feminine_presence']] if expression_test else []),
        'Clues: '+fields['career_evidence_1']+' '+fields['career_evidence_2'],
    ]
    if draw.get('cosplay_character') and draw.get('lane') in ('cosplay','fusion'):
        c=draw['cosplay_character']
        motif='; '.join(str(v) for v in c.get('visual_cues',[]))
        if len(motif)>420:raise ValueError('Cosplay clues need human semantic condensation')
        paras.append('Cosplay: '+c['name']+' ('+c['source']+'); '+motif+'.')
    mode_notes={
        'practical':'Feminine practical tailoring.', 'refined':'Refined feminine tailoring.',
        'game_feminine':'Game-heroine styling.', 'fantasy':'Imaginative heroine detail.',
        'bespoke':'',
    }
    paras.append('Outfit: '+fields['outfit_and_function']+
                 ((' '+mode_notes[costume_mode]) if mode_notes[costume_mode] else '')+
                 ((' '+(CHARM100_CHARM_NOTE if is_charm100 else B31_CHARM_NOTE if is_b31 else CHARM_TEST_OUTFIT_NOTE)) if charm_test else ''))
    shot=_remove_ending(fields['shot_and_distance'],
        [r'\s+Keep her (?:visible story action|actual task).*$',r'\s+Keep the .*?$'])
    medium=_remove_ending(fields['camera_medium'],
        [r',\s*capturing her chosen story moment$',r',\s*as a naturally observed professional moment$'])
    medium=re.sub(r'^Photographed with\s+', '', medium, flags=re.I)
    lens=re.sub(r'^Use\s+', '', _clean_sentence(fields['camera_lens']),flags=re.I)
    lighting=re.sub(r'^The photographic light is\s+', '',_clean_sentence(fields['lighting']),flags=re.I)
    color=_remove_ending(fields['color'],[r';\s*harmonize the visible outfit and setting$'])
    color=re.sub(r'^Palette:\s*','',color,flags=re.I)
    texture=re.sub(r'^Capture\s+', '',_remove_ending(fields['texture_depth'],
        [r',\s*respecting the original camera package.*$']),flags=re.I)
    camera='; '.join(x.strip(' .;') for x in (shot,medium,lens,lighting,color,texture) if x)
    if draw.get('camera_intensity')=='strong':camera+='; bold natural cinematic contrast'
    if is_framing:
        extent=draw.get('frame_extent','')
        if extent not in FRAMING_CROP_NAMES:
            raise ValueError('Framing branch requires a selected frame_extent, no silently defaulting to full length')
        camera+='; intentional '+FRAMING_CROP_NAMES[extent]+' portrait crop; '+FRAMING_CAMERA_NOTE
    paras.append('Camera: '+camera+'.')
    paras.append('Frame: '+fields['composition']+(' Clear face and story-defining work action. '+B31_NATURAL_PROPS+(' '+FRAMING_FRAME_NOTE if is_framing else '')+' Real materials; no watermark.' if is_b31 else ' Sharp heroine, readable face/hands/task; realistic materials, in-world signs; no watermark.'))
    msg=('((请创建一张照片))\n'+REFERENCE_INSTRUCTION_COMPACT+
         'Create ONE new photorealistic photograph.\n\n'+'\n\n'.join(paras))
    # Compare like-for-like against the v3.5.1 composer on the same visual fields.
    # If creative text makes the prompt unavoidably long, block BEFORE displaying
    # a button rather than silently dropping the story or sending an oversized one.
    baseline=compose_v31(fields,draw,costume_mode,FACE_EN,image_ref_hint=True,skip_size_check=True)
    max_by_ratio=int(len(baseline)*.75)
    expression_extra=(len(fields['feminine_presence'])+14) if expression_test else 0
    mood_extra=(len(draw.get('emotion_tone',''))+18) if is_tone else 0
    if is_b31:
        # B3.1 adds only two user-visible art-direction changes.
        # Adjust budget for their exact length, never trim story or identity.
        extra=len(CHARM100_CHARM_NOTE if is_charm100 else B31_CHARM_NOTE)+len(B31_NATURAL_PROPS)+(len(FRAMING_FRAME_NOTE)+len(FRAMING_CAMERA_NOTE)+140 if is_framing else 90)
        allowed=min(3960 if is_charm100 else 3640 if is_framing else 3150,max_by_ratio+extra+expression_extra+mood_extra)
    else:
        allowed=(min(2820,max_by_ratio+len(CHARM_TEST_OUTFIT_NOTE)+1+expression_extra+mood_extra) if mood_extra else min(2670,max_by_ratio+len(CHARM_TEST_OUTFIT_NOTE)+1+expression_extra) if expression_test else min(2490,max_by_ratio+len(CHARM_TEST_OUTFIT_NOTE)+1) if charm_test else min(2300,max_by_ratio))
    if len(msg)>allowed:
        raise ValueError(
            f'v3.5.2 image message too long ({len(msg)} chars; goal <= {allowed}). '
            'Rewrite the seven scene fields more concisely while keeping identity, action, two distinct clues, outfit and camera intent; never silently truncate.'
        )
    return msg

def sha(b):return hashlib.sha256(b).hexdigest()
def build(handoff_path, visual_details_path):
    # The existing English relay verifies every source field and draw hash.
    old=verify_english_source(handoff_path, visual_details_path)
    details=json.loads(Path(visual_details_path).read_text('utf-8'))
    fields=details['fields']
    costume_mode=details['costume_mode']
    source_draw=json.loads(Path(json.loads(Path(handoff_path).read_text('utf-8'))['source_draw_file']).read_text('utf-8'))
    is_v3=source_draw.get('mode')=='chosen'
    is_b32=source_draw.get('version')==B32_VERSION or source_draw.get('delivery_version')==B32_VERSION
    is_exposure_test=source_draw.get('version')==EXPOSURE_PHYSICS_VERSION or source_draw.get('delivery_version')==EXPOSURE_PHYSICS_VERSION
    is_charm_index=is_exposure_test or source_draw.get('version')==CHARM_INDEX_VERSION or source_draw.get('delivery_version')==CHARM_INDEX_VERSION
    if is_charm_index:normalize_index(source_draw.get('charm_index'))
    is_real100=is_b32 or is_charm_index or source_draw.get('version')==REAL100_VERSION or source_draw.get('delivery_version')==REAL100_VERSION
    is_sensual100=is_real100 or source_draw.get('version')==SENSUAL100_VERSION or source_draw.get('delivery_version')==SENSUAL100_VERSION
    is_compact100=is_sensual100 or source_draw.get('version')==COMPACT100_VERSION or source_draw.get('delivery_version')==COMPACT100_VERSION
    is_charm100=is_compact100 or source_draw.get('version')==CHARM100_FRAMING_VERSION or source_draw.get('delivery_version')==CHARM100_FRAMING_VERSION
    is_Framing=is_charm100 or source_draw.get('version')==FRAMING_VERSION or source_draw.get('delivery_version')==FRAMING_VERSION
    is_B31=is_Framing or source_draw.get('version')==B31_VERSION or source_draw.get('delivery_version')==B31_VERSION
    is_B3=is_B31 or source_draw.get('version')==B3_VERSION or source_draw.get('delivery_version')==B3_VERSION
    is_expression_test=is_B3 or source_draw.get('version')==CHARM_TEST_VERSION or source_draw.get('delivery_version')==CHARM_TEST_VERSION
    is_charm_test=is_expression_test or source_draw.get('version')==PREVIOUS_CHARM_TEST_VERSION or source_draw.get('delivery_version')==PREVIOUS_CHARM_TEST_VERSION
    is_v352=is_charm_test or source_draw.get('version')=='3.5.2' or source_draw.get('delivery_version')=='3.5.2'
    is_v35=is_v352 or source_draw.get('version')=='3.5' or source_draw.get('delivery_version')=='3.5'
    is_v34=source_draw.get('version')=='3.4' or source_draw.get('delivery_version')=='3.4'
    is_v33=source_draw.get('version')=='3.3' or source_draw.get('delivery_version')=='3.3'
    is_v31=(source_draw.get('version') in ('3.1','3.2','3.3','3.4','3.5','3.5.2','3.5.2-charm30-test','3.5.2-charm30-expression-test',B3_VERSION,B31_VERSION,FRAMING_VERSION,CHARM100_FRAMING_VERSION,COMPACT100_VERSION,SENSUAL100_VERSION,REAL100_VERSION,CHARM_INDEX_VERSION,EXPOSURE_PHYSICS_VERSION,B32_VERSION) or source_draw.get('delivery_version') in ('3.1','3.2','3.3','3.4','3.5','3.5.2','3.5.2-charm30-test','3.5.2-charm30-expression-test',B3_VERSION,B31_VERSION,FRAMING_VERSION,CHARM100_FRAMING_VERSION,COMPACT100_VERSION,SENSUAL100_VERSION,REAL100_VERSION,CHARM_INDEX_VERSION,EXPOSURE_PHYSICS_VERSION,B32_VERSION))
    reference_face=REFERENCE_FACE_EN if is_v35 or is_v34 else FACE_EN_V33 if is_v33 else FACE_EN_V32
    if costume_mode not in CHARM_ACCENTS:
        raise ValueError('Missing or unsupported locked costume mode')
    compressed={key:photographic_field(key,fields[key],costume_mode) for key in FIELDS} if not is_v31 else None
    # All original twenty-one English fields are processed before grouping.
    paras=[]
    for heading,keys in (() if is_v31 else (GROUPS_V3 if is_v3 else GROUPS)):
        parts=[compressed[k] for k in keys]
        if heading=='Her face and figure':
            parts=[reference_face,REFERENCE_BODY_EN]  # versioned adult face identity
        elif heading=='Wardrobe':
            parts.append(CHARM_ACCENTS[costume_mode])
        elif heading=='Composition, signage and presence':
            parts.append(SUBJECT_HIERARCHY_EN)
        paras.append(heading+': '+' '.join(parts))
    body='\n\n'.join(paras)
    message=(compose_v352(fields,source_draw,costume_mode,charm_test=is_charm_test,expression_test=is_expression_test) if is_v352 else compose_v31(fields,source_draw,costume_mode,reference_face,image_ref_hint=is_v35) if is_v31 else (INTRO_V3 if is_v3 else INTRO)+body+OUTRO)
    if len(FIELDS)!=21 or not (1100 if is_v352 else 1450 if is_v31 else 2200)<=len(message)<=((2450 if is_compact100 else 3960 if is_charm100 else 3640 if is_Framing else 3150 if is_B31 else 2820 if is_B3 else 2670 if is_expression_test else 2490 if is_charm_test else 2300 if is_v352 else 3300 if is_v35 else 3000) if is_v31 else 3650):
        raise ValueError(f'Compact 21-part photographic brief outside usable size: {len(message)} chars')
    for flag in RED_FLAGS:
        if flag in message.lower():
            raise ValueError('Image-editing instruction found in photographic brief: '+flag)
    if len(set(LABELS.values()))!=len(FIELDS):
        raise ValueError('Duplicate headings')
    role_first_note = ('All 21 signed source fields stay intact. Establish the selected role through its clothing materials and construction, '
                       'then develop feminine styling within that outfit. Facial reference access and image generation are not implied by text verification.')
    return {
        'schema':(SCHEMA_V31 if is_v31 else SCHEMA),'status':'prepared_not_generated','draw_id':old['draw_id'],
        'original_prompt_sha256':old['original_prompt_sha256'],
        'original_shoot_sha256':old['source_shoot_sha256'],
        'english_details_sha256':old['english_details_sha256'],
        'field_count':len(FIELDS),
        'delivery_character_count':len(message),
        'full_source_character_count':sum(len(fields[key]) for key in FIELDS),
        'delivery_policy':'B3.2_role_first_costume_climate_materials_free_adaptation' if is_b32 else 'v3.5.2_charm85_role_exposure50_hand_physics_compact30_test' if is_exposure_test else 'v3.5.2_charm_index_candid_realism_framing_compact30_test' if is_charm_index else 'v3.5.2_charm100_candid_realism_framing_compact30_test' if is_real100 else 'v3.5.2_charm100_sensual_framing_compact30_test' if is_sensual100 else 'v3.5.2_charm100_framing_compact30_test' if is_compact100 else 'v3.5.2_charm100_framing_sovereignty_test' if is_charm100 else 'v3.5.2_charm70_framing_sovereignty_test' if is_Framing else 'v3.5.2_B31_natural_props_charm70_emotion_first' if is_B31 else 'v3.5.2_B3_emotion_tone_first_21_signed_sources' if is_B3 else 'v3.5.2_charm30_expression_autonomy_21_signed_sources' if is_expression_test else 'v3.5.2_charm30_test_one_outfit_modifier_21_signed_sources' if is_charm_test else 'v3.5.2_25percent_shorter_story_intact_21_signed_sources' if is_v352 else 'v3.5_reference_lookup_single_face_story_first_21_signed_sources' if is_v35 else 'v3.4_single_refined_oval_face_story_first_21_signed_sources' if is_v34 else 'v3.3_facial_range_story_first_21_signed_sources' if is_v33 else 'v3.2_story_first_six_paragraph_21_signed_sources' if source_draw.get('version')=='3.2' or source_draw.get('delivery_version')=='3.2' else 'v3.1_story_first_six_paragraph_21_signed_sources' if is_v31 else 'v3_assistant_decided_character_story_first' if is_v3 else 'v2.9.18_character_appeal_first_eight_group_21_sources',
        'costume_mode':costume_mode,
        'message_sha256':sha(message.encode('utf-8')),
        'message':message,
        'delivery_route':'verified_user_message_button_in_new_chat_or_copy_to_clean_chat',
        'scene_audit_required':True,
        'image_generated':False,'success_sample_registration_enabled':False,
        'backend_mode_controlled':False,
        'reference_asset':'assets/xiaobunben-selected-reference-2026-11-01.jpg',
        'reference_sha256':'245c7aa75aa8f077b0f6352414d800cc955a287b6ecb95583ab955aaaa42e4f1',
        **({'charm_index':source_draw['charm_index'], 'charm_band':band(source_draw['charm_index'])} if is_charm_index else {}),
        **({'skin_exposure_boost_pct':source_draw['skin_exposure_boost_pct'], 'action_physics':source_draw['action_physics']} if is_exposure_test else {}),
        **({'sheer_lines_art_direction':True} if source_draw.get('sheer_lines_art_direction') else {}),
        **({'art_direction_revision':source_draw.get('art_direction_revision',ROLE_COSTUME_REVISION),'role_costume_first':True,'costume_plan':source_draw['costume_plan']} if is_role_first(source_draw) else {}),
        **({'costume_plan':source_draw['costume_plan'],'role_first_costume_design':True} if is_b32 else {}),
        'subjective_feminine_appeal_target':('role_first_costume_art_direction_no_numeric_charm_or_exposure' if is_role_first(source_draw) or is_b32 else 'user_controllable_styling_index_not_a_beauty_score' if is_charm_index else 'relative_plus_100_percent_natural_sensuality_and_candid_realism_not_numeric_or_guaranteed' if is_real100 else 'relative_plus_100_percent_with_sensuality_emphasis_not_numeric_or_guaranteed' if is_sensual100 else 'relative_plus_100_percent_B31_framing_test_not_numeric_or_guaranteed' if is_charm100 else 'relative_plus_70_percent_B31_test_not_numeric_or_guaranteed' if is_B31 else 'relative_plus_30_percent_test_not_numeric_or_guaranteed' if is_charm_test else 'adult face resemblance and art-directed feminine character appeal before real-world workwear accuracy'),
        'note':role_first_note if is_role_first(source_draw) else ('Reference lookup is requested at user-turn time, not actually attached to the one-click message. ' if is_v35 else '')+'All 21 signed source fields stay intact. The clearly adult age-20 face stays the identity anchor, and an art-directed feminine outfit takes priority over literal uniform functionality; work evidence and photographic draw remain readable. Text-only prompting cannot guarantee photo-reference likeness without actual image input.',
        **({'reference_face_crop_asset':'assets/xiaobunben-standard-face-crop-2026-11-01.jpg','reference_library_path':REFERENCE_FACE_PATH,'reference_image_attached_to_request':False} if is_v35 else {}),
        **({**trial_metadata(source_draw),'reference_asset':None,'reference_sha256':None,
            'reference_face_crop_asset':None,'reference_library_path':None,
            'reference_image_attached_to_request':False} if is_trial(source_draw) else {}),
    }
def verify(handoff, details, out):
    actual=json.loads(Path(out).read_text('utf-8'))
    if canonical(actual)!=canonical(build(handoff,details)):
        raise ValueError('Photo creation relay has been modified or source changed')
    return actual

def build_from_pending(pending_dir):
    """Rebind old handoff source paths; then verify it matches the sealed source."""
    pending=Path(pending_dir).resolve()
    old=json.loads((pending/'handoff.json').read_text('utf-8'))
    draw=json.loads((pending/'draw.json').read_text('utf-8'))
    shoot=json.loads((pending/'shoot.json').read_text('utf-8'))
    if digest(source_canonical(draw))!=old['draw_sha256']:
        raise ValueError('Portable draw fingerprint mismatch')
    if digest(source_canonical(shoot))!=old['shoot_sha256']:
        raise ValueError('Portable shoot fingerprint mismatch')
    recreated=seal(pending/'draw.json',pending/'shoot.json',old['capability'],old['prompt_kind'])
    for key in ('draw_id','role','scene','lane','camera_pack_id','outfit_mode',
                'prompt','prompt_sha256','draw_sha256','shoot_sha256'):
        if old[key]!=recreated[key]:
            raise ValueError('Portable handoff differs from original: '+key)
    with tempfile.TemporaryDirectory() as folder:
        handoff=Path(folder)/'current-handoff.json'
        handoff.write_text(json.dumps(recreated,ensure_ascii=False),encoding='utf-8')
        return build(handoff,pending/'english-details.json')

def verify_from_pending(pending_dir):
    pending=Path(pending_dir).resolve()
    expected=build_from_pending(pending)
    actual=json.loads((pending/'photo-creation-relay.json').read_text('utf-8'))
    if canonical(expected)!=canonical(actual):
        raise ValueError('Portable photo creation relay was changed')
    if (pending/'photo-creation-message.txt').read_text('utf-8')!=actual['message']:
        raise ValueError('Portable image-generation message was changed')
    return actual

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pending-dir',type=Path)
    p.add_argument('--handoff', type=Path)
    p.add_argument('--english-details', type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--message-output',type=Path)
    p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if a.pending_dir:
        pending=a.pending_dir.resolve()
        if a.verify:
            m=verify_from_pending(pending)
            print('PASS: portable compact 21-field photographic message verified, image not generated')
            return
        m=build_from_pending(pending)
        (pending/'photo-creation-relay.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (pending/'photo-creation-message.txt').write_text(m['message'],encoding='utf-8')
        verify_from_pending(pending)
        print('PASS: portable photographic message ready; sha256='+m['message_sha256'])
        return
    if not all((a.handoff,a.english_details,a.output)):
        p.error('Set --pending-dir or --handoff --english-details --output')
    if a.verify:
        m=verify(a.handoff,a.english_details,a.output)
        if a.message_output and a.message_output.read_text('utf-8')!=m['message']:
            raise ValueError('Visible message differs from relay')
        print('PASS: compact delivery + 21 full source visual parts verified, image not generated')
        return
    m=build(a.handoff,a.english_details)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if a.message_output:
        a.message_output.parent.mkdir(parents=True,exist_ok=True)
        a.message_output.write_text(m['message'],encoding='utf-8')
    print('PASS: photo creation brief ready; sha256='+m['message_sha256'])
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr)
        sys.exit(2)
