"""Render a standalone local copy button from a verified seal."""

from html import escape
from pathlib import Path
import re

from design_contract import SECTIONS
from story_compiler import canonical

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets' / 'open-card.html'


def notes_sections(notes):
    return ''.join(
        '<section><h3>' + escape(label) + '</h3><p>' + escape(notes['sections'][key]) + '</p></section>'
        for key, label in SECTIONS
    )


def notes_fragment(notes):
    return "<details><summary>创作思路</summary>" + notes_sections(notes) + "</details>\n"


def render_card(button, notes, status):
    if button['route'] != 'copy_only':
        raise ValueError('This browser card only supports the verified copy route')
    values = canonical({
        'message': button['full_user_message'],
        'messageSha256': button['source_message_sha256'],
    }).decode('utf-8').replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    sections = notes_sections(notes)
    labels = status['display_labels']
    lines = ''.join('<li>' + escape(label + ' · ' + labels[key]) + '</li>' for key, label in (
        ('focus', '专注创作'), ('library_browsed', '万卷故事 · 本次浏览'),
        ('library_adopted', '万卷故事 · 采用灵感'),
    ))
    template = TEMPLATE.read_text(encoding='utf-8')
    # Substitute only original placeholders, even when authored text contains them.
    replacements = {'__PAYLOAD__': values, '__NOTES__': sections, '__STATUS__': lines,
                    '__BUTTON__': escape(button['button_label'])}
    return re.sub(r'__(?:PAYLOAD|NOTES|STATUS|BUTTON)__', lambda match: replacements[match[0]], template)
