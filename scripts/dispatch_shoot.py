#!/usr/bin/env python3
"""v2.5 持久化拍摄交接封条：只证明文本/抽签一致，不控制图片生成器。"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REQUIRED_KEYS = ('draw_id','role','scene','camera_pack_id','generation_prompt','retry_prompt','action','career_cues')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def seal(draw_path,shoot_path,capability,prompt_kind="generation"):
    if prompt_kind not in ("generation","retry"):
        raise ValueError("只能选择 generation/retry 提示")
    if capability not in ('explicit_prompt','context_inferred'):
        raise ValueError('未知图像工具提示词能力；必须检查工具接口')
    draw=json.loads(draw_path.read_text(encoding='utf-8'))
    shoot=json.loads(shoot_path.read_text(encoding='utf-8'))
    if any(not shoot.get(k) for k in REQUIRED_KEYS):
        raise ValueError('拍摄规格缺少关键字段；禁止生成')
    if shoot.get('status')!='preflight_ready':
        raise ValueError('拍摄规格尚未完成前置编译')
    for x,y in (('draw_id','draw_id'),('role','role'),('camera_pack_id','camera_pack_id'),('category_id','category_id')):
        if x=='role' and draw.get('is_original') and draw.get('role','').startswith('原创职业'):
            # Original occupations draw a creation constraint, not a final job name.
            # prepare_shoot requires a specific role before dispatch; all other locked
            # dimensions are still compared below. Never permit an arbitrary change
            # to a fixed existing occupation or cosplay identity.
            if len(shoot.get('role','').strip())<3 or '待生成' in shoot['role']:
                raise ValueError('原创职业尚未定义真实职业名')
            continue
        if draw.get(x)!=shoot.get(y):
            raise ValueError(f'交接锁定字段不一致：{x}/{y}')
    if draw['suggested_scene']!=shoot['scene']:
        if shoot.get('original_suggested_scene')!=draw['suggested_scene'] or not shoot.get('scene_override_reason') or len(shoot['scene_override_reason'])<6:
            raise ValueError('场地与抽签不一致且未有合规更正理由')
    for field in ('generation_prompt','retry_prompt'):
        content=shoot[field]
        core=(shoot['role'],shoot['scene'],shoot['action'],*shoot['career_cues'])
        if not all(x in content for x in core):
            raise ValueError(f'{field}遗漏了职业/场景/动作/证据')
        camera=draw.get('camera_pack',{}).get('name')
        if not camera or camera not in content:
            raise ValueError(f'{field}遗漏摄影包')
        if len(content)<180:
            raise ValueError(f'{field}过短，不能承载完整拍摄目标')
    if shoot.get('lane')!=draw.get('lane','career'):
        raise ValueError('路线不一致')
    if shoot.get('lane') in ('cosplay','fusion') and (draw.get('cosplay_id')!=shoot.get('cosplay_id')):
        raise ValueError('Cos路线身份不一致')
    field='generation_prompt' if prompt_kind=='generation' else 'retry_prompt'
    prompt=shoot[field].strip()+'\n'
    h={'schema':'wardrobe-dispatch-v2.5','status':'ready_for_image_tool','draw_id':draw['draw_id'],
       'lane':shoot['lane'],'role':shoot['role'],'scene':shoot['scene'],
       'scene_override_reason':shoot.get('scene_override_reason'),
       'camera_pack_id':shoot['camera_pack_id'],'outfit_mode':shoot['costume_mode'], 'prompt_kind':prompt_kind,
       'prompt':prompt,'prompt_sha256':digest(prompt.encode('utf-8')),
       'draw_sha256':digest(canonical(draw)),'shoot_sha256':digest(canonical(shoot)),
       'source_draw_file':str(draw_path.resolve()),'source_shoot_file':str(shoot_path.resolve()),
       'capability':capability,'delivery_confirmed':False,
       'note':'本文件只核验本地交接内容一致，不代表图片生成器已接收或执行该提示。'}
    return h

def verify(manifest):
    if manifest.get('schema')!='wardrobe-dispatch-v2.5' or manifest.get('status')!='ready_for_image_tool':
        raise ValueError('交接清单不是已锁定的v2.5格式')
    d=Path(manifest['source_draw_file']);s=Path(manifest['source_shoot_file'])
    if not d.exists() or not s.exists():
        raise ValueError('源抽签/拍摄规格文件丢失')
    draw=json.loads(d.read_text(encoding='utf-8'))
    shoot=json.loads(s.read_text(encoding='utf-8'))
    if digest(canonical(draw))!=manifest['draw_sha256'] or digest(canonical(shoot))!=manifest['shoot_sha256']:
        raise ValueError('封条后源文件发生变化，禁止出图')
    expect=seal(d,s,manifest['capability'],manifest.get('prompt_kind','generation'))
    if any(expect[k]!=manifest[k] for k in ('draw_id','role','scene','camera_pack_id','prompt','prompt_sha256','draw_sha256','shoot_sha256')):
        raise ValueError('交接清单被篡改，禁止出图')
    return True

def main():
    p=argparse.ArgumentParser(description='v2.5 出图前只读锁定与指纹验证')
    p.add_argument('--draw',type=Path)
    p.add_argument('--shoot',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--prompt-output',type=Path)
    p.add_argument('--capability',choices=['explicit_prompt','context_inferred'],default='context_inferred')
    p.add_argument('--verify',type=Path)
    p.add_argument('--prompt-kind',choices=['generation','retry'],default='generation')
    a=p.parse_args()
    if a.verify:
        h=json.loads(a.verify.read_text(encoding='utf-8'))
        verify(h)
        print('PASS:交接文件和锁定抽签/拍摄规格一致；不代表图像工具已经接收提示')
        return
    if not a.draw or not a.shoot or not a.output or not a.prompt_output:
        p.error('必须提供 --draw --shoot --output --prompt-output 或 --verify')
    h=seal(a.draw,a.shoot,a.capability,a.prompt_kind)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.prompt_output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    a.prompt_output.write_text(h['prompt'],encoding='utf-8')
    verify(h)
    print('PASS:'+h['draw_id']+' '+h['role']+'; 提示SHA256='+h['prompt_sha256']+'; 交接模式='+h['capability'])

if __name__=='__main__':
    try:
        main()
    except (KeyError,ValueError,OSError,json.JSONDecodeError) as exc:
        print('禁止调用图片工具：'+str(exc),file=sys.stderr)
        sys.exit(2)
