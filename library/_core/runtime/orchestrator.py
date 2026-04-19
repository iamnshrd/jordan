"""Runtime orchestrator -- coordinate all runtime modules via direct imports.

Restructured from: runtime_orchestrator.py
All subprocess calls replaced with direct Python imports.
"""
from __future__ import annotations

from library._core.runtime.frame import select_frame
from library._core.runtime.respond import respond
from library._core.runtime.llm_prompt import build_prompt
from library._core.runtime.retrieval_validator import validate_chunks, get_relevance_judge
from library._core.runtime.voice import choose as choose_voice
from library._core.runtime.guardrails import detect_out_of_domain, maybe_reset_out_of_domain_streak
from library._core.session.continuity import read as read_continuity, load as load_continuity
from library._core.session.state import build_user_profile, update_session
from library._core.session.checkpoint import log as log_checkpoint
from library._core.session.progress import estimate as estimate_progress
from library._core.session.reaction import estimate as estimate_reaction
from library._core.session.effectiveness import update as update_effectiveness
from library._core.session.context import assemble as assemble_context
from library._core.state_store import StateStore
from library._core.mentor.checkins import record_reply
from library._core.mentor.commitments import record_commitment, maybe_resolve_from_reply
from library.config import get_default_store, canonical_user_id
import logging
from library.utils import timing_context, get_threshold

log = logging.getLogger('jordan')


_PRACTICAL_TRIGGERS = ['что мне делать', 'что делать', 'next step',
                       'практически', 'как мне', 'что дальше']
_DEEP_TRIGGERS = ['почему', 'разбери', 'объясни', 'помоги понять',
                  'что со мной происходит', 'в чём корень']

_mode_classifier = None
_kb_classifier = None


def set_mode_classifier(fn):
    """Register an LLM-based mode classifier: fn(question) -> 'deep'|'practical'|'quick'."""
    global _mode_classifier
    _mode_classifier = fn


def set_kb_classifier(fn):
    """Register an LLM-based KB router: fn(question) -> bool."""
    global _kb_classifier
    _kb_classifier = fn


def detect_mode(question):
    if _mode_classifier is not None:
        try:
            return _mode_classifier(question)
        except Exception:
            log.debug('LLM mode classifier failed, using heuristic')
    q = question.lower()
    if any(x in q for x in _DEEP_TRIGGERS):
        return 'deep'
    if any(x in q for x in _PRACTICAL_TRIGGERS):
        return 'practical'
    if len(q) < get_threshold('detect_mode_short_length', 80):
        return 'practical'
    return 'deep'


def should_use_kb(question):
    """Jordan is KB-first: all non-empty questions should go through retrieval."""
    q = (question or '').strip()
    if not q:
        return False
    if _kb_classifier is not None:
        try:
            decision = _kb_classifier(question)
            if decision is False:
                log.debug('KB classifier requested direct path, but KB-only mode keeps retrieval enabled')
        except Exception:
            log.debug('LLM KB classifier failed, using KB-only default')
    return True


def _build_kb_only_clarification(question: str, *,
                                 reason: str = '',
                                 validation: dict | None = None,
                                 selected: dict | None = None) -> str:
    """Return a non-generative clarification when DB grounding is weak."""
    avg = (validation or {}).get('avg_relevance')
    selected = selected or {}
    route_name = selected.get('route_name') or 'general'

    if not (question or '').strip():
        return ('Сформулируй один конкретный вопрос по материалам базы: тезис, '
                'цитату, книгу или проблему, которую нужно разобрать.')

    if reason.startswith('KB retrieval error'):
        return ('Сейчас я не могу надёжно опереться на базу знаний из-за ошибки '
                'retrieval. Повтори запрос чуть уже: укажи тему, цитату или '
                'источник, который нужно разобрать.')

    if avg is not None and avg <= 0.0:
        return ('В текущей базе я не вижу прямой опоры для уверенного ответа. '
                'Уточни, о каком тезисе, книге, цитате или жизненной проблеме '
                'из библиотеки идёт речь.')

    if route_name == 'general':
        return ('Я не хочу достраивать ответ вне базы. Уточни вопрос через '
                'конкретный тезис, источник или сформулируй проблему точнее.')

    return ('Опора на базу пока слишком слабая для честного ответа. '
            'Сузь вопрос до одного конфликта, паттерна, цитаты или книги, '
            'которую нужно разобрать.')


def orchestrate(question, user_id: str = 'default',
                store: StateStore | None = None):
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    if question.strip():
        record_reply(question, user_id=user_id, store=store)
        maybe_resolve_from_reply(question, user_id=user_id, store=store)

    with timing_context() as timings:
        result = _orchestrate_inner(question, user_id=user_id, store=store)
    result['_timings'] = timings
    return result


def orchestrate_for_llm(question: str, user_id: str = 'default',
                        store: StateStore | None = None) -> dict:
    """Build an LLM-ready prompt bundle for OpenClaw.

    Returns a dict with ``system``, ``user``, ``synthesis``, ``continuity``,
    plus orchestration metadata (``mode``, ``use_kb``, ``action``).
    Guardrail replies may bypass retrieval. All other questions must either
    produce a KB-backed prompt or a clarification that explicitly avoids
    model-only free generation.
    """
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()

    if question.strip():
        record_reply(question, user_id=user_id, store=store)
        maybe_resolve_from_reply(question, user_id=user_id, store=store)

    guardrail = detect_out_of_domain(question, user_id=user_id, store=store)
    if not guardrail:
        maybe_reset_out_of_domain_streak(question, user_id=user_id, store=store)
    if guardrail:
        return {
            'system': '',
            'user': question,
            'synthesis': None,
            'continuity': load_continuity(user_id=user_id, store=store),
            'mode': detect_mode(question),
            'use_kb': False,
            'action': 'answer-directly',
            'guardrail': guardrail,
            'direct_response': guardrail['message'],
        }

    if not should_use_kb(question):
        clarification = _build_kb_only_clarification(question)
        return {
            'system': '',
            'user': question,
            'synthesis': None,
            'continuity': load_continuity(user_id=user_id, store=store),
            'mode': detect_mode(question),
            'use_kb': True,
            'action': 'ask-clarifying-question',
            'direct_response': clarification,
            'clarifying_question': clarification,
        }

    mode = detect_mode(question)

    build_user_profile(user_id=user_id, store=store)
    assemble_context(user_id=user_id, store=store)

    try:
        selected = select_frame(question, user_id=user_id, store=store)
    except Exception as exc:
        log.exception('select_frame failed in LLM path: %s', exc)
        reason = f'KB retrieval error: {exc}'
        clarification = _build_kb_only_clarification(question, reason=reason)
        return {
            'system': '',
            'user': question,
            'synthesis': None,
            'continuity': load_continuity(user_id=user_id, store=store),
            'mode': mode,
            'use_kb': True,
            'action': 'ask-clarifying-question',
            'reason': reason,
            'direct_response': clarification,
            'clarifying_question': clarification,
        }

    confidence = selected.get('confidence', 'low')
    progress = estimate_progress(question, user_id=user_id, store=store)

    bundle = selected.get('bundle', {})
    retrieved_chunks = bundle.get('relevant_chunks', [])
    validation = validate_chunks(question, retrieved_chunks,
                                 judge=get_relevance_judge())

    if confidence == 'low' or (
        not validation['valid'] and confidence != 'high'
    ):
        clarification = _build_kb_only_clarification(
            question, validation=validation, selected=selected,
        )
        return {
            'system': '',
            'user': question,
            'synthesis': None,
            'continuity': load_continuity(user_id=user_id, store=store),
            'mode': mode,
            'use_kb': True,
            'action': 'ask-clarifying-question',
            'retrieval_validation': validation,
            'direct_response': clarification,
            'clarifying_question': clarification,
        }

    theme_name = (selected.get('selected_theme') or {}).get('name', '')
    voice_mode = choose_voice(question, theme=theme_name,
                              user_id=user_id, store=store) or 'default'
    if progress.get('recommended_voice_override'):
        voice_mode = progress['recommended_voice_override']

    prompt = build_prompt(question, user_id=user_id, store=store,
                          voice_mode=voice_mode, frame=selected,
                          progress=progress)
    prompt['mode'] = mode
    prompt['use_kb'] = True
    prompt['action'] = 'respond-with-kb'
    prompt['voice_mode'] = voice_mode
    prompt['retrieval_validation'] = validation
    return prompt


def _orchestrate_inner(question, user_id: str = 'default',
                       store: StateStore | None = None):
    user_id = canonical_user_id(user_id)
    mode = detect_mode(question)

    guardrail = detect_out_of_domain(question, user_id=user_id, store=store)
    if not guardrail:
        maybe_reset_out_of_domain_streak(question, user_id=user_id, store=store)
    if guardrail:
        return {
            'question': question,
            'mode': mode,
            'use_kb': False,
            'confidence': 'high',
            'action': 'answer-directly',
            'reason': f"Out-of-domain request: {guardrail['kind']}",
            'direct_response': guardrail['message'],
            'guardrail': guardrail,
            'continuity': read_continuity(user_id=user_id, store=store),
        }

    if not should_use_kb(question):
        clarification = _build_kb_only_clarification(question)
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': 'low',
            'action': 'ask-clarifying-question',
            'reason': 'Question is too underspecified for KB grounding.',
            'response': clarification,
            'direct_response': clarification,
            'clarifying_question': clarification,
            'continuity': read_continuity(user_id=user_id, store=store),
        }

    build_user_profile(user_id=user_id, store=store)

    try:
        selected = select_frame(question, user_id=user_id, store=store)
        record_commitment(question, route=selected.get('route_name') or '', user_id=user_id, store=store)
    except Exception as exc:
        log.exception('select_frame failed: %s', exc)
        reason = f'KB retrieval error: {exc}'
        clarification = _build_kb_only_clarification(question, reason=reason)
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': 'low',
            'action': 'ask-clarifying-question',
            'reason': reason,
            'response': clarification,
            'direct_response': clarification,
            'clarifying_question': clarification,
            'continuity': read_continuity(user_id=user_id, store=store),
        }
    confidence = selected.get('confidence', 'low')
    assemble_context(user_id=user_id, store=store)
    continuity = read_continuity(user_id=user_id, store=store)
    progress = estimate_progress(question, user_id=user_id, store=store)
    reaction = estimate_reaction(question, user_id=user_id, store=store)

    bundle = selected.get('bundle', {})
    retrieved_chunks = bundle.get('relevant_chunks', [])
    validation = validate_chunks(question, retrieved_chunks,
                                 judge=get_relevance_judge())

    if confidence == 'low' or (
        not validation['valid'] and confidence != 'high'
    ):
        clarification = _build_kb_only_clarification(
            question, validation=validation, selected=selected,
        )
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': confidence,
            'action': 'ask-clarifying-question',
            'reason': ('KB route is weak or retrieval relevance is low '
                       f'(avg={validation["avg_relevance"]:.2f}); '
                       'clarification preferred before forcing a frame.'),
            'selection': selected,
            'response': clarification,
            'direct_response': clarification,
            'clarifying_question': clarification,
            'continuity': continuity,
            'retrieval_validation': validation,
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
        route_name = selected.get('route_name') or 'general'
        update_effectiveness(source=primary, outcome=outcome,
                             route=route_name, user_id=user_id, store=store)

    effective_mode = mode if mode in {'quick', 'practical', 'deep'} else 'deep'
    response = respond(question, mode=effective_mode, voice=voice,
                       user_id=user_id, store=store,
                       frame=selected, progress=progress)

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
        'retrieval_validation': validation,
    }
