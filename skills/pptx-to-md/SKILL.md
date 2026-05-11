---
name: pptx-to-md
description: Convert PPTX/PPSX presentations to structured Markdown by rendering each slide as a PNG and describing it with Claude Vision. Preserves flowcharts, architecture diagrams, side-by-side comparisons, data tables, and visual hierarchy — information that shape-text extraction (e.g. markitdown) silently drops. Use this skill whenever the user wants to convert slides to Markdown, extract content from a presentation, or process decks into notes — even if they say "PPT → md", "extract these slides", or "turn this deck into a doc".
---

# PPTX → Markdown

PPTX information often lives in visual layout (side-by-side comparisons, flowchart arrows, data charts). Plain shape-text extraction loses this structure. This skill renders each slide as a PNG and lets Claude Vision describe the full content — preserving spatial relationships.

## Pipeline

```
PPTX → PDF (LibreOffice) → per-slide PNG (pymupdf, 150 dpi) → Vision description → merged .md
```

## Workflow

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python "${CLAUDE_SKILL_DIR}/scripts/pptx_to_md.py" \
  --input <pptx_or_dir> \
  --output <output_dir> \
  --dpi 150 \
  --concurrent 5 \
  --model claude-haiku-4-5
```

Output: `<output_dir>/<stem>.md` with one `## Slide N` section per slide.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--dpi` | `150` | Slide render resolution. 100 is fine for text-heavy decks; 200 for dense diagrams. |
| `--concurrent` | `5` | Parallel Vision calls per file. Lower if hitting API rate limits. |
| `--max-slides` | `200` | Per-file slide cap (cost guard). |
| `--workers` | `2` | Parallel files (currently sequential; reserved). |
| `--model` | `claude-haiku-4-5` | Vision model. Haiku is fast/cheap; `claude-sonnet-4-6` for richer descriptions. |

## Requirements

- Python 3.10+ with `pymupdf` and `anthropic`
- LibreOffice (`soffice` command). macOS: `brew install --cask libreoffice`. Debian/Ubuntu: `apt install libreoffice`.
- `ANTHROPIC_API_KEY`

## Notes

- LibreOffice's `--convert-to png` only exports the first slide on macOS, so this skill uses the PDF → PNG route (which works reliably).
- LibreOffice profile isolation (`-env:UserInstallation`) is built in — safe for concurrent runs without lock conflicts.
- `.ppsx` is supported the same way as `.pptx`.
