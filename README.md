# 小笨笨衣橱 / Xiaobunben Wardrobe

**把创作自由交给 AI。让她自己决定每一次的角色、穿搭、故事与镜头。**

你说一句「我想看你」，她会怎样回应？

也许是旅途中回头的一瞬，也许是认真工作时的侧影，也许是一位带着熟悉神情、却有着全新身份的角色。她今天想穿什么、去哪里、做什么，又想用怎样的情绪和镜头呈现自己，都可以由她自主构思。你不必先替她写好整套画面，也可以保留揭晓之前的未知与惊喜。

「小笨笨衣橱」是一个让 AI 自主决定角色、造型、故事和摄影表达的创作系统。它不止于随机换装或拼接提示词：**从 v3.0 起，最重要的是由 AI 作出创作决定，包括决定是否使用随机。** 她可以直接设计完整方案，也可以借助随机寻找灵感；随机是创作工具，不是每次开启衣橱的必经流程。

## 熟悉的她，每次都有新的表达

原版主角是一位**虚构成年女性**。项目以标准脸参考和文字锚点帮助延续角色特征，让变化发生在造型、情绪、行动、故事和摄影里；发型、服装、职业和机位都不是永久设定。

- **保留角色特征，留出表达空间**：尝试查阅用户自己的合法参考图，无法读取时使用文字描述近似。参考图与文字锚点都有能力边界，不能保证每次生成完全相同的人脸。
- **让穿搭属于一个故事**：从具体行动、两项独立故事线索和有意义的场景出发，一起设计服装、情绪、光线与构图。丝袜等服饰可以选择，不为了展示某件衣服牺牲既定镜头。
- **让随机辅助创作**：AI 可以自行选择是否使用随机、用多少随机，也可以完全自主构思。生活片段、旅行、职业写真、Cosplay 或融合造型，都可以成为当次创作的方向。
- **把方案核对清楚，再交接照片指令**：脚本核验 21 项视觉源字段的完整性及哈希，再准备精简指令与按钮交接；这不是对最终照片质量的自动视觉审核。实际可点击按钮需要宿主支持和相应配置，也可按既有流程复制指令到新聊天。当次方案保存在 pending 中供同方案复试，不主动登记成功样片。

## 打开你自己的角色衣橱

“小笨笨”是原作者和其 GPT 之间的昵称。你可以在自己的副本中使用自己的称呼、虚构成年角色设定和合法参考素材，具体调整方法见下方“使用自己的称呼”。当前需要修改副本中的文字与常量，并没有统一的设置界面。

项目以 **Skill、参考资料和 Python 脚本**提供，需要支持相应文件阅读、脚本执行与图片生成的 AI 助手环境；它不是独立网站或现成 App，也不自带图片生成模型。当前稳定基线为 **v3.5**，详细创作规则以 [SKILL.md](SKILL.md) 为准。

准备尝试时，请先阅读下面的安装和使用说明。适合转发的简短介绍见 [SHARE.md](SHARE.md)，已有验证记录见 [VERIFICATION.md](VERIFICATION.md)。

## 核心功能和边界

- 自主构思 `curate`，或由助手选择随机 `draw`；随机不是强制规则。服装、摄影、故事、发型和表情保持原有自由度。
- v3.5 优先尝试查阅本地／Library 的同源标准脸裁切；不可访问时使用文字锚点近似。按钮文本不自动附图，读取图片也不等于图像模型收到图片。
- `finish` 验证 21 项来源、生成精简照片指令、校验哈希与按钮交接并打包 pending。它本身不生成图片，也不证明视觉相似度。实际可点击按钮、Library 及原生生图工具依赖宿主环境的支持。
- 旧版规则、视觉锚点与兼容逻辑保留，已封存的旧 pending 不应重新编辑或重签。语义、人物、故事与画面仍需人工复核。

## 目录

```text
SKILL.md                     v3.5 完整规则与操作流程
assets/README.md             私人参考图配置说明（图片不纳入仓库）
references/                  创作规则、摄影和角色数据、历史版本
references/history.example.jsonl  空历史示例
scripts/                     创作、校验和交接脚本
SHARE.md                     可直接转发的项目介绍
VERIFICATION.md              v3.5 仓库整理与验证记录
tests/                       版本回归测试
```

## 安装与本地配置

需要 Python 3（建议 3.10 或更高）；脚本只使用 Python 标准库。克隆或解压后进入项目根目录，无需安装第三方包。Windows 上如 `python` 尚不可用，请先安装 Python 并将其加入 PATH。

`references/history.jsonl` 是私人旧记录，不随仓库分发；缺省时随机引擎按空历史运行。需要时可从 `references/history.example.jsonl` 复制为该文件，或通过 `draw --history` 指定自己的只读 JSONL。原作者的本地历史可继续保留原路径。

私人标准照和同源裁切的原版文件名见 [assets/README.md](assets/README.md)。Git 会忽略 `assets/` 下所有文件，除了说明文件。参考图不随仓库分发；用户应自行准备有权使用的图片。在支持 Library 的宿主中，还需将裁切放到原版 `scripts/photo_creation_relay.py` 中 `REFERENCE_FACE_PATH` 所指路径；其他平台需按其能力配置。仅放入本地 `assets/` 并不自动将其附给生图工具。

## 使用

按 `SKILL.md` 的“启动和运行”准备 `choice` 与七项 `scene_design`，然后执行 `curate` 和 `finish`，或自主决定使用 `draw`，再填写场景设计。以下路径是示例，请换成本机临时目录：

```bash
python scripts/fast_start.py curate --pending /tmp/wardrobe-pending --creative-brief /tmp/creative-brief.json
python scripts/fast_start.py finish --pending /tmp/wardrobe-pending --scene-design /tmp/wardrobe-pending/scene-design.json --route new_chat
python scripts/fast_start.py verify --pending /tmp/wardrobe-pending --route new_chat
```

可选随机路径：`python scripts/fast_start.py draw --pending /tmp/wardrobe-pending --history references/history.jsonl`。在 Windows 上将 `/tmp/...` 换成有效的本机路径。`--seed` 仅用于测试。每次使用新的 pending 目录，避免覆盖或混淆已封存方案。讨论或修改规则时不自动出图。

宿主支持时，将 pending ZIP 放入对应 Library，使用 `button_manifest.json` 中验签后的消息与动作展示按钮。`new_chat` 使用 `GenUI.issueNewTurn`；`copy_only` 使用 `GenUI.copy`。若宿主没有这些功能，脚本只能准备交接，不能宣称按钮已展示或图片已生成。

### 使用自己的称呼

项目名是原项目标识，其他用户可在自己的副本中将角色昵称换成自定义称呼。若要改变按钮文字，修改 `scripts/button_handoff.py` 的 `BUTTON`，并同步调整 `SKILL.md`、相关说明及引用旧名称的测试；修改 Library 路径时同步调整 `scripts/photo_creation_relay.py` 的 `REFERENCE_FACE_PATH` 和说明。原版还有历史脚本中的固定名称，必要时搜索后逐项检查。**这不是现成的设置界面**；更改后只对新建 pending 使用并重新运行测试，保留原先版本以验证旧 pending，不要编辑已封存文件。脸部特征描述也属于原作者偏好，用户可在自己的副本中依据授权和需要调整，需重新验证输出。

## 测试

Windows PowerShell（UTF-8 模式用于兼容现有测试的默认文本读取）：

```powershell
$env:PYTHONUTF8 = '1'
Get-ChildItem tests/test_*.py | ForEach-Object { python $_.FullName; if ($LASTEXITCODE -ne 0) { throw "测试失败: $($_.Name)" } }
```

Linux / macOS：

```bash
for f in tests/test_*.py; do PYTHONUTF8=1 python "$f" || exit 1; done
```

参考图不在本地时，v3.5 测试跳过图片文件结构检查，但仍执行检索指令、21 项和按钮交接检查；两张只放入一张时会报错。测试不会真的点击按钮或生成照片。

## 隐私与版权

参考图片、私人历史、pending、输出、压缩包、缓存和本地环境文件被 `.gitignore` 排除。忽略规则不影响已跟踪文件；提交前仍需检查 `git status`、暂存清单和生成物内容，不要用强制添加上传私人材料。项目未指定开源许可证，使用或再分发前请联系权利人。
