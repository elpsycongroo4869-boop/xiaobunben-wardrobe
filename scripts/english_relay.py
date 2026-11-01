#!/usr/bin/env python3
"""v2.9.1: seal a complete English user-message relay against a genuine Skill draw.

Verifies fidelity of structure, source hashes, and the complete English message.
Translation quality is checked by the assistant; it cannot be proved by a hash.
This does not interact with image generation or record successful pictures.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from dispatch_shoot import verify as verify_handoff

SCHEMA = 'wardrobe-english-native-relay-v2.9.1'
FIELDS = (
    'world_and_role', 'environment', 'work_action', 'career_evidence_1',
    'career_evidence_2', 'character_identity', 'body_proportions',
    'outfit_and_function', 'outfit_design_mode', 'shot_and_distance',
    'story_moment', 'camera_medium', 'camera_lens', 'lighting',
    'color', 'texture_depth', 'framing', 'intensity', 'composition',
    'in_world_writing', 'feminine_presence',
)
LABELS = {
    'world_and_role':'LOCKED WORLD AND IDENTITY',
    'environment':'SPECIFIC LOCATION AND ERA',
    'work_action':'VISIBLE WORK ACTION',
    'career_evidence_1':'VISUAL CAREER CUE ONE',
    'career_evidence_2':'VISUAL CAREER CUE TWO',
    'character_identity':'RECURRING ADULT CHARACTER',
    'body_proportions':'BODY AND ANATOMY CONTINUITY',
    'outfit_and_function':'AUTHENTIC FUNCTIONAL CLOTHING',
    'outfit_design_mode':'LOCKED COSTUME DESIGN MODE',
    'shot_and_distance':'SHOT LANGUAGE AND SUBJECT SCALE',
    'story_moment':'LOCKED NARRATIVE MOMENT',
    'camera_medium':'CAMERA PACKAGE / MEDIUM',
    'camera_lens':'LENS / OPTICS',
    'lighting':'LIGHTING DESIGN',
    'color':'COLOR PALETTE',
    'texture_depth':'TEXTURE / DEPTH OF FIELD',
    'framing':'FRAMING AND TOOL CONTEXT',
    'intensity':'STYLE INTENSITY',
    'composition':'INTEGRATED PHOTO COMPOSITION',
    'in_world_writing':'WRITING / SIGNAGE POLICY',
    'feminine_presence':'NATURAL FEMININE PRESENCE / ENHANCEMENT',
}

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def sha(bytes_):
    return hashlib.sha256(bytes_).hexdigest()

def build(handoff_path,translation_path):
    handoff_path=Path(handoff_path).resolve()
    translation_path=Path(translation_path).resolve()
    h=json.loads(handoff_path.read_text('utf-8'))
    verify_handoff(h)
    if h['prompt_kind']!='generation':
        raise ValueError('Only first-generation prompts can be wrapped in the default English blind-box relay')
    trans=json.loads(translation_path.read_text('utf-8'))
    if trans.get('draw_id')!=h['draw_id'] or trans.get('original_prompt_sha256')!=h['prompt_sha256']:
        raise ValueError('English detail file is not bound to the genuine compiled prompt')
    s=json.loads(Path(h['source_shoot_file']).read_text('utf-8'))
    d=json.loads(Path(h['source_draw_file']).read_text('utf-8'))
    for field,expected in (('lane',s['lane']),('costume_mode',s['costume_mode']),('camera_pack_id',s['camera_pack_id']),('camera_intensity',d['camera_intensity']),('feminine_presence_mode',s['feminine_presence_mode'])):
        if trans.get(field)!=expected:
            raise ValueError(f'Original random dimension mismatch: {field}')
    fields=trans.get('fields')
    if not isinstance(fields,dict) or set(fields)!=set(FIELDS):
        raise ValueError('English visual prompt must have every one of the 21 required dimensions')
    for k in FIELDS:
        value=fields[k]
        if not isinstance(value,str) or len(value.strip())<16 or value.strip()!=value:
            raise ValueError(f'Empty or underspecified English prompt section: {k}')
        if len(re.findall(r'[\u3400-\u9fff]',value))>max(3,len(value)//12):
            raise ValueError('English prompt section unexpectedly contains too much Chinese text: '+k)
    charm = fields['feminine_presence'].lower()
    expected_charm_terms = ('expression', 'gaze', 'lighting', 'tailor')
    if not all(t in charm for t in expected_charm_terms):
        raise ValueError('Feminine-presence pass must detail expression, gaze, lighting and tailoring')
    if fields['career_evidence_1']==fields['career_evidence_2']:
        raise ValueError('Two independent visual role cues required')
    # Keep the user-facing message strictly image-generation-only.
    # Draw verification, audit, and history registration remain in the local workflow.
    start=('Create one entirely NEW photorealistic photograph from scratch, using the complete '
           'locked visual specification below. This is a standalone new-image creation request. '
           'Build the recognizable role scene as a character-first work portrait, with the adult heroine and her feminine art direction leading.\n\n')
    if d.get('mode')=='chosen':
        start=('Create one entirely NEW original photorealistic photograph of the artist-chosen adult heroine, role and story. The twenty-one locked visual source dimensions support this creative decision.\n\n')
    body='\n'.join(f'{LABELS[k]}: {fields[k]}' for k in FIELDS)
    suffix=('\n\nFINAL IMAGE REQUIREMENTS: Deliver exactly one entirely new photograph of '
            'the adult woman performing this precise profession, with at least two clearly visible occupational '
            'cues and coherent world, scene, optics, lighting and composition. '
            'Keep any signage appropriate to the fictional world. The output is the finished photograph itself, '
            'without explanatory text, poster captions, or watermark.')
    if d.get('mode')=='chosen':
        suffix=('\n\nFINAL IMAGE REQUIREMENTS: One completely new photograph showing the fictional adult heroine in her chosen story moment, with her intended expressive action and two independent recognizable role clues, coherent location, optics, lighting and styling. No extra text, posters or watermarks.')
    message=start+body+suffix
    if len(message)<1700:
        raise ValueError('English prompt unusually short; likely omitted detailed specification')
    plan={
        'schema':SCHEMA, 'status':'prepared_not_clicked',
        'draw_id':h['draw_id'],'handoff_path':str(handoff_path),'translation_path':str(translation_path),
        'original_prompt_sha256':h['prompt_sha256'],
        'source_shoot_sha256':h['shoot_sha256'],
        'english_details_sha256':sha(canonical(trans)),
        'english_full_prompt':message,
        'english_full_prompt_sha256':sha(message.encode('utf-8')),
        'translation_human_semantic_review_required':True,
        'new_user_message_visible_after_click':True,
        'action':'GenUI.issueNewTurn',
        'button_label':'打开小笨笨衣橱',
        'image_generated':False,
        'image_audit_passed':False,
        'history_committed':False,
    }
    return plan

def verify(plan):
    if plan.get('schema')!=SCHEMA or plan.get('status')!='prepared_not_clicked':
        raise ValueError('Unsupported relay manifest')
    expected=build(plan['handoff_path'],plan['translation_path'])
    if canonical(expected)!=canonical(plan):
        raise ValueError('The English message changed after sealing or source was tampered')
    return True

def main():
    p=argparse.ArgumentParser(description='Full-fidelity English wardrobe relay, v2.9')
    p.add_argument('--handoff',type=Path)
    p.add_argument('--english-details',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--message-output',type=Path)
    p.add_argument('--verify',type=Path)
    a=p.parse_args()
    if a.verify:
        verify(json.loads(a.verify.read_text('utf-8')))
        print('PASS: English relay message is complete, source-bound and unchanged (not an image audit)')
        return
    if not all((a.handoff,a.english_details,a.output,a.message_output)):
        p.error('Need --handoff --english-details --output --message-output')
    m=build(a.handoff,a.english_details)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.message_output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    a.message_output.write_text(m['english_full_prompt'],encoding='utf-8')
    verify(m)
    print('PASS: English full prompt prepared, draw_id='+m['draw_id']+' sha256='+m['english_full_prompt_sha256'])

if __name__=='__main__':
    try:main()
    except (KeyError,ValueError,OSError,TypeError,json.JSONDecodeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr)
        sys.exit(2)
