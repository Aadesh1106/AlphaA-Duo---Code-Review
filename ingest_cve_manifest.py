import json
from pathlib import Path
from typing import Any


def line_of(diff: str, token: str) -> int:
    for idx, line in enumerate(diff.splitlines(), start=1):
        if token in line:
            return idx
    raise ValueError(f"Token not found in diff: {token}")


def to_dataset_entry(item: dict[str, Any]) -> dict[str, Any]:
    bug_line = line_of(item["diff"], item["marker"])
    severity = str(item["severity"])
    category = str(item["category"])
    bug_description = str(item["bug_description"])
    correct_fix = str(item["correct_fix"])

    return {
        "id": 0,
        "filename": item["filename"],
        "diff": item["diff"],
        "bug_line": bug_line,
        "severity": severity,
        "bug_description": bug_description,
        "correct_fix": correct_fix,
        "bug_category": category,
        "bugs": [
            {
                "line": bug_line,
                "severity": severity,
                "description": bug_description,
                "correct_fix": correct_fix,
                "category": category,
            }
        ],
        "is_clean": False,
        "repo_summary": item.get("repo_summary", ""),
        "file_context": item.get("file_context", ""),
        "source_type": "real_cve_seed",
        "source": {
            "cve": item["cve"],
            "repo": item["repo"],
            "url": item["commit_url"],
            "cwe": item.get("cwe", ""),
            "language": item.get("language", ""),
            "note": "Loaded from data/cve_manifest.json",
        },
    }


def main() -> None:
    data_path = Path("data") / "prs.json"
    manifest_path = Path("data") / "cve_manifest.json"

    if not data_path.exists():
        raise FileNotFoundError("data/prs.json not found")
    if not manifest_path.exists():
        raise FileNotFoundError("data/cve_manifest.json not found")

    prs = json.loads(data_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing_urls = {
        x.get("source", {}).get("url")
        for x in prs
        if x.get("source_type") == "real_cve_seed"
    }

    inserted = 0
    for item in manifest:
        if item["commit_url"] in existing_urls:
            continue
        prs.append(to_dataset_entry(item))
        inserted += 1

    for idx, pr in enumerate(prs, start=1):
        pr["id"] = idx

    data_path.write_text(json.dumps(prs, indent=2), encoding="utf-8")
    print(f"Inserted {inserted} entries from manifest. Total entries: {len(prs)}")


if __name__ == "__main__":
    main()
