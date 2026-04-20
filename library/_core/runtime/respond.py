"""Respond with KB -- synthesize, render, and update continuity.

Restructured from: respond_with_kb.py
"""
from __future__ import annotations

from library._core.runtime.grounding import (
    build_strict_clarification, can_render_strict,
)
from library._core.session.continuity import update as update_continuity, load as load_continuity
from library._core.state_store import StateStore
from library.config import canonical_user_id, VOICE_MODES
from library.utils import ensure_trace_context, load_json, log_event, timed, traced_stage


_voice_modes_cache: dict | None = None

_VOICE_FALLBACK = {
    'opening': 'Сначала нужно точно назвать, что здесь ломается.',
    'pattern': 'Под этим, похоже, работает следующий паттерн.',
    'responsibility': 'А значит, избегаемая ответственность выглядит примерно так.',
    'step': 'Следующий практический шаг такой.',
    'longer': 'А более глубокая коррекция выглядит так.',
}

def load_voice(mode_name='default'):
    global _voice_modes_cache
    if _voice_modes_cache is None:
        raw = load_json(VOICE_MODES) or {}
        _voice_modes_cache = raw if isinstance(raw, dict) else {}
    if _voice_modes_cache:
        entry = _voice_modes_cache.get(mode_name) or _voice_modes_cache.get('default')
        if isinstance(entry, dict):
            return {**_VOICE_FALLBACK, **entry}
        return _VOICE_FALLBACK
    return _VOICE_FALLBACK


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
    patterns = continuity.get('user_patterns') or []
    themes = continuity.get('recurring_themes') or []
    resolved = continuity.get('resolved_loops') or []
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
    policy = data.get('selection_policy') or {}
    if not policy.get('suppress_continuity'):
        lines += render_continuity_block(continuity)
    return '\n'.join(lines).strip()


def render(data, continuity, mode='deep', voice_mode='default'):
    if mode == 'quick':
        return render_quick(data)
    if mode == 'practical':
        return render_practical(data)
    return render_deep(data, continuity, voice_mode=voice_mode)


def render_plan(plan, mode: str | None = None, voice_mode: str | None = None) -> str:
    """Render the user-facing text from the authoritative grounded plan."""
    store = getattr(plan, 'store', None)
    user_id = canonical_user_id(plan.user_id)
    with traced_stage('runtime.render', store=store, user_id=user_id):
        if not plan.decision.allow_answer:
            text = plan.direct_response or plan.clarifying_question or ''
            log_event(
                'render.short_circuit',
                store=store,
                user_id=user_id,
                action=plan.action,
                response_preview=text[:180],
                response_length=len(text),
            )
            return text
        data = plan.synthesis or {}
        effective_mode = mode or plan.mode
        if not can_render_strict(data, mode=effective_mode):
            text = build_strict_clarification(data, mode=effective_mode)
            log_event(
                'render.strict_clarification',
                store=store,
                user_id=user_id,
                mode=effective_mode,
                response_preview=text[:180],
                response_length=len(text),
            )
            return text

        selected = data.get('raw_selection', {})
        theme = ((selected.get('selected_theme') or {}).get('name'))
        pattern = ((selected.get('selected_pattern') or {}).get('name'))

        if data.get('confidence') in {'medium', 'high'}:
            open_loop = data.get('core_problem', '')
            update_continuity(question=plan.question, theme=theme or '',
                              pattern=pattern or '', open_loop=open_loop,
                              user_id=user_id, store=store)

        continuity = load_continuity(user_id=user_id, store=store)
        text = render(
            data,
            continuity,
            mode=effective_mode,
            voice_mode=voice_mode or plan.voice_mode or 'default',
        )
        log_event(
            'render.completed',
            store=store,
            user_id=user_id,
            mode=effective_mode,
            voice_mode=voice_mode or plan.voice_mode or 'default',
            response_preview=text[:180],
            response_length=len(text),
        )
        return text


@timed('respond')
def respond(question, mode: str | None = None, voice='default',
            user_id: str = 'default', store: StateStore | None = None,
            plan=None,
            frame: dict | None = None, progress: dict | None = None,
            data: dict | None = None):
    """Main entry point -- synthesize, update continuity, render.

    Returns the rendered text string.
    """
    user_id = canonical_user_id(user_id)
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='response', question=question):
        log_event('respond.entry', store=store, user_id=user_id,
                  requested_mode=mode or '', voice_mode=voice)
        if plan is None:
            from library._core.runtime.planner import build_answer_plan
            plan = build_answer_plan(question, user_id=user_id, store=store, purpose='response')
            setattr(plan, 'store', store)
            return render_plan(plan, mode=mode, voice_mode=voice)

        if data is not None:
            plan.synthesis = data
        if frame is not None:
            plan.selection = frame
        if progress is not None:
            plan.progress = progress
        setattr(plan, 'store', store)
        return render_plan(plan, mode=mode, voice_mode=voice)
