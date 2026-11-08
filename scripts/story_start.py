#!/usr/bin/env python3
"""Prepare, inspect and verify wardrobe photographs and role profiles."""

import argparse
import json
from pathlib import Path
import sys
import time
import zipfile

from render_open import render_card
from role_profile import validate_profile
from story_seal import ROUTES, json_data, prepare, verify_archive, verify_legacy
from wardrobe_version import VERSION
from world_cards import DEFAULT_DECK, load_index

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROLE = ROOT / 'private' / 'role.json'
PRIVATE_DECK = ROOT / 'private' / 'worlds-102.json'


def role_path(path):
    if path is None and not PRIVATE_ROLE.is_file():
        raise ValueError('Choose --profile examples/role-new-woman.json or your own role JSON')
    return path or PRIVATE_ROLE


def seal_path(path):
    if path.is_dir():
        archives = list(path.glob('wardrobe-v4.5.*-pending-*.zip'))
        if len(archives) != 1:
            raise ValueError('Choose the exact v4.5 pending ZIP, or supply --legacy-engine for an old directory')
        return archives[0]
    return path


def save_new(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def author_request(profile, deck, keys):
    workflow = (ROOT / 'references' / 'creation-workflow.md').read_text(encoding='utf-8')
    shape = (ROOT / 'references' / 'brief-template.json').read_text(encoding='utf-8')
    material = []
    if keys:
        index = load_index(deck)
        for key in keys:
            if key not in index:
                raise ValueError('Unknown world-card ID: ' + key)
            material.append(index[key])
    return (
        '开始一份全新的衣橱盲盒创作。按下文创作、终审并只返回本次 JSON 底稿。'
        '不要生成图片。这份底稿用于本地封签。\n\n'
        + workflow + '\n\n本次角色资料（沿用已确认的角色）\n\n'
        + json.dumps(profile, ensure_ascii=False, indent=2)
        + ('\n\n用户点名希望翻阅的可选灵感卡\n\n'
           + json.dumps(material, ensure_ascii=False, indent=2) if material else '')
        + '\n\n底稿形状（占位描述全部替换，勿增加键）\n\n' + shape
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description='小笨笨衣橱 · 故事照片工作流')
    parser.add_argument('--version', action='version', version=VERSION)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare', help='验证底稿，保存新封签并准备开箱')
    prep.add_argument('--pending', type=Path, required=True)
    prep.add_argument('--creative-brief', type=Path, required=True)
    prep.add_argument('--profile', type=Path)
    prep.add_argument('--worlds', type=Path)
    prep.add_argument('--route', choices=ROUTES, default='copy_only')

    author = commands.add_parser('author', help='输出供创作者使用的角色和底稿说明')
    author.add_argument('--profile', type=Path)
    author.add_argument('--worlds', type=Path)
    author.add_argument('--card', action='append', default=[])
    author.add_argument('--output', type=Path, required=True)

    profile = commands.add_parser('profile', help='检查自定义角色或现有 GPT 的导出角色')
    profile.add_argument('--file', type=Path, required=True)

    catalog = commands.add_parser('catalog', help='按需查阅世界卡')
    catalog.add_argument('--worlds', type=Path)
    catalog.add_argument('--card')
    catalog.add_argument('--names', action='store_true')

    check = commands.add_parser('verify', help='只读验签')
    check.add_argument('--pending', type=Path, required=True)
    check.add_argument('--route', choices=ROUTES)
    check.add_argument('--pin', help='独立保留的 v4.5 manifest SHA-256')
    check.add_argument('--legacy-engine', type=Path, help='解压的正式 v4.4 scripts/story_start.py')

    card = commands.add_parser('card', help='从已验签的复制模式封签重建本地开箱卡')
    card.add_argument('--pending', type=Path, required=True)
    card.add_argument('--pin')
    card.add_argument('--output', type=Path, required=True)

    args = parser.parse_args(argv)
    started = time.perf_counter()
    if args.command == 'profile':
        verified = validate_profile(json_data(args.file.read_bytes()))
        result = {key: verified[key] for key in ('schema', 'name', 'age', 'source')}
    elif args.command == 'catalog':
        index = load_index(args.worlds or (PRIVATE_DECK if PRIVATE_DECK.is_file() else DEFAULT_DECK))
        if args.card:
            if args.card not in index:
                raise ValueError('Unknown world-card ID: ' + args.card)
            result = index[args.card]
        else:
            groups = {}
            for entry in index.values():
                groups.setdefault(entry['category'], []).append({key: entry[key] for key in ('id', 'title')})
            result = {'count': len(index), 'categories': {
                key: values if args.names else len(values) for key, values in groups.items()
            }}
    elif args.command in ('author', 'prepare'):
        active_role = json_data(role_path(args.profile).read_bytes())
        worlds = args.worlds or (PRIVATE_DECK if PRIVATE_DECK.is_file() else DEFAULT_DECK)
        if args.command == 'author':
            save_new(args.output, author_request(validate_profile(active_role), worlds, args.card))
            result = {'author_request': str(args.output.absolute())}
        else:
            brief = json_data(args.creative_brief.read_bytes())
            input_time = time.perf_counter() - started
            result = prepare(args.pending, brief, active_role, worlds, args.route)
            result['timings_seconds']['read_inputs'] = round(input_time, 6)
    elif args.command == 'verify' and args.legacy_engine is not None:
        if args.pin:
            raise ValueError('A v4.5 manifest pin cannot be applied to a historical seal')
        result = verify_legacy(args.pending, args.legacy_engine, args.route)
    else:
        manifest, files = verify_archive(seal_path(args.pending), args.pin)
        if args.command == 'card':
            button, notes, status = (
                json_data(files[name]) for name in ('button_manifest.json', 'creative-notes.json', 'creative-status.json')
            )
            save_new(args.output, render_card(button, notes, status))
            result = {'open_card': str(args.output.absolute()), 'verified': True}
        else:
            if args.route is not None and manifest['route'] != args.route:
                raise ValueError('Requested route differs from the verified button route')
            result = {**manifest, 'verified': True}
            del result['files']
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, AttributeError, KeyError, OSError, zipfile.BadZipFile) as error:
        print('衣橱暂未通过校验。' + str(error), file=sys.stderr)
        sys.exit(2)
