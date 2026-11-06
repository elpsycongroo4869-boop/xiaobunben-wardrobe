# 职业衣装先成立：字段与检查

本轮先确定环境与身份，再完成衣装基础和女性化改造。不要从既有的亚麻上衣、短裙或其他模板反推职业。

## 创作计划

完整可运行底稿见 `references/role-costume-first-creative-fixture.json`。它用于核对原有字段、摄影结构和新衣装计划的格式；实际盲盒仍自行重新构思，不把示例骑士或它的衣装当作默认。

在原 creative brief 的 choice 中加入：

```json
{
  "costume_plan": {
    "context_and_climate": "A sheltered castle gate at the end of a cool evening patrol.",
    "role_foundation": "The knight wears articulated metal armor secured with leather straps; these features establish her identity.",
    "material_anchors": ["steel", "leather"],
    "construction_anchors": ["articulated pauldrons", "segmented tassets"],
    "feminine_adaptation": "A fitted armor waist and asymmetric tassets shape her silhouette; a small side opening follows the armor panels."
  }
}
```

相应 scene_design.wardrobe 可以写：

`Etched steel cuirass with a fitted waist, articulated pauldrons, leather straps, asymmetric segmented tassets and a narrow side opening; fitted dark undersuit.`

此为说明格式，不是默认角色、材质、开口或固定穿搭。科幻、Cos、现代制服和日常衣装也各自建立依据；不需要有盔甲。
锚点只是这一次可见衣装的保真检查，不是证明职业正确的词库。程序不能判断金属、皮革、某个制服结构是否适合角色，仍需人工审阅。

## 保持自由与完整性

- 冬季、雨天、夜晚、室内等先自主选择，再设计适合当下的衣装与魅力；没有天气出现配额。
- 女性化改造可大胆，保留这套衣服的职业结构和材质语言；不追加胸部尺寸或强调程度的控制。
- 新提示词不用魅力评分或露肤百分比，直接写本套服装的剪裁、线条与材质设计。
- 材料不设白名单或禁令；亚麻可以使用，但不是跨职业通用起点。
- 服装只写入镜部分。不要求完整服装、丝袜或鞋子出镜，也不为凑锚点改变景别。
- 角色外观、动作、两条线索、情绪、表情、物理支点、摄影和道具朝向沿用现行规则。
- 情绪基调在 choice.emotion_tone 中先确定，再设计具体动作和 expression，最后统合画面。
- 总提示词超限时先删重复说明；衣装字段可以用到 280 字符，不得丢掉所选材料与结构。
- 摄影的 texture/palette 若提及衣料，同步检查是否与本次衣装一致。

## 新入口与旧签兼容

当前新创作用 scripts/role_first_start.py，默认启用角色衣装计划。
内部仍使用 fast_start.py 的成熟封存与按钮内核；历史函数和旧版本消息分支保留，不重写已封存提示词。
计划、修订标记与 21 项底稿共同封存。新规则既存在于说明里，也实际进入 Outfit 的构造与交接检查。

仅做文字试跑不证明照片审美达标。真正开启时仍先给按钮，点击后才生成。
