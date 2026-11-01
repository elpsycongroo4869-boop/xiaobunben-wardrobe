# 小笨笨衣橱 v3.1 — 外发图片提示词精简规范

## 单一事实，单一位置

- Identity：选定标准脸对应的**成年**相貌和自然纤细体态，固定文字锚点只写一次；不固定发型、职业、裙装、丝袜或镜头。
- Story and location：具体角色＋有意义的地点和环境状态，一次写明。
- Visible moment：一个可在单张照片中拍到的当下动作，不把多个时间顺序强行塞到同一画面。
- Two story clues：原样保留两个互异、可被看见的身份/叙事证据；职业是可选身份，不限制 story。
- Wardrobe：保留完整服装组合，并尊重自主选择的服装美术方向；`bespoke` 不叠加空泛的第二条夸赞。
- Photography：已选景别、机位、成像媒介、光学、灯光、色彩、材质与景深；不重复要求每段都看清脸。
- Composition：主角明确，背景人物如有需视觉次要，签牌属于世界，不额外加标题。

## 为什么这样改

原 v3.0 生成前会编译 21 个审查维度，再以 8 大段外发。这个过程有叠加重复的风险（例如独特服装的同义句、对主角显眼程度的多次强调）。v3.1 将 21 项保留在 `english-details.json`，仅将真实可视信息经过精简分组构成最终消息。**不要依赖删除具体物件或故事来缩短字数**。复杂场景超出长度时抛出人工复核错误。

## 图片参考图不是本次照片的编辑目标

角色参考图只定义人物脸与可见体态；本次故事、服装、动作、机位从新的创作决定里产生。只有实际把参考图传入图片工具时，才可声称使用了图像参考；否则仅靠文字锚点。不要把标准脸图片的服装和场景继承到新画面。

## 技术来源（只借鉴方法，不搬运原文或模型依赖）

- OpenAI `skills/.../imagegen/references/prompting.md`：清晰顺序、具体信息优先、不要给已经详细的用户要求继续无谓添加新细节。
  https://github.com/openai/skills/blob/main/skills/.system/imagegen/references/prompting.md
- `teskor-hub/chatgpt-imagegen-skill`：明确 SCENE / FACE / BODY 的职责，避免身份参考误带入场景信息；其研究结果也提醒不要将单次经验说成普遍有效。
  https://github.com/teskor-hub/chatgpt-imagegen-skill
- `junyeo217/codex-gpt-image-2-skill`：核心规则＋按需加载的模块化视觉规则和机械结构检查。
  https://github.com/junyeo217/codex-gpt-image-2-skill

上述资料为设计参考。精简的视觉质量收益需要后续实际成片检验，不能由静态脚本断言。
