#!/usr/bin/env python3
"""Extract text from a PDF file and save it to a plain text file."""

import argparse
from pathlib import Path

from pypdf import PdfReader


def extract_pdf_to_text(pdf_path: Path, output_path: Path) -> int:
    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"--- Page {page_number} ---\n{text.strip()}\n")

    output_path.write_text("\n".join(pages), encoding="utf-8")
    return len(reader.pages)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from a PDF into a text file.")
    parser.add_argument(
        "pdf",
        nargs="?",
        default="tree_of_life_catalog.pdf",
        help="Path to the input PDF (default: tree_of_life_catalog.pdf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output text file (default: <pdf_name>.txt)",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    output_path = Path(args.output) if args.output else pdf_path.with_suffix(".txt")
    page_count = extract_pdf_to_text(pdf_path, output_path)

    print(f"Extracted {page_count} pages from {pdf_path}")
    print(f"Saved text to {output_path}")


if __name__ == "__main__":
    main()
