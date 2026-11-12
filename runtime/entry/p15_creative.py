"""Interaction and first-draft guidance for a single creative pass."""
import json

INTERACTION = (
    '找这个世界和本轮情境自然会发生的变化，让事件结果或现场痕迹成为可见线索。'
    '互动对象可来自人物手上的工作、身边的生物、自然现象或已有道具。'
    '加一件道具前要知道它承担哪条故事因果，选择合乎场景的大小和用法。'
    '若近期有相似画面，自由创作可换行为或结果，预设定格只调整不影响 Point 的细节。'
    '保留确实由故事、职业或用户选择所需的物件。'
)
def recent_moment_context(ledger):
    recent = ledger.get('recent_story_moments', [])
    if not isinstance(recent, list):
        return ''
    moments = (row.get('moment') for row in recent[-3:] if isinstance(row, dict))
    entries = [line[:180] for line in moments if isinstance(line, str) and line.strip()]
    if not entries:
        return ''
    return '近期已成片的画面瞬间（仅供避开相似解法）\n' + json.dumps(entries, ensure_ascii=False)
