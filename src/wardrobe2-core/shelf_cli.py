"""Read-only optional bookshelf commands. Default cli.py remains unchanged."""
import argparse
import json
import random
from pathlib import Path

from ai_bridge import production_prompt
from bookshelf_nav import BASE, browse_shelf, choose_shelf, load_selected_card, selection_prompt_for_shelf
from studio import read_json


def main(argv=None):
    p=argparse.ArgumentParser(description='P1.2.3 optional mixed 30-book shelf pilot')
    p.add_argument('--root',type=Path,default=BASE)
    p.add_argument('--state',type=Path,help='READ ONLY: point to current shelf-state.json')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('choose-shelf').add_argument('--seed',type=int)
    b=sub.add_parser('browse');b.add_argument('group_id')
    s=sub.add_parser('choice-prompt');s.add_argument('group_id');s.add_argument('persona_summary')
    w=sub.add_parser('selected-card');w.add_argument('book_id')
    a=sub.add_parser('production-prompt');a.add_argument('selection_json',type=Path);a.add_argument('persona_json',type=Path);a.add_argument('work_id')
    args=p.parse_args(argv)
    if args.command in ('choose-shelf','browse','choice-prompt'):
        if args.state is None:
            raise SystemExit('Please specify --state (read-only, current global CD ledger).')
        state=read_json(args.state)
    if args.command=='choose-shelf':
        x={'shelf_id':choose_shelf(state,args.root,random.Random(args.seed) if args.seed is not None else None)}
    elif args.command=='browse':x=browse_shelf(args.group_id,state,args.root)
    elif args.command=='choice-prompt':x={'prompt':selection_prompt_for_shelf(browse_shelf(args.group_id,state,args.root),args.persona_summary)}
    elif args.command=='selected-card':x=load_selected_card(args.book_id,args.root)
    else:x={'prompt':production_prompt(read_json(args.selection_json),read_json(args.persona_json),args.work_id,world_card_dir=args.root/'cards')}
    print(json.dumps(x,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
