---
name: docx-to-md
description: Convert DOCX/Word documents to structured Markdown. Extracts headings, paragraphs, and tables losslessly via python-docx. Embedded large images are extracted to disk and referenced via standard Markdown image syntax at their original document position — you (the agent) then describe them using your built-in Vision capability via the Read tool. No separate API key required. Use this skill whenever the user wants to convert a Word document to Markdown, extract content from a .docx, or process Word reports into notes — even if they say "Word → md", "extract this docx", or "turn this report into Markdown".
---

# DOCX → Markdown

DOCX is structured XML, so text/tables can be extracted losslessly without OCR. But embedded images (architecture diagrams, flowcharts, screenshots) carry information that text-only extractors silently drop. This skill extracts them to disk and references them via standard Markdown image syntax at their original position — you describe them inline using your built-in Vision capability.

## Workflow (agent mode — default, zero config)

### Step 1 — Run the extractor

```bash
python "${CLAUDE_SKILL_DIR}/scripts/docx_to_md.py" \
  --input <docx_or_dir> \
  --output <output_dir>
```

Output:
- `<output_dir>/<stem>.md` — headings, paragraphs, tables in document order, plus `![](<stem>/imgs/img_NNN.png)` placeholders at each large image's original position
- `<output_dir>/<stem>/imgs/` — extracted image files

### Step 2 — Fill in image descriptions

Open the produced `.md`. Each embedded large image appears as a placeholder:
```markdown
![](report/imgs/img_003.png)
```

Replace each placeholder with a description block. **Pick one approach based on image count:**

- **≤5 images total**: use your Read tool to view each image, then Edit the placeholder line to:
  ```markdown
  > **[image]**
  >
  > <your description: nodes/edges if a diagram, numbers/trends if a chart, table contents if a table>
  ```

- **>5 images, or multiple documents at once**: spawn subagents via the Agent tool. Image bytes only enter the subagent's context, not yours. Suggested chunking: 10–20 images per subagent. Prompt each subagent:
  > "For each image path in this list, Read the image and produce a Markdown description (flowchart → nodes & connections; chart → numbers & trends; table → Markdown table). Return a JSON array of `{path, description}` objects."
  
  Then apply the replacements to the `.md` files in your context.

## Standalone mode (backend / cron)

For headless automation outside Claude Code, pass `--api-key`:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/docx_to_md.py" \
  --input report.docx --output out/ \
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

- Python 3.10+ with `python-docx`
- For `--api-key` standalone mode only: `pip install anthropic`

## Notes

- Works only on native `.docx`. Legacy `.doc` files need conversion first:
  `soffice --headless --convert-to docx file.doc`
- Does not extract EMF/WMF vector images (not directly exposed by python-docx). Focuses on PNG/JPEG/WEBP embeds, which is the common case.
- Image placeholders use standard Markdown syntax, so they render in Obsidian / GitHub / any viewer even before you describe them.
