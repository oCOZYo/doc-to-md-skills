#!/usr/bin/env python3
"""Convert native-text PDFs to Markdown via pymupdf (fast, no OCR needed).

Auto-detects whether a PDF has extractable text:
- Text PDF (avg >50 chars/page): extract directly — lossless, instant
- Scanned PDF (avg ≤50 chars/page): print warning, skip (use OCR instead)

Large embedded images (>threshold KB) are saved to disk and referenced via
standard Markdown ![](path) at their original page position. The calling agent
(Claude Code) describes them by reading them with the Read tool — no API key
required.

For backend / non-interactive use, pass --api-key to have the script call
Claude Vision itself and inline the descriptions.

Usage:
  # Agent mode (default, zero config):
  python pdf_to_md.py --input file.pdf --output ./out/

  # Standalone mode (script calls Vision directly):
  python pdf_to_md.py --input file.pdf --output ./out/ --api-key sk-ant-...

  # Pure text, skip image extraction entirely:
  python pdf_to_md.py --input file.pdf --output ./out/ --no-images
"""
import argparse
import base64
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    sys.exit("ERROR: pip install pymupdf")

VISION_PROMPT = (
    "Describe this image completely. "
    "If it is a flowchart or architecture diagram, describe each node and the "
    "connections between them. "
    "If it is a chart or data table, extract key numbers, axis labels, and trends. "
    "If it is a table, output it as a complete Markdown table. "
    "If it is a UI screenshot, describe the key regions and the data shown. "
    "Output Markdown directly, no preamble."
)

# Minimum avg chars/page to classify as text PDF
TEXT_THRESHOLD = 50

RASTER_SIGS = {
    b"\xff\xd8\xff": ("image/jpeg", "jpg"),
    b"\x89PNG": ("image/png", "png"),
    b"GIF8": ("image/gif", "gif"),
}


def detect_format(blob: bytes) -> tuple[str, str] | None:
    for sig, info in RASTER_SIGS.items():
        if blob[: len(sig)] == sig:
            return info
    return None


def is_text_pdf(doc: fitz.Document) -> tuple[bool, float]:
    total = sum(len(page.get_text()) for page in doc)
    avg = total / len(doc) if len(doc) else 0
    return avg > TEXT_THRESHOLD, avg


def median_font_size(blocks: list) -> float:
    sizes = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    sizes.append(span["size"])
    if not sizes:
        return 10.0
    sizes.sort()
    return sizes[len(sizes) // 2]


def heading_level(size: float, body: float) -> int:
    ratio = size / body if body else 1
    if ratio > 2.0:
        return 1
    if ratio > 1.5:
        return 2
    if ratio > 1.2:
        return 3
    return 0


def blocks_to_md(page: fitz.Page) -> str:
    data = page.get_text("dict")
    blocks = data.get("blocks", [])
    body = median_font_size(blocks)

    lines_out = []
    prev_y = None

    for b in blocks:
        if b.get("type") != 0:  # skip non-text blocks (images handled separately)
            continue

        block_lines = []
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            max_size = max(s.get("size", 10) for s in spans)
            level = heading_level(max_size, body)
            if level:
                block_lines.append("#" * level + " " + text)
            else:
                block_lines.append(text)

        if block_lines:
            y0 = b["bbox"][1]
            if prev_y is not None and (y0 - prev_y) > body * 1.5:
                lines_out.append("")
            lines_out.extend(block_lines)
            prev_y = b["bbox"][3]

    return "\n".join(lines_out)


def extract_page_images(page: fitz.Page, doc: fitz.Document) -> list[bytes]:
    """Return blobs for images embedded in this page."""
    blobs = []
    for img in page.get_images(full=False):
        xref = img[0]
        try:
            info = doc.extract_image(xref)
            if info and info.get("image"):
                blobs.append(info["image"])
        except Exception:
            pass
    return blobs


def call_vision(blob: bytes, media_type: str, model: str, client) -> str:
    b64 = base64.standard_b64encode(blob).decode()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": VISION_PROMPT},
            ],
        }],
    )
    return resp.content[0].text.strip()


def convert(
    pdf_path: Path,
    output_dir: Path,
    extract_images: bool,
    large_image_kb: int,
    max_images: int,
    standalone_client=None,
    model: str = "claude-haiku-4-5",
) -> tuple[Path | None, str]:
    """Convert one PDF. Returns (output_path, status_string)."""
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return None, f"error: {e}"

    is_text, avg_chars = is_text_pdf(doc)
    if not is_text:
        doc.close()
        return None, f"scanned (avg {avg_chars:.0f} ch/pg)"

    stem = pdf_path.stem
    imgs_dir = output_dir / stem / "imgs"
    threshold = large_image_kb * 1024
    images_processed = 0
    page_sections = []

    for page_idx, page in enumerate(doc, 1):
        parts = []
        text_md = blocks_to_md(page)
        if text_md.strip():
            parts.append(text_md)

        if extract_images and images_processed < max_images:
            for blob in extract_page_images(page, doc):
                if len(blob) < threshold:
                    continue
                fmt = detect_format(blob)
                if not fmt:
                    continue
                media_type, ext = fmt
                images_processed += 1
                if standalone_client is not None:
                    try:
                        desc = call_vision(blob, media_type, model, standalone_client)
                        parts.append(f"\n> **[image]**\n>\n> {desc}\n")
                    except Exception as e:
                        parts.append(f"\n> *[image vision failed: {e}]*\n")
                else:
                    imgs_dir.mkdir(parents=True, exist_ok=True)
                    img_name = f"p{page_idx}_i{images_processed:03d}.{ext}"
                    (imgs_dir / img_name).write_bytes(blob)
                    parts.append(f"\n![]({stem}/imgs/{img_name})\n")
                if images_processed >= max_images:
                    break

        if parts:
            page_sections.append("\n\n".join(parts))

    doc.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / (stem + ".md")
    out.write_text("\n\n---\n\n".join(page_sections), encoding="utf-8")
    return out, f"text (avg {avg_chars:.0f} ch/pg, {images_processed} images)"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input", required=True, help="PDF file or directory of PDFs")
    ap.add_argument("--output", required=True, help="Output directory")
    ap.add_argument(
        "--large-image-kb",
        type=int,
        default=30,
        help="Images larger than this (KB) are extracted/described (default: 30)",
    )
    ap.add_argument(
        "--max-images",
        type=int,
        default=50,
        help="Max images per document (cost guard, default: 50)",
    )
    ap.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image extraction entirely (text-only output)",
    )
    ap.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key. If provided, the script calls Vision itself "
             "and inlines descriptions (standalone mode for backend / cron use). "
             "Default: extract images to disk and emit ![](...) placeholders "
             "for the calling agent to fill in.",
    )
    ap.add_argument(
        "--model",
        default="claude-haiku-4-5",
        help="Vision model when --api-key is set",
    )
    args = ap.parse_args()

    extract_images = not args.no_images
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    standalone_client = None
    if args.api_key:
        try:
            import anthropic
        except ImportError:
            sys.exit("ERROR: --api-key requires `pip install anthropic`")
        standalone_client = anthropic.Anthropic(api_key=args.api_key)

    pdfs = (
        sorted(input_path.glob("*.pdf"))
        if input_path.is_dir()
        else [input_path]
    )

    if not pdfs:
        print("No PDF files found.")
        return

    mode = "standalone" if standalone_client else ("agent" if extract_images else "text-only")
    print(f"Mode: {mode}")
    skipped = converted = total_imgs = 0
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf.name} ...", end=" ", flush=True)
        out, status = convert(
            pdf, output_dir,
            extract_images=extract_images,
            large_image_kb=args.large_image_kb,
            max_images=args.max_images,
            standalone_client=standalone_client,
            model=args.model,
        )
        print(status)
        if out:
            converted += 1
            # crude extract from status: "...N images)"
            try:
                total_imgs += int(status.split(", ")[-1].split()[0])
            except (ValueError, IndexError):
                pass
        else:
            skipped += 1

    print(f"\nDone: {converted} converted, {skipped} skipped (scanned/error) → {output_dir}")
    if skipped:
        print("  Scanned PDFs need PaddleOCR (see ocr_extract.py).")
    if mode == "agent" and total_imgs > 0:
        print("\nNext: ask Claude Code to fill in the ![](...) image placeholders.")


if __name__ == "__main__":
    main()
