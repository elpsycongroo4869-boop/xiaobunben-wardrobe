#!/usr/bin/env python3
"""Wardrobe 4.0: choose a story moment and a fresh camera, then seal a text-only blind box."""

import argparse
import json
import sys
from pathlib import Path

from button_handoff import verify as verify_button
from fast_start import stage_curate, stage_finish
from photo_creation_relay import verify_from_pending
from story_first import VERSION, REVISION, is_story_first


def main():
    parser = argparse.ArgumentParser(description='Story-first wardrobe 4.0; no image generation')
    commands = parser.add_subparsers(dest='command', required=True)
    curate = commands.add_parser('curate')
    curate.add_argument('--pending', type=Path, required=True)
    curate.add_argument('--creative-brief', type=Path, required=True)
    for name in ('finish', 'verify'):
        command = commands.add_parser(name)
        command.add_argument('--pending', type=Path, required=True)
        command.add_argument('--route', choices=('new_chat', 'copy_only'), default='new_chat')
        if name == 'finish':
            command.add_argument('--scene-design', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'curate':
        result = stage_curate(args.pending, args.creative_brief, role_costume_first=True,
                              face_sensual_trial=True, story_first=True)
    else:
        draw = json.loads((args.pending / 'draw.json').read_text('utf-8'))
        if not is_story_first(draw):
            raise ValueError('Use the historical entry for a sealed older pending; do not upgrade its source')
        if args.command == 'finish':
            result = stage_finish(args.pending, args.scene_design, args.route)
        else:
            record = verify_from_pending(args.pending)
            if record.get('wardrobe_version') != VERSION:
                raise ValueError('The pending does not deliver wardrobe 4.0')
            verify_button(args.pending, args.route, args.pending / 'button_manifest.json')
            result = {'verified': True, 'draw_id': record['draw_id']}
    print(json.dumps({**result, 'version': VERSION, 'art_direction_revision': REVISION}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, AssertionError, json.JSONDecodeError) as exc:
        print('STORY-FIRST BLOCKED: ' + str(exc), file=sys.stderr)
        sys.exit(2)
