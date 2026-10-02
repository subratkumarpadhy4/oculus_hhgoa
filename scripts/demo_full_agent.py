import csv, sys, json, time
sys.path.insert(0, 'C:/HHGoa')
from agent.graph import run_case
from agent.answer_generator import generate_answer_file

with open('C:/HHGoa/data/case_pack.csv', encoding='utf-8-sig') as f:
    cases = list(csv.DictReader(f))

case = cases[0]  # HHG-001
print('=' * 70)
print('HHGOA AGENTIC FRAUD INVESTIGATION — FULL DEMO')
print('Case:', case['case_id'])
print('Trigger Type:', case['trigger_type'])
print('Trigger Text:', case['trigger_text'])
print('Flagged Txn:', case['flagged_txn_id'])
print('Customer:', case['customer_id'])
print('Card:', case['card_id'])
print('=' * 70)

start = time.time()
state = run_case(case)
elapsed = time.time() - start

answer = generate_answer_file(state)

print()
print('=' * 70)
print('AGENT TRACE (node-by-node)')
print('=' * 70)
for entry in state.get('trace', []):
    node = entry.get('node', '?')
    ts = entry.get('timestamp', '')
    details = entry.get('details', '')
    print(f'  [{ts}] {node}: {details}')

print()
print('=' * 70)
print('FINAL ANSWER FILE')
print('=' * 70)
print(json.dumps(answer, indent=2, default=str))

print()
print(f'Total elapsed: {elapsed:.1f}s')
