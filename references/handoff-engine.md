# 衣橱 2.3｜独立出图交接层（针对连续串片）

## 已知故障与边界

2026-10-31 一次真实 v2.2 抽签锁定为「武侠江湖／游方女医侠／竹林山道／梦核朦胧镜头」，`prepare_shoot.py` 正确生成完整文字，图像工具却连续返回现代办公室角色照。**它证明：正确的抽签与规格不保证最终图片符合。** 无法仅凭现象断言根因是对话记忆、图片工具内部提示或者历史图污染。

2.3 修改的是编译、**交接路径**、失败留痕和提交门禁，不改变图像模型，不保证彻底解决。

## 强制流程

1. 若用户要求全新随机出图，先读取成功历史、执行 `roll_wardrobe.py`，再锁定职业与摄影包；若用户要求「重试刚才那张」，读取 `pending/2026-10-31-locked-draw.json`，**不要重新抽签**。
2. 确定实际工作动作、两项清晰职业证据；运行 `prepare_shoot.py`，优先将 `generation_prompt` 导出为独立 TXT 文件。此字段是**纯正向提示**，从目标场景、职业、动作、职业证据、摄影风格构成，不要补充过去错图的关键词。
3. 交接给生成器：如果图像工具允许显式传入提示文本，按其正式接口交付 `generation_prompt`；如果工具只能从当前会话推断、不能显式传递提示，**在调用前最后一段可见话中完整、清楚地描述本轮目标画面**，并承认无法验证实际内部提示。不把“脚本已经编译”误当“工具已经收到/照办”。如果可生成独立会话，优先在无旧图干扰的上下文内做对照，但也不能保证有效。
4. 图像生成后**人工验收**：世界/时代、地点、职业、具体行动、两项可见线索、摄影包、成年同一人；另将 `outfit_role_match`（职业装真实安全）与 `portrait_aesthetic_match`（人物写真美感）分别判断。外观很美不代替职业匹配，职业匹配也不应掩盖人物视觉失衡。
5. 第一次偏离时写失败日志，**沿用相同 draw_id**，用 `retry_prompt` 调整正向措辞（不重抽职业或风格）。若已连续两次严重跑题，停止在本会话继续反复调用图像工具，保留锁定 draw、shoot 和失败记录，建议在独立新对话重试同一套规格。
6. 仅对真正成功的照片创建人工验收 JSON（手工目视后）。至少包含 `image_file` 真实可读取路径、与文件一致的 `image_sha256`、原来的各项真值判断；`roll_wardrobe.py --commit --audit-file ...` 核验图片存在性和 SHA256，但**不自动判断语义是否正确**。
7. 失败日志 `scripts/log_attempt.py` 只写 `failed-attempts.jsonl`，不会占用16类/24摄影包乱序袋，绝对不当做成功照片历史。ZIP 内记录不会自动回写跨会话的用户 Library。

## 出图提示的三个隔离规则

- **只谈要生成的目标**：交接给图像生成器的 `generation_prompt` 里不写旧图职业、错误地点、上一张情节，也不写否定式的“不要某某旧照片”。失败分析只在日志里。
- **突出工作现场**：至少两个具体职业物件/迹象进入画面，人物工作动作明确。不能只出现一个漂亮人物和象征性的办公桌。
- **唯一真相源**：图像生成时使用 `shoot.json` 的 `generation_prompt`；失败后使用 `retry_prompt`；不自行用“想象中的美照”重写职业/场景/滤镜。

## 示例命令

```bash
python3 scripts/prepare_shoot.py --draw pending/2026-10-31-locked-draw.json \
  --action '刚为樵夫包扎，半跪石阶边记录伤情与草药配伍' \
  --cue1 '打开的木质随身药箱、草药和绷带' \
  --cue2 '纸质诊簿、毛笔和樵夫包扎好的手臂' \
  --output /tmp/shoot.json --prompt-output /tmp/prompt.txt --retry-output /tmp/retry.txt

python3 scripts/log_attempt.py --draw pending/2026-10-31-locked-draw.json \
  --shoot /tmp/shoot.json --image /tmp/actual-image.png \
  --reason '人工验收发现世界和职业不符' --observed-scene '实际错误场景' \
  --history /tmp/failed-attempts.jsonl
```

真实图片验收成功后，获取图片 `sha256sum /tmp/actual-image.png`，在审核 JSON 中提供：

```json
{
  "draw_id": "以draw.json真实ID为准",
  "image_file": "/tmp/actual-image.png",
  "image_sha256": "图片文件计算得到的64位SHA256值",
  "image_exists": true,
  "world_match": true,
  "role_match": true,
  "action_visible": true,
  "career_cues_visible": 2,
  "photography_match": true,
  "continuity_match": true,
  "outfit_role_match": true,
  "portrait_aesthetic_match": true
}
```

**不要为未检查的图填 true。** 若生成器的图片不能以文件路径提供给当前脚本，就不执行程序式成功登记，不虚构证明。

## v2.3.1 兼容说明

抽签版本与概率仍为2.3，`prepare_shoot.py` 编译版本为2.3.1；新的人工成功登记要求职业服饰真实性、人物写真美感独立验收。以前已经记录成功的历史不追溯改写。

## v2.5 修订

旧版“图片工具调用前写一句拍摄说明”只作为上下文推断型接口的**尽力方案**，不能保证工具已接收。v2.5 出图前必须先由 `dispatch_shoot.py` 生成和验证 SHA256 封条；详见 `references/dispatch-engine.md`。
