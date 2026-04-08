#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

CASES = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/runtime_regression_cases.json')
SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/runtime_regression_report.json')


def main():
    cases = json.loads(CASES.read_text())
    rows = []
    passes = 0
    for case in cases:
        out = subprocess.check_output(['python3', str(SELECT), case['question']], text=True)
        data = json.loads(out)
        preferred = (data.get('preferred_sources') or [None])[0]
        ok = preferred == case['expect_preferred_source']
        passes += int(ok)
        rows.append({
            'question': case['question'],
            'expect_preferred_source': case['expect_preferred_source'],
            'got_preferred_source': preferred,
            'ok': ok,
            'confidence': data.get('confidence'),
        })
    report = {'total': len(rows), 'pass': passes, 'results': rows}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
