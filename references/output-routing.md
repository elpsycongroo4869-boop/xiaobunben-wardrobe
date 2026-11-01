> v2.7 更新：原生一键用户消息按钮交接见 `native-user-relay.md`。这是新验证的默认 ChatGPT 路线；下述 v2.6 Figma/Adobe 为需要额外许可的显式 API 备选。

# v2.6 | 真随机盲盒照片：显式 Prompt 路由与防剧透执行合同

## 新发现与边界

2026-10-31 连续发生「正确抽签/正确文本，却输出其他职业照片」事故。原生图像接口只暴露不受控/废弃的 `prompt` 字段，无法保证文字原样传入；故推断原因尚不明，不能声称是历史照片缓存或系统优先听取用户简短口令。v2.6 **修复路由流程，而不是证明图像模型绝不会跑题**。

## 盲盒默认操作（新增强制要求）

1. **收到了“想看你/启动衣橱”** → 仅在内部加载最新版 Skill 和 ZIP，确定没有显式指定职业/风格，执行真随机抽签、去重、规格编译、正向提示准备、SHA256 封条验证。默认只抽一签，失败保留该签。
2. **用户界面防剧透**：不得在图片成功展现前，发送职业、角色、场景、摄影包、衣服、完整正向提示；也不展示抽签表格、封条内容、技术性的详细过程。允许一句不泄密的确认/进度。工具后台参数正常包含完整提示，不能为防剧透而删除必要词。出图成功可先给图，再在用户有兴趣时讨论拍摄身份。
3. **显式路由优先**：先核对工具当前参数规格，不凭传闻推断。首选可在 `prompt` 参数中直接传入文本的 **Figma `generate_image` + `gpt-image-2.5-sunburst`**（不代表画质已实测）；另一条可用的是 Adobe Firefly `image_generate`，但其 `prompt` <=1500 字符，用户此前不喜欢 Adobe 成片，不得为了凑字数悄悄截断提示。工具必须能实际调用且具有相应账号/文件权限。
4. **费用门禁**：Figma `generate_image` 会消耗 Figma AI credits；Adobe 也可能消耗 Firefly credits。每次实际调用前，确认用户已针对该次调用明确同意可能扣除积分；如果无同意，则不要调用，询问一次是否允许。Figma 必须有用户可编辑的真实 Figma Design 文件 `fileKey`；若没有，先依据 Figma 技能指导创建新文件，需要先取得用户同意。保存 fileKey 方便后续复用，但不要捏造或将用户文件可访问性假定为永久。
5. **程序封条**：`dispatch_shoot.py --capability explicit_prompt` 封存 `handoff.json`。`image_route.py --handoff ... --backend figma_gpt --figma-file-key <真实key> --paid-approved --output ...` 创建精确调用参数绑定，执行 `image_route.py --verify ...` 校验；必须严格把计划 `args` 原样传给工具，不允许绕过计划自写一句“漂亮女孩”。本地指纹只证明准备阶段参数没被改动，不证明接口接受、传输完成或生成符合目标。
6. **不具备显式工具时采用 v2.7 用户消息按钮路线**：禁止助手直接调用 `context_inferred` 图片工具作为无声降级；按 `native-user-relay.md` 将完整生成指令原样绑定到可点击用户消息按钮。若按钮不支持，停止，不显示错误图片；不能把简化提示词当作完整版。
7. **真正出图后验收**：仍需检查职业/场景、行动、两个身份线索、摄影包、镜头、人物连续性、服装合理性、肖像质量；失败记入 pending，不算成功，不消耗乱序袋。连续两次显著跑题停止，而不是无限重试。成功方可记录实际图片文件、SHA256、审核 JSON 并 commit 历史。第三方返回“success=true”≠图片语义验收成功。
8. **发布方式**：Figma 生成结果放在 Figma 文件，工具如提供内联预览或可用图片 URL，优先让用户直接看照片，再附原文件链接。若 Figma 不能直接内联展示或接口无权限，坦诚说明，避免假称已经在聊天直接交付图片。

## 模式之间保持隔离

默认随机职业/纯Cos/融合抽签概率与全部乱序袋都完全不变；挑战模式明确标识，不占随机名额。人物不强制丝袜，真实工作场景高于审美附加项。

## 例子：前置操作

```bash
python3 scripts/roll_wardrobe.py --history references/history.jsonl --output /tmp/draw.json
python3 scripts/prepare_shoot.py --draw /tmp/draw.json --action '...' --cue1 '...' --cue2 '...' --output /tmp/shoot.json
python3 scripts/dispatch_shoot.py --draw /tmp/draw.json --shoot /tmp/shoot.json --output /tmp/handoff.json --prompt-output /tmp/handoff.txt --capability explicit_prompt
python3 scripts/dispatch_shoot.py --verify /tmp/handoff.json
# 以下需要当前回合用户明确允许使用付费积分、真实 fileKey
python3 scripts/image_route.py --handoff /tmp/handoff.json --backend figma_gpt --figma-file-key <REAL_KEY> --paid-approved --output /tmp/route.json
python3 scripts/image_route.py --verify /tmp/route.json
# 再按 route.json 的 tool_name + args 调用相应 connector，验收图片后才允许提交。
```

## 注意事项

- 本仓库不是自动连接、自动安装或自动切换图像模型的插件；实际出图取决于可调用工具、权限及费用授权。
- Figma `gpt-image-2.5-sunburst` 是当前工具声明的可选模型，不声称与 ChatGPT 原生图像生成的内部执行完全相同。
- 上一轮未成功的「城市无人机飞手」抽签与错图记录在 `pending/2026-10-31-v2.5-live-failed-b4e444b4/`，不进入成功历史。
