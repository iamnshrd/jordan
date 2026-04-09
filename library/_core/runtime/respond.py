"""Respond with KB — synthesize, render, and update continuity.

Restructured from: respond_with_kb.py
"""
from library._core.runtime.synthesize import synthesize
from library._core.session.continuity import update as update_continuity, load as load_continuity
from library.config import VOICE_MODES
from library.utils import load_json


def load_voice(mode_name='default'):
    data = load_json(VOICE_MODES)
    if data:
        return data.get(mode_name) or data.get('default')
    return {
        'opening': 'Сначала нужно точно назвать, что здесь ломается.',
        'pattern': 'Под этим, похоже, работает следующий паттерн.',
        'responsibility': 'А значит, избегаемая ответственность выглядит примерно так.',
        'step': 'Следующий практический шаг такой.',
        'longer': 'А более глубокая коррекция выглядит так.',
    }


def render_quick(data):
    return '\n'.join([
        data.get('core_problem', '—'),
        '',
        'Следующий шаг: ' + data.get('practical_next_step', '—'),
    ]).strip()


def render_practical(data):
    return '\n'.join([
        data.get('core_problem', '—'),
        '',
        'Опорный принцип: ' + data.get('guiding_principle', '—'),
        '',
        'Следующий шаг:',
        data.get('practical_next_step', '—'),
        '',
        'Что менять глубже:',
        data.get('longer_term_correction', '—'),
    ]).strip()


def render_continuity_block(continuity):
    lines = []
    patterns = continuity.get('user_patterns', [])
    themes = continuity.get('recurring_themes', [])
    resolved = continuity.get('resolved_loops', [])
    if patterns or themes or resolved:
        lines.append('')
        lines.append('Контекст continuity:')
        if themes:
            theme_names = [
                t['name'] if isinstance(t, dict) else str(t)
                for t in themes[:5]
            ]
            lines.append('- recurring themes: ' + ', '.join(theme_names))
        if patterns:
            pattern_names = [
                p['name'] if isinstance(p, dict) else str(p)
                for p in patterns[:5]
            ]
            lines.append('- recurring patterns: ' + ', '.join(pattern_names))
        if resolved:
            resolved_names = [
                r['summary'] if isinstance(r, dict) else str(r)
                for r in resolved[:3]
            ]
            lines.append('- recently resolved: ' + '; '.join(resolved_names))
    return lines


def render_deep(data, continuity, voice_mode='default'):
    voice = load_voice(voice_mode)
    lines = [
        voice['opening'],
        data.get('core_problem', '—'),
        '',
        voice['pattern'],
        data.get('relevant_pattern', '—'),
        '',
        voice['responsibility'],
        data.get('responsibility_avoided', '—'),
        '',
        'Поэтому опорный принцип здесь не в абстрактном героизме, а в более узкой и требовательной дисциплине.',
        data.get('guiding_principle', '—'),
    ]
    if data.get('supporting_quote'):
        lines += ['', 'Цитата: ' + data['supporting_quote']]
    blend = data.get('source_blend') or {}
    if blend.get('primary') and blend.get('secondary'):
        lines += ['', f"Источник рамки: {blend['primary']} -> {blend['secondary']}"]
    lines += [
        '',
        voice['step'],
        data.get('practical_next_step', '—'),
        '',
        voice['longer'],
        data.get('longer_term_correction', '—'),
    ]
    lines += render_continuity_block(continuity)
    return '\n'.join(lines).strip()


def render(data, continuity, mode='deep', voice_mode='default'):
    if mode == 'quick':
        return render_quick(data)
    if mode == 'practical':
        return render_practical(data)
    return render_deep(data, continuity, voice_mode=voice_mode)


def respond(question, mode='deep', voice='default'):
    """Main entry point — synthesize, update continuity, render.

    Returns the rendered text string.
    """
    data = synthesize(question)
    selected = data.get('raw_selection', {})
    theme = ((selected.get('selected_theme') or {}).get('name'))
    pattern = ((selected.get('selected_pattern') or {}).get('name'))

    if data.get('confidence') in {'medium', 'high'}:
        open_loop = data.get('core_problem', '')
        update_continuity(question, theme=theme or '', pattern=pattern or '',
                          open_loop=open_loop)

    continuity = load_continuity()
    return render(data, continuity, mode=mode, voice_mode=voice)
