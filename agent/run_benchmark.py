import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("C:/HHGoa")))

from agent.graph import run_case

CASE_PACK = Path("C:/HHGoa/data/case_pack.csv")
OUTPUT_DIR = Path("C:/HHGoa/results/cases")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(CASE_PACK, encoding="utf-8-sig") as f:
    cases = list(csv.DictReader(f))

print(f"Running {len(cases)} benchmark cases...")
results = []

for i, case in enumerate(cases, 1):
    print(f"\n[{i}/{len(cases)}] {case['case_id']} ({case['trigger_type']})")
    start = time.time()
    try:
        state = run_case(case)
        elapsed = time.time() - start
        output = {
            "case_id": case["case_id"],
            "trigger_type": case["trigger_type"],
            "final_status": state.get("final_case_status"),
            "sufficiency": state.get("sufficiency"),
            "evidence_rounds": state.get("evidence_rounds"),
            "llm_findings": state.get("llm_findings"),
            "recommended_actions": state.get("recommended_actions"),
            "approval_route": state.get("approval_route"),
            "evidence_requests": state.get("evidence_requests"),
            "elapsed_seconds": round(elapsed, 2)
        }
        results.append(output)
        
        output_file = OUTPUT_DIR / f"{case['case_id']}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"  status={output['final_status']} sufficiency={output['sufficiency']} rounds={output['evidence_rounds']}")
        print(f"  actions={[a['action'] for a in output.get('recommended_actions', [])]}")
        print(f"  elapsed={elapsed:.1f}s")
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"case_id": case["case_id"], "error": str(e)})

summary_file = OUTPUT_DIR / "_summary.json"
with open(summary_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n=== ALL {len(cases)} CASES COMPLETE ===")
print(f"Results written to: {OUTPUT_DIR}")
print(f"Summary: {summary_file}")
