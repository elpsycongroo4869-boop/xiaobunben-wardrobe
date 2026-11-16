"""Story-driven performance and its versioned render boundary."""
import re

RENDER_POLICY_EMOTION_V1 = 'emotion_v1'

AUTHORING_GUIDANCE = [
    '【制作人】章节 Point 原样继承，自由创作由你决定这一帧必须发生的事。'
    '只有剧情明确需要固定表演时，在 producer.performance_lock 写对象，'
    '含 type="precise_local_action"、instruction（固定行为原文）、source="producer"。'
    '预设章节的 instruction 必须逐字摘自 Point；没有固定要求就省略此字段。'
    '眨媚眼、特定眼睛落泪等明确剧情要求必须锁定；其余具体演绎留给演员。',
    '【场景与服装】scene 设计空间、材质、道具和可见证据；wardrobe 设计完整造型与入镜部分。'
    '沿用故事行为，不编排身体或表情。',
    '【情绪导演】只写 performance.emotional_context。用简洁的演员指导交代角色经历了什么、'
    '知道什么、最在意什么、此刻的感受及变化。可指导放声大哭、开怀大笑或夸张狡黠等整体表演，'
    '强度随故事。将眉眼嘴、泪水路径、头部角度和手指等局部动作留给演员。'
    '无须把锁定要求复写在这里；程序会原样加入最终正文。避免用否定句规定局部动作。',
    '【灯光】只设计光源、方向与效果，照亮既定事件。',
    '【摄影】camera 自主决定机位、景别、构图、主体可见性与有叙事意义的视线关系。'
    'visible_frame 写清关键行为和证据，保留妆发、服装、光影、材质及取景。'
    '情绪的依据和固定表演由程序直接并入摄影正文；摄影可呈现已确定的整体神态，'
    '眉、眼、口、鼻等器官表现及肢体动作由制作人按 Point 锁定或由演员自行演绎。其他岗位不新增动作或器官要求。角色卡的固定外貌由程序补齐。',
]

# A conservative pre-seal guard. Match body part + action in the same short
# phrase, including negated commands, without treating anatomy words as errors.
# Host authoring guidance covers free-form paraphrases beyond these patterns.
LOCAL_DIRECTION = re.compile(
    r'(?:眉(?:毛|梢|头)?|眼(?:睛|皮|球|睑)?|双眸|嘴(?:角|唇|巴)?|唇(?:角|间)?|脸颊|鼻翼|鼻孔|面部肌肉|'
    r'手指|指尖|拇指|食指|头部)'
    r'[^，。；、！？,\n;.!?]{0,9}?'
    r'(?:抬[高起]|微抬|轻抬|挑起|扬起|上[扬挑]|下压|睁[大开]|眯[起眼]|紧闭|闭[合上]|张[开大]|微张|分开|'
    r'抿[紧起]?|咬[住紧]?|微咧|咧开|颤抖|抽动|转动|弯曲|伸出|倾斜|偏转|(?:向|朝)[左右]倾|绷紧|翕动|翕张|扩张|耸动|泛红|涨红|'
    r'(?:自然)?睁开|落泪|流出|滑落|不动)'
    r'|(?:张|撇|努|抿)嘴(?:巴)?|(?:睁大|睁开|闭上)(?:她的|他的)?(?:双|[左右])?眼|(?:抬|挑|皱)眉|眨(?:了(?:一下)?)?(?:一下)?(?:媚|[左右])?眼|闭(?:上)?(?:双|[左右])眼|'
    r'(?:不要|别|禁止|不必|请勿)\s*(?:张嘴|咬唇|抿唇|脸红)|脸红|咬(?:住)?唇|抿唇|'
    r'(?:一滴)?(?:眼泪|泪珠|泪水)[^，。；、！？,\n;.!?]{0,10}(?:从|沿|滑过|流过)[^，。；、！？,\n;.!?]{0,12}(?:眼|颊|脸)|'
    r'(?:从|沿)(?:她的|他的)?[左右]眼[^，。；、！？,\n;.!?]{0,10}(?:流|落|滑)|'
    r'(?:头部|头)[^，。；、！？,\n;.!?]{0,12}(?:\d+|十五|十|五)度|'
    r'(?:\b(?:left|right)\s+(?:eye|eyebrow|brow|cheek|fingers?)\b'
    r'[^,.;!?\n]{0,32}\b(?:close[ds]?|shut|raise[ds]?|lift[eds]*|blink[eds]*|tear[s]?|bend[s]?|curl[s]?|stay[ds]?)\b)|'
    r'\b(?:brows?|eyebrows?|eyes?|lips?|eyelids?|mouth|fingers?|head)\b'
    r'[^,.;!?\n]{0,20}\b(?:raise[ds]?|lift(?:ed|s)?|widen(?:ed|s)?|part(?:ed|s)?|'
    r'open(?:ed|s)?|clos(?:e[ds]?|ing)|squint(?:ed|s)?|purs(?:e[ds]?|ing)|'
    r'curl(?:ed|s)?|tilt(?:ed|s)?|twitch(?:ed|es)?)\b|'
    r'\b(?:wink(?:ed|s|ing)?|bit(?:e[ds]?|ing)\s+(?:(?:her|his|their)\s+)?(?:lower\s+)?lip|'
    r'tear[s]?\s+[^,.;!?\n]{0,28}\b(?:left|right)\s+(?:eye|cheek))\b'
    r'|(?:请|必须|务必|让|要求)(?:她|他|主角|演员)?[^，。；、！？,\n;.!?]{0,8}'
    r'(?:抬头|低头|回头|转头|耸肩|抬手|举手|握拳|屈膝|迈步|伸手|伸指|叉腰|扭腰|转身|蹙眉|张嘴|努嘴)'
    r'|(?:左|右)(?:手|脚|腿|臂|肩)[^，。；、！？,\n;.!?]{0,8}(?:抬起|放在|向前|弯曲|伸出|抬高|收回)'
    r'|\b(?:nostrils? (?:flare|flaring|flared)|(?:must|should|make her|make him)\s+'
    r'(?:tilt|turn|raise|lift|lower|bend|extend)\s+(?:her|his|their)\s+(?:head|hand|arm|leg|finger))\b',
    re.IGNORECASE,
)


def render_performance(job):
    """Validate the authored split and return signed performance text."""
    producer = job['producer']
    roles = job['roles']
    performance = roles['performance']
    if not isinstance(performance, dict) or set(performance) != {'emotional_context'}:
        raise ValueError('emotion_v1 requires roles.performance.emotional_context only')
    context = performance['emotional_context']
    if not isinstance(context, str) or not context.strip():
        raise ValueError('performance.emotional_context must be nonempty text')

    chapter = job.get('chapter') or {}
    preset = chapter.get('id') in (1, 2, 3, 4)
    point = chapter['point'] if preset else producer['moment']
    if not isinstance(point, str) or not point.strip():
        raise ValueError('producer.moment must be nonempty text')
    lock = producer.get('performance_lock')
    instruction = None
    if lock is not None:
        if (not isinstance(lock, dict) or set(lock) != {'type', 'instruction', 'source'}
                or lock['type'] != 'precise_local_action' or lock['source'] != 'producer'
                or not isinstance(lock['instruction'], str) or not lock['instruction'].strip()):
            raise ValueError('invalid producer.performance_lock; use a precise_local_action from producer')
        instruction = lock['instruction']
        if preset and instruction not in point:
            raise ValueError('preset performance_lock must quote the original Point exactly')

    def clauses(text):
        return [part.strip().rstrip('.,，。；！？;') for part in
                re.split(r'[。；！？;\n]|(?<!\d)\.\s+', text)]

    authorized = set(clauses(point))
    if instruction:
        authorized.update(clauses(instruction))
    handoffs = dict(roles)
    if 'role_director' in job:
        handoffs['role_director'] = {'story_fit': job['role_director']['story_fit']}
    for role, handoff in handoffs.items():
        if not isinstance(handoff, dict):
            raise ValueError(f'{role} must be object')
        if 'performance_lock' in handoff:
            raise ValueError(f'{role}.performance_lock is reserved for producer')
        for field, text in handoff.items():
            if not isinstance(text, str):
                continue
            # A verbatim authorized instruction can be quoted, but a different
            # action or negation in that same clause is still a conflict.
            for candidate in clauses(text):
                if candidate in authorized:
                    continue
                if match := LOCAL_DIRECTION.search(candidate):
                    raise ValueError(
                        f'{role}.{field} contains possible unauthorized local performance: {match.group()!r}. '
                        'Rewrite the clause as story context, overall emotion or framing. '
                        'Keep precise required behavior in producer.performance_lock.'
                    )

    lines = ['故事定格 / Story moment: ' + point]
    if instruction and instruction not in point:
        lines.append('制作人固定表演 / Required performance: ' + instruction)
    lines.append('情境与整体表演 / Emotional performance: ' + context.strip())
    return lines
