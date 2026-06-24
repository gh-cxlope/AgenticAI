#!/usr/bin/env python3
"""Export plant descriptions from a Numbers spreadsheet into individual text files."""

import argparse
import re
from pathlib import Path

from numbers_parser import Document


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned or "plant"


def export_descriptions(input_path: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = Document(str(input_path))
    table = doc.sheets[0].tables[0]
    exported = 0

    for row in range(1, table.num_rows):
        scientific_name = table.cell(row, 1).value
        common_name = table.cell(row, 2).value
        description = table.cell(row, 3).value

        if not scientific_name or not description:
            continue

        scientific_name = str(scientific_name).strip()
        common_name = str(common_name).strip() if common_name else ""
        description = str(description).strip()

        filename = f"{sanitize_filename(scientific_name)}.txt"
        file_path = output_dir / filename

        lines = [scientific_name]
        if common_name:
            lines.append(common_name)
        lines.append("")
        lines.append(description)

        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        exported += 1

    return exported


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one text file per plant from a Numbers descriptions spreadsheet."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="descriptions.csv.numbers",
        help="Path to the Numbers file (default: descriptions.csv.numbers)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="descriptions",
        help="Output folder for text files (default: descriptions)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    count = export_descriptions(input_path, output_dir)
    print(f"Exported {count} description files to {output_dir}/")


if __name__ == "__main__":
    main()
