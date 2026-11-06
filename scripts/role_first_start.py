#!/usr/bin/env python3
"""Current wardrobe entry: context -> role clothing -> feminine adaptation."""

import argparse
import json
import sys
from pathlib import Path

from button_handoff import verify as verify_button
from fast_start import ROOT, stage_curate, stage_draw, stage_finish
from photo_creation_relay import verify_from_pending
from role_costume import REVISION, is_role_first
from face_sensual_trial import REVISION as FACE_SENSUAL_REVISION


def main():
    parser = argparse.ArgumentParser(description='Role-costume-first wardrobe; prepares text only')
    sub = parser.add_subparsers(dest='command', required=True)
    curate = sub.add_parser('curate')
    curate.add_argument('--pending', type=Path, required=True)
    curate.add_argument('--creative-brief', type=Path, required=True)
    curate.add_argument('--art-direction', choices=('current', 'role-first'), default='current',
                        help='current enables provisional face and sensual costume redesign; role-first verifies the earlier workflow')
    draw = sub.add_parser('draw')
    draw.add_argument('--pending', type=Path, required=True)
    draw.add_argument('--history', type=Path, default=ROOT / 'references/history.jsonl')
    draw.add_argument('--lane', choices=('career', 'cosplay', 'fusion'))
    draw.add_argument('--seed', type=int, help='reproducible tests only')
    draw.add_argument('--art-direction', choices=('current', 'role-first'), default='current')
    for name in ('finish', 'verify'):
        command = sub.add_parser(name)
        command.add_argument('--pending', type=Path, required=True)
        command.add_argument('--route', choices=('new_chat', 'copy_only'), default='new_chat')
        if name == 'finish':
            command.add_argument('--scene-design', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'curate':
        result = stage_curate(args.pending, args.creative_brief, role_costume_first=True,
                              face_sensual_trial=args.art_direction == 'current')
    elif args.command == 'draw':
        result = stage_draw(args.pending, args.history, args.lane, args.seed,
                            role_costume_first=True, face_sensual_trial=args.art_direction == 'current')
    elif args.command == 'finish':
        source = json.loads((args.pending / 'draw.json').read_text('utf-8'))
        if not is_role_first(source):
            raise ValueError('Use legacy fast_start.py for an existing historical pending; do not re-sign it')
        result = stage_finish(args.pending, args.scene_design, args.route)
    else:
        record = verify_from_pending(args.pending)
        if record.get('art_direction_revision') not in (REVISION, FACE_SENSUAL_REVISION):
            raise ValueError('Verify historical pending with fast_start.py; it is not a new role-first draw')
        verify_button(args.pending, args.route, args.pending / 'button_manifest.json')
        result = {'verified': True, 'draw_id': record['draw_id']}
    source = json.loads((args.pending / 'draw.json').read_text('utf-8'))
    print(json.dumps({'art_direction_revision': source.get('art_direction_revision', REVISION), **result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, AssertionError, json.JSONDecodeError) as exc:
        print('ROLE-FIRST BLOCKED: ' + str(exc), file=sys.stderr)
        sys.exit(2)
