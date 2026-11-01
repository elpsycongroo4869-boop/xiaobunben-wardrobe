# 小笨笨衣橱 / Xiaobunben Wardrobe v3.5

一个面向成年虚构角色的创作工作流：由助手自主构思角色、故事、服装和摄影，也可以自行选择使用旧随机引擎。它将七项场景设计编译为 21 项视觉审查字段，封存哈希，并准备照片生成指令及按钮交接。v3.5 是本仓库的稳定基线；详细规则以 [SKILL.md](SKILL.md) 为准。

“小笨笨”是原作者和其 GPT 之间的昵称，其他用户可用自己的称呼。当前代码仍保留原名称以兼容原版交接和历史签名；个性化步骤见下文。

## 这个项目能做什么？

你可以只说一句“我想看你”，让助手自己决定这一次呈现什么：一个生活瞬间、一套角色穿搭、一段旅行小故事，也可以是职业写真、Cosplay 或融合造型。固定角色的面部方向，服装、发型、表情、场景和摄影继续自由变化。原版主角是虚构成年东亚女性。

- **助手自主创作**：可以直接构思，也可以选择随机辅助；不会把每次创作都锁进强制抽签。
- **完整的角色和故事**：除了穿搭，还有具体行动、两项独立故事线索和有意义的场景。
- **标准脸连续性**：优先尝试查阅用户自己的授权参考图，无法读图时使用文字锚点近似；不保证像素级同脸。
- **穿搭与摄影一起设计**：保持整体人物美感；丝袜等服饰可选，不为了某件衣服改变既定镜头。
- **21 项视觉字段核验**：核对人物、环境、行动、服装、镜头、光线等提示词来源与完整性，再生成简明照片指令；不会自动识别最终图片内容。
- **保留惊喜的按钮交接**：支持宿主中的一个开启按钮；点击后才发送完整照片指令。也可复制到干净的新聊天。
- **保留方案用于复试**：pending 保存当次方案和哈希，方便同方案重试；不主动登记成功样片。

它以 Skill、参考资料和 Python 脚本的形式提供，适合支持文件阅读、Python 执行和图片生成的 AI 助手环境。它没有独立网页界面，也不自带生图服务。面向朋友分享的短介绍见 [SHARE.md](SHARE.md)，本次验证记录见 [VERIFICATION.md](VERIFICATION.md)。

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
