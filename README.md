# 小笨笨衣橱二号 · 5.0

只说一句 `4869`，让你的 AI 为自己的成年角色挑一个世界，构思一段故事，再拍下最值得记住的那一帧。照片会在你亲手打开衣橱之后生成。

[下载 5.0 正式运行包](https://github.com/elpsycongroo4869-boop/xiaobunben-wardrobe/releases/tag/v5.0.0) · [在 ChatGPT 中使用](CHATGPT.md)

## 看看衣橱拍下的故事

<table>
<tr>
<td width="50%"><img src="docs/gallery/01-midnight-ticket.png" alt="夜站里，女孩拿起剪了心形孔的车票"><br>夜站的心形票</td>
<td width="50%"><img src="docs/gallery/02-nest-in-the-wall.png" alt="阳光下，修墙人发现墙缝里的两只幼鸟"><br>墙缝里的幼鸟</td>
</tr>
<tr>
<td width="50%"><img src="docs/gallery/03-lighthouse.png" alt="风雨后的塔楼里，女孩检修灯塔透镜"><br>灯塔透镜旁</td>
<td width="50%"><img src="docs/gallery/04-outfit-triptych.png" alt="夕照中的驿站，同一位主角的三格穿搭"><br>同一场故事，三种穿搭</td>
</tr>
</table>

## 第一次使用

1. 下载 Release 里的运行 ZIP，上传到支持文件读取、Python 执行和原生图片生成的 ChatGPT 对话。
2. 对 Chat 说 **「把这个衣橱设置成我家 AI 的衣橱，使用我确认的虚构成年角色。以后我发 4869，就用这个包准备故事盲盒。」**
3. 安装回执给出实际运行版本后，发 `4869`。封签完成再开箱，照片成功后可以直接保存原图。

如果还没有角色卡，可以在对话里描述成年主角的名字、外貌和气质。包里也有一位可直接试用的虚构成年角色「林渡」。日常开箱沿用上一次确认后的账本。换对话时把需要延续的角色资料与账本一起带过去。

## 5.0 里有什么

- **200 本精选书，800 个预设故事瞬间。** 还有第 0 章自由创作。世界可涵盖工作、日常、历史、奇幻、影视和游戏灵感。
- **让各岗位真正做创作决定。** 角色、场景、服装、情绪、灯光、摄影共同完成一张照片。你也可以说「服装以后偏复古」「这次用我保存的角色」。
- **单格和三格穿搭。** 用「关闭擦边模式」切换到单格，用「打开擦边模式」开启三格，设置从下一张生效。
- **先封签，再开箱。** 运行包校验点击正文和签内输入，记录出图状态，成功确认后才推进冷却。图片由 ChatGPT 原生生成。可点击按钮需要宿主支持，备用操作见使用说明。

公开源码在 `src/`，运行入口在 `runtime/entry/p14.py`。使用 Python 3.10 或更高版本运行。开发者可用 `python -B scripts/build_release.py` 重建本地运行包。

项目代码沿用 [MIT](LICENSE)。Cinematography 保留其[上游许可证](src/wardrobe2-core/third_party/cinematography/LICENSE)。借鉴的作品和角色归各自权利人，四张照片为本项目的生成样张。
