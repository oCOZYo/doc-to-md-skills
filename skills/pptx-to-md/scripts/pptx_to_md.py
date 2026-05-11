#!/usr/bin/env python3
"""Convert PPTX/PPSX to Markdown by rendering each slide as a PNG.

Pipeline:
  1. PPTX → PDF (LibreOffice headless)
  2. PDF  → per-slide PNG (pymupdf, 150 dpi by default)
  3. Write .md with one section per slide referencing each PNG via ![](...)

The calling agent (Claude Code) describes each slide by reading the PNGs
with the Read tool — no API key required. For large decks the agent can
spawn subagents to keep image bytes out of the main context.

For backend / non-interactive use, pass --api-key to have the script call
Claude Vision itself and inline the descriptions.

Usage:
  # Agent mode (default, zero config):
  python pptx_to_md.py --input file.pptx --output ./out/

  # Standalone mode (script calls Vision directly, parallel):
  python pptx_to_md.py --input file.pptx --output ./out/ --api-key sk-ant-...
"""
import argparse
import base64
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    sys.exit("ERROR: pip install pymupdf")

VISION_PROMPT = (
    "This is a screenshot of a PPT slide. Describe the slide's full content:\n"
    "- Title and subtitle (preserve original text)\n"
    "- Body content (keep the hierarchy, render as Markdown lists)\n"
    "- If there's a flowchart/architecture diagram: describe each node and "
    "the connections (arrow direction, hierarchy)\n"
    "- If there's a chart/data: extract values, axis labels, trends\n"
    "- If there's a side-by-side layout: describe each part and the comparison\n"
    "- If there's a table: output it as a complete Markdown table\n"
    "Output Markdown directly, no preamble."
)

CONVERTIBLE = {".pptx", ".ppsx"}


def pptx_to_pdf(pptx_path: Path, pdf_dir: Path, worker_id: int = 0) -> Path | None:
    """Convert PPTX to PDF via LibreOffice. Returns path to PDF or None on failure."""
    profile = f"/tmp/lo_profile_pptx2md_{worker_id}"
    try:
        subprocess.run(
            [
                "soffice", "--headless",
                "--convert-to", "pdf",
                "--outdir", str(pdf_dir),
                f"-env:UserInstallation=file://{profile}",
                str(pptx_path),
            ],
            capture_output=True, timeout=120,
        )
        pdf = pdf_dir / (pptx_path.stem + ".pdf")
        if pdf.exists() and pdf.stat().st_size > 0:
            return pdf
        return None
    except (subprocess.TimeoutExpired, Exception):
        return None


def pdf_to_pngs(pdf_path: Path, png_dir: Path, dpi: int = 150) -> list[Path]:
    """Render each PDF page to a PNG. Returns sorted list of PNG paths."""
    png_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    pngs = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i, page in enumerate(doc):
        png_path = png_dir / f"slide_{i + 1:03d}.png"
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        pix.save(str(png_path))
        pngs.append(png_path)
    doc.close()
    return pngs


def describe_slide(png_path: Path, slide_num: int, model: str, client) -> tuple[int, str]:
    """Send one slide PNG to Vision. Returns (slide_num, markdown_description)."""
    blob = png_path.read_bytes()
    b64 = base64.standard_b64encode(blob).decode()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }
            ],
        )
        return slide_num, resp.content[0].text.strip()
    except Exception as e:
        return slide_num, f"*[Slide {slide_num} Vision error: {e}]*"


def convert(
    pptx_path: Path,
    output_dir: Path,
    dpi: int,
    max_slides: int,
    worker_id: int,
    standalone_client=None,
    model: str = "claude-haiku-4-5",
    concurrent: int = 5,
) -> tuple[Path, int]:
    """Returns (output_path, slide_count)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = pptx_path.stem

    # Persistent slide directory — the agent will Read these
    slides_dir = output_dir / stem / "slides"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Step 1: PPTX → PDF
        pdf = pptx_to_pdf(pptx_path, tmp_path, worker_id)
        if not pdf:
            out = output_dir / (stem + ".md")
            out.write_text(f"# {stem}\n\n*[PDF conversion failed]*\n")
            return out, 0

        # Step 2: PDF → per-slide PNGs (rendered into persistent slides_dir)
        slides_dir.mkdir(parents=True, exist_ok=True)
        pngs = pdf_to_pngs(pdf, slides_dir, dpi)
        if not pngs:
            out = output_dir / (stem + ".md")
            out.write_text(f"# {stem}\n\n*[No slides rendered]*\n")
            return out, 0

        pngs = pngs[:max_slides]

    # Step 3: Either inline descriptions (standalone) or emit ![](...) placeholders (agent)
    lines = [f"# {stem}\n"]

    if standalone_client is not None:
        # Standalone mode: parallel Vision calls
        results: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            futures = {
                pool.submit(describe_slide, png, i + 1, model, standalone_client): i + 1
                for i, png in enumerate(pngs)
            }
            for future in as_completed(futures):
                num, desc = future.result()
                results[num] = desc
        for i in range(1, len(pngs) + 1):
            lines.append(f"\n## Slide {i}\n")
            lines.append(results.get(i, "*[missing]*"))
    else:
        # Agent mode: emit placeholders for the agent to fill in
        for i, png in enumerate(pngs, 1):
            lines.append(f"\n## Slide {i}\n")
            lines.append(f"![]({stem}/slides/{png.name})\n")

    out = output_dir / (stem + ".md")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out, len(pngs)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input", required=True, help="PPTX/PPSX file or directory")
    ap.add_argument("--output", required=True, help="Output directory")
    ap.add_argument("--dpi", type=int, default=150,
                    help="Slide render resolution (default: 150)")
    ap.add_argument("--max-slides", type=int, default=200,
                    help="Max slides per file (cost guard, default: 200)")
    ap.add_argument(
        "--api-key", default=None,
        help="Anthropic API key. If provided, the script calls Vision itself "
             "and inlines descriptions (standalone mode for backend / cron use). "
             "Default: render PNGs and emit ![](...) placeholders for the "
             "calling agent to fill in.",
    )
    ap.add_argument("--model", default="claude-haiku-4-5",
                    help="Vision model when --api-key is set")
    ap.add_argument("--concurrent", type=int, default=5,
                    help="Parallel Vision calls per file in standalone mode (default: 5)")
    args = ap.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    standalone_client = None
    if args.api_key:
        try:
            import anthropic
        except ImportError:
            sys.exit("ERROR: --api-key requires `pip install anthropic`")
        standalone_client = anthropic.Anthropic(api_key=args.api_key)

    files = (
        sorted(f for f in input_path.iterdir() if f.suffix.lower() in CONVERTIBLE)
        if input_path.is_dir()
        else [input_path]
    )

    if not files:
        print("No PPTX/PPSX files found.")
        return

    mode = "standalone" if standalone_client else "agent"
    print(f"Mode: {mode}")
    print(f"Processing {len(files)} file(s) → {output_dir}")

    total_slides = 0
    for i, pptx_path in enumerate(files):
        print(f"[{i+1}/{len(files)}] {pptx_path.name} ...", end=" ", flush=True)
        _out, n = convert(
            pptx_path, output_dir,
            dpi=args.dpi,
            max_slides=args.max_slides,
            worker_id=i % 4,
            standalone_client=standalone_client,
            model=args.model,
            concurrent=args.concurrent,
        )
        total_slides += n
        print(f"done ({n} slides)")

    print(f"\nTotal: {len(files)} files, {total_slides} slides → {output_dir}")
    if mode == "agent" and total_slides > 0:
        print("\nNext: ask Claude Code to fill in the ![](...) slide placeholders.")


if __name__ == "__main__":
    main()
