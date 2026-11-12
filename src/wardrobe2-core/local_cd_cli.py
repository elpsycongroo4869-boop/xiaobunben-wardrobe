"""Read-only demonstration CLI for the optional local-CD prototype.

Never mutates Library, the official state or any seal.
"""
import argparse
import json
import random
from pathlib import Path
from bookshelf_nav import BASE, catalog, selection_prompt_for_shelf
from bookshelf_local_cd import bootstrap_from_legacy, browse_local, choose


def main(argv=None):
    p = argparse.ArgumentParser(description='Local CD selection proof of concept (READ ONLY)')
    p.add_argument('--legacy-state', type=Path, required=True)
    p.add_argument('--root', type=Path, default=BASE)
    p.add_argument('--seed', type=int)
    p.add_argument('--persona', default='本轮成年主角')
    a = p.parse_args(argv)
    legacy = json.loads(a.legacy_state.read_text(encoding='utf-8'))
    cat = catalog(a.root)
    sidecar = bootstrap_from_legacy(legacy, cat)
    choice = choose(sidecar, cat, legacy, random.Random(a.seed) if a.seed is not None else None)
    if choice['shelf_id'] is None:
        out = {'selection': choice, 'message':'No active fixed books; consider Original entry'}
    else:
        shelf = browse_local(choice['shelf_id'], sidecar, cat, legacy, a.root,
                             override_book_id=choice['override_book_id'])
        original = legacy['original']
        shelf['original_entry'] = ({'id': 'ORIGINAL','title':'原创','intro':'自由发明此刻想拍的世界和事件'}
                                   if legacy['auto_seq']+1 >= original['next_eligible_auto_seq'] else None)
        out = {'selection':choice,'book_spines':shelf,
               'producer_choice_prompt':selection_prompt_for_shelf(shelf,a.persona),
               'read_only':True}
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
