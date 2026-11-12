"""Generate compact, explicit instructions for the current host AI.

P1 does not call any model. This is a bridge for a future ChatGPT host adapter.
"""
import json
from pathlib import Path
from studio import Studio, read_json
from preference_router import route_preferences

HERE = Path(__file__).resolve().parent

SIGNATURE_SCENE = (
    '本卡标志定格作为本轮核心。以当前成年主角演绎卡中的角色原型，保留标志动作和画面因果。'
    '取景、光线、衣装与非关键环境按这一帧自由设计。'
)

SHARED_CINEMA = (
    'Cinematography craft: choose a camera position for the real story moment; decide lens feel, framing, '
    'depth, occlusion and layers intentionally. Establish physically meaningful source/direction/softness of '
    'light and plausible face, fabric, metal and glass response. Use light for narrative, not generic adjectives. '
    'The character acts for her/his own story, not to display clothes or props to a camera. '
    'Keep the complete outfit separately from what will be visible. The camera controls the final frame.'
)


def selection_prompt(studio: Studio, persona_summary: str, now) -> str:
    """One read, one producer choice; no entire history and no frequency leaderboard."""
    entries = studio.menu(now)['available_entries']
    lines = ['- ' + v['id'] + ' ' + v['title'] + '：' + v.get('hook', '') for v in entries]
    return '\n'.join([
        '# 小笨笨衣橱二号 · 制作人一次选题',
        '本次 AI 角色：' + persona_summary,
        '请先观察这一次可用的世界书架，认真选一项你此刻真正想拍的内容。',
        '原创与世界书都在同一份候选目录；不设置历史次数排行榜，不要求优先选未去过的世界。',
        '仅从此处可用目录选一个；不要提出多套候选，不要反复推翻选择。',
        '已经有具体且明确的原创灵感时允许以 autonomous_spontaneous 表达，并说明具体想法。',
        '输出仅一份 JSON：{"origin":"autonomous_library|autonomous_original|autonomous_spontaneous",'
        '"book_id":"B010或null", "initial_intent":"本次想拍什么"}。',
        '\n'.join(lines),
    ])


def production_prompt(selection: dict, persona: dict, work_id: str, *,
                      world_card_dir: Path | None = None,
                      compact_character_draft=False, emotion_only=False,
                      selected_book=None, chapter=None) -> str:
    """One selected book's complete details (if any) + professional responsibilities."""
    origin = selection['origin']; book_id = selection.get('book_id')
    world_lines = ['本次为原创，没有需要照搬的世界卡。']
    if origin == 'autonomous_library':
        # Only a selected fixed world needs the 102-book reference text.
        # Original/spontaneous work must keep its creative prompt unchanged,
        # while avoiding an unnecessary filesystem fetch on the host path.
        if selected_book is not None:
            book = selected_book
        elif world_card_dir is not None:
            # Optional bookshelf path: read only the chosen card; preserve the
            # original JSON dict and exact prompt bytes, including key order.
            from bookshelf_nav import load_selected_card
            book = load_selected_card(book_id, Path(world_card_dir).parent)
        else:
            library = read_json(HERE / 'world_library.json')
            book = next((v for v in library['entries'] if v['id'] == book_id), None)
        if book is None:
            raise ValueError('unknown fixed world')
        if chapter is None:
            world_lines = ['选中世界书的详细知识：' + json.dumps(book, ensure_ascii=False)]
            if book.get('signature_scene'):
                world_lines.append(SIGNATURE_SCENE)
        else:
            world_lines = [f"选中世界《{book['title']}》：{book['world_logic']}"]
            if chapter['id'] == 0:
                world_lines.append('第 0 章自由创作。' + book.get('open_possibilities', ''))
            else:
                world_lines.append(f"第 {chapter['id']} 章《{chapter['title']}》Point：{chapter['point']}")
            if book.get('wardrobe_anchor'):
                world_lines.append('书卡衣装：' + book['wardrobe_anchor'])
        if book.get('wardrobe_anchor'):
            world_lines.append(
                '服装岗位把本卡的衣类、剪裁和关键材质做成这轮造型的特点。'
                '若本轮采用三格，保留衣类与文化辨识度，通过叠穿、搭配和合身程度变化。'
            )
    routed = route_preferences(persona)
    if emotion_only:
        routed.pop('performance')
    directed = ['- '+role+': '+'；'.join(notes) for role,notes in routed.items() if notes]
    if routed['performance.expression']:
        directed.append('performance.expression 的偏好用于内心反应，优先回应事件并继承制作人指定的关键表情。')
    public_persona = {k:v for k,v in persona.items() if k != 'preferences'}
    if emotion_only:
        responsibilities = [
            '必要的故事行为只由章节 Point 或自由创作的制作人 Point 决定。具体站姿、步态与四肢配合交给演员自然演绎。',
            'scene 设计空间、材质、道具及可见证据；wardrobe 设计完整造型与入镜服装。两岗均不安排人物动作。',
            '【情绪导演】只写 performance.expression，用准确自然的语言交代内心、情绪层次和面部反应。'
            '继承 Point 指定的表情。禁止指导动作、视线方向、姿势、手脚和道具操作。',
            'lighting 只设计光源、方向与效果，照亮既定事件。',
            '【摄影定稿】camera 自主取景，将 Point 的关键行为、道具接触与可见证据拍清；不新增姿势、动作或道具操作。',
            'camera.visible_frame 只写最终可见画面，情绪的来由留在创作笔记。关键证据拍不清就调整取景。'
            '程序会注入角色卡，摄影不得复述固定姓名、年龄、五官或体态；'
            '可写本轮发型、妆容、表情、造型及光线如何落在脸上。',
        ]
    else:
        responsibilities = [
            'scene 决定世界空间/材质/道具；wardrobe 决定完整造型与镜头可见造型（不要求全拍到）；'
            'performance 承接必要行为与人物内心；lighting 依据场景、材质和表演做真实布光；camera 自由决定取景。',
        ]
    performance_fields = 'expression' if emotion_only else 'action,expression'
    return '\n'.join([
        '# 小笨笨衣橱二号 · 一个故事的完整深化',
        f'work_id: {work_id}',
        f'origin: {origin} / book_id: {book_id}',
        '当前成年角色设定：' + json.dumps(public_persona, ensure_ascii=False),
        '书卡里的主角称谓按本轮已选成年角色自然适配，保留职业、世界设定和关键事件。',
        '制作人的创作起点：' + selection['initial_intent'],
        *world_lines,
        ('制作人直接按章节 Point 分发任务，可补少量创意，保留核心事件、必要行为与可见证据。'
         if chapter and chapter['id'] else
         '一次先确立真正想表达的故事事实：何时何地、发生了什么、主角为何在乎、哪一个瞬间值得拍。'),
        '随后按专业责任内部组织一个连续的创作过程。不是六次模型/API调用：',
        *responsibilities,
        SHARED_CINEMA,
        '岗位专用偏好（只能由对应岗位读取，不能反向控制选题）：' + ('\n'.join(directed) if directed else '无'),
        '不因长期审美偏好反向决定世界，不给任何单品设置固定入镜义务；用户偏好只传给相关岗位。',
        '不要使用一次额外的审片专家或选题回退循环。场景、造型、动作、光源、机位必须服务同一故事。',
        '仅输出一份结构化 JSON job，字段为 work_id/origin/book_id/persona/producer/roles。',
        ('persona 只需写 adult=true 和本轮职业或处境 story_role。程序从选定角色卡补入稳定身份与外貌。'
         if compact_character_draft else
         'persona 的 identity/appearance 沿用本轮角色设定，职业身份写入 story_role。'),
        ('预设第 1–4 章：producer 只需 {\"visual_decisions\":\"本轮确实新增且会影响画面的决定\"}，'
         '没有新增决定可用 {}。勿重述五栏，也不要重写既定 Point；程序从本次封存章节自动补入完整 producer，'
         '并将 Point 原文作为 producer.moment。摄影视角、造型、光线与演员仍要充分创作。'
         if chapter and chapter['id'] != 0 else 'producer 字段: intent/context/event/moment/emotion。'),
        'roles 字段: scene{plan,props}, wardrobe{full_outfit,visible_outfit}, '
        f'performance{{{performance_fields}}}, lighting{{plan}}, camera{{plan,visible_frame}}。'
        '如果是原创，加 event_signature（简短、具体的故事事件）。',
        '不确定的专业设计由本次故事主动选择，不要照抄示例。不要复制整个知识库到输出。',
    ])
