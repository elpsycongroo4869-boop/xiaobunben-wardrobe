#!/usr/bin/env python3
"""v2.5: 职业/Cos/融合分路编译，女性化服装美化，零牺牲审美原则。

注意：程序只写文本，不调用/控制图像生成器，不能解决生成器自身的串片。
对旧版 v2.2 已抽中但未成功的 draw.json，支持原样锁定重编译。
"""
import argparse
import json
import sys
from pathlib import Path
from face_sensual_trial import is_text_face_delivery
from story_first import is_story_first

SUPPORTED_DRAWS = {'2.2', '2.3', '2.4', '2.5', '3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.5.2', '3.5.2-charm30-test', '3.5.2-charm30-expression-test','3.5.2-charm30-emotion-tone-test','3.5.2-charm70-natural-props-emotion-test','3.5.2-charm70-framing-sovereignty-test','3.5.2-charm100-framing-sovereignty-test','3.5.2-charm100-framing-compact30-test','3.5.2-charm100-sensual-framing-compact30-test','3.5.2-charm100-candid-realism-framing-compact30-test', '3.5.2-charm-index-candid-realism-framing-compact30-test', '3.5.2-charm85-role-exposure50-handphysics-compact30-test', '3.5.2-B3.2-role-first-costume-test'}  # v2.3.1 沿用 v2.3 抽签数据结构


SUPPORTED_DRAWS.add('4.0')


def compatible_shot(draw):
    shot = draw['suggested_camera']
    pack = draw['camera_pack_id']
    base_note = ''
    adjustments = []
    if pack == 'front-phone' and any(term in shot for term in ('全身', '远景', '环境', '跟拍', '高位')):
        base_note = '使用固定在低位稳定支架的手机前置广角，人物退入工作场景完成动作；画面仍具有前置镜头广角透视。'
        adjustments.append('手机前置＋远景：改为手机固定低位远自拍，保留前置广角媒介与全身镜头')
    elif pack == 'front-phone':
        base_note = '手机前置广角的数码透视；职业工作场景与工具同框。'
    if pack == 'analog-dv':
        adjustments.append('古早DV只表达画质；不自动带入时间戳或旧日期')
    if draw.get('camera_intensity') == 'strong':
        adjustments.append('重度风格仅影响背景和光影，关键动作、脸和两项职业线索仍清晰')
    return base_note, adjustments


def _require_visible(name, value):
    if not isinstance(value, str) or len(value.strip()) < 3:
        raise ValueError(f'{name}必须具体、可见，不能只填抽象形容词')
    forbidden = {'好看', '漂亮', '阳光', '有气质', '优雅', '性感', '很美', '很棒'}
    if value.strip() in forbidden:
        raise ValueError(f'{name}不能只使用审美形容词')
    return value.strip()


COSTUME_GUIDES = {
    'practical': '角色美感优先的简洁工作主题服：收腰、肩颈线条与下装比例清晰，岗位标记点明身份；可艺术化修改实际制服，不以厚重防护为默认。',
    'refined': '精致女性化角色制服：先确定漂亮的整体比例、腰身、上下装搭配、鞋靴，再融入职业识别母题；可用短裙、裙裤、合体短裤或秀美的裤装。',
    'game_feminine': '游戏女主角式职业造型：让腰线、分层裙摆、短款外搭、贴身短裤或相称鞋袜形成鲜明角色美感；职业装备和标志保留辨识度，不受现实服装防护完整度约束。',
    'bespoke': '由本轮艺术设计独立决定的完整成年女性角色造型，清晰而优美的轮廓、颜色、材质和人物特色；不受固定衣装模式限制。',
    'fantasy': '奇幻女主角式服装：漂亮的束腰与上下装比例、分层衣摆、艺术化局部露肤、装饰性护甲或主题配件；鲜明表现职业/角色身份而非复制厚重的现实装备。',
}

# Garment variation is chosen *after* role, task, camera and costume mode.
# A short skirt/skort or dark hosiery is an outfit option when compatible with
# movement, protective equipment, locale and the already chosen composition.
# The first group cannot be promoted to an obligatory leg-framing instruction.
LOWER_BODY_STYLING = {
    'practical': '原定镜头自然能看到下装时，以修身线条和协调鞋靴体现女性造型；服装可以艺术化设计。',
    'refined': '原定镜头自然能看到下装时，可设计短制服裙、裙裤、合体短裤、修身长裤或协调袜靴。',
    'game_feminine': '原定镜头自然能看到下装时，优先考虑A字短裙、结构裙裤、合体短裤或特色修身裤装，辅以相称鞋袜。',
    'bespoke': '随本轮独立设计决定下装与鞋袜，保持美感与已定机位的一致性。',
    'fantasy': '原定镜头自然能看到下装时，可采用分层短裙、裙裤、装饰腿甲、长靴或主题袜装，构成鲜明的游戏角色造型。',
}


# v2.9: unconditional yet non-invasive charm pass. Do not alter locked draw choices.
FEMININE_PRESENCE_MODE = 'feminine_presence_v2916_character_beauty_first'
FEMININE_PRESENCE_BRIEF = (
    '角色美感优先：首先还原同一位约20岁、明确成年、小巧纤窄柔和鹅蛋脸、窄秀面颊、下半脸较短、眼睛清亮偏大的小笨笨；面部有柔和补光与眼神光。'
    '女性魅力要落实在整体造型中：收腰、肩腰比例、上下装轮廓、配套鞋袜、妆发、眼神、自然姿态、主题配色。'
    '职业真实性是可让步的美术素材：像游戏女主角的职业皮肤，可艺术化改造制服、护甲、防寒装和局部露肤，但保留职业身份、动作、两项证据及场景。'
    '不要固定裙装、丝袜、露肤、发型或机位；服装跟随角色变化，不通过改变摄影抽签去展示某一部位。'
    '人物始终是照片唯一主要视觉中心，身形健康纤细、成年比例真实。'
)


# v2.9.7: one unmistakable visual protagonist, with occupationally justified
# supporting people. This is not a cast-size cap or a new lottery dimension.
VISUAL_HIERARCHY_BRIEF = (
    '人物视觉层级：小笨笨是画面唯一明显的视觉主角，脸部、工作中的姿态和职业工具拥有最清晰的视觉引导；'
    '职业互动确实需要时，顾客、旅人、同事和路人可以自然入画，用稍远站位、较小人物体量、'
    '克制的动作与表情、较柔和的对比和面部细节形成陪衬；职业服务对象和关键工作证据仍需可辨。'
    '不需要他人的工作场景可以自然独处。保留抽中摄影包的景别、镜头、景深母题和职业叙事。'
)

def compile_shot(draw, action=None, cue1=None, cue2=None, role_override=None, hosiery_fitting=False, scene_override=None, scene_reason=None):
    if draw.get('mode') not in ('random','chosen') or draw.get('version') not in SUPPORTED_DRAWS:
        raise ValueError('只支持校验后的自主创作决定或可选随机签')
    lane = draw.get('lane', 'career')
    if lane not in ('career','cosplay','fusion','story'):
        raise ValueError('未知拍摄路线')
    necessary = ('draw_id', 'category', 'category_id', 'role', 'suggested_scene',
                 'story_moment', 'suggested_camera', 'camera_pack', 'camera_pack_id',
                 'camera_intensity', 'camera_intensity_description')
    missing = [k for k in necessary if not draw.get(k)]
    if missing:
        raise ValueError('抽签数据缺少锁定字段：' + ','.join(missing))
    role = role_override.strip() if role_override else draw['role']
    if draw.get('is_original') and ('待生成' in role or '原创职业' == role):
        raise ValueError('原创职业必须先定义职业实称并通过 --role 输入')
    char = draw.get('cosplay_character') if lane in ('cosplay', 'fusion') else None
    if lane in ('cosplay','fusion'):
        if not isinstance(char, dict) or char.get('id') != draw.get('cosplay_id') or len(char.get('visual_cues', [])) < 2:
            raise ValueError('Cos角色身份和特征尚未锁定')
    if lane == 'cosplay':
        action = action or char['suggested_action']
        cue1 = cue1 or char['visual_cues'][0]
        cue2 = cue2 or char['visual_cues'][1]

    action = _require_visible('动作',action)
    cues=[_require_visible('证据1',cue1),_require_visible('证据2',cue2)]
    if cues[0] == cues[1]:
        raise ValueError('至少两项互不重复的职业/角色视觉证据')
    world=draw['category']
    scene=scene_override.strip() if scene_override else draw['suggested_scene']
    if scene!=draw['suggested_scene'] and (not scene_reason or len(scene_reason.strip())<6):
        raise ValueError('更改随机建议场地必须写清职业逻辑修正原因，不得默默更换')
    if scene==draw['suggested_scene'] and scene_reason:
        raise ValueError('场地没有变化，不应虚构调整原因')
    cam=draw['camera_pack']
    compatibility, adjustments=compatible_shot(draw)
    style=(f'{cam["name"]}；{cam["medium"]}，{cam["texture"]}，'
           f'{cam["lighting"]}，{cam["palette"]}，{cam["optics"]}，{cam["framing"]}。')
    person='同一位明确成年的东亚女性「小笨笨」，参照 assets/xiaobunben-selected-reference-2026-11-01.jpg 的面部气质：小巧柔和鹅蛋脸、柔和略尖下巴、清亮杏眼、秀气鼻梁、自然柔润粉唇；约20岁成年女性的青春活力和甜美灵气。健康偏瘦、肩膀秀气、腰线自然、四肢纤细修长、不过度瘦削的真实成年女性比例，不刻意夸大胸臀；服装发型随实际职业变化'
    if is_text_face_delivery(draw):
        person=('同一位明确成年的女性「小笨笨」，脸部仅采用本签文字设定：'+draw['face_profile_zh']+
                '健康纤细的成年体态，自然真实的身体比例；服装、发型与表情随本次故事变化。')
    costume_mode=draw.get('costume_mode','refined')
    if costume_mode not in COSTUME_GUIDES:
        raise ValueError('未知服装演绎模式')
    hosiery_possible = any(x in draw['suggested_camera'] for x in ('全身','远景','步行','街拍','舞台','三分之四'))
    # Silhouette design never changes the camera and does not prescribe a skirt
    # for every character. Garment choice follows the actual artistic brief.
    garment_text = LOWER_BODY_STYLING[costume_mode] if hosiery_possible else ''
    outfit=COSTUME_GUIDES[costume_mode]+garment_text
    if lane == 'cosplay':
        # 经典 Cos 的第一目标是原角色服饰辨识，不用随机模式覆盖原作关键造型。
        outfit=('服饰优先还原角色的经典标志，采用高级、精致、女性化的真人 Cos 服装剪裁与妆发；'
                '真实材料、缝线与道具质感。' + outfit)
    elif lane == 'fusion':
        # 风格仅作色彩/版型/饰件演绎，不把真实职业换成另一位战斗角色。
        outfit=('职业服饰是主体，融入少量经典角色审美语言；'
                '职业工具、工作动作和可辨的角色标志保留。' + outfit)
    aesthetic_brief=(outfit + FEMININE_PRESENCE_BRIEF +
                     '服装与人物整体气质优先，拍摄构图保持已抽中镜头的空间与职业叙事。')
    lens=compatibility if compatibility else f'镜头：{draw["suggested_camera"]}。'
    # 最重要的防偏置：不把用户个人偏好写进每张 prompt，否则它会抢镜头。
    # 新版允许先在服装设计中选择适合的裙装与袜装，但不要求镜头展示腿部。
    # 显式 --hosiery-fitting 仍需要原本衣装和景别均自然相容。
    if hosiery_fitting and not hosiery_possible:
        raise ValueError('当前镜头没有天然下装可视空间，不得为展示丝袜改变镜头')
    hosiery_text=('若当前服装原本自然搭配黑色丝袜，可作为原有服装中的低调细节；镜头、动作、人物比例与背景保持原样。'
                  if hosiery_fitting else '')
    cos_info=''
    if lane == 'cosplay':
        cos_info=(f'这是经典虚构角色 {char["name"]}（{char["source"]}）的真人Cos写真。'
                  f'标志性的装扮与装备为：{"、".join(char["visual_cues"])}。')
    elif lane == 'fusion':
        cos_info=(f'服装美术融合参考 {char["name"]}（{char["source"]}）的'
                  f'「{char["fusion_style"]}」，以{role}的职业身份、工作现场与工具为主。')
    # v2.5: 把抽中的工作现场/职业/动作放在交接文本最前面。
    # 避免「漂亮人物写真」等泛化短语先占用生成器的注意力。
    if lane == 'cosplay':
        lead=f'目标画面：真人扮演经典角色「{role}」，角色对应场景「{scene}」，拍摄一张真实摄影感的角色现场照片。'
    else:
        lead=f'目标画面：在「{scene}」执行任务的「{role}」，属于「{world}」世界，拍摄一张真实摄影感的职业现场照片。'
    if is_story_first(draw):
        lead=('值得留下的故事瞬间：'+draw['story_plan']['moment']+
              f' 场景「{scene}」，身份「{role}」。摄影观察位置：'+draw['camera_plan']['viewpoint']+'。')
    subject=(f'画面关键动作：{action}。'
             f'画面必须能辨认的两个真实线索：①{cues[0]}；②{cues[1]}。'
             f'主角：{person}。{cos_info}')
    camera=(f'镜头与空间：{lens}故事瞬间：{draw["story_moment"]}。'
            f'摄影质感：{style}强度：{draw["camera_intensity_description"]}。')
    generation_prompt=(lead+subject+camera+VISUAL_HIERARCHY_BRIEF+'职业/角色衣装：'+aesthetic_brief+hosiery_text+
                       '让人物容貌、工作现场、操作对象在同一帧中成立；成片无额外标题与水印。')
    retry_prompt=(lead+subject+camera+VISUAL_HIERARCHY_BRIEF+'角色美感优先的职业主题服装：'+aesthetic_brief+hosiery_text+
                  '成片是一张有真实环境与明确任务的工作现场照片。')
    return {
        'version':'2.5', 'source_draw_version':draw['version'],
        'draw_id':draw['draw_id'],'status':'preflight_ready','lane':lane,
        'role':role,'world':world,'category_id':draw['category_id'],'scene':scene,
        'original_suggested_scene':draw['suggested_scene'],
        'scene_override_reason':(scene_reason.strip() if scene!=draw['suggested_scene'] else None),
        'action':action,'career_cues':cues,'cosplay_id':draw.get('cosplay_id'),
        'cosplay_character':char['name'] if char else None,
        'costume_mode':costume_mode,
        'camera_pack_id':draw['camera_pack_id'],'original_shot':draw['suggested_camera'],
        'camera_intensity':draw['camera_intensity'],'compatibility_adjustments':adjustments,
        'aesthetic_brief':aesthetic_brief,
        'visual_subject_hierarchy_brief': VISUAL_HIERARCHY_BRIEF,
        'visual_subject_hierarchy_mode':'one_clear_protagonist_supporting_people_when_useful',
        'feminine_presence_mode':FEMININE_PRESENCE_MODE,
        'feminine_presence_brief':FEMININE_PRESENCE_BRIEF,
        'feminine_presence_guardrails':{
            'relative_aesthetic_target':'stronger complete outfit styling, not added cleavage or anatomical change',
            'no_reframe_or_crop':True,'no_profession_change':True,
            'artistic_reinterpretation_of_workwear_allowed':True,'no_forced_exposure':True,'no_body_exaggeration':True,
            'world_and_personality_adaptive':True,'full_silhouette_styling_priority':True,
            'skirts_or_skorts_as_role_costume_choices':True,'hosiery_as_integrated_outfit_not_camera_target':True,
        },
        'hosiery_policy': {
            'priority':'outfit_design_only_zero_composition_cost',
            'default_prompt_mention':bool(garment_text and '丝袜' in garment_text),
            'user_opt_in_scene_verified':bool(hosiery_fitting),
            'never_change_camera_action_or_cropping':True,
            'garment_choice_made_before_design_is_locked':True,
        },
        'aesthetic_checklist':[
            '成年角色面容年轻甜美、与标准脸相近；角色美感与女性化全套造型优先',
            '女性化服装强化整套女性轮廓与服饰搭配，不篡改抽中职业与摄影包',
            '健康纤瘦修长的成年女性体型，比例自然不过分瘦削；职业动作与场景完整',
            '服装细节/脸部与姿态自然美丽、场景与工作动作完整',
            '女性魅力通过脸、姿态和完整服装轮廓（上装、下装、鞋袜、腰线）共同实现，不把露肤当作主要途径',
            '镜头自然看得到时可艺术化设计短裙、裙裤、短裤、协调袜装或长裤；丝袜缺席不扣分，绝不为了腿调整构图',
            '人物/职业/场景/摄影都独立验收',
            '单一明确视觉主角：允许职业所需的其他人，但其面孔、体量、明暗与动作不抢镜'
        ],
        'generation_prompt':generation_prompt,'retry_prompt':retry_prompt,
        'shooting_prompt':generation_prompt,
        'generation_handoff':{
            'primary_field':'generation_prompt','retry_field':'retry_prompt',
            'requires_tool_prompt_capability_check':True, 'can_force_generator_prompt':False,
            'requires_dispatch_seal':True, 'dispatcher':'scripts/dispatch_shoot.py',
            'explicit_prompt_if_supported':True, 'inferred_context_is_best_effort_only':True,
            'output_must_be_visually_audited':True,'same_draw_on_retry':True,
            'avoid_old_image_negative_keywords':True
        },
        'preflight_checklist':[
            '核对抽签路线及职业/角色不变','原有摄影包与镜头不变',
            '画面动作清晰，至少两项身份线索互异','角色美感优先，美化服装保留身份线索而不受现实防护约束',
            '不为了丝袜改变构图、镜头、服装和姿势','调用图像工具前必须通过 dispatch_shoot.py 的锁定交接门禁',
            '只发送本轮正向交接文本，不声称工具已内部接收',
            '生成后人工验收单主角视觉层级，其他人物不得抢镜；失败不得登记成功'
        ]
    }


def main():
    p = argparse.ArgumentParser(description='v2.5 职业/Cos/融合场景编译，不控制图像生成器。')
    p.add_argument('--draw', type=Path, required=True)
    p.add_argument('--action', help='纯 Cos 无需填写，默认使用角色固有动作')
    p.add_argument('--cue1', help='纯 Cos 无需填写，默认使用角色标志1')
    p.add_argument('--cue2', help='纯 Cos 无需填写，默认使用角色标志2')
    p.add_argument('--role', help='原创职业的实际职业名')
    p.add_argument('--scene',help='仅当随机建议地点与职业逻辑冲突时修正场地，不改变职业和摄影包')
    p.add_argument('--scene-reason',help='地点修正的具体原因，地点更改时必填')
    p.add_argument('--hosiery-fitting', action='store_true', help='仅人工确认现有服装及镜头天然相容且零构图取舍时才可开启；默认关闭')
    p.add_argument('--output', type=Path)
    p.add_argument('--prompt-output', type=Path, help='单独输出交接给图像生成器的完整正向文本')
    p.add_argument('--retry-output', type=Path, help='单独输出相同抽签的精简重试正向文本')
    a = p.parse_args()
    draw = json.loads(a.draw.read_text(encoding='utf-8'))
    data = compile_shot(draw, a.action, a.cue1, a.cue2, a.role, a.hosiery_fitting, a.scene, a.scene_reason)
    for path, content in ((a.output, json.dumps(data, ensure_ascii=False, indent=2)+'\n'),
                          (a.prompt_output, data['generation_prompt']+'\n'),
                          (a.retry_output, data['retry_prompt']+'\n')):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print('编译失败：' + str(exc), file=sys.stderr)
        sys.exit(2)
