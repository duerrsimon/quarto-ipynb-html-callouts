#!/usr/bin/env python3
"""
Convert Quarto fenced divs (:::{.callout-*} ... :::) in Jupyter notebooks
into inline-styled HTML blocks that render nicely in JupyterLab.

This script processes all .ipynb files recursively in the current directory.
"""

import glob
import json
import re
from pathlib import Path

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

    body_md = "\n".join(body_lines).strip()

    # Convert minimal markdown in body to HTML (bold, italic, code, links)
    body_html = body_md
    body_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body_html)
    body_html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", body_html)
    body_html = re.sub(r"`(.+?)`", r'<code style="background:#e0e0e0;padding:1px 4px;border-radius:3px;font-size:0.9em;">\1</code>', body_html)
    body_html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', body_html)

    # Turn blank-line-separated chunks into <p> tags
    paragraphs = re.split(r"\n{2,}", body_html)
    body_html = "".join(f"<p style='margin:0.4em 0;'>{p.strip()}</p>" for p in paragraphs if p.strip())

    html = (
        f'<div style="border-left:4px solid {style["border"]};background:{style["bg"]};'
        f'border-radius:6px;margin:12px 0;overflow:hidden;">\n'
        f'  <div style="background:{style["title_bg"]};color:{style["title_color"]};'
        f'padding:8px 14px;font-weight:700;font-size:1.0em;">'
        f'{icon} {display_title}</div>\n'
        f'  <div style="padding:10px 14px;color:#1a1a1a;font-size:0.95em;">\n'
        f"    {body_html}\n"
        f"  </div>\n"
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
