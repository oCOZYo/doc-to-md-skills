---
name: docx-to-md
description: Convert DOCX/Word documents to structured Markdown. Extracts headings, paragraphs, and tables losslessly via python-docx, and optionally describes embedded large images inline using Claude Vision (preserving the image's original position in the document). Use this skill whenever the user wants to convert a Word document to Markdown, extract content from a .docx, or process Word reports into notes — even if they say "Word → md", "extract this docx", or "turn this report into Markdown".
---

# DOCX → Markdown

DOCX is structured XML, so text/tables can be extracted losslessly without OCR. But embedded images (architecture diagrams, flowcharts, screenshots) carry information that text-only extractors silently drop. This skill describes those images inline with Claude Vision at their original position.

## Workflow

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python "${CLAUDE_SKILL_DIR}/scripts/docx_to_md.py" \
  --input <docx_or_dir> \
  --output <output_dir> \
  --large-image-kb 30 \
  --model claude-haiku-4-5
```

Output: `<output_dir>/<stem>.md` with headings, paragraphs, and tables in document order, plus `> **[image]**` description blocks for large embedded images.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--large-image-kb` | `30` | Only images larger than this (KB) are sent to Vision. 30 KB filters out logos/icons by default. |
| `--no-vision` | — | Text-only mode, skip all images, zero API cost. |
| `--max-images` | `50` | Per-document image cap (cost guard). |
| `--model` | `claude-haiku-4-5` | Vision model. Haiku is fast/cheap; use `claude-sonnet-4-6` for richer descriptions. |

## Requirements

- Python 3.10+ with `python-docx` and `anthropic`
- `ANTHROPIC_API_KEY` — required when Vision is enabled (default)

## Notes

- Works only on native `.docx`. Legacy `.doc` files need conversion first:
  `soffice --headless --convert-to docx file.doc`
- Does not extract EMF/WMF vector images (not directly exposed by python-docx). Focuses on PNG/JPEG embeds, which is the common case.
