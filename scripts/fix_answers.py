"""
fix_answers.py
--------------
Post-process answer JSON files in C:/HHGoa/results/answers to clean up
pattern and status fields without LLM calls.
"""

import json
from collections import Counter
from pathlib import Path

valid_patterns = [
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none",
]


def fix_answers():
    answers_dir = Path("C:/HHGoa/results/answers")
    files = sorted(answers_dir.glob("HHG-*.json"))

    files_processed = 0
    files_changed = 0
    pattern_counter = Counter()
    status_counter = Counter()

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        case = data.get("case", {})
        original_case_json = json.dumps(case, sort_keys=True)
        files_processed += 1

        # FIX A — Pattern field
        pattern = case.get("pattern", "")
        if "|" in pattern:
            candidates = [p.strip() for p in pattern.split("|")]
            chosen = None
            for c in candidates:
                if c in valid_patterns and c not in ("none", "unknown"):
                    chosen = c
                    break
            if not chosen:
                chosen = "undocumented" if case.get("verdict") == "fraud" else "none"
            case["pattern"] = chosen

        current_pattern = case.get("pattern", "")
        if current_pattern not in valid_patterns and current_pattern not in ("unknown",):
            if case.get("verdict") == "fraud":
                case["pattern"] = "undocumented"
            else:
                case["pattern"] = "none"

        # FIX B — Status field
        if case.get("status") == "open":
            verdict = case.get("verdict", "")
            if verdict == "fraud":
                case["status"] = "closed_fraud"
            elif verdict == "legitimate":
                case["status"] = "closed_legitimate"
            else:
                case["status"] = "escalated"

        pattern_counter[case.get("pattern", "")] += 1
        status_counter[case.get("status", "")] += 1

        if json.dumps(case, sort_keys=True) != original_case_json:
            files_changed += 1
            data["case"] = case
            f.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Files processed: {files_processed}")
    print(f"Files changed: {files_changed}")
    print(f"New pattern distribution: {dict(pattern_counter)}")
    print(f"New status distribution: {dict(status_counter)}")


if __name__ == "__main__":
    fix_answers()
