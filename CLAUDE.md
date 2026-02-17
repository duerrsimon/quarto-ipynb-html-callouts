# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A GitHub Action that converts Quarto-style fenced divs (`:::{.callout-*} ... :::`) in Jupyter notebook (`.ipynb`) markdown cells into inline-styled HTML callout blocks that render in JupyterLab. It is a single-file Python tool (`convert_fenced_divs.py`) with no external dependencies beyond Python 3.10+ stdlib (`json`, `re`, `glob`, `pathlib`).

## Running

```bash
# Process all .ipynb files recursively in the current directory
python convert_fenced_divs.py
```

No install step or virtual environment needed — pure stdlib.

## Architecture

The script has two main phases:

1. **Parsing**: Regex-based state machine (`OPEN_RE`, `CLOSE_RE`, `HASH_TITLE_RE`) walks markdown cell source lines, detecting `:::{.callout-TYPE}` opening fences, optional `title="..."` attributes or `# Heading` titles, body content, and `:::` closing fences.

2. **HTML generation** (`make_html_block`): Produces self-contained `<div>` blocks with inline CSS (no external stylesheets) so they render in JupyterLab without extensions. Minimal markdown-to-HTML conversion handles bold, italic, inline code, and links within callout bodies.

Key design details:
- Callout styles are defined in the `CALLOUT_STYLES` dict — each type maps to colors, icon, and default title.
- The `exercise` callout type has auto-numbering (`"numbered": True`) with a shared counter across cells within a notebook.
- Unknown callout types fall back to `DEFAULT_STYLE`.
- Notebooks are modified in-place with `json.dump(indent=1)`.

## GitHub Action

`action.yml` defines a composite action that sets up Python and runs the script. The action path is resolved via `${GITHUB_ACTION_PATH}`.
