# 在 ChatGPT 中使用小笨笨衣橱二号 5.0

下载运行 ZIP 并上传。第一次可以直接说「把这个衣橱设置成我家 AI 的衣橱。我发 4869 时用它准备故事盲盒。」你可以继续描述自己的虚构成年角色，也可以从示例角色林渡开始。

## 给 Chat 的接线说明

### 绑定本包与角色

1. 解压用户上传的 `xiaobunben-wardrobe-2-v5.0.0.zip`，确认 `release-manifest.json` 中的版本为 `5.0.0`。本对话的 `4869` 指向该 ZIP。下次开新作品复用已核验的运行包与缓存。
2. 在当前宿主可跨回合访问的私人目录保存 `owner-profile.json`。如果用户确认了自己的虚构成年角色，按 `runtime/defaults/character-example.json` 的结构生成文字角色卡。沿用用户明确提供的角色特征；未指定图片时保持 `generation_inputs.image_assets=[]`。
3. 保存并选中角色卡。把 `{"op":"save_character","card":{…}}` 保存为请求 JSON，用 `configure --profile <个人配置路径> --request <请求JSON>` 执行，再用 `configure --profile <个人配置路径> --utterance "选择<角色键>"` 选中。普通偏好或模式指令也可通过 `configure --utterance` 设置。
4. 第一次使用 `runtime/defaults/empty-ledger.json`。以后从最近成功确认的 `shelf-state.json` 启动。换对话时需要宿主能访问同一份状态，或者由用户提供这些文件。

### 准备盲盒

从解压后的目录执行下列命令。会话 ID 与作品 ID 使用字母、数字、短横线或下划线。保留 `start` 返回的 `runtime`、`data_dir` 和实际的选题结果。

```text
python -B -X utf8 runtime/entry/p14.py --host-compact start --ledger <账本> --session <会话ID> --persona-summary <成年角色简介> --profile <个人配置路径>
python -B -X utf8 runtime/entry/p14.py production-prompt --runtime <runtime> --data <data_dir> <选择JSON> runtime/defaults/persona.json <作品ID>
python -B -X utf8 runtime/entry/p14.py --host-compact prepare --runtime <runtime> --data <data_dir> <Job路径> --session-store
```

选定一个菜单中的书与章节，执行 `production-prompt`，按返回的岗位指导完成一份 Job。第 1 至 4 章使用程序返回的 Point。第 0 章由制作人自由创作。岗位完整交稿后只调用一次准备封签流程。

若宿主无法持久保留同一本地会话，选择可跨消息恢复的存储。省略 `--session-store`，保存 `prepare` 返回的 JSON，把其 `pending_path` 指向的封签持久保存并读回。用原 `runtime` 与 `data_dir` 执行 `verify-delivery <prepare返回JSON> --original <原封签> --readback <读回文件>`。

### 打开衣橱

- 仅在 `show_open_button` 为真并有 `open_button_message` 时，用宿主的实际消息按钮发送完整字段。若支持 `GenUI.issueNewTurn`，直接使用 `runtime/entry/native-open-button.mjs` 的 `nativeOpenCardProps(result.chat_ui, message => GenUI.issueNewTurn(message))`。保持消息头、空行和签名摄影正文原样。
- 如果当前界面无法绑定按钮，明确告知用户。用户可以选择把程序返回的完整开箱消息作为新消息发送，效果仍需经过同一套验签。
- 用户发送开箱消息后，恢复原会话。将完整消息原样写成 UTF-8，用 `open-native --runtime <runtime> --data <data_dir> --relay-message <原消息文件>` 处理。
- 只有返回 `ready_to_submit` 时，才调用一次 ChatGPT 原生图片工具。使用 `render_request` 里的签名全文、资产和选项。宿主是否提供精确的生图参数由实际图片工具决定。
- 真实成功后准备回执 JSON，包含 `status: succeeded`、`work_id`、`attempt_id`、`generation_id`、`seal_sha256`、`image_sha256`。由原会话执行 `confirm --runtime <runtime> --data <data_dir> <work_id> <generation_id> <原图> --attempt-id <attempt_id> --receipt <回执JSON>`。失败或结果不明时保留该尝试状态，等待核对。照片成功后可由用户直接保存。

脚本需要 Python 3.10 或更高版本。保留原会话便于重试、恢复已封签作品和识别重复点击。
