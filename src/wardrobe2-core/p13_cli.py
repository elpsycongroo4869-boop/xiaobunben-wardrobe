"""Wardrobe 2 offline CLI; no LLM calls and no image generation."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ai_bridge import production_prompt
from bookshelf_nav import load_selected_card
from chapter_shelf import selected_point
from p13_runtime import P13Studio, migrate_ledger
from studio import read_json, atomic_json, role_contract
from p13_chat_ui import native_chat_payload

BASE=Path(__file__).resolve().parent


def main(argv=None):
    p=argparse.ArgumentParser(description='Wardrobe 2, integrated shelves/SELF and render ledger')
    p.add_argument('--data',type=Path,default=BASE/'demo-data-p13')
    sub=p.add_subparsers(dest='command',required=True)
    m=sub.add_parser('migrate');m.add_argument('--legacy-state',type=Path,required=True)
    sub.add_parser('menu').add_argument('--memory-available',action='store_true')
    sel=sub.add_parser('select-prompt');sel.add_argument('persona_summary');sel.add_argument('--memory-available',action='store_true')
    prod=sub.add_parser('production-prompt');prod.add_argument('selection_json',type=Path);prod.add_argument('persona_json',type=Path);prod.add_argument('work_id')
    prod.add_argument('--compact-character-draft', action='store_true')
    prod.add_argument('--emotion-only', action='store_true')
    prod.add_argument('--emotion-context', action='store_true')
    prep=sub.add_parser('prepare');prep.add_argument('job_file',type=Path)
    cp=sub.add_parser('chat-preview');cp.add_argument('work_id');cp.add_argument('--seal-sha256',required=True)
    op=sub.add_parser('open');op.add_argument('work_id');op.add_argument('--seal-sha256')
    for cmd in ('start-attempt','fail-attempt'):
        x=sub.add_parser(cmd);x.add_argument('work_id');x.add_argument('attempt_id')
    con=sub.add_parser('confirm');con.add_argument('work_id');con.add_argument('render_id');con.add_argument('image_file',type=Path);con.add_argument('--attempt-id')
    sub.add_parser('contract');sub.add_parser('state')
    a=p.parse_args(argv)
    if a.command=='migrate':
        if a.legacy_state.resolve()==(a.data/'shelf-state.json').resolve():
            raise ValueError('migration source and output must differ')
        if (a.data/'shelf-state.json').exists():
            raise ValueError('P1.3 output ledger already exists; refusing overwrite')
        now=datetime.now(timezone.utc)
        migrated=migrate_ledger(read_json(a.legacy_state),BASE/'world_index.json',BASE/'bookshelf_extension',now=now)
        atomic_json(a.data/'shelf-state.json',migrated)
        result={'status':'migrated','destination':str((a.data/'shelf-state.json').resolve()),
                'auto_seq':migrated['auto_seq'],'p13_schema':migrated['p13']['schema']}
    else:
        from p13_runtime import world_paths
        index, shelf_root = world_paths(BASE, a.data)
        profile_path = a.data / '.golden-profile.json'
        card = read_json(profile_path)['character'] if profile_path.is_file() else None
        if a.command != 'production-prompt':
            studio=P13Studio(a.data, index, shelf_root=shelf_root)
        now=datetime.now(timezone.utc)
        if a.command=='menu': result=studio.menu(now,memory_available=a.memory_available)
        elif a.command=='select-prompt': result=studio.selection_prompt(a.persona_summary,now,memory_available=a.memory_available)
        elif a.command=='production-prompt':
            selection=read_json(a.selection_json)
            book = chapter = None
            if shelf_root.parent.name == 'curated' and selection['origin'] == 'autonomous_library':
                book = load_selected_card(selection['book_id'], shelf_root)
                chapter = selected_point(book, selection.get('chapter_id'))
            out=production_prompt(selection,read_json(a.persona_json),a.work_id,
                                  world_card_dir=shelf_root/'cards',
                                  compact_character_draft=a.compact_character_draft,
                                  emotion_only=a.emotion_only, emotional_context=a.emotion_context,
                                  selected_book=book, chapter=chapter)
            if selection['origin']=='autonomous_self':
                self_id=selection.get('self_book_id')
                if self_id not in ('SELF_FREE','SELF_ECHO'):raise ValueError('invalid SELF book')
                extra='\n本次是本轮主角的独立表达；仍必须交付完整制作人五字段与五岗位，绝不强制采用固定造型。'
                if self_id=='SELF_ECHO':
                    if not selection.get('memory_source_verified') or not selection.get('memory_inspiration'):
                        raise ValueError('SELF_ECHO requires verified source and transformed inspiration')
                    extra+='\n已核实可访问的灵感摘要：'+selection['memory_inspiration']+'；不要复制隐私原文进出图指令。'
                out+=extra+'\njob 内保留 self_book_id、必要的记忆来源类型与验证标记。'
            result={'prompt':out}
            if chapter is not None:
                result['chapter'] = {'book_id': book['id'], **chapter}
        elif a.command=='prepare':
            job=read_json(a.job_file)
            if card is not None and any(job['persona'].get(field) != card[key]
                                        for field, key in (('identity', 'identity'), ('appearance', 'appearance'),
                                                           ('identity_continuity', 'continuity'))):
                raise ValueError('job identity differs from the session character')
            result=studio.prepare(job)
            # Native ChatGPT data from the verified sealed source; no HTML,
            # webpage upload, standalone acceptance note or redundant image.
            result['chat_ui']=native_chat_payload(studio,result['work_id'],
                expected_seal=result['seal_sha256'])
        elif a.command=='chat-preview':
            result=native_chat_payload(studio,a.work_id,expected_seal=a.seal_sha256)
        elif a.command=='open':
            result=studio.open(a.work_id,expected_seal=a.seal_sha256)
            import hashlib
            payload=result['render_instruction']
            result['render_payload_chars']=len(payload)
            result['render_payload_sha256']=hashlib.sha256(payload.encode('utf-8')).hexdigest()
            # The hash proves local bytes; the external image provider
            # must independently attest what bytes it actually received.

        elif a.command=='start-attempt':result=studio.start_attempt(a.work_id,a.attempt_id)
        elif a.command=='fail-attempt':result=studio.fail_attempt(a.work_id,a.attempt_id)
        elif a.command=='confirm':
            result=studio.confirm_image(a.work_id,a.render_id,a.image_file,attempt_id=a.attempt_id)
        elif a.command=='contract':result=role_contract(emotional_context=True)
        else:result=studio.shelf.state
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
