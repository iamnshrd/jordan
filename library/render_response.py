#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

SYNTH = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/synthesize_response.py')


def synthesize(question):
    out = subprocess.check_output(['python3', str(SYNTH), question], text=True)
    return json.loads(out)


def render(question):
    data = synthesize(question)
    lines = []
    lines.append('What the problem actually is')
    lines.append(data.get('core_problem', '—'))
    lines.append('')
    lines.append('What pattern is likely running')
    lines.append(data.get('relevant_pattern', '—'))
    lines.append('')
    lines.append('What responsibility is being avoided')
    if data.get('selected_principle_reason') == 'discipline/order tie-break':
        lines.append('Скорее всего, ты перестал добровольно наводить локальный порядок и ждёшь, что мотивация вернётся раньше структуры.')
    elif data.get('selected_principle_reason') == 'meaning-direction tie-break':
        lines.append('Похоже, что ты уклоняешься от выбора направления и от ответственности, которая идёт вместе с ним.')
    else:
        lines.append('Есть ощущение, что часть ответственности была отложена, а вместе с ней распалась и опора.')
    lines.append('')
    lines.append('What stabilizing principle applies')
    lines.append(data.get('guiding_principle', '—'))
    lines.append('')
    lines.append('Supporting quote')
    lines.append(data.get('supporting_quote') or 'Подходящая цитата пока не выбрана достаточно надёжно.')
    lines.append('')
    lines.append('Immediate next step')
    lines.append(data.get('practical_next_step', '—'))
    lines.append('')
    lines.append('Longer-term correction')
    if 'meaning' in (data.get('raw_selection', {}).get('selected_theme') or {}).get('name', ''):
        lines.append('Тебе нужно не ждать возвращения смысла как чувства, а заново строить его через цель, дисциплину и повторяющееся действие.')
    elif 'resentment' in (data.get('raw_selection', {}).get('selected_theme') or {}).get('name', ''):
        lines.append('Долгосрочно придётся отделить реальную несправедливость от горечи, которая выросла из избегания и бессилия.')
    else:
        lines.append('Долгосрочная коррекция требует более честной структуры жизни, а не только эмоционального облегчения.')
    lines.append('')
    lines.append(f"Confidence: {data.get('confidence','unknown')}")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(render(args.question))


if __name__ == '__main__':
    main()
