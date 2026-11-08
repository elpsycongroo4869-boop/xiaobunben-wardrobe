# GitHub 版安装与第一次开箱

用随包示例先打开一只盲盒。走完这一步，你就能把示例换成自己的角色和全新故事。

## 1. 下载并检查版本

1. 从 [GitHub Releases](https://github.com/elpsycongroo4869-boop/xiaobunben-wardrobe/releases) 选 `v4.5.0`。在 Assets 中下载 `xiaobunben-wardrobe-v4.5.0-github.zip`，解压到新文件夹。
2. 从 [Python 官网](https://www.python.org/downloads/) 安装 Python 3.10 或更新版本。完整使用流程只需要 Python 标准库。
3. 打开解压后的内层文件夹。看到 `scripts`、`examples` 和 `README.md` 后，Windows 用户可在文件资源管理器地址栏输入 `powershell` 并回车。macOS 和 Linux 用户在终端进入同一个目录。

Windows 在 PowerShell 里运行下面一行。如果本机能用 `python --version`，也可以把全文的 `py -3` 换成 `python`。

```powershell
py -3 scripts/story_start.py --version
```

macOS 和 Linux 把本指南命令开头的 `py -3` 换成 `python3`。版本应显示 `4.5.0`。

## 2. 用示例开第一张图

```powershell
py -3 scripts/story_start.py prepare --profile examples/role-new-woman.json --creative-brief examples/brief-woman.json --pending local/demo
py -3 scripts/story_start.py verify --pending local/demo
```

看到 `"verified": true` 后，在文件资源管理器双击 `local/demo/open.html`。等开箱按钮启用，点「开箱并复制出图指令」，在一个支持图片生成的空白 ChatGPT 对话里粘贴并发送。若浏览器拦下复制，卡片会显示并选中同一份文字，手动复制即可。图片出来后，回到开箱卡展开「创作思路」。

想用已有成年男性 GPT 角色的合成示例做同样的练习，运行下面一行并打开 `local/demo-man/open.html`。

```powershell
py -3 scripts/story_start.py prepare --profile examples/role-existing-gpt-man.json --creative-brief examples/brief-man.json --pending local/demo-man
```

## 3. 换成自己的角色

打开 `local` 文件夹，将 `examples/role-new-woman.json` 或 `examples/role-existing-gpt-man.json` 复制进去，改名 `role.json`。用文本编辑器以 UTF-8 保存。名字换成你喜欢的称呼，年龄填写 18 或以上的整数，`identity`、`appearance`、`build` 用一行英文描述。性格、衣装和审美偏好可以用中文。

如果已经有自己的 GPT，可以先问它「请把我已确认的虚构成年角色整理为简短角色卡，保留姓名、年龄、外貌、体型、性格、穿衣习惯和审美」。将你有权使用的资料填进已有角色模板，保留 `"source": "existing_gpt"`。查看[角色导入说明](../references/role-import.md)，再检查配置：

```powershell
py -3 scripts/story_start.py profile --file local/role.json
```

## 4. 创作、封签，再开箱

1. 运行下方的 `author` 命令，将 `local/author-01.txt` 交给有创作能力的 AI。请它按要求构思一份新底稿，暂缓出图。需要借用灵感时，可先用 `catalog --names` 看六张卡的目录，用 `catalog --card O002` 读卡，再按需要在 `author` 命令后加 `--card O002`。完全原创时，直接运行原命令。
2. 将 AI 返回的 JSON 主体保存为 UTF-8 的 `local/brief-01.json`，去掉 Markdown 代码围栏。继续运行下方的 `prepare` 和 `verify` 命令。
3. 打开 `local/draw-01/open.html`，点击、复制、粘贴并发送。保留生成的封签 ZIP。如果需要以后验证是不是当时保存的原签，再独立记下准备输出的 `manifest_sha256`，验签时用 `--pin` 传入该值。

```powershell
py -3 scripts/story_start.py author --profile local/role.json --output local/author-01.txt
py -3 scripts/story_start.py prepare --profile local/role.json --creative-brief local/brief-01.json --pending local/draw-01
py -3 scripts/story_start.py verify --pending local/draw-01
```

每张新照片换一套编号，例如 `author-02.txt`、`brief-02.json`、`draw-02`。需要原生点击发送的开发者可看[宿主接线说明](INTEGRATION.md)。

## 更新、回退与卸载

- 更新时解压到新目录，先用新版本重跑示例。把自己的角色和世界资料复制过去，历史封签继续保存在原处。
- 如需回退，打开自己保存的正式 v4.4 运行包。v4.4 的封签可以用原验证器，也可从 v4.5 使用 `verify --pending <旧签文件或目录> --legacy-engine <解压后的 v4.4 scripts/story_start.py 路径>` 只读验证。v4.5 的封签继续用 v4.5 验证。
- 卸载前备份 `local/` 的角色和封签，再移除解压目录。

## 常见问题

| 看到什么 | 怎么处理 |
| --- | --- |
| 找不到 `py` 或 `python3` | 先检查 Python 是否安装。Windows 可试 `python --version`，安装后重新打开终端。 |
| 找不到 `scripts/story_start.py` | 在含有 `scripts` 的解压目录打开终端。 |
| JSON、画面约束或长度报错 | 把报错交给创作 AI，让它修正当前未封签的底稿。 |
| 输出目录已存在 | 选择新的 `--pending` 目录。旧封签留作记录。 |
| 开箱卡不能复制 | 使用卡片提供的手动复制栏。 |
| 已复制但还没出图 | 到支持图片的对话粘贴、发送，确认该宿主支持图片生成。 |
| 想少等一会儿 | 可请 AI 直接原创、少查可选资料、删去重复风格要求。创作到一张成片通常约 6 分钟，具体取决于宿主。 |

## 运行测试

```powershell
py -3 -m unittest discover -s tests/current -v
$env:WARDROBE_PYTHON = (py -3 -c "import sys; print(sys.executable)")
node --test tests/current/test_card.mjs
```

macOS 或 Linux 运行 `python3 -m unittest discover -s tests/current -v` 和 `node --test tests/current/test_card.mjs`。Node.js 20+ 仅用于第二组测试，Windows 使用 `WARDROBE_PYTHON` 给它指定实际 Python 路径。
