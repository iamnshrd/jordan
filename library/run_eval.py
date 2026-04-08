#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

CASES = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/eval_cases.json')
SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')
RESPOND = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/respond_with_kb.py')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/eval_report.json')


def run_case(case):
    sel_out = subprocess.check_output(['python3', str(SELECT), case['question']], text=True)
    data = json.loads(sel_out)
    resp_out = subprocess.check_output(['python3', str(RESPOND), case['question']], text=True)
    got_theme = (data.get('selected_theme') or {}).get('name')
    got_principle = (data.get('selected_principle') or {}).get('name')
    got_pattern = (data.get('selected_pattern') or {}).get('name')
    acceptable_themes = case.get('acceptable_themes', [case['expect_theme']])
    acceptable_principles = case.get('acceptable_principles', [case['expect_principle']])
    acceptable_patterns = case.get('acceptable_patterns', [case['expect_pattern']])
    quote_type = None
    if 'Цитата:' in resp_out:
        quote_line = [line for line in resp_out.splitlines() if line.startswith('Цитата:')]
        if quote_line:
            quote_text = quote_line[0]
            if 'порядок у себя дома' in quote_text.lower() or 'наполнено смыслом' in quote_text.lower():
                quote_type = 'discipline-quote'
            elif 'молчание' in quote_text.lower() or 'трудное' in quote_text.lower() or 'не давайте детям' in quote_text.lower() or 'невзлюбить' in quote_text.lower():
                quote_type = 'relationship-quote'
            elif 'стыд' in quote_text.lower() or 'никчемности' in quote_text.lower():
                quote_type = 'shame-quote'
            elif 'правду' in quote_text.lower() or 'не лги' in quote_text.lower():
                quote_type = 'principle-quote'
    quote_ok = True
    if case.get('expect_quote_type'):
        quote_ok = quote_type == case['expect_quote_type']
    return {
        'id': case['id'],
        'question': case['question'],
        'expect_theme': case['expect_theme'],
        'acceptable_themes': acceptable_themes,
        'got_theme': got_theme,
        'theme_ok': got_theme in acceptable_themes,
        'expect_principle': case['expect_principle'],
        'acceptable_principles': acceptable_principles,
        'got_principle': got_principle,
        'principle_ok': got_principle in acceptable_principles,
        'expect_pattern': case['expect_pattern'],
        'acceptable_patterns': acceptable_patterns,
        'got_pattern': got_pattern,
        'pattern_ok': got_pattern in acceptable_patterns,
        'expect_quote_type': case.get('expect_quote_type'),
        'got_quote_type': quote_type,
        'quote_ok': quote_ok,
        'confidence': data.get('confidence'),
        'theme_reason': data.get('selected_theme_reason'),
        'principle_reason': data.get('selected_principle_reason'),
        'pattern_reason': data.get('selected_pattern_reason'),
    }


def main():
    cases = json.loads(CASES.read_text())
    results = [run_case(c) for c in cases]
    summary = {
        'total': len(results),
        'theme_pass': sum(r['theme_ok'] for r in results),
        'principle_pass': sum(r['principle_ok'] for r in results),
        'pattern_pass': sum(r['pattern_ok'] for r in results),
        'quote_pass': sum(r['quote_ok'] for r in results),
        'all_pass': sum(r['theme_ok'] and r['principle_ok'] and r['pattern_ok'] and r['quote_ok'] for r in results),
        'results': results,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
