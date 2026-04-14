"""Runtime orchestrator -- coordinate all runtime modules via direct imports.

Restructured from: runtime_orchestrator.py
All subprocess calls replaced with direct Python imports.
"""
from __future__ import annotations

from library._core.runtime.frame import select_frame
from library._core.runtime.respond import respond
from library._core.runtime.voice import choose as choose_voice
from library._core.session.continuity import read as read_continuity
from library._core.session.state import build_user_profile, update_session
from library._core.session.checkpoint import log as log_checkpoint
from library._core.session.progress import estimate as estimate_progress
from library._core.session.reaction import estimate as estimate_reaction
from library._core.session.effectiveness import update as update_effectiveness
from library._core.session.context import assemble as assemble_context
from library._core.state_store import StateStore
from library.config import get_default_store
from library.utils import timing_context


def detect_mode(question):
    q = question.lower()
    practical_triggers = ['что мне делать', 'что делать', 'next step',
                          'практически', 'как мне', 'что дальше']
    deep_triggers = ['почему', 'разбери', 'объясни', 'помоги понять',
                     'что со мной происходит', 'в чём корень']
    if any(x in q for x in deep_triggers):
        return 'deep'
    if any(x in q for x in practical_triggers):
        return 'practical'
    if len(q) < 80:
        return 'practical'
    return 'deep'


def should_use_kb(question):
    q = question.lower()
    triggers = [
        'смысл', 'дисциплин', 'обид', 'стыд', 'отношен', 'конфликт',
        'карьер', 'призвание', 'хаос', 'вру', 'самообман',
        'туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры',
        'отклады', 'прокраст', 'жестк', 'расписан', 'график',
    ]
    return any(t in q for t in triggers)


def orchestrate(question, user_id: str = 'default',
                store: StateStore | None = None):
    store = store or get_default_store()

    with timing_context() as timings:
        result = _orchestrate_inner(question, user_id=user_id, store=store)
    result['_timings'] = timings
    return result


def _orchestrate_inner(question, user_id: str = 'default',
                       store: StateStore | None = None):
    mode = detect_mode(question)

    if not should_use_kb(question):
        return {
            'question': question,
            'mode': mode,
            'use_kb': False,
            'confidence': 'low',
            'action': 'answer-directly',
            'reason': ('Question does not strongly match '
                       'psychological/philosophical KB routes.'),
            'continuity': read_continuity(user_id=user_id, store=store),
        }

    build_user_profile(user_id=user_id, store=store)
    selected = select_frame(question, user_id=user_id, store=store)
    confidence = selected.get('confidence', 'low')
    continuity = read_continuity(user_id=user_id, store=store)
    progress = estimate_progress(question, user_id=user_id, store=store)
    reaction = estimate_reaction(question, user_id=user_id, store=store)

    if confidence == 'low':
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': confidence,
            'action': 'ask-clarifying-question',
            'reason': ('KB route is weak; clarification preferred '
                       'before forcing a frame.'),
            'selection': selected,
            'continuity': continuity,
        }

    theme_name = (selected.get('selected_theme') or {}).get('name') or ''
    pattern_name = (selected.get('selected_pattern') or {}).get('name') or ''
    principle_name = (selected.get('selected_principle') or {}).get('name') or ''
    blend = selected.get('source_blend') or {}
    source_blend_str = (f"{blend.get('primary', '')}"
                        f"->{blend.get('secondary', '')}")

    voice = choose_voice(question, theme=theme_name,
                         user_id=user_id, store=store) or 'default'
    if progress.get('recommended_voice_override'):
        voice = progress['recommended_voice_override']

    update_session(
        question,
        theme=theme_name,
        pattern=pattern_name,
        principle=principle_name,
        source_blend=source_blend_str,
        voice=voice,
        goal=theme_name,
        user_id=user_id,
        store=store,
    )

    action_step = ('narrow-burden'
                   if progress.get('recommended_response_mode') == 'narrow'
                   else 'normal-step')

    resolved_loop_summary = ''
    if continuity.get('resolved_loops'):
        first = continuity['resolved_loops'][0]
        if isinstance(first, dict):
            resolved_loop_summary = first.get('summary', '')
        else:
            resolved_loop_summary = str(first)

    log_checkpoint({
        'question': question,
        'theme': theme_name,
        'pattern': pattern_name,
        'principle': principle_name,
        'source_blend': source_blend_str,
        'voice': voice,
        'confidence': confidence,
        'action_step': action_step,
        'movement_estimate': progress.get('progress_state', 'unknown'),
        'user_reaction_estimate': reaction.get('user_reaction_estimate',
                                               'unknown'),
        'resolved_loop_if_any': resolved_loop_summary,
        'session_goal': theme_name,
        'recommended_next_mode': progress.get('recommended_response_mode',
                                              'normal'),
    }, user_id=user_id, store=store)

    primary = blend.get('primary', '')
    progress_state = progress.get('progress_state')
    reaction_est = reaction.get('user_reaction_estimate')

    if progress_state == 'moving' and reaction_est == 'accepting':
        outcome = 'helpful'
    elif progress_state == 'fragile' or reaction_est == 'ambiguous':
        outcome = 'neutral'
    else:
        outcome = 'resisted'

    if primary:
        update_effectiveness(source=primary, outcome=outcome,
                             route=theme_name, user_id=user_id, store=store)

    assemble_context(user_id=user_id, store=store)

    effective_mode = mode if mode in {'quick', 'practical', 'deep'} else 'deep'
    response = respond(question, mode=effective_mode, voice=voice,
                       user_id=user_id, store=store)

    return {
        'question': question,
        'mode': mode,
        'use_kb': True,
        'confidence': confidence,
        'action': 'respond-with-kb',
        'selection': selected,
        'continuity': continuity,
        'progress': progress,
        'reaction': reaction,
        'response': response,
    }
