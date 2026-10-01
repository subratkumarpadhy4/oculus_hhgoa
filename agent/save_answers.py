"""
save_answers.py
---------------
Runs the 20 benchmark cases with NVIDIA NIM and saves submission-ready answer JSON files
to results/answers/. Skips cases whose answer files already exist.
"""

import csv
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path("C:/HHGoa")))

from agent.answer_generator import generate_answer_file
from agent.graph import run_case

CASE_PACK_PATH = Path("C:/HHGoa/data/case_pack.csv")
ANSWERS_DIR = Path("C:/HHGoa/results/answers")
ANSWERS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    if not CASE_PACK_PATH.exists():
        print(f"Error: case pack file not found at {CASE_PACK_PATH}", flush=True)
        sys.exit(1)

    with open(CASE_PACK_PATH, mode="r", encoding="utf-8-sig") as f:
        cases = list(csv.DictReader(f))

    print(f"Loaded {len(cases)} benchmark cases from {CASE_PACK_PATH}", flush=True)
    print(f"Saving answer files to: {ANSWERS_DIR}\n", flush=True)

    summary = []
    skipped_count = 0
    completed_count = 0
    errored_count = 0
    total_start = time.time()

    for idx, case_row in enumerate(cases, 1):
        case_id = case_row.get("case_id", f"CASE-{idx}")
        output_file = ANSWERS_DIR / f"{case_id}.json"

        # Check if already completed
        if output_file.exists():
            try:
                with open(output_file, mode="r", encoding="utf-8") as existing_f:
                    existing_data = json.load(existing_f)
                status = existing_data.get("case", {}).get("status", "unknown")
                verdict = existing_data.get("case", {}).get("verdict", "unknown")
                pattern = existing_data.get("case", {}).get("pattern", "unknown")
                actions = [a.get("action") for a in existing_data.get("next_best_actions", {}).get("final", [])]
                routes = [a.get("route") for a in existing_data.get("next_best_actions", {}).get("final", []) if a.get("route")]
                overall_route = "L2" if "L2" in routes else ("L1" if "L1" in routes else "auto")
                sar_file = existing_data.get("sar", {}).get("file", False)

                summary.append({
                    "case_id": case_id,
                    "status": status,
                    "verdict": verdict,
                    "pattern": pattern,
                    "actions": actions,
                    "approval_route": overall_route,
                    "sar_filed": sar_file,
                    "elapsed_s": existing_data.get("latency_s", 0.0),
                    "skipped": True
                })
            except Exception:
                pass

            skipped_count += 1
            print(f"[{idx}/{len(cases)}] {case_id} ... SKIPPED (already exists)", flush=True)
            continue

        # Run the case
        print(f"[{idx}/{len(cases)}] {case_id} ... running...", end=" ", flush=True)
        start_t = time.time()
        try:
            state = run_case(case_row)
            answer_data = generate_answer_file(state)

            with open(output_file, mode="w", encoding="utf-8") as out_f:
                json.dump(answer_data, out_f, indent=2, ensure_ascii=False)

            status = answer_data.get("case", {}).get("status", "unknown")
            verdict = answer_data.get("case", {}).get("verdict", "unknown")
            sar_file = answer_data.get("sar", {}).get("file", False)
            actions = [a.get("action") for a in answer_data.get("next_best_actions", {}).get("final", [])]
            routes = [a.get("route") for a in answer_data.get("next_best_actions", {}).get("final", []) if a.get("route")]
            overall_route = "L2" if "L2" in routes else ("L1" if "L1" in routes else "auto")
            pattern = answer_data.get("case", {}).get("pattern", "unknown")
            elapsed = round(time.time() - start_t, 2)

            completed_count += 1
            print(f"status={status}, actions={actions}, sar={sar_file} [{elapsed}s]", flush=True)
            summary.append({
                "case_id": case_id,
                "status": status,
                "verdict": verdict,
                "pattern": pattern,
                "actions": actions,
                "approval_route": overall_route,
                "sar_filed": sar_file,
                "elapsed_s": elapsed,
                "skipped": False
            })
        except Exception as err:
            elapsed = round(time.time() - start_t, 2)
            errored_count += 1
            print(f"ERROR: {err} [{elapsed}s]", flush=True)
            summary.append({
                "case_id": case_id,
                "error": str(err),
                "elapsed_s": elapsed,
                "skipped": False
            })

    total_elapsed = round(time.time() - total_start, 2)
    summary_file = ANSWERS_DIR / "_answers_summary.json"
    with open(summary_file, mode="w", encoding="utf-8") as sf:
        json.dump(summary, sf, indent=2, ensure_ascii=False)

    # Compute detailed statistics across all 20 cases
    valid_cases = [s for s in summary if "error" not in s]

    status_counts = Counter(s.get("status") for s in valid_cases)
    pattern_counts = Counter(s.get("pattern") for s in valid_cases)
    route_counts = Counter(s.get("approval_route") for s in valid_cases)
    action_counts = Counter()
    for s in valid_cases:
        for a in s.get("actions", []):
            action_counts[a] += 1
    sar_count = sum(1 for s in valid_cases if s.get("sar_filed"))
    avg_elapsed = round(sum(s.get("elapsed_s", 0) for s in summary) / len(summary), 2) if summary else 0.0

    print("\n" + "=" * 60, flush=True)
    print("BENCHMARK SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"Total cases: {len(cases)}", flush=True)
    print(f"Completed in this run: {completed_count}", flush=True)
    print(f"Skipped: {skipped_count}", flush=True)
    print(f"Errored: {errored_count}", flush=True)
    print(f"Status distribution: {dict(status_counts)}", flush=True)
    print(f"Pattern distribution: {dict(pattern_counts)}", flush=True)
    print(f"Action distribution: {dict(action_counts)}", flush=True)
    print(f"Approval route distribution: {dict(route_counts)}", flush=True)
    print(f"SARs filed: {sar_count}", flush=True)
    print(f"Average elapsed time per case: {avg_elapsed}s (Total: {total_elapsed}s)", flush=True)
    print("=" * 60, flush=True)
    print(f"Summary written to: {summary_file}", flush=True)


if __name__ == "__main__":
    main()
