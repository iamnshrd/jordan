"""Render mentor follow-up messages."""

from __future__ import annotations


def _render_effectiveness(snapshot: dict) -> str:
    best = snapshot.get('best') or []
    worst = snapshot.get('worst') or []
    lines = []
    if best:
        lines.append('Лучше всего обычно заходят: ' + '; '.join(x.get('key', '') for x in best[:2] if x.get('key')))
    if worst:
        lines.append('Хуже всего обычно заходят: ' + '; '.join(x.get('key', '') for x in worst[:2] if x.get('key')))
    return '\n'.join(lines).strip()


def _render_commitment_summary(summary: dict) -> str:
    top = summary.get('top_open') or []
    if not top:
        return ''
    bullets = []
    for item in top[:3]:
        bits = [item.get('summary', '')]
        if item.get('due_hint'):
            bits.append(f"срок: {item.get('due_hint')}")
        if item.get('strength'):
            bits.append(f"тип: {item.get('strength')}")
        bullets.append('— ' + ' | '.join([x for x in bits if x]))
    resolved = summary.get('top_resolved') or []
    movement = summary.get('movement_signal', 'stuck')
    movement_line = 'Сейчас есть движение, потому что ты уже кое-что закрыл.' if movement == 'moving' else 'Сейчас картина больше похожа на зависание, чем на движение.'
    lines = [
        'Короткая сводка по твоим обещаниям:',
        movement_line,
        *bullets,
    ]
    if resolved:
        lines.append('Недавно закрыто: ' + '; '.join(x.get('summary', '') for x in resolved[:2] if x.get('summary')))
    if summary.get('next_focus'):
        lines.append('Главный фокус сейчас: ' + summary.get('next_focus', ''))
    lines.append('Что из этого ты реально закроешь первым?')
    return '\n'.join(lines).strip()


def render_event(event: dict) -> str:
    if not event:
        return ''
    if event.get('type') == 'mentor-summary':
        body = _render_commitment_summary(event.get('commitment_summary') or {})
        eff = _render_effectiveness(event.get('effectiveness_summary') or {})
        return '\n'.join([x for x in [body, eff] if x]).strip()
    return ''
