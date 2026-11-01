# v2.7 | 原生用户消息按钮，完整版 Skill 零缩写交接

## 要解决什么

用户在新窗口只说「我想看你/打开衣橱」；助手内部完整执行所有随机/去重/角色职业/Cos/摄影/审美/拍摄规格；按钮外不剧透；点击按钮后原样完整的拍摄提示词作为**用户新消息**发出，原生图片生成器负责生成。不可把之前的简化版职业文字作为正式衣橱体验。

## 流程（默认随机模式）

1. 读取最新版 Library Skill 和 ZIP，查找可核查的成功历史；使用程序真随机执行完整规则。失败 pending 的前次抽签不作为成功历史。
2. 核查抽中职业或 Cos 角色、场地可行性，确定可见动作和两项独立职业/角色证据；调用 `prepare_shoot.py`。其 `generation_prompt` 必须完整包含路线/世界、职业/角色、场景、动作、两线索、脸部锚点、镜头、摄影包及强度、故事瞬间、服装美化、画面质量。
3. `dispatch_shoot.py --capability context_inferred` 生成 handoff 并 `--verify`。此 capability 表示原生图片工具本身无可靠显式 prompt 参数；用户消息发送是一条不同的、曾验证可用的交接路径，不等于显式 API。
4. `user_relay.py` 生成 `relay.json` 和 `relay-message.txt` 并 `--verify`。`message` 里的 `full_prompt` 是 `handoff.prompt` 原样文本，不得摘要。不能把在屏幕上显示的短按钮标签当成出图 prompt。
5. 在创建用户按钮前先将抽签四件套放入持续保存的 pending，后续以 `draw_id` 读取，防止跨回合失去验收依据。按钮形式：`<button onClick={() => GenUI.issueNewTurn(完整relay.message)}>打开小笨笨衣橱</button>`。这是表达式示意，实际必须按当前 UI 规范写合法的点击回调，确保使用已验签消息原文。
6. 用户按下按钮后的新的用户消息会**可见**；界面目前不能隐藏这段正文。按钮展开前可做到不剧透，点击后无法保证不剧透；明确这一局限。
7. 收到该用户消息的下一回合，应直接以其详细拍摄内容调用原生生图，不重新理解为“简单居家写真”。随后对真实照片语义验收与图片指纹检查；成功则记账，失败 pending 不消耗乱序袋。无法获取图片文件或无法写入持久记录时，必须诚实声明尚未登记。

## 命令

```bash
python3 scripts/roll_wardrobe.py --history references/history.jsonl --output /tmp/draw.json
python3 scripts/prepare_shoot.py --draw /tmp/draw.json --action '...' --cue1 '...' --cue2 '...' --output /tmp/shoot.json
python3 scripts/dispatch_shoot.py --draw /tmp/draw.json --shoot /tmp/shoot.json --output /tmp/handoff.json --prompt-output /tmp/handoff.txt --capability context_inferred
python3 scripts/dispatch_shoot.py --verify /tmp/handoff.json
python3 scripts/user_relay.py --handoff /tmp/handoff.json --output /tmp/relay.json --message-output /tmp/relay-message.txt
python3 scripts/user_relay.py --verify /tmp/relay.json
```

## 硬性禁令

- 不得随机后由助手凭回忆改写成一个看上去差不多的短提示。
- 不得把简化 prompt 的图片成功当作「完整版 Skill 已全功能通过」。
- 不得在按钮之前剧透抽签，或把没有调用过的用户按钮说成已经生成照片。
- 不得为获得较高生图成功率而更换抽中的角色、地点、摄影包。
- 不得把屏幕上的短提示或 hash 交给原生图像工具，并假装模型知道隐藏内容；**必须发送实际全文**。
- 图片生成不合格、不具真实图片指纹、或持久历史未写成功，均不得报告成功登记。


## v2.9.4 最新优先规则

在新建空白聊天首次触发衣橱时，必须先真正显示标签**「打开小笨笨衣橱」**的可点击控件；完整英文用户消息由 `photo_creation_relay.py` 编译、`button_handoff.py --route new_chat` 封存，点击后 `GenUI.issueNewTurn(full_user_message)`。只有按钮真的出现，才算第一关成功；不能跳过按钮自己直接生图。

已有照片/失败尝试的长对话则使用同名按钮配 `button_handoff.py --route copy_only`，点击只执行 `GenUI.copy(full_user_message)`；必须说明要在新空白聊天粘贴发送才能出图。不要让 `copy` 与 `issueNewTurn` 混用，也不要提前把英文全文剧透。最新 21 项正向照片描述以 `photo_creation_relay.py` 为准，而非本文件早期的简化用户消息模板。
