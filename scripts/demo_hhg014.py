import csv, sys, json, time
sys.path.insert(0, 'C:/HHGoa')
from agent.graph import run_case
from agent.answer_generator import generate_answer_file

with open('C:/HHGoa/data/case_pack.csv', encoding='utf-8-sig') as f:
    cases = list(csv.DictReader(f))

case = cases[13]  # HHG-014
print('=' * 60)
print('Running case ' + case['case_id'] + ' (trigger: ' + case['trigger_type'] + ')')
print('=' * 60)

start = time.time()
state = run_case(case)
elapsed = time.time() - start

answer = generate_answer_file(state)
print()
print('=' * 60)
print('FINAL ANSWER FILE')
print('=' * 60)
print(json.dumps(answer, indent=2, default=str))
print()
print('Total elapsed: ' + str(round(elapsed, 1)) + 's')