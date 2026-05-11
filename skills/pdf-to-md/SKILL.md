---
name: pdf-to-md
description: Convert PDF files to structured Markdown. Auto-detects native-text PDFs (extracted instantly with pymupdf, zero API cost) versus scanned/image PDFs (routed through PaddleOCR). Embedded large images are extracted to disk and referenced via standard Markdown image syntax — you (the agent) then describe them using your built-in Vision capability via the Read tool. No separate API key required. Use this skill whenever the user wants to convert a PDF to Markdown, extract text from PDFs, OCR scanned documents, or turn PDF reports into notes — even if they say "PDF → md", "extract this PDF", or "OCR these scans".
---

# PDF → Markdown

PDFs route by content type. The script does deterministic extraction; you (the agent) describe any embedded images using your built-in Vision capability.

## Routing

| Input | Path | Notes |
|-------|------|-------|
| Native-text PDF (avg >50 chars/page) | `pdf_to_md.py` (pymupdf) | Seconds, zero API cost |
| Scanned / image PDF | `ocr_extract.py` (PaddleOCR) | Auto-skipped from fast path; OCR vendor handles it |

## Workflow (agent mode — default, zero config)

### Step 1 — Run the extractor

```bash
python "${CLAUDE_SKILL_DIR}/scripts/pdf_to_md.py" \
  --input <source_dir_or_file> \
  --output <output_dir>
```

Per-file status:
- `text (avg NNN ch/pg, N images)` — extracted, result at `<output_dir>/<stem>.md`, images at `<output_dir>/<stem>/imgs/`
- `scanned (avg N ch/pg)` — skipped, route to Step 3

### Step 2 — Fill in image descriptions

Open the produced `.md`. Each embedded large image appears as a placeholder:
```markdown
![](report/imgs/p3_i007.png)
```

Replace each placeholder with a description block. **Pick one approach based on image count:**

- **≤5 images total**: use your Read tool to view each image, then Edit the placeholder line to:
  ```markdown
  > **[image]**
  >
  > <your description: nodes/edges if a diagram, numbers/trends if a chart, table contents if a table>
  ```

- **>5 images, or multiple files at once**: spawn subagents via the Agent tool. Image bytes only enter the subagent's context, not yours. Suggested chunking: 10–20 images per subagent. Prompt each subagent:
  > "For each image path in this list, Read the image and produce a Markdown description (flowchart → nodes & connections; chart → numbers & trends; table → Markdown table). Return a JSON array of `{path, description}` objects."
  
  Then apply the replacements to the `.md` files in your context.

### Step 3 — OCR (scanned PDFs only)

For PDFs that printed `scanned` in Step 1:

```bash
export PADDLEOCR_TOKEN="your_token"
export PADDLEOCR_API_URL="https://xxxx.aistudio-app.com/layout-parsing"
python "${CLAUDE_SKILL_DIR}/scripts/ocr_extract.py" \
  <source_dir> <output_dir>
```

Get free PaddleOCR credentials at https://aistudio.baidu.com/paddleocr.

## Standalone mode (backend / cron)

For headless automation outside Claude Code, pass `--api-key` to have the script call Vision itself:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/pdf_to_md.py" \
  --input docs/ --output out/ \
  --api-key sk-ant-... --model claude-haiku-4-5
```

## Flags

| Flag | Default | Notes |
|------|---------|-------|
| `--large-image-kb` | `30` | Only extract/describe images larger than this (KB). 30 KB filters out logos/icons. |
| `--max-images` | `50` | Per-document image cap (cost guard). |
| `--no-images` | — | Skip image extraction entirely (text-only output). |
| `--api-key` | — | Standalone mode (script calls Vision). Default is agent mode. |
| `--model` | `claude-haiku-4-5` | Vision model when `--api-key` is set. |

## Requirements

- Python 3.10+ with `pymupdf`
- For Step 3 (scanned PDFs): `requests` + `PADDLEOCR_TOKEN` / `PADDLEOCR_API_URL`
- For `--api-key` standalone mode only: `pip install anthropic`

## Notes

- Native-text PDFs cost nothing and finish in seconds — always run Step 1 first.
- Image placeholders use standard Markdown syntax, so they render in Obsidian / GitHub / any viewer even before you describe them.
- Keep `PADDLEOCR_TOKEN` in environment variables; never pass on the command line.
- `ocr_extract.py` also supports a local MLX VLM server via `--server_url`; see `--help`.
