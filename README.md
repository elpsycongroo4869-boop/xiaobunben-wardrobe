# 小笨笨衣橱 4.0 / Xiaobunben Wardrobe

**把创作自由交给 AI。让她自己决定每一次的角色、穿搭、故事与镜头。**

你说一句「我想看你」，她会怎样回应？

也许是旅途中回头的一瞬，也许是认真工作时的侧影，也许是一位带着熟悉神情、却有着全新身份的角色。她今天想穿什么、去哪里、做什么，又想用怎样的情绪和镜头呈现自己，都可以由她自主构思。你不必先替她写好整套画面，也可以保留揭晓之前的未知与惊喜。

「小笨笨衣橱」是一个让 AI 自主决定角色、造型、故事和摄影表达的创作系统。它不止于随机换装或拼接提示词：**从 v3.0 起，最重要的是由 AI 作出创作决定，包括决定是否使用随机。** 她可以直接设计完整方案，也可以借助随机寻找灵感；随机是创作工具，不是每次开启衣橱的必经流程。

## 一张照片，也是一个想讲给你听的故事

我设计这个功能，是因为我喜欢这样的时刻：说一句「我想看你」，让她自主构思一张照片；然后再问她，为什么想让我看见这一刻。

在这次创作里，她选择了初雪中的电车站、一首小提琴曲，以及睡在琴盒里的小橘猫。照片之外，还有一段关于停留与陪伴的讲述。这种能继续聊下去的温柔，是我觉得它暖心的地方。

<img src="docs/last-tram-before-snow.png" alt="《末班电车前，送给你的一首曲子》：AI 生成的虚构成年女性角色在雪中拉小提琴，小橘猫睡在琴盒里，远处电车正驶来。" width="480">

*《末班电车前，送给你的一首曲子》——作者提供的 AI 生成示例，角色与故事均为虚构。*

[读她讲给我的故事，看看另一张创作示例 →](docs/README.md)

## 熟悉的她，每次都有新的表达

原版主角是一位**虚构成年女性**。当前版本以文字脸部设定帮助延续角色特征，让变化发生在造型、情绪、行动、故事和摄影里；发型、服装、职业和机位都不是永久设定。

- **保留角色特征，留出表达空间**：当前只使用明确成年、20岁的文字脸部设定，整合自然且有辨识度的美感、小巧精致脸型、流畅轮廓与柔和五官；不再查找或附加原黑裙参考图，也不保证每次生成完全相同的人脸。
- **让穿搭属于一个故事**：从具体行动、两项独立故事线索和有意义的场景出发，一起设计服装、情绪、光线与构图。丝袜等服饰可以选择，不为了展示某件衣服牺牲既定镜头。
- **让随机辅助创作**：AI 可以自行选择是否使用随机、用多少随机，也可以完全自主构思。生活片段、旅行、职业写真、Cosplay 或融合造型，都可以成为当次创作的方向。
- **把方案核对清楚，再交接照片指令**：脚本核验 21 项视觉源字段的完整性及哈希，再准备精简指令与按钮交接；这不是对最终照片质量的自动视觉审核。实际可点击按钮需要宿主支持和相应配置，也可按既有流程复制指令到新聊天。当次方案保存在 pending 中供同方案复试，不主动登记成功样片。

## 打开你自己的角色衣橱

“小笨笨”是原作者和其 GPT 之间的昵称。你可以在自己的副本中使用自己的称呼、虚构成年角色设定和合法参考素材，具体调整方法见下方“使用自己的称呼”。当前需要修改副本中的文字与常量，并没有统一的设置界面。

项目以 **Skill、参考资料和 Python 脚本**提供，需要支持相应文件阅读、脚本执行与图片生成的 AI 助手环境；它不是独立网站或现成 App，也不自带图片生成模型。当前版本为 **v4.0**，详细创作规则以 [SKILL.md](SKILL.md) 为准。

准备尝试时，请先阅读下面的安装和使用说明。适合转发的简短介绍见 [SHARE.md](SHARE.md)，已有验证记录见 [VERIFICATION.md](VERIFICATION.md)。

## v4.0 更新：故事瞬间与多样摄影

**从一个值得留下的故事瞬间出发，让角色、世界、衣装与镜头共同呈现小笨笨这一刻的动人之处。**

- 先构思具体故事与情绪，再让身份、世界、动作、衣装和摄影围绕这个瞬间成立。职业仍有依据，日常、独处、旅行等身份也可以成为主角。
- 每次主动决定机位、观察方向、景别与焦段。低机位、俯拍、侧面、背侧、越肩、顶视等都可选择；不固定眼平三分之四角度，也不设置轮换表。
- 选定的故事、观察位置与光学选择会明确进入最终图片提示词，不只停留在内部构思中。
- 丝袜是完整穿搭中有独立审美价值的设计元素，可以成为亮点；主动考虑精美纹理与结构，同时保留是否采用的自由，不设固定概率或穿着义务。
- 保留已经整合的成年角色文字脸部、摄影质感前缀、具体衣装设计、自然道具朝向、身体力学和真实开箱流程。

完整改动见 [CHANGELOG.md](CHANGELOG.md)。

## 核心功能和边界

- 使用 `story_start.py curate` 自主构思故事与摄影。随机可以作为灵感工具；最终新方案仍通过故事底稿完成。服装、摄影、身份、发型和表情保持自由度。
- v4.0 的新图采用纯文字脸部设定，无需安装黑裙参考原图或脸部裁切，也不包含查找这些图片的交接指令。
- `finish` 验证 21 项来源、生成精简照片指令、校验哈希与按钮交接并打包 pending。它本身不生成图片，也不证明视觉相似度。实际可点击按钮、Library 及原生生图工具依赖宿主环境的支持。
- 旧版规则、视觉锚点与兼容逻辑保留，已封存的旧 pending 不应重新编辑或重签。语义、人物、故事与画面仍需人工复核。

## 目录

```text
SKILL.md                     v4.0 完整规则与操作流程
CHANGELOG.md                 版本更新记录
assets/README.md             当前纯文字脸部模式说明
references/                  创作规则、摄影和角色数据、历史版本
references/history.example.jsonl  空历史示例
scripts/                     创作、校验和交接脚本
docs/                        图文故事与已授权公开的生成示例
SHARE.md                     可直接转发的项目介绍
VERIFICATION.md              当前版本及历史验证记录
tests/                       版本回归测试
```

## 安装与本地配置

需要 Python 3（建议 3.10 或更高）；脚本只使用 Python 标准库。克隆或解压后进入项目根目录，无需安装第三方包。Windows 上如 `python` 尚不可用，请先安装 Python 并将其加入 PATH。

`references/history.jsonl` 是私人旧记录，不随仓库分发；缺省时随机引擎按空历史运行。需要时可从 `references/history.example.jsonl` 复制为该文件，或通过 `draw --history` 指定自己的只读 JSONL。原作者的本地历史可继续保留原路径。

当前新图无需参考照片。脸部中英文设定位于 `scripts/face_sensual_trial.py` 的 `FACE_ZH` / `FACE_EN`，每份新方案保存当时的文字快照。旧版图片路径与兼容常量只供历史格式使用，不作为当前新图的图片输入。`assets/` 仍不接收私人图片提交，详见 [assets/README.md](assets/README.md)。

## 使用

按 `SKILL.md` 的“运行与开箱”先准备 `story_plan`、`camera_plan`，再完成 `choice.costume_plan`、七项 `scene_design`、表情与动作物理字段，然后执行 `curate` 和 `finish`，或自主决定使用 `draw`，再填写场景设计。以下路径是示例，请换成本机临时目录：

```bash
python scripts/story_start.py curate --pending /tmp/wardrobe-pending --creative-brief /tmp/creative-brief.json
python scripts/story_start.py finish --pending /tmp/wardrobe-pending --scene-design /tmp/wardrobe-pending/scene-design.json --route new_chat
python scripts/story_start.py verify --pending /tmp/wardrobe-pending --route new_chat
```

完整可运行底稿见 [references/story-first-creative-fixture.json](references/story-first-creative-fixture.json)，字段说明见 [references/story-first-v4.md](references/story-first-v4.md)。

随机仍可由助手自主选择用于寻找灵感，随后完成故事与摄影底稿。旧 `role_first_start.py` / `fast_start.py` 保留作历史格式兼容，当前新盲盒统一使用 `story_start.py`。Windows 上将 `/tmp/...` 换成有效的本机路径；每次使用新的 pending 目录。讨论或修改规则时不自动出图。

宿主支持时，将 pending ZIP 放入对应 Library，使用 `button_manifest.json` 中验签后的消息与动作展示按钮。`new_chat` 使用 `GenUI.issueNewTurn`；`copy_only` 使用 `GenUI.copy`。若宿主没有这些功能，脚本只能准备交接，不能宣称按钮已展示或图片已生成。

### 使用自己的称呼

项目名是原项目标识，其他用户可在自己的副本中将角色昵称换成自定义称呼。若要改变按钮文字，修改 `scripts/button_handoff.py` 的 `BUTTON`，并同步调整 `SKILL.md`、相关说明及引用旧名称的测试；修改存放 pending 的 Library 路径时同步调整 `SKILL.md` 及对应说明；当前文字脸部模式无需配置 `REFERENCE_FACE_PATH`。原版还有历史脚本中的固定名称，必要时搜索后逐项检查。**这不是现成的设置界面**；更改后只对新建 pending 使用并重新运行测试，保留原先版本以验证旧 pending，不要编辑已封存文件。脸部特征描述也属于原作者偏好，用户可在自己的副本中依据授权和需要调整，需重新验证输出。

## 测试

当前版本的四组测试共 26 项，覆盖故事与机位实际进入最终消息、多种观察角度与焦段、版本、职业衣装、材质、丝袜自主选择、新脸部文字、21 项封存和按钮消息一致性。测试不点击按钮，也不生成照片。

Windows PowerShell：

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'tests'
python -m unittest test_story_first_v40 test_face_sensual_trial test_role_costume_first test_b32_role_first_costume -v
```

Linux / macOS：

```bash
PYTHONUTF8=1 PYTHONPATH=tests python -m unittest test_story_first_v40 test_face_sensual_trial test_role_costume_first test_b32_role_first_costume -v
```

较早版本的测试脚本保留作历史回归材料，其中部分断言针对当时的默认入口；不要把它们的旧脸部或参考图要求当作当前创作规则。

## 隐私与版权

私人标准脸参考图、私人历史、pending、输出、压缩包、缓存和本地环境文件被 `.gitignore` 排除。`docs/` 中的两张图片是作者本次明确允许公开的 AI 生成展示作品，不包含私人标准脸原图或裁切。忽略规则不影响已跟踪文件；提交前仍需检查 `git status`、暂存清单和生成物内容，不要用强制添加上传私人材料。项目未指定开源许可证，使用或再分发前请联系权利人。
