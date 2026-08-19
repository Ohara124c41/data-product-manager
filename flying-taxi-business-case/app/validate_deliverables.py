#!/usr/bin/env python3
"""Independent, reproducible verification checks for the Flyber package."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


EXPECTED = {
    "taxi_records": 1_048_468,
    "taxi_unique_ids": 1_048_468,
    "quality_records": 1_031_441,
    "survey_records": 500,
    "survey_valid_q8": 499,
    "survey_willing": 400,
    "deck_slides": 49,
}


def csv_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return sum(1 for _ in handle) - 1


def taxi_identity(path: Path) -> tuple[int, int]:
    total = 0
    ids: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            total += 1
            ids.add(row["id"])
    return total, len(ids)


def pptx_slide_count(path: Path) -> int:
    with zipfile.ZipFile(path) as package:
        return sum(
            1
            for name in package.namelist()
            if name.startswith("ppt/slides/slide")
            and name.endswith(".xml")
            and Path(name).stem[5:].isdigit()
        )


def pptx_placeholders(path: Path) -> list[str]:
    hits: list[str] = []
    with zipfile.ZipFile(path) as package:
        for name in package.namelist():
            if not (name.startswith("ppt/slides/slide") and name.endswith(".xml")):
                continue
            root = ET.fromstring(package.read(name))
            values = [(node.text or "").strip() for node in root.iter() if node.tag.endswith("}t")]
            text = " ".join(values)
            if "Fill out your answer" in text or "Answer Slide" in values:
                hits.append(name)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi", type=Path, required=True)
    parser.add_argument("--survey", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pptx", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    taxi_records, taxi_ids = taxi_identity(args.taxi)
    summary = json.loads((args.output_dir / "analysis_summary.json").read_text())
    survey_records = csv_count(args.survey)
    slides = pptx_slide_count(args.pptx)
    placeholders = pptx_placeholders(args.pptx)

    observed = {
        "taxi_records": taxi_records,
        "taxi_unique_ids": taxi_ids,
        "quality_records": int(summary["data_scope"]["operational_quality_records"]),
        "survey_records": survey_records,
        "survey_valid_q8": int(summary["survey"]["valid_flying_taxi_answers"]),
        "survey_willing": int(summary["survey"]["willing_count"]),
        "deck_slides": slides,
    }
    checks = {key: observed[key] == value for key, value in EXPECTED.items()}
    checks["deck_placeholders_removed"] = not placeholders
    required = [
        "data_quality_reconciliation.csv",
        "descriptive_statistics.csv",
        "passenger_histogram.png",
        "spatial_opportunity.png",
        "temporal_patterns.png",
        "user_adoption_segments.png",
        "willingness_to_pay.png",
        "objections.png",
        "tableau_taxi_enriched.csv",
    ]
    missing = [name for name in required if not (args.output_dir / name).is_file()]
    checks["required_analysis_outputs_exist"] = not missing

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "expected": EXPECTED,
        "observed": observed,
        "checks": checks,
        "placeholder_slides": placeholders,
        "missing_outputs": missing,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
