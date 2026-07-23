from __future__ import annotations

import csv
import json
from pathlib import Path

from .knowledge import safe_child
from .lead_scoring import score_lead_text


def load_leads(root: Path, input_path: str) -> list[dict[str, str]]:
    path = safe_child(root, input_path)
    if not path.exists():
        raise ValueError(f"lead file does not exist: {input_path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON lead file must contain a list of objects")
        return [{str(k): str(v) for k, v in row.items()} for row in data]

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [{str(k): str(v) for k, v in row.items()} for row in csv.DictReader(handle)]

    raise ValueError("lead file must be .csv or .json")


def score_leads(root: Path, input_path: str, *, focus: str = "") -> list[dict[str, object]]:
    rows = load_leads(root, input_path)
    results: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        text = " ".join(row.values()) + " " + focus
        score = score_lead_text(text)
        company = row.get("company") or row.get("公司") or f"lead-{index}"
        results.append(
            {
                "company": company,
                "score": score.score,
                "priority": score.priority,
                "positive_signals": score.positive_signals,
                "risks": score.risks,
                "source_row": row,
            }
        )
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["company"])))


def write_report(root: Path, output_path: str, rows: list[dict[str, object]]) -> str:
    path = safe_child(root, output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path.relative_to(root))
