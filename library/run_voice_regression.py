#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

CASES = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/voice_regression_cases.json')
RESPOND = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/respond_with_kb.py')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/voice_regression_report.json')


def main():
    cases = json.loads(CASES.read_text())
    rows = []
    passes = 0
    for case in cases:
        out = subprocess.check_output([
            'python3', str(RESPOND), case['question'], '--mode', 'deep', '--voice', case['voice']
        ], text=True)
        ok = all(token in out for token in case['must_include'])
        passes += int(ok)
        rows.append({
            'voice': case['voice'],
            'question': case['question'],
            'must_include': case['must_include'],
            'ok': ok,
        })
    report = {'total': len(rows), 'pass': passes, 'results': rows}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
