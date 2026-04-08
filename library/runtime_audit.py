#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

QUESTIONS = [
    'Я не понимаю, куда мне двигаться в карьере и что вообще для меня призвание',
    'У нас с женой постоянные конфликты и скрытая обида',
    'Мне стыдно за себя и я чувствую отвращение к себе',
    'Я потерял смысл, дисциплину и направление',
    'Моя жизнь превращается в хаос, я всё больше спиваюсь и теряю контроль',
]
SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/runtime_audit_report.json')


def main():
    rows = []
    for q in QUESTIONS:
        out = subprocess.check_output(['python3', str(SELECT), q], text=True)
        data = json.loads(out)
        rows.append({
            'question': q,
            'preferred_sources': data.get('preferred_sources'),
            'theme': (data.get('selected_theme') or {}).get('name'),
            'principle': (data.get('selected_principle') or {}).get('name'),
            'pattern': (data.get('selected_pattern') or {}).get('name'),
            'confidence': data.get('confidence'),
        })
    report = {'cases': rows}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
