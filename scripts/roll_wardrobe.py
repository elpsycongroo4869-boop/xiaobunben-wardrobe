#!/usr/bin/env python3
"""小笨笨衣橱 2.5：可核验的分层随机抽签器（只产出主题，不生成图片）。

用法：
  python scripts/roll_wardrobe.py --output /tmp/wardrobe-draw.json
  # v2.9.13 以后不再登记成功样片，历史档案只读。

历史 JSONL 应保存在可持久读写的位置；仅修改安装包内的副本不等于跨会话保存。
"""
import argparse
import json
import random
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from image_integrity import fingerprint

ROOT = Path(__file__).resolve().parents[1]
CAT_PATH = ROOT / 'references/category-pool.json'
DEFAULT_HISTORY = ROOT / 'references/history.jsonl'
CAMERA_PATH = ROOT / 'references/camera-packs.json'
VERSION = '2.5'
HISTORY_COMPAT = ('2.0', '2.1', '2.2', '2.3', '2.4', '2.5')
COSPLAY_PATH = ROOT / 'references/cosplay-pool.json'
LANES = ('career', 'cosplay', 'fusion')
LANE_WEIGHTS = (70, 20, 10)
COSTUME_MODES = ('practical', 'refined', 'game_feminine', 'fantasy')
COSTUME_WEIGHTS = (10, 20, 55, 15)
SHOT_POOL = [
    '远景环境人像：人物与世界比例鲜明',
    '中景纪实抓拍：正在完成工作动作',
    '全身动作摄影：明确身体姿态与工具',
    '腰部以上的现场抓拍：交代职业与背景',
    '轻微低机位电影镜头：强调场景空间',
    '肩后跟拍：展现职业操作及目标',
    '自然光街拍：真实环境里的角色瞬间',
    '广角职业场景合影感：突出人物与设施',
    '任务完成后的现场瞬间：情绪与工作痕迹',
    '舞台/竞技现场摄影：按职业调整镜头',
    '环境特写：面部清楚且两项职业线索入画',
    '高位俯拍：展现工作台和正在操作的对象',
    '背光侧面抓拍：角色面貌和工具均可辨',
    '步行跟拍：由近及远交代行动过程',
]
MOMENT_POOL = [
    '任务开始前的准备', '执行任务的关键动作', '向同伴或学员讲解',
    '刚解决一个突发难题', '中途休息但仍保留工作痕迹', '为工作做现场记录',
    '检查工具和装备', '完成任务后的一次回望', '在困难环境中持续工作',
    '与工作对象互动', '工作地点的意外发现', '准备前往下一个地点',
]
STRENGTH_POOL = ('subtle', 'medium', 'strong')
STRENGTH_WEIGHTS = (30, 50, 20)
STRENGTH_DESC = {
    'subtle':'轻度：有辨识度的微弱拍摄质感，职业信息优先',
    'medium':'中度：拍摄媒介、用光与色调都清楚可见，职业仍清晰',
    'strong':'重度：明显风格化，但人物面容和至少两项职业线索仍须可辨',
}
ACT_POOL = ['修复','护送','追踪','勘察','训练','救援','守护','培育','驾驶','协商','演奏','建造']
SUBJECT_POOL = ['濒危生物','破碎仪器','季节变迁','航线与贸易','地下遗迹','特殊材料','古老技艺','日常民生','生态灾害','城市能源','未知语言','迁徙群体']
TWIST_POOL = ['关键任务即将结束','现场突发难题','首次独立值勤','同伴需要支援','节庆日的特殊工作','罕见天气即将到来','失传工艺突然重现','漫长夜班的最后一刻']
BASE_COOLDOWN = ('绘图','制图','测绘','地图师','星图','星象','飞艇','浮空船','占星')


def load_history(path):
    if not path.exists():
        return []
    records=[]
    for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),start=1):
        if not line.strip():
            continue
        try:
            obj=json.loads(line)
            if isinstance(obj,dict) and obj.get('status','success')=='success':
                records.append(obj)
        except json.JSONDecodeError as exc:
            raise ValueError(f'历史记录第{i}行不是合法JSON：{exc}')
    return records


def existing_random(history):
    return [x for x in history if x.get('mode')=='random' and x.get('version') in HISTORY_COMPAT and x.get('lane','career') in ('career', 'fusion')]


def select_camera_pack(history, rng):
    packs=json.loads(CAMERA_PATH.read_text(encoding='utf-8'))['camera_packs']
    camera_history=[x for x in history if x.get('mode')=='random' and x.get('status','success')=='success' and x.get('camera_pack_id')]
    phase=len(camera_history)%len(packs)
    used={x.get('camera_pack_id') for x in camera_history[-phase:]} if phase else set()
    options=[x for x in packs if x['id'] not in used]
    if not options:
        raise ValueError('摄影乱序袋状态异常：请核对历史。')
    recent={x.get('camera_pack_id') for x in camera_history[-3:]}
    fresh=[x for x in options if x['id'] not in recent]
    if fresh:
        options=fresh
    chosen=rng.choice(options)
    return chosen, phase+1, len(packs)


def select_cosplay(history, rng, lane):
    """纯 Cos 和融合 Cos 各自持有独立的24角色无放回袋。"""
    chars = json.loads(COSPLAY_PATH.read_text(encoding='utf-8'))['characters']
    matched = [r for r in history if r.get('status','success') == 'success'
               and r.get('mode') == 'random' and r.get('lane') == lane and r.get('cosplay_id')]
    phase = len(matched) % len(chars)
    used = {r['cosplay_id'] for r in matched[-phase:]} if phase else set()
    options = [c for c in chars if c['id'] not in used]
    if not options:
        raise ValueError('Cos角色乱序袋状态异常')
    recent = {r.get('cosplay_id') for r in history[-4:]}
    fresh = [c for c in options if c['id'] not in recent]
    if fresh:
        options = fresh
    return rng.choice(options), phase+1, len(chars)


def draw(history, rng, lane_override=None):
    lane = lane_override or rng.choices(LANES, weights=LANE_WEIGHTS, k=1)[0]
    if lane not in LANES:
        raise ValueError('不支持的随机路线')
    random_records = existing_random(history)
    world_fields = {}
    dedup_relaxed = False
    if lane in ('career', 'fusion'):
        cats=json.loads(CAT_PATH.read_text(encoding='utf-8'))['categories']
        n=len(cats)
        phase=len(random_records)%n
        used={h.get('category_id') for h in random_records[-phase:]} if phase else set()
        available=[c for c in cats if c['id'] not in used]
        if not available:
            raise ValueError('职业世界乱序袋状态异常，请检查历史记录')
        recent={h.get('category_id') for h in random_records[-3:]}
        fresh=[c for c in available if c['id'] not in recent]
        if fresh:
            available=fresh
        category=rng.choice(available)

        past_roles={h.get('role') for h in history[-10:]}
        roles=[r for r in category['roles'] if r not in past_roles]
        if len(random_records)<8:
            cooled=[r for r in roles if not any(word in r for word in BASE_COOLDOWN)]
            if cooled:
                roles=cooled
        if not roles:
            roles=category['roles']
            dedup_relaxed=True
        original=(rng.randrange(5)==0)
        if original:
            job='原创职业（待生成时命名；登记时必须填写真实职业）'
            creative={'行动':rng.choice(ACT_POOL),'对象':rng.choice(SUBJECT_POOL),'特殊情境':rng.choice(TWIST_POOL)}
        else:
            job=rng.choice(roles)
            creative=None
        world_fields = {
            'category_id':category['id'],'category':category['name'],
            'role':job, 'is_original':original, 'creative_constraints':creative,
            'suggested_scene':rng.choice(category['scenes']),
            'cycle_position':phase+1,'cycle_size':n,
        }
    else:
        # 纯 Cos 作品不消耗16世界/128职业乱序袋名额。
        world_fields={
            'category_id':'classic-cosplay','category':'经典虚构角色 Cos',
            'role':'待锁定经典Cos角色','is_original':False,'creative_constraints':None,
            'suggested_scene':'待锁定角色舞台', 'cycle_position':None, 'cycle_size':16,
        }

    cosplay_fields = {'cosplay_id':None,'cosplay_character':None,'cosplay_cycle_position':None,
                      'cosplay_cycle_size':24}
    if lane in ('cosplay','fusion'):
        character, cp, cs = select_cosplay(history, rng, lane)
        cosplay_fields.update({'cosplay_id': character['id'], 'cosplay_character':character,
                               'cosplay_cycle_position':cp, 'cosplay_cycle_size':cs})
        if lane=='cosplay':
            world_fields['role']=character['name']
            world_fields['suggested_scene']=character['suggested_scene']

    camera_pack, cam_pos, cam_count=select_camera_pack(history,rng)
    intensity=rng.choices(STRENGTH_POOL,weights=STRENGTH_WEIGHTS,k=1)[0]
    costume_mode=rng.choices(COSTUME_MODES,weights=COSTUME_WEIGHTS,k=1)[0]
    return {
        'version':VERSION, 'draw_id':str(uuid.uuid4()), 'mode':'random','lane':lane,
        **world_fields, **cosplay_fields,
        'costume_mode':costume_mode,
        'suggested_camera':rng.choice(SHOT_POOL),
        'camera_pack_id':camera_pack['id'],'camera_pack':camera_pack,
        'camera_cycle_position':cam_pos,'camera_cycle_size':cam_count,
        'camera_intensity':intensity,'camera_intensity_description':STRENGTH_DESC[intensity],
        'story_moment':rng.choice(MOMENT_POOL),'history_records_seen':len(history),
        'dedup_relaxed':dedup_relaxed,
        'instruction':'按路线锁定职业或Cos角色；服装风格只在抽签后编译，丝袜为抽签后可选的穿搭辅件，适宜时可见、不适宜则省略；不干预镜头。失败不重新抽签或登记成功。',
        'status':'drawn_not_yet_generated','requires_preflight':True,
        'preflight_script':'scripts/prepare_shoot.py'
    }


def commit(history_path, draw_path, role, scene, motif, audit_path):
    data=json.loads(draw_path.read_text(encoding='utf-8'))
    if data.get('version') not in ('2.2', '2.3', '2.4', VERSION) or data.get('mode')!='random' or not data.get('draw_id'):
        raise ValueError('不是有效的衣橱2.2/2.3/2.4/2.5随机抽签结果')
    if not audit_path or not audit_path.is_file():
        raise ValueError('v2.3 必须真实出图、人工验收、提供 --audit-file 才能提交历史')
    audit=json.loads(audit_path.read_text(encoding='utf-8'))
    expected_fields=('image_exists','world_match','role_match','action_visible','photography_match','continuity_match','outfit_role_match','portrait_aesthetic_match','visual_subject_hierarchy_match')
    if audit.get('draw_id')!=data['draw_id'] or (data.get('lane') in ('cosplay','fusion') and audit.get('cosplay_match') is not True) or any(audit.get(k) is not True for k in expected_fields) or (type(audit.get('career_cues_visible')) is not int or audit['career_cues_visible']<2):
        raise ValueError('摄影验收未全部通过，不可登记；请检查审核文件并重新出图')
    # 与语义验收分开，仅用文件存在性和指纹核验避免把不存在的图片记入成功历史。
    image_file = audit.get('image_file')
    image_sha256 = audit.get('image_sha256')
    if not image_file or not image_sha256:
        raise ValueError('v2.3 成功登记还需审核文件中的 image_file 与 image_sha256')
    image_path = Path(image_file)
    actual_hash = fingerprint(image_path)['image_sha256']
    if actual_hash != image_sha256:
        raise ValueError('成功图片内容与审核文件的 sha256 不一致')
    history=load_history(history_path)
    if any(r.get('draw_id')==data['draw_id'] for r in history):
        raise ValueError('这张抽签结果已登记成功，不得重复登记。')
    job=role or data.get('role','')
    if data.get('is_original') and (not role or '待生成' in job):
        raise ValueError('原创职业必须提供 --role 填写最后实际生成的职业名。')
    record={
        'date':datetime.now(timezone.utc).date().isoformat(),
        'draw_version':data['version'], 'version':VERSION,'status':'success','mode':'random',
        'draw_id':data['draw_id'],'category_id':data['category_id'],
        'category':data['category'],'role':job,
        'lane':data.get('lane','career'),'cosplay_id':data.get('cosplay_id'),
        'costume_mode':data.get('costume_mode','refined'),
        'scene':scene or data.get('suggested_scene',''),
        'camera':data.get('suggested_camera',''),
        'camera_pack_id':data.get('camera_pack_id',''),
        'camera_pack_name':data.get('camera_pack',{}).get('name',''),
        'camera_intensity':data.get('camera_intensity',''),
        'story_moment':data.get('story_moment',''),
        'motif':motif or '',
        'source':'人工已验收图片、提供成功审核文件后登记',
        'outfit_role_match':True, 'portrait_aesthetic_match':True, 'visual_subject_hierarchy_match':True,
        'audited':True, 'image_sha256':actual_hash
    }
    history_path.parent.mkdir(parents=True,exist_ok=True)
    with history_path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(record,ensure_ascii=False)+'\n')
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description='小笨笨衣橱2.5：世界、职业、摄影包、镜头和故事瞬间的分层真随机抽签，默认不接触图像工具。')
    p.add_argument('--history',type=Path,default=DEFAULT_HISTORY)
    p.add_argument('--output',type=Path,help='抽签结果JSON写入指定文件，方便成功后提交历史')
    p.add_argument('--commit',type=Path,help='已停用：不再登记成功样片')
    p.add_argument('--role',help='成功生成的实际角色职业（原创职业必填）')
    p.add_argument('--scene',help='成功生成的实际场景（如果与建议地点不同）')
    p.add_argument('--motif',help='主题母题标签，如 airship / gothic / star-map')
    p.add_argument('--audit-file',type=Path,help='提交历史时必填：真实出图后的人工验收 JSON 文件')
    p.add_argument('--lane',choices=LANES, help='仅用于用户指定路线/测试，不指定时随机三路线')
    p.add_argument('--seed',type=int,help='仅供本地测试：确定性随机种子。真实使用不要传入。')
    a=p.parse_args(argv)
    if a.commit:
        raise ValueError("Success sample registration was retired in v2.9.13; use draw only")
    else:
        rng=random.Random(a.seed) if a.seed is not None else secrets.SystemRandom()
        out=draw(load_history(a.history),rng,a.lane)
    content=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(content+'\n',encoding='utf-8')
    print(content)

if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as exc:
        print('抽签失败：'+str(exc),file=sys.stderr)
        sys.exit(2)
