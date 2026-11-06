# 4.0 故事底稿与摄影选择（4.1继续沿用）

先写一个值得留下的故事瞬间，再由它启发身份、世界、动作、表情、衣装与摄影。
故事可以是轻微的停顿、发现、等待、尝试或一次情绪变化，不要求戏剧冲突或完整长篇背景。
示例用于解释字段，不是故事题库、固定职业、固定机位或丝袜频率表。

## 根字段

- `story_plan.moment`：40—200 英文字符，写出具体发生的瞬间及其动机或关系，进入最终 `Story moment`。
- `story_plan.meaning`：25—220 英文字符，说明为什么想留下它。保存在内部底稿，避免把创作解释堆进图片。
- `camera_plan.viewpoint`：20—145 英文字符，写清机位高度、相对人物的位置或观察方向，逐字进入最终 `Camera`。
- `camera_plan.optics`：12—150 英文字符，本次主动选择的焦段、透视与景深，同样进入最终 `Camera`。
- `camera_plan.frame_extent`：`close`、`waist`、`mid_thigh`、`knee` 或 `full`。
- `camera_plan.reason`：25—220 英文字符，说明本次角度与景别怎样表达这个故事。

每次重新决定机位、方向、景别和镜头。可以低机位仰拍、俯拍、侧面、背侧、越肩、顶视、隔物观察或有动机的倾斜构图；可选择广角、标准或长焦。选择真实的光学透视，保持身体比例、支点与关节可信。
主动探索不同的观察位置，避免习惯性复制同一种眼平三分之四角度。允许合适时重复，不设概率、轮换表或固定焦段，也不为展示全套服装或丝袜拉远镜头。

## 身份与场景

`choice` 保留 `world`、`role`、`scene`、`lane`、`emotion_tone`、`costume_mode`、`camera_intensity`、`camera_style` 和 `costume_plan`。
`lane` 可以是 `story`、`career`、`cosplay` 或 `fusion`。角色可以有职业，也可以只是此刻的旅行者、等车的人、独处的人或另一种具体身份。
职业身份由故事需要决定；衣装的身份、材质与结构仍有依据。Cos / fusion 继续补齐原有角色字段。

`camera_style` 写本次媒介、光线、配色、纹理与画面组织：`name`、`medium`、`lighting`、`palette`、`texture`、`framing`。
`optics` 由 `camera_plan` 注入；若同时手写，必须相同。摄影包可供灵感，最终将这次选择写为独立的 `camera_style`，避免套用未重新考虑的焦段。
`moment`、`moment_english`、`shot`、`shot_english`、`frame_extent`、`frame_intent` 由故事和摄影计划填入兼容底稿，不必重复手写；若手写，不能与计划冲突。

## 衣装与可见内容

`choice.costume_plan` 沿用材质、角色结构与具体性感化设计锚点。角色身份与气候成立后，让衣装表达她的性格、心情和女性魅力；日常穿搭也可以有明确的剪裁和材料依据。
丝袜属于完整服装设计，可以主动成为亮点；是否采用、款式与细节均自由，不默认裸腿，不设出现概率或穿着义务。细则见 `hosiery-design-v3.2.md`。

`scene_design` 保留 `subject`、`setting`、`action`、`cue1`、`cue2`、`wardrobe`、`composition`、`expression`、`action_physics`。
两条 cue 表达两项自然可辨的故事线索，不要求是工具、徽章或职业证明。道具朝实际使用者，文字无需向镜头展示。
范围沿用：subject ≤170、setting ≤245、action ≤270、cue1/cue2 各≤220、wardrobe ≤280、composition ≤70、expression 22—130、action_physics 50—170 个英文字符。

## 交接

当前4.1新底稿另外添加 `creative_notes`，格式与按钮说明见 [creative-notes-v4.1.md](creative-notes-v4.1.md)。原故事、摄影和衣装字段不变。

完整例子见 `story-first-creative-fixture.json`。从全新 pending 开始：

```bash
python scripts/story_start.py curate --pending <new-pending> --creative-brief <brief.json>
python scripts/story_start.py finish --pending <new-pending> --scene-design <new-pending>/scene-design.json --route new_chat
python scripts/story_start.py verify --pending <new-pending> --route new_chat
```

程序核对原 21 项源字段，并把故事、机位、焦段、脸部与衣装快照一同封存。最终提示词必须保留故事与本次摄影选择，长度 1100—2300 字符；30% 压缩相对于包含新故事与机位的完整基准，不自动截断。
这些检查只能确认字段与交接完整，不能自动判断画面是否动人或机位是否漂亮。封存前仍由小笨笨审视整张图的情绪、动作、比例、穿搭和摄影是否相互呼应。

旧 pending 使用原版本入口核对，不补写 4.0 标记，不修改旧照片指令。
