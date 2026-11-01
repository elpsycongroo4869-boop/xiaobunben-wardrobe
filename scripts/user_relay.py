#!/usr/bin/env python3
"""v2.7 one-click native user-message relay.

Creates and checks the exact full generation_prompt to use as the argument to
GenUI.issueNewTurn. This file never calls the image generator, triggers a click,
or claims that the provider received or complied with the text.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from dispatch_shoot import verify as verify_handoff

SCHEMA='wardrobe-native-user-relay-v2.7'


def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def build(handoff_path):
    src=Path(handoff_path).resolve()
    handoff=json.loads(src.read_text(encoding='utf-8'))
    verify_handoff(handoff)
    prompt=handoff['prompt']
    if handoff.get('prompt_kind')!='generation':
        raise ValueError('首次按钮只能使用原样 generation_prompt；失败重试需单独验签')
    if sha(prompt.encode('utf-8'))!=handoff['prompt_sha256']:
        raise ValueError('编译提示词指纹不符')
    if not all(s in prompt for s in (handoff['role'],handoff['scene'])):
        raise ValueError('完整拍摄提示缺少身份或场景')
    # All visual content remains verbatim. Other rules were executed BEFORE this point.
    prefix='请直接使用 ChatGPT 原生图片生成工具生成一张符合下述全部拍摄规格的高清写实写真。本轮已完成完整 Skill 真随机抽签和拍摄规格编译，以下是原样生成指令：\n\n'
    suffix=('\n本轮抽签编号：'+handoff['draw_id']+'。生成后请依据最新版 Library「小笨笨衣橱」Skill 对实际图片逐项验收；'
            '只有图片内容合格、真实文件可核验并完成记录，才能登记成功。')
    message=prefix+prompt+suffix
    plan={
       'schema':SCHEMA,'status':'prepared_not_clicked','handoff_file':str(src),
       'handoff_sha256':sha(canonical(handoff)), 'draw_id':handoff['draw_id'],
       'prompt_sha256':handoff['prompt_sha256'], 'full_prompt':prompt,
       'message':message,'message_sha256':sha(message.encode('utf-8')),
       'button_label':'打开小笨笨衣橱','action':'GenUI.issueNewTurn',
       'new_user_message_visible_after_click':True,'click_triggered':False,
       'delivered_to_image_tool':False,'image_audit_passed':False,
       'note':'按钮需由实际 ChatGPT 交互界面构造；脚本不执行按钮。成功生成也不代表完成验收登记。'
    }
    return plan


def verify(plan):
    if plan.get('schema')!=SCHEMA or plan.get('status')!='prepared_not_clicked':
        raise ValueError('无效的用户消息转发清单')
    expected=build(plan['handoff_file'])
    if canonical(expected)!=canonical(plan):
        raise ValueError('消息文本非编译器原样输出或原始封条已变化')
    if plan['message'].count(plan['full_prompt'])!=1:
        raise ValueError('完整提示词应精确包含一次')
    return True


def main():
    ap=argparse.ArgumentParser(description='v2.7 原生图片生成的用户消息按钮文本与原样指纹校验')
    ap.add_argument('--handoff',type=Path)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--message-output',type=Path)
    ap.add_argument('--verify',type=Path)
    a=ap.parse_args()
    if a.verify:
        verify(json.loads(a.verify.read_text(encoding='utf-8')))
        print('PASS:按钮消息已与交接封条中的完整 generation_prompt 原样匹配；仅验证按钮准备阶段')
        return
    if not a.handoff or not a.output or not a.message_output:
        ap.error('需要 --handoff --output --message-output 或 --verify')
    plan=build(a.handoff)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.message_output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    a.message_output.write_text(plan['message'],encoding='utf-8')
    verify(plan)
    print('PASS:用户消息按钮准备完成；draw_id='+plan['draw_id']+'; 原样 prompt sha256='+plan['prompt_sha256'])

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError,json.JSONDecodeError) as exc:
        print('用户消息交接门禁拒绝：'+str(exc),file=sys.stderr)
        sys.exit(2)
