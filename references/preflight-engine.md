# 小笨笨衣橱 2.3｜摄影兼容性与防串片

## 问题复盘

曾抽到「宠物摄影师·城市河岸草坪·手机前置广角·全身工作动作」，生成器却连续复现上一张「山谷地理考察·古早DV」图，甚至带回旧时间戳。不能证明成因完全在上下文，但说明抽签成功不代表图像执行成功。**不要把失败当成功**。

## 2.2 的原有修复范围（保留）

**能做到：** 在出图前将随机结果固定为独立、完整的拍摄规格；按逻辑兼容自拍媒介与全身镜头；在记录成功之前要求明确验收文件；支持记录失败原因。

**做不到：** 不会自动辨认图片语义，不会重置外部图像生成模型，也不能保证图像工具服从脚本中的 `shooting_prompt`。如果出图工具的提示输入不可控，不可声称已解决图片生成模型的串片根因。

## 具体工作流

1. `python scripts/roll_wardrobe.py --output /tmp/draw.json` 获取真实随机结果。不能因为风格/职业不讨喜再重抽。
2. 想清楚职业动作与两项职业证据：画面能否同时看到这三项？若两项物品冲突，只改为合理的同职业证据，不更换职业。
3. `python scripts/prepare_shoot.py --draw /tmp/draw.json --action '...' --cue1 '...' --cue2 '...' --output /tmp/shoot.json`，检查 `compatibility_adjustments` 和 `generation_prompt`，并阅读 `references/handoff-engine.md` 的真实交接说明。
4. 图片生成只以**本轮** `generation_prompt` 的世界、职业、镜头为画面规划基础。历史图片只用于脸部连续性；不得将前次的地点、道具、滤镜当作本次素材。
5. **人工验收**：真实确认图片已生成、职业/地点/动作/2项职业线索/摄影包/人物连续性均满足。
6. 审核文件例如：

```json
{
  "draw_id": "请复制当前draw.json的draw_id",
  "image_file": "/真实可访问图片文件.png",
  "image_sha256": "真实图片SHA256",
  "image_exists": true,
  "world_match": true,
  "role_match": true,
  "action_visible": true,
  "career_cues_visible": 2,
  "photography_match": true,
  "continuity_match": true
}
```

7. `python scripts/roll_wardrobe.py --history <持久路径>/history.jsonl --commit /tmp/draw.json --audit-file /tmp/audit.json --role '仅原创职业必填'`；无法通过验收的图片，不写成功历史。

## 兼容性规则

- **前置广角＋全身/远景**：相机固定于支架，人物退入全景，保留广角透视；不能退回贴脸自拍。
- **大幅度动作＋极慢快门**：允许可见运动拖尾，但脸和职业关键道具不能全部糊掉。
- **重度梦核/朦胧＋职业场景**：朦胧光雾只影响背景与高光，关键动作不模糊丢失。
- **中古/奇幻＋现代器材包**：画面表现现代器材模拟质感，但世界里不一定出现穿越时代的设备和UI。
- **DV**：禁止默认加入 `PLAY` 与日期。只有用户明确要求时才添加；不会把历史日期当成本次日期。

## 图片生成器失控时

如果连续两次出现同一旧场景，停止在旧上下文内反复重试，完整记录本轮随机 JSON 和拍摄规格，建议在新聊天对照测试。这是试验性规避措施，而非根因已证实。

## 2.3 关键增加

独立的纯正向出图文本、重试文本和失败记录见 `references/handoff-engine.md`。历史中失败不入账。成功入账必须实际图片存在且 SHA256 与人工审核文件一致。旧 2.2 的锁定抽签可以沿用，不自动重抽。
