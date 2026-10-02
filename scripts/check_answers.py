import json
from pathlib import Path

for f in sorted(Path('C:/HHGoa/results/answers').glob('HHG-*.json')):
    d = json.loads(f.read_text(encoding='utf-8'))
    c = d['case']
    ev = c.get('evidence', [])
    http_errors = 0
    for e in ev:
        if 'HTTPConnection' in str(e.get('claim', '')):
            http_errors += 1
    marker = 'OK' if http_errors == 0 and c.get('written_to_graph') else 'FAIL'
    status = c.get('status', '?')
    pattern = c.get('pattern', '?')
    print(f"{f.stem} [{marker}] status={status} pattern={pattern} http_errors={http_errors}")