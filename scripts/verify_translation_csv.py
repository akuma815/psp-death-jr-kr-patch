"""Read-only validation of translator edits against the frozen extraction snapshot."""
import csv
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'workspace/text'
baseline = json.loads((folder / 'english_script_source.json').read_text(encoding='utf-8'))
with (folder / 'DeathJr_English_Script.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == len(baseline), 'Row count changed'
by_id = {r['id']: r for r in rows}
assert len(by_id) == len(rows), 'Duplicate ID'
warnings = []
for original in baseline:
    row = by_id[original['id']]
    for key, value in original.items():
        if key not in ('translation', 'status', 'notes'):
            assert row[key] == str(value), (row['id'], 'immutable column changed', key)
    if row['translation']:
        tokens = re.findall(r'\{BYTE_[0-9A-F]{2}\}|%(?:[-+0 #]*\d*(?:\.\d+)?[a-zA-Z])', row['translation'])
        if sorted(tokens) != sorted(original['tokens'].split()):
            warnings.append({'id': row['id'], 'issue': 'Token change requires review'})
print(json.dumps({'rows': len(rows), 'translated': sum(bool(r['translation']) for r in rows), 'source_integrity': 'PASS', 'warnings': warnings}, ensure_ascii=True, indent=2))
