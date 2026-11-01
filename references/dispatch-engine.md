> **历史文档**：本页记录 v2.5 的实现与失败案例。v2.6 的默认盲盒出图路由以 `references/output-routing.md` 为准，废止默认 `context_inferred` 出图。

# v2.5｜出图交接与触发隔离门禁

## 根因和可证实边界

v2.4 的 2026-10-31 博物馆讲解员抽签与拍摄规格都正确，但两次图片输出成完全无关的卧室女仆/猫耳写真。故障不在概率抽签，而是**提示交接可靠性未得到验证**，加上生成器可能受会话上下文影响。仅凭图片不能证明图像生成器究竟何时在内部形成意图；也不能证明必然受旧图污染。

**关键限制**：目前本会话图片工具没有一个可用于强制指定生成提示词的受支持字段；即使脚本产生了正确文本，也不能证明图像模型内部以它为准。v2.5 能修复**本地校验与触发时序**，但不能承诺修复图像模型的隐式输入机制。

## 唯一执行顺序，杜绝提前启动

1. 读取**最新版** Skill 与 ZIP，不在读文件、抽签和准备阶段调用图片工具。默认运行 `roll_wardrobe.py`；若用户明确要求重试待完成抽签，保留 draw_id，不重抽。
2. 如果随机建议地点与职业明显不合逻辑，可用 `prepare_shoot.py --scene ... --scene-reason ...` 修正场地，并在交接记录中保存原地点与理由，不允许修改职业或摄影包；之后编译完整正向 `generation_prompt` 和 `retry_prompt`。职业与工作现场写在**首句**，接着是动作、两项职业线索，再是镜头与女性化服装审美。更纤瘦体型以一小段普通人物锚点出现，不使其成为场景主题。
3. 运行 `scripts/dispatch_shoot.py --draw DRAW --shoot SHOOT --output handoff.json --prompt-output handoff.txt --capability context_inferred`；它做身份、场景、摄影包、职业证据、提示词一致性校验并给出 SHA256 交接清单。出图前先运行 `--verify handoff.json`；检验失败**禁止调用图片工具**。只有准备就绪才可以启动工具。
4. 检查**当前实际图像工具的正式参数**：若允许明确传入 prompt，把 `handoff.txt` 原文传入；若不允许且只能推断上下文，则在调用前最后一段可见指令中放置完整 `handoff.txt`，直接调用一次生成，不夹杂自我夸奖、旧图讨论或私人照片示例；在记录中把交接能力标为 `context_inferred`、`delivery_confirmed=false`。不能谎称图像工具已使用文件文本。
5. 调用后的验收和失败记录与 v2.4 一样，增加 **体型连续性** 检查。图片“好看”不能替代职业符合。第一次失败仍可使用同一抽签的 `--prompt-kind retry` 封条并验签后重试，即 retry_prompt；第二次严重跑题则停止在本会话重复生成，把原抽签与失败日志留待独立对照。
6. 只有真实图片通过审核、具有可读取的图像文件与 SHA256 后提交成功历史。不把**测试通过**、**交接验签通过**、**图片工具响应成功**等同于内容验收成功。

## 检查表

- 强制调用图片工具必须晚于抽签、编译、验签三件事；抽签前调用即违反流程。
- `handoff.json` 包含锁定 draw_id、角色、地点、镜头及提示词 SHA256；它只是本地防篡改证明，不是图像模型内部提示的读取回执。
- 纯 Cos 保留经典外观辨识；融合保留真实职业，不能改做 Cos 女仆。
- 人物身形保持健康纤瘦，不抢职业动作、构图及场景。
- 必须保留失败记录；失败不消耗成功乱序袋，不凭满意度重新抽签。

## 推荐命令

```bash
python3 scripts/roll_wardrobe.py --history references/history.jsonl --output /tmp/draw.json
python3 scripts/prepare_shoot.py --draw /tmp/draw.json --action '...具体动作...' --cue1 '...线索1...' --cue2 '...线索2...' --output /tmp/shoot.json
python3 scripts/dispatch_shoot.py --draw /tmp/draw.json --shoot /tmp/shoot.json --output /tmp/handoff.json --prompt-output /tmp/handoff.txt --capability context_inferred
python3 scripts/dispatch_shoot.py --verify /tmp/handoff.json
# 以上全部成功后，才调用图片工具。真实审核前不提交成功历史。
```

## v2.5 真实出图冒烟测试（2026-10-31）

- 真随机抽中高铁驾驶员（风雪中的高铁驾驶室，low-fi-security摄影），职业与场景修正、交接指纹检查均通过。
- 当前图像工具仅支持上下文推断交接，无法明确传入受控生成prompt。第一次及同draw_id重试第二次，图片却分别输出上一轮主题的博物馆讲解员。
- 两次均已写入 `pending/2026-10-31-v2.5-smoke-failed/failed-attempts.jsonl`（含实际图片文件SHA256），失败并未计入成功历史。
- 该现象支持“过期主题或跨调用上下文影响”的猜测，但不能断言内部排队或缓存的具体机制。**v2.5 程序前置门禁修复完成，出图正确性未修复成功**。
- 下一轮若继续发生此故障，应优先寻找真正支持显式prompt且可确认输入的图片工具，或在独立对话中用锁定的prompt测试，不能一直靠聊天尾部重说提示。
