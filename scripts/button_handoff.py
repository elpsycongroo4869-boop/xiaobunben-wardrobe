#!/usr/bin/env python3
"""v2.9.8: source-verified 21-field image prompt and user-visible button contract.

Use 'new_chat' on a clean conversation entry. A button labeled 打开小笨笨衣橱
calls GenUI.issueNewTurn(full_message). In a conversation contaminated with old
images/edit discussion, use 'copy_only' and GenUI.copy(full_message), then
paste into a separately opened clean chat. This program prepares and verifies;
it cannot display the button or control the native image-generation backend.
"""
import argparse, hashlib, json, sys
from pathlib import Path
from english_relay import canonical
from photo_creation_relay import build_from_pending

SCHEMA='wardrobe-button-handoff-v2.9.8'
BUTTON='打开小笨笨衣橱'
ROUTES={'new_chat':'GenUI.issueNewTurn','copy_only':'GenUI.copy'}

def build(pending_dir,route):
    if route not in ROUTES: raise ValueError('Unsupported button route')
    photo=build_from_pending(Path(pending_dir))
    return {
        'schema':SCHEMA, 'status':'prepared_not_clicked',
        'source_draw_id':photo['draw_id'],
        'source_message_sha256':photo['message_sha256'],
        'source_field_count':21,
        'button_label':BUTTON,'action':ROUTES[route], 'route':route,
        'full_user_message':photo['message'],
        'native_image_generation_succeeded':False,
        'full_workflow_tested':False,
        'history_committed':False,
    }

def verify(pending_dir,route,output):
    expected=build(pending_dir,route)
    actual=json.loads(Path(output).read_text('utf-8'))
    if canonical(actual)!=canonical(expected):
        raise ValueError('Button content or routing changed after verification')
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pending-dir',type=Path,required=True)
    p.add_argument('--route',choices=tuple(ROUTES),default='new_chat')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if a.verify:
        verify(a.pending_dir,a.route,a.output)
        print('PASS: button + 21 fields + original draw sealed, click/render not simulated')
        return
    record=build(a.pending_dir,a.route)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    verify(a.pending_dir,a.route,a.output)
    print('PASS: '+record['button_label']+' prepared, route='+a.route+', sha256='+record['source_message_sha256'])
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr)
        sys.exit(2)
