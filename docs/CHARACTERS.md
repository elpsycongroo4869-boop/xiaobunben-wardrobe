# 角色卡 · 创建、导入与更换

角色卡为同一位虚构成年主角保留文字身份、外貌和气质。故事、职业、衣装、妆发和摄影方案仍然可以随作品变化。

## 直接在 ChatGPT 里设置

| 想做什么 | 可以发给 Chat 的话 |
| --- | --- |
| 创建并使用一位新主角 | 「建一张角色卡。沈桥是 32 岁的虚构成年男性，短卷发、深棕眼睛、鼻梁有淡雀斑，气质沉静。保留这些辨识点，职业和穿搭随故事变化。请用这张卡作为以后衣橱的主角。」 |
| 导入已有的角色卡 | 上传文字或 JSON，然后说「把这份设定保存为衣橱角色卡，命名为沈桥，设为以后使用的角色。让我核对固定特征。」 |
| 切到已保存角色 | 「换成我保存的沈桥」 |
| 只为下一份作品换人 | 「这次换成我保存的沈桥」 |
| 回到默认示例 | 「恢复默认角色」 |
| 调整一张已保存的卡 | 「只把沈桥卡里的发型改为直短发，保留其余设定。更新这张卡。」 |

新建或导入后，等 Chat 确认角色名称、固定特征与使用范围，再发启动咒语。如果有两张同名卡，用 Chat 提供的角色键来选。临时换角需要先保存该角色。恢复默认后会使用包内成年示例角色「林渡」，已保存的自定义角色仍可选。

角色配置在开始准备新作品时固定。若当前已有待开箱作品，换角会作用于下一份新盲盒。想保留配置到别的对话，可以请 Chat 导出自己的 `owner-profile.json`，或保留单张角色卡 JSON 以便重新导入。前者含已保存角色与个人偏好，适合私人使用。书籍冷却另存在账本里。

## 一张卡需要写什么

| 内容 | 字段 | 怎么填 |
| --- | --- | --- |
| 格式与身份来源 | `schema`、`identity_source`、`adult` | 分别为 `wardrobe2-character-card-v1`、`text_profile`、`true`。 |
| 角色键与名称 | `character_key`、`display_name` | 角色键用字母、数字、短横线或下划线，例如 `shen-qiao`。显示名称可以用中文。 |
| 人物与外貌 | `identity`、`appearance` | 写虚构成年身份、外貌辨识点和整体气质。 |
| 哪些特征跨作品保留 | `continuity`、`stable_traits` | 一句连续性说明，加上固定特征列表，例如雀斑、眼睛颜色。 |
| 哪些特征可以随故事改变 | `flexible_traits` | 列出职业、服装、发型等由你决定可变化的特征。 |
| 参考图资产 | `generation_inputs.image_assets` | 只使用文字时填 `[]`。如需参考图，资产必须是本轮宿主能访问且你明确指定的图片。 |

[下载或查看包内示例角色卡](../runtime/defaults/character-example.json)

## 给维护者和 Chat 的操作方式

把确认好的卡包在 `{"op":"save_character","card":{…}}` 中，保存为 `save-character.json`，再执行保存与选择。更新同一角色沿用原角色键，创建另一个角色时用新键。

```text
python -B -X utf8 runtime/entry/p14.py configure --profile owner-profile.json --request save-character.json
python -B -X utf8 runtime/entry/p14.py configure --profile owner-profile.json --utterance "选择shen-qiao"
python -B -X utf8 runtime/entry/p14.py configure --profile owner-profile.json --utterance "恢复默认角色"
```

第三条是日后切回示例角色时才执行的命令。长期选择后，后续 `start` 使用同一份 `--profile owner-profile.json`。只换一次时，用 `configure --utterance "这次换成shen-qiao"` 核对覆盖项，再在下一次 `start` 传入 `--this-time "这次换成shen-qiao"`，并同时传入同一个配置路径。临时选择会随该轮固定，长期角色设置继续沿用。

[回到安装和开箱说明](../CHATGPT.md)
