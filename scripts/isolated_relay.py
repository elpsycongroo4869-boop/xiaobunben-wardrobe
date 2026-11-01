#!/usr/bin/env python3
"""v2.9.2 clipboard -> fresh chat relay, sealed against the ORIGINAL v2.9.1 retry.

This is a transport / portability repair, not a generator fix. Never treats a
verified prompt, a copied clipboard, or a generated file as an image success.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from dispatch_shoot import seal, canonical, digest
from english_relay import FIELDS, LABELS, build as build_english

SCHEMA = 'wardrobe-isolated-clipboard-relay-v2.9.2'
REQUIRED = ('draw.json', 'shoot.json', 'handoff.json', 'english-details.json',
            'relay.json', 'message.txt', 'retry_manifest.json',
            'history_before_draw.jsonl', 'failed-attempts.jsonl')

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(p.read_text('utf-8'))

def prepare(pending):
    pending = Path(pending).resolve()
    if any(not (pending / f).is_file() for f in REQUIRED):
        missing = [f for f in REQUIRED if not (pending / f).is_file()]
        raise ValueError('Missing original locked bundle files: ' + ', '.join(missing))
    draw = load(pending / 'draw.json')
    shoot = load(pending / 'shoot.json')
    old_handoff = load(pending / 'handoff.json')
    original_relay = load(pending / 'relay.json')
    details = load(pending / 'english-details.json')
    retry = load(pending / 'retry_manifest.json')
    draw_id = draw['draw_id']
    if not all(obj['draw_id'] == draw_id for obj in (shoot, old_handoff, original_relay, details, retry)):
        raise ValueError('Original draw identity mismatch')
    if retry.get('history_committed') is not False:
        raise ValueError('The original draw cannot be marked as already committed')
    if old_handoff.get('prompt_kind') != 'generation':
        raise ValueError('Isolated relay only supports original new generation')
    # Verify the original sealed data in its portable extracted location, without
    # trusting obsolete /mnt/data paths embedded by a previous container session.
    if digest(canonical(draw)) != old_handoff['draw_sha256']:
        raise ValueError('Original draw hash mismatch')
    if digest(canonical(shoot)) != old_handoff['shoot_sha256']:
        raise ValueError('Original shot hash mismatch')
    original = seal(pending/'draw.json', pending/'shoot.json', old_handoff['capability'], old_handoff['prompt_kind'])
    for k in ('draw_id', 'lane', 'role', 'scene', 'camera_pack_id',
              'outfit_mode', 'prompt', 'prompt_sha256', 'draw_sha256', 'shoot_sha256'):
        if original[k] != old_handoff[k]:
            raise ValueError(f'Original handoff changed: {k}')
    if retry.get('version') != '2.9.1':
        raise ValueError('Unknown original retry format')
    with tempfile.TemporaryDirectory() as temp:
        rebound = Path(temp) / 'rebound-handoff.json'
        rebound.write_text(json.dumps(original, ensure_ascii=False), 'utf-8')
        reconstructed = build_english(rebound, pending/'english-details.json')
    message = (pending/'message.txt').read_text('utf-8')
    if original_relay['english_full_prompt'] != message:
        raise ValueError('Original English user message changed')
    if reconstructed['english_full_prompt'] != message:
        raise ValueError('The recompiled 21-field message differs from the original locked English prompt')
    if original_relay['english_full_prompt_sha256'] != sha(message.encode('utf-8')):
        raise ValueError('Original English relay hash mismatch')
    if retry['prompt_sha256'] != sha(message.encode('utf-8')):
        raise ValueError('Original retry manifest message hash mismatch')
    for key in FIELDS:
        label = LABELS[key]+': '
        if message.count(label) != 1 or details['fields'][key] not in message:
            raise ValueError('English 21-field completeness mismatch: '+key)
    if len(FIELDS) != 21 or len(message) < 1700:
        raise ValueError('English message is incomplete')
    inputs={f:sha((pending/f).read_bytes()) for f in REQUIRED}
    return {
        'schema':SCHEMA,
        'version':'2.9.2',
        'draw_id':draw_id,
        'status':'prepared_not_generated',
        'delivery_route':'copy_exact_english_prompt_into_new_empty_chat',
        'button_action':'GenUI.copy',
        'prompt_file':'message.txt',
        'prompt_sha256':sha(message.encode('utf-8')),
        'original_prompt_unchanged':True,
        'field_count':len(FIELDS),
        'input_sha256':inputs,
        'needs_new_blank_chat':True,
        'message_becomes_visible_when_pasted':True,
        'native_image_tool_success_unverified':True,
        'image_generated':False,
        'image_audit_passed':False,
        'history_committed':False,
    }

def verify(pending):
    pending=Path(pending).resolve()
    found=load(pending/'isolated_relay.json')
    expected=prepare(pending)
    if found != expected:
        raise ValueError('Isolated delivery plan or original input changed')
    if (pending/'clipboard-message.txt').read_bytes()!=(pending/'message.txt').read_bytes():
        raise ValueError('Clipboard text deviated from source message')
    return found

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pending-dir',type=Path)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify:
        m=verify(args.verify)
        print('PASS: portable new-chat clipboard relay is intact; 21 unchanged fields; sha256='+m['prompt_sha256'])
    elif args.pending_dir:
        m=prepare(args.pending_dir)
        (args.pending_dir/'clipboard-message.txt').write_bytes((args.pending_dir/'message.txt').read_bytes())
        (args.pending_dir/'isolated_relay.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n','utf-8')
        verify(args.pending_dir)
        print('PASS: 21-field original draw locked; fresh-chat clipboard file prepared; sha256='+m['prompt_sha256'])
    else:
        parser.error('Set --pending-dir or --verify')

if __name__=='__main__':
    try:main()
    except (KeyError, ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr)
        sys.exit(2)
