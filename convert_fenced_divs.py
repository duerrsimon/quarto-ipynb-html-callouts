#!/usr/bin/env python3
"""
Convert Quarto fenced divs (:::{.callout-*} ... :::) in Jupyter notebooks
into inline-styled HTML blocks that render nicely in JupyterLab.

This script processes all .ipynb files recursively in the current directory.
"""

import glob
import json
import re
import uuid
from pathlib import Path

import markdown

# ── Callout type styles ──────────────────────────────────────────────────────

CALLOUT_STYLES = {
    "note": {
        "icon": "📝",
        "border": "#4582ec",
        "bg": "#e8f0fe",
        "title_bg": "#4582ec",
        "title_color": "#ffffff",
        "default_title": "Note",
    },
    "tip": {
        "icon": "💡",
        "border": "#2ecc71",
        "bg": "#eafaf1",
        "title_bg": "#2ecc71",
        "title_color": "#ffffff",
        "default_title": "Tip",
    },
    "warning": {
        "icon": "⚠️",
        "border": "#f0ad4e",
        "bg": "#fef9e7",
        "title_bg": "#f0ad4e",
        "title_color": "#ffffff",
        "default_title": "Warning",
    },
    "caution": {
        "icon": "🔥",
        "border": "#e74c3c",
        "bg": "#fdedec",
        "title_bg": "#e74c3c",
        "title_color": "#ffffff",
        "default_title": "Caution",
    },
    "important": {
        "icon": "❗",
        "border": "#9b59b6",
        "bg": "#f4ecf7",
        "title_bg": "#9b59b6",
        "title_color": "#ffffff",
        "default_title": "Important",
    },
    "exercise": {
        "icon": "✏️",
        "border": "#2a6fdb",
        "bg": "#e8f0fe",
        "title_bg": "#2a6fdb",
        "title_color": "#ffffff",
        "default_title": "Exercise",
        "numbered": True,
    },
}

# Fallback for unknown callout types
DEFAULT_STYLE = {
    "icon": "ℹ️",
    "border": "#6c757d",
    "bg": "#f8f9fa",
    "title_bg": "#6c757d",
    "title_color": "#ffffff",
    "default_title": "Callout",
}


# ── Markdown converter instance ──────────────────────────────────────────────

MD = markdown.Markdown(extensions=[
    'tables',
    'fenced_code',
    'def_list',
    'footnotes',
    'attr_list',
    'sane_lists',
])

# ── Inline style injection ──────────────────────────────────────────────────

HEADING_STYLES = {
    "h1": "font-size:1.4em;margin:0.6em 0 0.3em;font-weight:700;",
    "h2": "font-size:1.25em;margin:0.5em 0 0.3em;font-weight:700;",
    "h3": "font-size:1.1em;margin:0.4em 0 0.2em;font-weight:700;",
    "h4": "font-size:1.0em;margin:0.4em 0 0.2em;font-weight:700;",
    "h5": "font-size:0.95em;margin:0.3em 0 0.2em;font-weight:700;",
    "h6": "font-size:0.9em;margin:0.3em 0 0.2em;font-weight:700;",
}

TAG_STYLES = {
    "blockquote": "border-left:3px solid #ccc;margin:0.5em 0;padding:0.4em 1em;background:#f9f9f9;color:#555;",
    "table": "border-collapse:collapse;width:100%;margin:0.5em 0;",
    "th": "border:1px solid #ddd;padding:6px 10px;background:#f0f0f0;font-weight:700;text-align:left;",
    "td": "border:1px solid #ddd;padding:6px 10px;",
    "ul": "margin:0.4em 0;padding-left:1.5em;",
    "ol": "margin:0.4em 0;padding-left:1.5em;",
    "li": "margin:0.2em 0;",
    "hr": "border:none;border-top:1px solid #ccc;margin:0.8em 0;",
    "dl": "margin:0.5em 0;",
    "dt": "font-weight:700;margin-top:0.4em;",
    "dd": "margin-left:1.5em;margin-bottom:0.3em;",
    "p": "margin:0.4em 0;",
    "a": "color:#0366d6;",
    "img": "max-width:100%;",
    "del": "text-decoration:line-through;",
}

PRE_STYLE = "background:#2b2b2b;color:#f8f8f2;padding:10px 14px;border-radius:4px;overflow-x:auto;font-size:0.85em;margin:0.5em 0;"
CODE_INLINE_STYLE = "background:#e0e0e0;padding:1px 4px;border-radius:3px;font-size:0.9em;"


def add_inline_styles(html: str) -> str:
    """Inject inline styles into HTML tags so they render in JupyterLab."""

    # 1. Style <pre><code> blocks: style <pre>, force inner <code> to inherit
    CODE_IN_PRE_STYLE = "color:#f8f8f2;background:transparent;padding:0;border-radius:0;font-size:inherit;"

    def _style_pre_code(m):
        pre_attrs = m.group(1) or ""
        code_attrs = m.group(2) or ""
        return f'<pre{pre_attrs} style="{PRE_STYLE}"><code{code_attrs} style="{CODE_IN_PRE_STYLE}">'

    html = re.sub(r"<pre([^>]*)><code([^>]*)>", _style_pre_code, html)

    # 2. Style standalone <code> (not inside <pre>)
    #    Split on <pre>...</pre> blocks to avoid double-styling
    parts = re.split(r"(<pre[^>]*>.*?</pre>)", html, flags=re.DOTALL)
    for idx, part in enumerate(parts):
        if not part.startswith("<pre"):
            parts[idx] = re.sub(
                r"<code(?![^>]*style=)([^>]*)>",
                rf'<code\1 style="{CODE_INLINE_STYLE}">',
                part,
            )
    html = "".join(parts)

    # 3. Headings
    for tag, sty in HEADING_STYLES.items():
        html = re.sub(
            rf"<{tag}(?![^>]*style=)([^>]*?)>",
            rf'<{tag}\1 style="{sty}">',
            html,
        )

    # 4. All other tags
    for tag, sty in TAG_STYLES.items():
        # Handle self-closing tags (e.g. <hr />, <img ... />) — inject style before the /
        html = re.sub(
            rf"<{tag}(?![^>]*style=)([^>]*?)\s*(/?)>",
            rf'<{tag}\1 style="{sty}"\2>',
            html,
        )

    # 5. Checkbox styling for task lists
    html = re.sub(
        r'<input(?![^>]*style=)([^>]*type="checkbox"[^>]*)>',
        r'<input\1 style="margin-right:0.4em;">',
        html,
    )

    return html


# ── Math protection ──────────────────────────────────────────────────────────

def _protect_math(text: str):
    """Replace math expressions with UUID placeholders to protect from markdown parsing."""
    placeholders = {}
    # Display math first ($$...$$), including multiline
    def _replace_display(m):
        key = f"MATH_{uuid.uuid4().hex}"
        placeholders[key] = m.group(0)
        return key
    text = re.sub(r"\$\$(.+?)\$\$", _replace_display, text, flags=re.DOTALL)
    # Inline math ($...$) — avoid matching $$ or currency like $5
    def _replace_inline(m):
        key = f"MATH_{uuid.uuid4().hex}"
        placeholders[key] = m.group(0)
        return key
    text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", _replace_inline, text)
    return text, placeholders


def _restore_math(html: str, placeholders: dict) -> str:
    """Restore math expressions from placeholders."""
    for key, original in placeholders.items():
        html = html.replace(key, original)
    return html


# ── Quarto extension pre/post-processing ────────────────────────────────────

def _preprocess_quarto_extensions(text: str):
    """Handle Quarto/Pandoc extensions not supported by the markdown lib."""
    placeholders = {}

    # Strikethrough: ~~text~~ → placeholder (restore as <del> after)
    def _replace_strike(m):
        key = f"STRIKE_{uuid.uuid4().hex}"
        placeholders[key] = f"<del>{m.group(1)}</del>"
        return key
    text = re.sub(r"~~(.+?)~~", _replace_strike, text)

    # Subscript: H~2~O → H<sub>2</sub>O
    text = re.sub(r"(?<!\~)~(?!\~)([^~]+?)~(?!~)", r"<sub>\1</sub>", text)

    # Protect footnote references [^N] and definitions [^N]: from superscript regex
    fn_placeholders = {}
    def _protect_footnote(m):
        key = f"FN_{uuid.uuid4().hex}"
        fn_placeholders[key] = m.group(0)
        return key
    text = re.sub(r"\[\^[^\]]+\](?::)?", _protect_footnote, text)

    # Superscript: E=mc^2^ → E=mc<sup>2</sup>
    text = re.sub(r"(?<!\^)\^(?!\^)([^^]+?)\^(?!\^)", r"<sup>\1</sup>", text)

    # Restore footnote syntax
    for key, orig in fn_placeholders.items():
        text = text.replace(key, orig)

    return text, placeholders


def _postprocess_task_lists(html: str) -> str:
    """Convert [ ] and [x] markers in list items to checkbox HTML."""
    html = re.sub(
        r"<li([^>]*)>\s*\[ \]\s*",
        r'<li\1><input type="checkbox" disabled> ',
        html,
    )
    html = re.sub(
        r"<li([^>]*)>\s*\[x\]\s*",
        r'<li\1><input type="checkbox" checked disabled> ',
        html,
        flags=re.IGNORECASE,
    )
    return html


# ── Body-to-HTML conversion ─────────────────────────────────────────────────

def md_body_to_html(body_lines: list[str]) -> str:
    """Convert markdown body lines to styled HTML."""
    body_text = "\n".join(body_lines).strip()
    if not body_text:
        return ""

    # 1. Protect math
    body_text, math_placeholders = _protect_math(body_text)

    # 2. Pre-process Quarto extensions
    body_text, strike_placeholders = _preprocess_quarto_extensions(body_text)

    # 3. Convert with markdown lib
    html = MD.reset().convert(body_text)

    # 4. Post-process task lists
    html = _postprocess_task_lists(html)

    # 5. Restore strikethrough placeholders
    for key, replacement in strike_placeholders.items():
        html = html.replace(key, replacement)

    # 6. Add inline styles
    html = add_inline_styles(html)

    # 7. Restore math
    html = _restore_math(html, math_placeholders)

    return html


def make_html_block(callout_type: str, title: str | None, body_lines: list[str], counters: dict) -> str:
    """Build an inline-styled HTML block for a callout."""
    style = CALLOUT_STYLES.get(callout_type, DEFAULT_STYLE)
    icon = style["icon"]

    # Auto-number if the callout type is flagged for numbering
    if style.get("numbered"):
        counters[callout_type] = counters.get(callout_type, 0) + 1
        n = counters[callout_type]
        display_title = title or f"{style['default_title']} {n}"
        if title:
            display_title = f"{style['default_title']} {n} — {title}"
    else:
        display_title = title or style["default_title"]

    body_html = md_body_to_html(body_lines)

    html = (
        f'<div style="border-left:4px solid {style["border"]};background:{style["bg"]};'
        f'border-radius:6px;margin:12px 0;overflow:hidden;">\n'
        f'<div style="background:{style["title_bg"]};color:{style["title_color"]};'
        f'padding:8px 14px;font-weight:700;font-size:1.0em;">'
        f'{icon} {display_title}</div>\n'
        f'<div style="padding:10px 14px;color:#1a1a1a;font-size:0.95em;">\n'
        f"{body_html}\n"
        f"</div>\n"
        f"</div>"
    )
    return html


# ── Fenced div patterns ─────────────────────────────────────────────────────

# Opening: :::{.callout-<type>}  or  :::{.callout-<type> title="My Title"}
# Also supports # Title on the next line
OPEN_RE = re.compile(
    r"^:::\{\.callout-(\w+)"          # :::{.callout-TYPE
    r'(?:\s+title="([^"]*)")?'        # optional title="..."
    r"\s*\}?\s*$"                      # closing brace & whitespace
)
CLOSE_RE = re.compile(r"^:{3,}\s*$")  # ::: (closing fence)
HASH_TITLE_RE = re.compile(r"^#{1,3}\s+(.+)$")  # ## Title on line after opening


def convert_cell_source(source_lines: list[str], counters: dict) -> list[str]:
    """
    Process a markdown cell's source lines, replacing fenced divs
    with HTML callout blocks.
    """
    result: list[str] = []
    i = 0

    while i < len(source_lines):
        line = source_lines[i].rstrip("\n")
        m = OPEN_RE.match(line)

        if m:
            callout_type = m.group(1)
            title = m.group(2)  # may be None
            body: list[str] = []
            i += 1

            # Check if next non-blank line is a # heading (used as title)
            if i < len(source_lines):
                ht = HASH_TITLE_RE.match(source_lines[i].rstrip("\n"))
                if ht:
                    title = title or ht.group(1)
                    i += 1

            # Collect body lines until closing :::
            while i < len(source_lines):
                cline = source_lines[i].rstrip("\n")
                if CLOSE_RE.match(cline):
                    i += 1
                    break
                body.append(cline)
                i += 1

            html = make_html_block(callout_type, title, body, counters)
            result.append(html + "\n")
        else:
            result.append(source_lines[i])
            i += 1

    return result


def convert_notebook(nb: dict) -> int:
    """Convert all fenced divs in markdown cells of a notebook dict.

    Returns the number of conversions made.
    """
    counters: dict[str, int] = {}  # shared across cells for consistent numbering
    conversions = 0

    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            original = cell["source"]
            # Normalize source to list of lines
            if isinstance(original, str):
                lines = original.splitlines(keepends=True)
            else:
                lines = list(original)

            # Count fenced divs before conversion
            for line in lines:
                if OPEN_RE.match(line.rstrip("\n")):
                    conversions += 1

            cell["source"] = convert_cell_source(lines, counters)

    return conversions


def main():
    """Process all notebooks recursively and convert fenced divs in-place."""
    all_notebooks = glob.glob('**/*.ipynb', recursive=True)

    if len(all_notebooks) == 0:
        print('No notebooks found')
        return

    total_conversions = 0

    for nb_path in all_notebooks:
        with open(nb_path, encoding='utf-8') as f:
            nb = json.load(f)

        conversions = convert_notebook(nb)
        total_conversions += conversions

        with open(nb_path, 'w', encoding='utf-8') as outfile:
            json.dump(nb, outfile, indent=1, ensure_ascii=False)
            outfile.write('\n')

        if conversions > 0:
            print(f'Converted {conversions} fenced div(s) in {nb_path}')
        else:
            print(f'No fenced divs found in {nb_path}')

    print(f'\nTotal: {total_conversions} fenced div(s) converted in {len(all_notebooks)} notebook(s)')


if __name__ == "__main__":
    main()
