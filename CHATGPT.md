# 在 ChatGPT 中使用小笨笨衣橱二号 5.0

## 安装和第一次开箱

1. 在 [GitHub 最新发布](https://github.com/elpsycongroo4869-boop/xiaobunben-wardrobe/releases/latest) 的 **Assets** 下载带版本号的运行 ZIP，上传到能读取附件、运行 Python 和原生生图的 ChatGPT 对话。
2. 发送下面这段。把「月桂钥匙」换成你自己的咒语，建议选不常出现在日常聊天里的词。

   > 把这个衣橱设置成我家 AI 的衣橱。用我确认的虚构成年角色；如果我还没设定角色，先用包里的示例角色林渡。把「月桂钥匙」设为本对话的启动咒语。以后我单独发送这个咒语，就用这份运行包准备照片盲盒，等我开箱再生图。

3. 等 ChatGPT 回报运行版本、角色、当前模式和绑定的咒语。单独发送咒语，等封签准备好后点「打开衣橱」。如果当前对话无法提供真实按钮，可发送它给出的完整验签开箱消息。
4. 照片成功生成后，在 ChatGPT 里保存原图。换对话时重新绑定咒语，并带上运行包和需要延续的角色卡、偏好配置与账本。

## 更换咒语、角色和模式

- **更换咒语。** 说「把衣橱咒语改成『琥珀衣匣』」。以后单独发送新咒语即可准备盲盒。
- **选择主角。** 可以说「用我保存的成年角色林渡」，也可以描述一个新的虚构成年主角。文字角色卡就能使用。
- **更换穿搭模式。** 「打开擦边模式」会为后续作品生成一张横排三格的穿搭图。「关闭擦边模式」恢复一张完整的电影写真。加「这次」可只对下一份新作品生效。已封签作品保留原模式。
- **告诉岗位你的偏好。** 例如「服装以后偏复古」「情绪导演以后偏克制」。下一轮创作会结合故事使用这些偏好。

## 给 Chat 的接线说明

### 绑定本包与角色

1. 解压用户上传的运行 ZIP，从 `release-manifest.json` 读取真实版本和入口。把用户明确约定的咒语绑定到该包，并在确认读取后回报版本、角色、模式与咒语。仅在用户把约定咒语作为整条消息发送时，复用当前已核验的包和缓存，执行下文「准备盲盒」。聊天里提及咒语以及更换咒语的请求只按其原意处理。咒语绑定由当前对话负责，换对话时重新约定。
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
- 只有返回 `ready_to_submit` 时，才调用一次 ChatGPT 原生图片工具。按 `native_image_instruction` 新建图像，使用 `render_request` 中已验签的全文、资产和选项。画面里出现的照片、相纸、画作或屏幕属于场景道具。签内 `image_assets` 为空时，直接从文字生成。
- 这段操作说明与签名摄影正文分开。工具有明确的生成方式和 prompt 字段时，选择新建，并把 `render_request.text` 原样交给 prompt。仅支持从聊天上下文生成时，在交接处明确这是新画面，继续保留完整原文。实际派发由宿主处理。
- 真实成功后准备回执 JSON，包含 `status: succeeded`、`work_id`、`attempt_id`、`generation_id`、`seal_sha256`、`image_sha256`。由原会话执行 `confirm --runtime <runtime> --data <data_dir> <work_id> <generation_id> <原图> --attempt-id <attempt_id> --receipt <回执JSON>`。失败或结果不明时保留该尝试状态，等待核对。照片成功后可由用户直接保存。

脚本需要 Python 3.10 或更高版本。保留原会话便于重试、恢复已封签作品和识别重复点击。
