"""Simple response renderer — synthesize and format as text.

Restructured from: render_response.py
"""
from library._core.runtime.synthesize import synthesize


def render(question):
    """Render a full response for *question*.  Returns a text string."""
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
        lines.append('Скорее всего, ты перестал добровольно наводить '
                     'локальный порядок и ждёшь, что мотивация вернётся '
                     'раньше структуры.')
    elif data.get('selected_principle_reason') == 'meaning-direction tie-break':
        lines.append('Похоже, что ты уклоняешься от выбора направления '
                     'и от ответственности, которая идёт вместе с ним.')
    else:
        lines.append('Есть ощущение, что часть ответственности была '
                     'отложена, а вместе с ней распалась и опора.')
    lines.append('')

    lines.append('What stabilizing principle applies')
    lines.append(data.get('guiding_principle', '—'))
    lines.append('')

    lines.append('Supporting quote')
    lines.append(data.get('supporting_quote')
                 or 'Подходящая цитата пока не выбрана достаточно надёжно.')
    lines.append('')

    lines.append('Immediate next step')
    lines.append(data.get('practical_next_step', '—'))
    lines.append('')

    lines.append('Longer-term correction')
    theme_name = (
        (data.get('raw_selection', {}).get('selected_theme') or {})
        .get('name', '')
    )
    if 'meaning' in theme_name:
        lines.append('Тебе нужно не ждать возвращения смысла как чувства, '
                     'а заново строить его через цель, дисциплину и '
                     'повторяющееся действие.')
    elif 'resentment' in theme_name:
        lines.append('Долгосрочно придётся отделить реальную '
                     'несправедливость от горечи, которая выросла из '
                     'избегания и бессилия.')
    else:
        lines.append('Долгосрочная коррекция требует более честной '
                     'структуры жизни, а не только эмоционального '
                     'облегчения.')
    lines.append('')

    lines.append(f"Confidence: {data.get('confidence', 'unknown')}")
    return '\n'.join(lines)
