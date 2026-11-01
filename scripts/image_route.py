#!/usr/bin/env python3
"""v2.6 受控出图路由：将已验签的提示词原样绑定到明确支持 prompt 的图像工具参数。

本模块只创建/验证可供工具调用使用的计划。不会调用 Figma/Adobe，不会扣费，
也不会声称服务商收到了该请求；后续执行工具时必须按 plan.args 精确传参。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from dispatch_shoot import verify as verify_handoff

TOOLS = {
    'figma_gpt': 'mcp__Figma__generate_image',
    'adobe_firefly': 'mcp__Adobe__image_generate',
}
MODEL = 'gpt-image-2.5-sunburst'

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def make_plan(handoff_path, backend, paid_approved=False, file_key=None):
    if backend not in TOOLS:
        raise ValueError('该出图通道无法保证显式传入 prompt；盲盒模式停止出图，不允许隐式替代')
    if not paid_approved:
        raise ValueError('此接口可能消耗第三方 AI 积分，尚未获得用户明确授权；禁止生成')
    handoff=json.loads(Path(handoff_path).read_text(encoding='utf-8'))
    verify_handoff(handoff)
    if handoff.get('capability')!='explicit_prompt':
        raise ValueError('必须使用 explicit_prompt 封条；不能将 context_inferred 假装成显式接口')
    prompt=handoff['prompt']
    if sha(prompt.encode('utf-8'))!=handoff['prompt_sha256']:
        raise ValueError('原始提示词指纹不符')
    if backend=='figma_gpt':
        if not file_key or not re.fullmatch(r'[0-9A-Za-z]{22,128}',file_key):
            raise ValueError('Figma 需要用户可编辑文件的真实 fileKey；不得编造')
        args={'fileKey':file_key,'model':MODEL,'prompt':prompt,'width':1024,'height':1536}
    else:
        if len(prompt)>1500:
            raise ValueError('Adobe 输入限制1500字符；不自动删减场景/线索/摄影包。优先用 Figma。')
        args={'options':{'prompt':prompt,'n':1,'aspectRatio':'3:4','promptReasoner':'quality'}}
    plan={'schema':'wardrobe-route-v2.6','status':'ready_not_dispatched',
          'source_handoff_file':str(Path(handoff_path).resolve()),'handoff_sha256':sha(canonical(handoff)),
          'draw_id':handoff['draw_id'],'backend':backend,'tool_name':TOOLS[backend],
          'args':args,'prompt_sha256':handoff['prompt_sha256'],
          'prompt_field':'args.prompt' if backend=='figma_gpt' else 'args.options.prompt',
          'paid_approved':True,'no_spoiler_before_image':True,
          'delivery_confirmed':False,'image_audit_passed':False,
          'note':'本地验证不等于服务商已收到或正确生成图片；调用工具和图片验收须另行完成。'}
    return plan

def verify_plan(plan):
    if plan.get('schema')!='wardrobe-route-v2.6' or plan.get('status')!='ready_not_dispatched':
        raise ValueError('无效的v2.6路由清单')
    src=Path(plan['source_handoff_file'])
    if not src.exists():raise ValueError('来源封条文件不存在')
    handoff=json.loads(src.read_text(encoding='utf-8'))
    if sha(canonical(handoff))!=plan['handoff_sha256']:
        raise ValueError('来源封条被修改')
    expected=make_plan(src,plan['backend'],plan['paid_approved'],plan.get('args',{}).get('fileKey'))
    if canonical(expected)!=canonical(plan):
        raise ValueError('路由参数发生修改，禁止生成')
    return True

def main():
    p=argparse.ArgumentParser(description='v2.6 显式提示词路由与盲盒守门')
    p.add_argument('--handoff',type=Path)
    p.add_argument('--backend',choices=['figma_gpt','adobe_firefly','native_implicit'])
    p.add_argument('--figma-file-key')
    p.add_argument('--paid-approved',action='store_true',help='用户已明确同意此次第三方积分消耗')
    p.add_argument('--output',type=Path)
    p.add_argument('--verify',type=Path)
    a=p.parse_args()
    if a.verify:
        verify_plan(json.loads(a.verify.read_text(encoding='utf-8')))
        print('PASS: 路由计划含完整原样提示词；这是本地验签，不是服务商交付回执')
        return
    if not a.handoff or not a.backend or not a.output:p.error('需要 --handoff --backend --output')
    plan=make_plan(a.handoff,a.backend,a.paid_approved,a.figma_file_key)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    verify_plan(plan)
    print('PASS: 显式prompt调用计划已封存，不代表调用已发生；draw_id='+plan['draw_id'])

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError,json.JSONDecodeError) as ex:
        print('出图门禁拒绝：'+str(ex),file=sys.stderr)
        sys.exit(2)
