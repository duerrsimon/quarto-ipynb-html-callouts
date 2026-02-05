# Convert Quarto Fenced Divs to HTML

GitHub Action to convert Quarto fenced divs (`:::{.callout-*}`) in Jupyter notebooks into inline-styled HTML blocks that render in JupyterLab.

## Supported Callout Types

| Type | Icon | Description |
|------|------|-------------|
| `note` | 📝 | General notes and information |
| `tip` | 💡 | Helpful tips and suggestions |
| `warning` | ⚠️ | Warning messages |
| `caution` | 🔥 | Caution alerts for dangerous operations |
| `important` | ❗ | Important information |
| `exercise` | ✏️ | Exercises (auto-numbered) |

## Usage

Add this action to your workflow to convert all Quarto fenced divs in `.ipynb` files:

```yaml
- name: Convert Quarto Fenced Divs
  uses: your-username/quarto-ipynb-html-callouts@main
```

### Example Workflow

```yaml
name: Convert Notebooks
on: [push]

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - name: Convert Quarto Fenced Divs
        uses: your-username/quarto-ipynb-html-callouts@main

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add -A
          git diff --quiet && git diff --staged --quiet || git commit -m "Convert fenced divs to HTML"
          git push
```

## Input Syntax

The action converts Quarto-style fenced divs:

```markdown
:::{.callout-note}
This is a note.
:::

:::{.callout-warning title="Watch Out"}
This has a custom title.
:::

:::{.callout-tip}
## Tip Title
You can also use a heading as the title.
:::
```

## Output

The fenced divs are converted to inline-styled HTML that renders as colored callout boxes in JupyterLab, with appropriate icons, colors, and formatting for each callout type.
