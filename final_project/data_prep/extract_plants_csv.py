#!/usr/bin/env python3
"""Parse Tree of Life catalog text into a structured plant CSV."""

import argparse
import csv
import re
from pathlib import Path

BULLET = "\u2022"
CULTIVAR_QUOTES = "'’‘"

SKIP_EXACT = {
    "full sun",
    "part shade",
    "full shade",
    "naturalize",
    "H20 1x/month",
    "H20 2x/month",
    "H20 4x/month",
    "moist",
    "flowers",
    "hardy to 15º F",
    "height (in feet)",
    "spread (in feet)",
    "sun/shade summer H20 characteristics",
    "BOTANICAL NAME COMMON NAME region location elevation community",
    "NAME & DESCRIPTION RANGE",
    "PLANTING GUIDE",
    "KEY TO TERMS & PLANTING GUIDE",
}

SKIP_PREFIXES = (
    "--- Page",
    "REGION:",
    "CULTIVARS:",
    "SUN/SHADE:",
    "LOCATION:",
    "ELEVATION:",
    "CHARACTERISTICS:",
    "COMMUNITY:",
    "SUMMER H20:",
    "Please inquire",
    "Indicates the plant",
    "Describes areas",
    "Refers to the",
    "The recommended",
    "northern -",
    "central -",
    "southern -",
    "flowers -",
    "hardy to 15",
    "height/spread -",
    "naturalize -",
    "1x/mo -",
    "2x/mo -",
    "4x/mo -",
    "moist soil -",
    "The information on",
    "RSABG:",
    "Among the many",
)

GEO_REGION_START = re.compile(
    r"\s+(?:"
    r"statewide|"
    r"north(?:ern)?(?:\s+to\s+central)?|"
    r"central|"
    r"southern|"
    r"North America|South America|Rocky Mtns|Sonoran Desert|"
    r"Mexico|Arizona|New Mexico|Texas|W\. Texas|"
    r"Baja California|Cedros Island|"
    r"endemic(?:\s+to)?|"
    r"islands?(?:,|\s)|"
    r"island(?:,|\s)"
    r")",
    re.IGNORECASE,
)

METADATA_START = re.compile(r"\s+(?:horticultural selection|hybrid(?:,|\s))", re.IGNORECASE)

GENUS_ONLY = re.compile(r"^[A-Z][a-z]+$")
GENUS_CONTINUED = re.compile(r"^([A-Z][a-z]+)\s+\(continued\)$")
BINOMIAL_START = re.compile(r"^([A-Z][a-z]+)\s+([a-z])")
DIMENSION = re.compile(r"^<?\d")
PLACEHOLDER = re.compile(r"^species\s+statewide\b", re.IGNORECASE)
CROSS_REF = re.compile(r"\(see\s+.+?\)$", re.IGNORECASE)

PLANT_LIST_START = re.compile(r"^Abies concolor\b")
PLANT_LIST_END = re.compile(r"^How to Use This Guide$")


def should_skip(line: str) -> bool:
    if not line or line in SKIP_EXACT:
        return True
    if line.isdigit():
        return True
    return any(line.startswith(prefix) for prefix in SKIP_PREFIXES)


def extract_dimensions(suffix: str) -> tuple[str, str]:
    cleaned = suffix.replace(BULLET, " ")
    cleaned = re.sub(r"\b(?:SU|SP|W|H|F|\?|CLIMBER)\b", " ", cleaned)
    cleaned = re.sub(r"\bW\d+\b", " ", cleaned)
    cleaned = re.sub(r"\bH\d+\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = cleaned.split()
    dim_tokens = [token for token in tokens if DIMENSION.match(token) or token == "CLIMBER" or "+" in token]

    if not dim_tokens:
        return "", ""
    if len(dim_tokens) == 1:
        token = dim_tokens[0]
        if token == "CLIMBER":
            return "", "CLIMBER"
        return "", token
    return dim_tokens[-2], dim_tokens[-1]


def split_entry_prefix(prefix: str) -> tuple[str, str]:
    geo_match = GEO_REGION_START.search(prefix)
    meta_match = METADATA_START.search(prefix)

    if geo_match and (not meta_match or geo_match.start() <= meta_match.start()):
        name_part = prefix[: geo_match.start()].strip()
        return name_part, ""

    if meta_match:
        name_part = prefix[: meta_match.start()].strip()
        notes = prefix[meta_match.start() :].strip()
        return name_part, notes

    return prefix.strip(), ""


def is_cultivar_token(token: str) -> bool:
    return bool(token) and token[0] in CULTIVAR_QUOTES


def build_scientific_name(current_genus: str, scientific_fragment: str) -> str:
    scientific_fragment = scientific_fragment.replace("❂", "").strip()
    scientific_fragment = re.sub(r"\s+", " ", scientific_fragment)

    if BINOMIAL_START.match(scientific_fragment):
        parts = scientific_fragment.split()
        species_tokens = []
        for index, token in enumerate(parts[1:], start=1):
            if token[0].isupper() and not is_cultivar_token(token) and index > 1:
                break
            species_tokens.append(token)
        species = " ".join(species_tokens).strip()
        return f"{parts[0]} {species}".strip()

    if current_genus:
        return f"{current_genus} {scientific_fragment}".strip()

    return scientific_fragment


def split_scientific_and_common(name_part: str) -> tuple[str, str]:
    if not name_part:
        return "", ""

    if is_cultivar_token(name_part):
        close_idx = next(
            (index for index, char in enumerate(name_part[1:], start=1) if char in CULTIVAR_QUOTES),
            -1,
        )
        if close_idx == -1:
            return name_part, ""
        cultivar = name_part[: close_idx + 1]
        remainder = name_part[close_idx + 1 :].strip()
        common = remainder.split(" horticultural selection")[0]
        common = common.split(" hybrid,")[0]
        return cultivar, common.strip()

    if BINOMIAL_START.match(name_part):
        parts = name_part.split()
        species_tokens = []
        common_tokens = []
        for index, token in enumerate(parts[1:], start=1):
            if not species_tokens:
                species_tokens.append(token)
                continue
            if token[0].islower() or token.startswith("(") or token.startswith("ssp.") or is_cultivar_token(token):
                species_tokens.append(token)
                continue
            if token[0].isupper():
                common_tokens = parts[index:]
                break
        if not common_tokens and len(parts) > 2:
            common_tokens = parts[2:]
        scientific = f"{parts[0]} {' '.join(species_tokens)}".strip()
        common = " ".join(common_tokens).strip()
        return scientific, common

    parts = name_part.split()
    species_tokens = []
    common_tokens = []
    for token in parts:
        if (
            not common_tokens
            and (
                token[0].islower()
                or token.startswith("(")
                or token.startswith("ssp.")
                or is_cultivar_token(token)
            )
        ):
            species_tokens.append(token)
            continue
        common_tokens.append(token)

    scientific = " ".join(species_tokens).strip()
    common = " ".join(common_tokens).strip()
    return scientific, common


def clean_common_name(name: str) -> str:
    return name.replace("❂", "").strip(" ,")


def parse_entry_line(line: str, current_genus: str) -> dict | None:
    if BULLET not in line:
        return None

    bullet_idx = line.index(BULLET)
    prefix = line[:bullet_idx].strip()
    suffix = line[bullet_idx:].strip()

    name_part, entry_notes = split_entry_prefix(prefix)
    scientific_fragment, common_name = split_scientific_and_common(name_part)
    scientific_name = build_scientific_name(current_genus, scientific_fragment)
    height, spread = extract_dimensions(suffix)

    return {
        "scientific_name": scientific_name,
        "common_name": clean_common_name(common_name),
        "height": height,
        "spread": spread,
        "description": entry_notes,
    }


def flush_pending(plants: list[dict], pending_entry: dict | None) -> dict | None:
    if pending_entry:
        pending_entry["description"] = re.sub(r"\s+", " ", pending_entry["description"]).strip()
        plants.append(pending_entry)
    return None


def parse_catalog(text: str) -> list[dict]:
    lines = [line.strip() for line in text.splitlines()]
    plants: list[dict] = []
    current_genus = ""
    in_plant_list = False
    pending_entry: dict | None = None

    for line in lines:
        if PLANT_LIST_START.match(line):
            in_plant_list = True
        if not in_plant_list:
            continue
        if PLANT_LIST_END.match(line):
            break
        if should_skip(line):
            continue

        continued = GENUS_CONTINUED.match(line)
        if continued:
            pending_entry = flush_pending(plants, pending_entry)
            current_genus = continued.group(1)
            continue

        if CROSS_REF.search(line) or PLACEHOLDER.match(line):
            pending_entry = flush_pending(plants, pending_entry)
            continue

        if GENUS_ONLY.match(line):
            pending_entry = flush_pending(plants, pending_entry)
            current_genus = line
            continue

        entry = parse_entry_line(line, current_genus)
        if entry:
            pending_entry = flush_pending(plants, pending_entry)
            pending_entry = entry
            continue

        if pending_entry and line and BULLET not in line:
            if pending_entry["description"]:
                pending_entry["description"] += " "
            pending_entry["description"] += line

    flush_pending(plants, pending_entry)

    for plant_id, plant in enumerate(plants, start=1):
        plant["plant_id"] = plant_id

    return plants


def write_csv(plants: list[dict], output_path: Path) -> None:
    fieldnames = [
        "plant_id",
        "scientific_name",
        "common_name",
        "height",
        "spread",
        "description",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(plants)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract plant records from catalog text into CSV.")
    parser.add_argument(
        "input",
        nargs="?",
        default="tree_of_life_catalog.txt",
        help="Path to the catalog text file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="plants.csv",
        help="Path to the output CSV file (default: plants.csv)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    plants = parse_catalog(input_path.read_text(encoding="utf-8"))
    write_csv(plants, output_path)

    print(f"Extracted {len(plants)} plants from {input_path}")
    print(f"Saved CSV to {output_path}")


if __name__ == "__main__":
    main()
