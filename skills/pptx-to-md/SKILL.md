---
name: pptx-to-md
description: Convert PPTX/PPSX presentations to structured Markdown by rendering each slide as a PNG. Preserves flowcharts, architecture diagrams, side-by-side comparisons, and visual layouts that shape-text extraction (markitdown, pandoc) silently drops. Slides are rendered to disk and referenced via standard Markdown image syntax — you (the agent) describe them using your built-in Vision capability via the Read tool. No separate API key required. Use this skill whenever the user wants to convert slides to Markdown, extract content from a presentation, or process decks into notes — even if they say "PPT → md", "extract these slides", or "turn this deck into a doc".
---

# PPTX → Markdown

PPTX information often lives in visual layout (side-by-side comparisons, flowchart arrows, charts). Plain shape-text extraction loses this structure. This skill renders each slide as a PNG and lets you describe the full content — preserving spatial relationships.

## Pipeline

```
PPTX → PDF (LibreOffice) → per-slide PNG (pymupdf, 150 dpi) → .md with ![](...) placeholders → you fill in descriptions
```

## Workflow (agent mode — default, zero config)

### Step 1 — Run the renderer

```bash
python "${CLAUDE_SKILL_DIR}/scripts/pptx_to_md.py" \
  --input <pptx_or_dir> \
  --output <output_dir>
```

Output:
- `<output_dir>/<stem>.md` — one `## Slide N` section per slide, each referencing the slide PNG
- `<output_dir>/<stem>/slides/slide_NNN.png` — per-slide images

Example produced `.md`:
```markdown
# my_deck

## Slide 1

![](my_deck/slides/slide_001.png)

## Slide 2

![](my_deck/slides/slide_002.png)
```

### Step 2 — Fill in slide descriptions

Replace each `![](...)` placeholder with a Markdown description of that slide. **Pick one approach based on slide count:**

- **≤5 slides total**: use your Read tool on each PNG, then Edit the placeholder line to a full description of the slide (title, bullets, diagrams, tables, comparisons).

- **>5 slides, or multiple decks at once**: spawn subagents via the Agent tool. Slide image bytes only enter the subagent's context, not yours. Suggested chunking: 10–20 slides per subagent. Prompt each subagent:
  > "For each PNG path in this list, Read it as a slide image and produce a Markdown description: title + subtitle, bullet hierarchy, any diagrams (nodes & connections), any charts (numbers & trends), any tables (as Markdown tables), any side-by-side comparisons. Return a JSON array of `{path, description}` objects."
  
  Then apply the replacements to the `.md` in your context.

  For very large jobs (hundreds of slides), spawn the subagents in waves to stay within concurrency limits.

## Standalone mode (backend / cron)

For headless automation outside Claude Code, pass `--api-key` to have the script call Vision itself with parallel requests:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/pptx_to_md.py" \
  --input deck.pptx --output out/ \
  --api-key sk-ant-... --model claude-haiku-4-5 --concurrent 5
```

## Flags

| Flag | Default | Notes |
|------|---------|-------|
| `--dpi` | `150` | Slide render resolution. 100 for text-heavy decks; 200 for dense diagrams. |
| `--max-slides` | `200` | Per-file slide cap (cost guard). |
| `--api-key` | — | Standalone mode (script calls Vision). Default is agent mode. |
| `--model` | `claude-haiku-4-5` | Vision model when `--api-key` is set. |
| `--concurrent` | `5` | Parallel Vision calls per file in standalone mode. |

## Requirements

- Python 3.10+ with `pymupdf`
- LibreOffice (`soffice` command). macOS: `brew install --cask libreoffice`. Debian/Ubuntu: `apt install libreoffice`.
- For `--api-key` standalone mode only: `pip install anthropic`

## Notes

- LibreOffice's `--convert-to png` only exports the first slide on macOS, so this skill uses the PDF → PNG route (which works reliably).
- LibreOffice profile isolation (`-env:UserInstallation`) is built in — safe for concurrent runs.
- `.ppsx` is supported the same way as `.pptx`.
