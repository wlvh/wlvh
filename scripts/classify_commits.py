"""Classify local commit messages into a public aggregate topic map.

Purpose:
    Convert raw local commit JSONL into an ignored classified audit file and a
    publishable aggregate JSON file for the profile README SVG.

Call graph:
    main -> parse_args -> load_taxonomy -> classify_rows -> write_outputs
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ClassifyConfig:
    """Runtime parameters for commit classification.

    Attributes:
        raw_path: UTF-8 JSONL file with raw commit records.
        taxonomy_path: JSON taxonomy with category rules.
        classified_path: Ignored UTF-8 JSONL output for local audit.
        public_path: Public aggregate JSON output.
    """

    raw_path: Path
    taxonomy_path: Path
    classified_path: Path
    public_path: Path


def parse_args() -> ClassifyConfig:
    """Parse required paths so classification never depends on hidden state."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--taxonomy", required=True)
    parser.add_argument("--classified", required=True)
    parser.add_argument("--public", required=True)
    args = parser.parse_args()
    return ClassifyConfig(
        raw_path=Path(args.raw),
        taxonomy_path=Path(args.taxonomy),
        classified_path=Path(args.classified),
        public_path=Path(args.public),
    )


def read_jsonl(*, path: Path) -> list[dict[str, Any]]:
    """Read a UTF-8 JSONL file and fail on malformed rows."""

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            text = line.strip()
            if text == "":
                raise ValueError(f"Blank JSONL row at {path}:{line_number}")
            rows.append(json.loads(text))
    return rows


def load_taxonomy(*, path: Path) -> dict[str, Any]:
    """Load taxonomy JSON and verify that the fallback category exists."""

    taxonomy = json.loads(path.read_text(encoding="utf-8"))
    category_ids = {category["id"] for category in taxonomy["categories"]}
    if "other" not in category_ids:
        raise ValueError("taxonomy must define an 'other' category")
    return taxonomy


def score_category(
    *,
    row: dict[str, Any],
    category: dict[str, Any],
    repo_weight: int,
    keyword_weight: int,
) -> int:
    """Score one category using repo priors plus observed commit text."""

    score = 0
    repo_name = row["repo"]
    text = f"{row['repo']} {row['subject']} {row['body']}".lower()

    # Repo priors are strong because many messages are generic update/upload
    # subjects; without repo context those commits become false "other" noise.
    if repo_name in category["repos"]:
        score += repo_weight

    for keyword in category["keywords"]:
        if keyword.lower() in text:
            score += keyword_weight
    return score


def classify_row(
    *,
    row: dict[str, Any],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    """Attach category metadata to one commit row."""

    scored = []
    for category in taxonomy["categories"]:
        if category["id"] == "other":
            continue
        score = score_category(
            row=row,
            category=category,
            repo_weight=taxonomy["repo_weight"],
            keyword_weight=taxonomy["keyword_weight"],
        )
        scored.append((score, category))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_category = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0
    if best_score == 0:
        best_category = next(
            category
            for category in taxonomy["categories"]
            if category["id"] == "other"
        )

    # Confidence is a rough audit hint, not a statistical claim.
    confidence = 0.35
    if best_score > 0:
        confidence = min(0.98, 0.55 + (best_score - second_score) / 12)

    output = dict(row)
    output["category"] = best_category["id"]
    output["category_label"] = best_category["label"]
    output["confidence"] = round(confidence, 2)
    return output


def classify_rows(
    *,
    rows: list[dict[str, Any]],
    taxonomy: dict[str, Any],
) -> list[dict[str, Any]]:
    """Classify every commit row using the same taxonomy version."""

    return [classify_row(row=row, taxonomy=taxonomy) for row in rows]


def month_key(*, iso_date: str) -> str:
    """Return YYYY-MM from a GitHub commit timestamp."""

    return iso_date[:7]


def public_aggregate(
    *,
    rows: list[dict[str, Any]],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    """Build a public-safe aggregate without raw commit text or private names."""

    categories_by_id = {
        category["id"]: category for category in taxonomy["categories"]
    }
    category_counts = Counter(row["category"] for row in rows)
    total = len(rows)
    public_count = sum(1 for row in rows if not row["repo_private"])
    private_count = total - public_count
    public_repos = {row["repo"] for row in rows if not row["repo_private"]}
    private_repos = {row["repo"] for row in rows if row["repo_private"]}

    monthly_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        monthly_counts[month_key(iso_date=row["date"])][row["category"]] += 1

    category_items = []
    for category_id, count in category_counts.most_common():
        category = categories_by_id[category_id]
        category_items.append(
            {
                "id": category_id,
                "label": category["label"],
                "color": category["color"],
                "count": count,
                "share": round(count / total, 4),
            }
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "owned non-fork default branches; "
            "private commit messages aggregated only"
        ),
        "taxonomy_note": taxonomy["privacy_note"],
        "raw_messages_committed": False,
        "total_commits": total,
        "public_commits": public_count,
        "private_commits": private_count,
        "public_repo_count": len(public_repos),
        "private_repo_count": len(private_repos),
        "categories": category_items,
        "monthly_counts": {
            month: dict(counter)
            for month, counter in sorted(monthly_counts.items())
        },
    }


def write_outputs(
    *,
    classified_path: Path,
    public_path: Path,
    rows: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> None:
    """Write ignored local audit rows and public aggregate JSON."""

    classified_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    with classified_path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=False) + "\n")
    public_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Classify commits and publish aggregate topic data."""

    config = parse_args()
    taxonomy = load_taxonomy(path=config.taxonomy_path)
    raw_rows = read_jsonl(path=config.raw_path)
    classified_rows = classify_rows(rows=raw_rows, taxonomy=taxonomy)
    aggregate = public_aggregate(rows=classified_rows, taxonomy=taxonomy)
    write_outputs(
        classified_path=config.classified_path,
        public_path=config.public_path,
        rows=classified_rows,
        aggregate=aggregate,
    )
    print(
        f"classified {aggregate['total_commits']} commits -> "
        f"{config.public_path}"
    )


if __name__ == "__main__":
    main()
