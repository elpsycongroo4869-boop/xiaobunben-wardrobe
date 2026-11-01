# v2.9 · English blind-box relay (native ChatGPT, full-fidelity)

## Intended user interaction

User: “亲爱的，我想看你 / 打开小笨笨衣橱.” Assistant must **actually execute** the installed ZIP Python engine, not improvise a career from remembered prose. It obtains a cryptographically identified draw/shoot/handoff and composes a faithful full-length **English** visual specification. User first sees only the button “打开小笨笨衣橱.” When tapped, the complete English prompt is submitted as a **visible user message** and is likely to be read as a direct image-generation instruction; then the image is generated and audited. The English text is not hidden technically; its difficulty is only a practical visual spoiler barrier, and the subject may be decipherable in English.

## Mandatory execution order

1. Read latest Library SKILL.md and ZIP. Prefer the newest persistent Library `/小笨笨衣橱/history.jsonl` over bundled `references/history.jsonl` when accessible; no guessing missing history.
2. `roll_wardrobe.py --history ... --output ...` with the real random source. Read real `draw_id`, `lane`, `role`, `scene`, `camera_pack`, `shot`, `moment`, `intensity`, `costume_mode`, and optional cosplay and original-career constraints.
3. Confirm scene/action are occupationally plausible. `prepare_shoot.py --draw ... --action ... --cue1 ... --cue2 ... --output ...` and manually validate sources and two independent visible cues.
4. `dispatch_shoot.py --draw ... --shoot ... --output ... --prompt-output ... --capability context_inferred`; then `--verify`. Inference capability is honest for the native image tool; this relay does not grant a true explicit tool prompt.
5. Translate **all 21 sections** of the generated shot to English faithfully in a structured `english-details.json`, bound to `draw_id` + source prompt SHA256 and five locked random dimensions (including feminine_presence_mode). Include the original character/face/body silhouette anchor and all camera-pack properties, not a new aesthetic guess. For cosplay/fusion, role and costume sections should also express the original character's visual cues and allowed fusion style. The outline is a checklist, not permission to alter the subject.
6. `english_relay.py --handoff ... --english-details ... --output ... --message-output ...`, then `english_relay.py --verify ...`. The verifier checks all sections, locked random dimensions and hashes, and message integrity. **It cannot judge semantic equivalence in translation**; manually proofread sections against `shoot.json` and the original full prompt.
7. Before displaying button, save a pending ZIP of the actual draw/shoot/handoff/translation/relay records in Library `/小笨笨衣橱/pending/`, without exposing the subject in its filename. Do not log success.
8. Give only a neutral spoiler-free `<button onClick={() => GenUI.issueNewTurn(full_english_message)}>打开小笨笨衣橱</button>`. The message text must equal the verified `english_full_prompt` **exactly**; do not replace it with placeholder/status or a short version. On click the full text becomes a visible user message: do not lie about UI ability to hide it.
9. After the next turn and actual image generation, visually audit its identity, setting, tools, action, photograph and woman. Use actual image bytes and SHA256; commit success only if verified and persistent. Failure stays pending and does not consume draw bags.

## Language and image labels


Writing instructions in English must **not** force the scene's in-world lettering into English. Add a scenario-grounded statement: historic Chinese work can display historically appropriate Chinese inscriptions; other worlds should follow their own diegetic writing, not English by default. Text labels are incidental. No additional captions, poster typography or watermarks.

## Distinctions

- Having a working Python script ≠ the library SKILL.md self-executes on its own.
- Hash matches and complete fields ≠ semantically perfect English translation or guaranteed visual compliance.
- Button displayed ≠ button clicked, image generated or history committed.
- An English prompt after click is visible; it preserves *some* surprise for this user, not secrecy. Full hiding requires a separate backend/UI or different tool route.

## v2.9 mandatory 21st section: Feminine presence

The relay's `feminine_presence` must translate `shoot.feminine_presence_brief` faithfully and specifically: expressive gaze, character-appropriate expression, subtle grooming, believable garment tailoring and body line, face lighting and photographic three-dimensionality. Aim for an approximately 20–30% **subjective lift in natural feminine appeal**, not a 20–30% anatomical change or skin exposure. Never reframe, enlarge the subject, change the locked lens, or displace occupational tools. Do not force flirtation, eye contact or smiles when the character is working. Required JSON field `feminine_presence_mode` must equal the compiled shot mode.

## v2.9.1 NEW-IMAGE ROUTING: generator prompt and audit are separate

- In the *user-level message* sent to native image generation, state unequivocally at the beginning that the user is creating **one entirely new photograph from scratch**. Keep the full 21 compiled visual fields; never drop occupational details, natural feminine presence, costume mode or photography.
- Do not include internal success registration, fingerprint auditing, retry instructions, file paths or draw identifiers in the image-generation message. They are workflow metadata, stored separately in Library pending records and run **after** a genuine new image is produced. Do not instruct the image tool to write history.
- The generator may infer edit mode from conversation image attachments even on a new-image task. This is a hypothesis, not a proven root cause. If the native tool again misclassifies the request, preserve the same draw, mark failed, and offer a fresh-window retry with the same *verified* complete prompt. Do not claim a software-level fix of image tool routing.
- First verify in a fresh chat when possible, with no image uploaded as a reference. The user should only say “启动小笨笨衣橱，沿用待重试抽签” and the assistant should fetch the latest pending record from Library rather than re-roll. The English button text is still visible after click; neither a button nor its user message can be automatically transferred into a newly opened chat.


## v2.9.2 · Isolation by a completely new chat (default for failed old-thread retries)

The old v2.9.1 button uses `GenUI.issueNewTurn`, which remains in the *same* conversation and thus cannot clear any image attachment context. We have no confirmed visibility into the image generator's classification. Instead, use `scripts/isolated_relay.py` to seal a portable, fully faithful 21-section copyable user prompt from the already existing draw. After local verification, show a spoiler-free button with `GenUI.copy(verified_english_message)`. The user creates a truly empty new chat and pastes the complete English text there as a user message; this is not an image edit request. This workflow cannot auto-open a new chat and is not an image-generation success claim. Preserve pending until the actual picture and audit are complete. No modification to the 21 visual field values is permitted.

## v2.9.7 Single visual protagonist, natural supporting cast

In the final 21-field `photo_creation_relay.py` message, the original `composition` text is followed by a positive visual-hierarchy instruction; this is not a new 22nd field. The heroine's face and working gesture remain the main focus. Patients, pilgrims, clients, colleagues and passersby may appear where the scene benefits from them, at quieter secondary visual scale and contrast. Do not sacrifice occupational interaction, existing lens/camera package, or source-bound career evidence. The 21 source fields remain sealed and unmodified; `photo-creation-message` and its derived SHA256 change for this new delivery revision, so regenerate manifests rather than using a stale `button_manifest.json`.

## v2.9.8 当前覆盖规则：完整内部21字段，约半长的最终出图消息

严格区分验签用21项 `english-details.json` **完整源规格** 和按钮真正发送的 `photo-creation-message.txt` **精简指令**。两者都必须存在，前者通过 `english_relay.py` 验签，后者通过 `photo_creation_relay.py --verify`、`button_handoff.py --verify` 校验。当前按钮发送完整的**精简指令**，不是原21项英文段落逐字拼接；不能在按钮回调现场再缩写。外部景别/动作/两项证据/世界和随机服装摄影仍需逐项人工核对，若丢失重要事实不得过关。输出长度目标约3,800—7,300字符。女性化制服描述允许职业合理的局部露锁骨、肩、上背、腰侧，随锁定的服装模式调整；健康纤细成年女性、必要防护与工作功能必须保留。提示词缩短可能改善识别但不是已验证的因果证明。


## v2.9.10 8 组短英文交接 + 用户选定成年面容锚点

21 项 `english-details.json` 完整源和哈希、随机签、拍摄规格、摄影包依旧完整保留。`photo_creation_relay.py` 读齐 21 项后，最终递送的英文消息压缩为 8 组自然语义段，字符门禁 **2,350—3,950**（以实测成功手动精简文本为参照，而非宣称长度与生成成败有因果保证）。职业世界、具体工作动作、两项独立职业证据、摄影包核心媒介/镜头/光线、画内文字与单主角视觉层级必须人工检查。引入 `assets/xiaobunben-selected-reference-2026-11-01.jpg` 的统一成年年轻女性脸/身形文字锚点，并落实主观女性魅力约 +50%；保持职业/服装模式、随机镜头优先。所有新按钮必须生成并验签该**短报文**，不能重新发旧 21 段长文。
