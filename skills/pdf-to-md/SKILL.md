---
name: pdf-to-md
description: Convert PDF files (and JPG/PNG/BMP/TIFF/WEBP images) to structured Markdown. Auto-detects native-text PDFs (extracted instantly with pymupdf, zero API cost) versus scanned/image PDFs (routed through PaddleOCR). Embedded large images can optionally be described inline by Claude Vision. Use this skill whenever the user wants to convert a PDF to Markdown, extract text from scanned documents, OCR a batch of image files, or turn PDF reports into notes — even if they say "PDF → md", "extract this PDF", "OCR these scans", or similar.
---

# PDF → Markdown

## Routing

| Input | Path | Notes |
|-------|------|-------|
| Native-text PDF (avg >50 chars/page) | `pdf_to_md.py` (pymupdf) | Seconds, no API cost |
| Scanned / image PDF | `ocr_extract.py` (PaddleOCR) | Auto-skipped from fast path, falls through to OCR |
| Image file (JPG / PNG / BMP / TIFF / WEBP) | `ocr_extract.py` | OCR only |

## Workflow

### Step 1 — Fast extract for text PDFs

Run the fast extractor on every PDF. Native-text PDFs produce `.md` immediately; scanned PDFs print `scanned` and are skipped (handled in Step 2).

```bash
python "${CLAUDE_SKILL_DIR}/scripts/pdf_to_md.py" \
  --input <source_dir_or_file> \
  --output <output_dir>
```

Per-file status output:
- `text (avg NNN ch/pg, N images)` — extracted, result at `<output_dir>/<stem>.md`
- `scanned (avg N ch/pg)` — skipped, proceed to Step 2

Optional flags:
- `--large-image-kb 30` — send embedded large images to Claude Vision (requires `ANTHROPIC_API_KEY`)
- `--no-vision` — text-only mode, no API calls
- `--max-images 50` — per-document image cap
- `--model claude-haiku-4-5` — Vision model (Haiku is fast/cheap; use `claude-sonnet-4-6` for richer descriptions)

If the input only contains images (no PDFs), skip this step and go straight to Step 2.

### Step 2 — OCR (scanned PDFs + image files)

```bash
export PADDLEOCR_TOKEN="your_token"
export PADDLEOCR_API_URL="https://xxxx.aistudio-app.com/layout-parsing"
python "${CLAUDE_SKILL_DIR}/scripts/ocr_extract.py" \
  <source_dir> <output_dir>
```

Output structure:
- `per_page/` — one `.md` per page (cloud mode only, multi-page docs)
- `merged/` — full-document `.md`, ready to drop into a knowledge base

Get PaddleOCR credentials at https://aistudio.baidu.com/paddleocr (free tier available).

## Requirements

- Python 3.10+ with `pymupdf` (and `anthropic` if using Vision, `requests` for OCR)
- `ANTHROPIC_API_KEY` — only when using `--large-image-kb` for inline image descriptions
- `PADDLEOCR_TOKEN` / `PADDLEOCR_API_URL` — only for Step 2 (scanned PDFs and image files)

## Notes

- Native-text PDFs cost nothing and finish in seconds — always run Step 1 first.
- Keep `PADDLEOCR_TOKEN` in environment variables; never pass on the command line.
- `ocr_extract.py` also supports a local MLX VLM server via `--server_url`; see `--help`.
