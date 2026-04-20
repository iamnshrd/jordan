"""Controlled runtime planning for all user-facing answer paths."""
from __future__ import annotations

import logging

from library._core.mentor.checkins import record_reply
from library._core.mentor.commitments import record_commitment, maybe_resolve_from_reply
from library._core.runtime.frame import select_frame
from library._core.runtime.guardrails import (
    detect_out_of_domain, maybe_reset_out_of_domain_streak,
)
from library._core.runtime.grounding import (
    GroundedAnswerPlan, GroundingDecision,
    build_strict_clarification, can_render_strict,
)
from library._core.runtime.retrieval_validator import (
    get_relevance_judge, validate_chunks,
)
from library._core.runtime.routes import is_broad_question
from library._core.runtime.synthesize import synthesize
from library._core.runtime.voice import choose as choose_voice
from library._core.session.checkpoint import log as log_checkpoint
from library._core.session.context import assemble as assemble_context
from library._core.session.continuity import load as load_continuity
from library._core.session.effectiveness import update as update_effectiveness
from library._core.session.progress import estimate as estimate_progress
from library._core.session.reaction import estimate as estimate_reaction
from library._core.session.state import build_user_profile, update_session
from library._core.state_store import StateStore
from library.config import canonical_user_id, get_default_store
from library.utils import (
    ensure_trace_context, get_threshold, log_event, traced_stage,
)

log = logging.getLogger('jordan')

_PRACTICAL_TRIGGERS = ['что мне делать', 'что делать', 'next step',
                       'практически', 'как мне', 'что дальше']
_DEEP_TRIGGERS = ['почему', 'разбери', 'объясни', 'помоги понять',
                  'что со мной происходит', 'в чём корень']

_mode_classifier = None
_kb_classifier = None


def set_mode_classifier(fn):
    """Register an LLM-based mode classifier: fn(question) -> mode."""
    global _mode_classifier
    _mode_classifier = fn


def set_kb_classifier(fn):
    """Register an LLM-based KB router: fn(question) -> bool."""
    global _kb_classifier
    _kb_classifier = fn


def detect_mode(question: str) -> str:
    if _mode_classifier is not None:
        try:
            return _mode_classifier(question)
        except Exception:
            log.debug('LLM mode classifier failed, using heuristic')
    q = (question or '').lower()
    if any(x in q for x in _DEEP_TRIGGERS):
        return 'deep'
    if any(x in q for x in _PRACTICAL_TRIGGERS):
        return 'practical'
    if len(q) < get_threshold('detect_mode_short_length', 80):
        return 'practical'
    return 'deep'


def should_use_kb(question: str) -> bool:
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


def _has_fallback_frame(selected: dict | None) -> bool:
    selected = selected or {}
    reasons = [
        selected.get('selected_theme_reason') or '',
        selected.get('selected_principle_reason') or '',
        selected.get('selected_pattern_reason') or '',
    ]
    return any(reason == 'top-score fallback' for reason in reasons)


def _should_force_clarification(question: str,
                                selected: dict | None,
                                validation: dict | None,
                                synthesis: dict | None = None) -> tuple[bool, str]:
    selected = selected or {}
    bundle = selected.get('bundle', {}) if isinstance(selected, dict) else {}
    route_name = selected.get('route_name') or 'general'
    avg_relevance = float((validation or {}).get('avg_relevance') or 0.0)
    fallback_frame = _has_fallback_frame(selected)
    broad = is_broad_question(question)
    claims = bundle.get('relevant_claims', []) or []
    practices = bundle.get('relevant_practices', []) or []
    confidence = (selected.get('confidence') or '').lower()

    if broad and route_name == 'general':
        return True, 'Broad question stayed on general route'
    if broad and avg_relevance < 0.70:
        return True, 'Broad question lacks sufficiently tight retrieval relevance'
    if avg_relevance < 0.50:
        return True, 'Retrieval relevance is too low for a trustworthy answer'
    if avg_relevance < 0.75:
        return True, 'Retrieval relevance is below the trust threshold for a KB answer'
    if route_name == 'general' and (fallback_frame or avg_relevance < 0.75):
        return True, 'General route lacks strong retrieval grounding'
    if fallback_frame and avg_relevance < 0.60:
        return True, 'Frame still relies on fallback under weak retrieval'
    if confidence != 'high' and avg_relevance < 0.55:
        return True, 'Medium-confidence frame needs stronger retrieval grounding'
    if broad and fallback_frame and avg_relevance < 0.85:
        return True, 'Broad question relies on fallback frame'
    if broad and not claims and not practices:
        return True, 'Broad question lacks source-linked claims/practices'

    if synthesis is not None:
        report = synthesis.get('grounding_report') or {}
        fields = report.get('fields') or {}
        heuristic_fields = sorted(
            name for name, meta in fields.items()
            if meta.get('source') == 'heuristic'
        )
        if route_name == 'general' and heuristic_fields:
            return True, 'General route still depends on heuristic synthesis'

    return False, ''


def _build_decision(*,
                    action: str,
                    mode: str,
                    use_kb: bool,
                    confidence: str = '',
                    reason: str = '',
                    validation: dict | None = None,
                    selected: dict | None = None,
                    synthesis: dict | None = None) -> GroundingDecision:
    selected = selected or {}
    bundle = selected.get('bundle', {}) if isinstance(selected, dict) else {}
    route_name = selected.get('route_name') or 'general'
    evidence_count = len(bundle.get('relevant_chunks', []) or [])
    quote_count = len(bundle.get('relevant_quotes', []) or [])
    avg_relevance = (validation or {}).get('avg_relevance')
    degradation_mode = 'none'
    if action == 'ask-clarifying-question':
        degradation_mode = 'clarify'
    elif action == 'answer-directly' and not use_kb:
        degradation_mode = 'guardrail-direct'
    grounding = (synthesis or {}).get('grounding_report') or {}
    return GroundingDecision(
        action=action,
        mode=mode,
        use_kb=use_kb,
        confidence=confidence,
        reason=reason,
        route_name=route_name,
        evidence_count=evidence_count,
        quote_count=quote_count,
        avg_relevance=avg_relevance,
        degradation_mode=degradation_mode,
        backed_fields=list(grounding.get('backed_fields', [])),
        missing_fields=list(grounding.get('missing_fields', [])),
    )


def _log_runtime_side_effects(question: str,
                              user_id: str,
                              store: StateStore,
                              selected: dict,
                              progress: dict,
                              reaction: dict,
                              confidence: str,
                              voice_mode: str) -> None:
    theme_name = (selected.get('selected_theme') or {}).get('name') or ''
    pattern_name = (selected.get('selected_pattern') or {}).get('name') or ''
    principle_name = (selected.get('selected_principle') or {}).get('name') or ''
    blend = selected.get('source_blend') or {}
    source_blend_str = (f"{blend.get('primary', '')}"
                        f"->{blend.get('secondary', '')}")

    update_session(
        question,
        theme=theme_name,
        pattern=pattern_name,
        principle=principle_name,
        source_blend=source_blend_str,
        voice=voice_mode,
        goal=theme_name,
        user_id=user_id,
        store=store,
    )

    action_step = ('narrow-burden'
                   if progress.get('recommended_response_mode') == 'narrow'
                   else 'normal-step')

    continuity = load_continuity(user_id=user_id, store=store)
    resolved_loop_summary = ''
    if continuity.get('resolved_loops'):
        first = continuity['resolved_loops'][0]
        resolved_loop_summary = (
            first.get('summary', '') if isinstance(first, dict) else str(first)
        )

    log_checkpoint({
        'question': question,
        'theme': theme_name,
        'pattern': pattern_name,
        'principle': principle_name,
        'source_blend': source_blend_str,
        'voice': voice_mode,
        'confidence': confidence,
        'action_step': action_step,
        'movement_estimate': progress.get('progress_state', 'unknown'),
        'user_reaction_estimate': reaction.get('user_reaction_estimate', 'unknown'),
        'resolved_loop_if_any': resolved_loop_summary,
        'session_goal': theme_name,
        'recommended_next_mode': progress.get('recommended_response_mode', 'normal'),
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
        update_effectiveness(
            source=primary,
            outcome=outcome,
            route=route_name,
            user_id=user_id,
            store=store,
        )


def build_answer_plan(question: str, user_id: str = 'default',
                      store: StateStore | None = None,
                      purpose: str = 'response') -> GroundedAnswerPlan:
    """Build the single authoritative plan for answer/prompt generation."""
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose=purpose, question=question):
        mode = detect_mode(question)
        log_event(
            'planner.request_received',
            store=store,
            user_id=user_id,
            question=question,
            mode=mode,
            purpose=purpose,
        )

        if question.strip():
            with traced_stage('mentor.reply_record', store=store, user_id=user_id):
                record_reply(question, user_id=user_id, store=store)
                maybe_resolve_from_reply(question, user_id=user_id, store=store)

        with traced_stage('guardrails.detect', store=store, user_id=user_id):
            guardrail = detect_out_of_domain(question, user_id=user_id, store=store)
            if not guardrail:
                maybe_reset_out_of_domain_streak(question, user_id=user_id, store=store)
        if guardrail:
            decision = _build_decision(
                action='answer-directly',
                mode=mode,
                use_kb=False,
                confidence='high',
                reason=guardrail['kind'],
            )
            log_event(
                'planner.guardrail_blocked',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                guardrail_kind=guardrail['kind'],
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                continuity=load_continuity(user_id=user_id, store=store),
                guardrail=guardrail,
                direct_response=guardrail['message'],
                user=question,
            )

        if not should_use_kb(question):
            clarification = _build_kb_only_clarification(question)
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence='low',
                reason='Question is too underspecified for KB grounding.',
            )
            log_event(
                'planner.kb_rejected',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                continuity=load_continuity(user_id=user_id, store=store),
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        with traced_stage('runtime.profile_context', store=store, user_id=user_id):
            build_user_profile(user_id=user_id, store=store)
            assemble_context(user_id=user_id, store=store)

        try:
            with traced_stage('runtime.frame_selection', store=store, user_id=user_id):
                selected = select_frame(question, user_id=user_id, store=store)
                if purpose == 'response':
                    record_commitment(
                        question,
                        route=selected.get('route_name') or '',
                        user_id=user_id,
                        store=store,
                    )
            log_event(
                'planner.frame_selected',
                store=store,
                user_id=user_id,
                route_name=selected.get('route_name') or 'general',
                confidence=selected.get('confidence', 'low'),
                selected_theme=((selected.get('selected_theme') or {}).get('name') or ''),
                selected_principle=((selected.get('selected_principle') or {}).get('name') or ''),
                selected_pattern=((selected.get('selected_pattern') or {}).get('name') or ''),
            )
        except Exception as exc:
            log.exception('select_frame failed: %s', exc)
            reason = f'KB retrieval error: {exc}'
            clarification = _build_kb_only_clarification(question, reason=reason)
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence='low',
                reason=reason,
            )
            log_event(
                'planner.frame_failed',
                level=logging.ERROR,
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                error=str(exc),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                continuity=load_continuity(user_id=user_id, store=store),
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        confidence = selected.get('confidence', 'low')
        with traced_stage('runtime.user_state', store=store, user_id=user_id):
            continuity = load_continuity(user_id=user_id, store=store)
            progress = estimate_progress(question, user_id=user_id, store=store)
            reaction = (
                estimate_reaction(question, user_id=user_id, store=store)
                if purpose == 'response' else {}
            )

        bundle = selected.get('bundle', {})
        retrieved_chunks = bundle.get('relevant_chunks', [])
        with traced_stage('runtime.retrieval_validation', store=store, user_id=user_id):
            validation = validate_chunks(
                question, retrieved_chunks, judge=get_relevance_judge(),
            )
        log_event(
            'planner.retrieval_validated',
            store=store,
            user_id=user_id,
            avg_relevance=validation.get('avg_relevance'),
            valid=validation.get('valid'),
            chunk_count=len(retrieved_chunks),
        )

        if confidence == 'low' or (not validation['valid'] and confidence != 'high'):
            clarification = _build_kb_only_clarification(
                question, validation=validation, selected=selected,
            )
            reason = (
                'KB route is weak or retrieval relevance is low '
                f'(avg={validation["avg_relevance"]:.2f}); '
                'clarification preferred before forcing a frame.'
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason=reason,
                validation=validation,
                selected=selected,
            )
            log_event(
                'planner.clarified_pre_synthesis',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                avg_relevance=validation.get('avg_relevance'),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                selection=selected,
                continuity=continuity,
                progress=progress,
                reaction=reaction,
                retrieval_validation=validation,
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        force_clarify, force_reason = _should_force_clarification(
            question, selected, validation,
        )
        if force_clarify:
            clarification = _build_kb_only_clarification(
                question, validation=validation, selected=selected,
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason=force_reason,
                validation=validation,
                selected=selected,
            )
            log_event(
                'planner.clarified_by_gate',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                route_name=selected.get('route_name') or 'general',
                avg_relevance=validation.get('avg_relevance'),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                selection=selected,
                continuity=continuity,
                progress=progress,
                reaction=reaction,
                retrieval_validation=validation,
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        theme_name = (selected.get('selected_theme') or {}).get('name', '')
        with traced_stage('runtime.voice_selection', store=store, user_id=user_id):
            voice_mode = choose_voice(
                question, theme=theme_name, user_id=user_id, store=store,
            ) or 'default'
            if progress.get('recommended_voice_override'):
                voice_mode = progress['recommended_voice_override']

        if purpose == 'response':
            with traced_stage('runtime.side_effects', store=store, user_id=user_id):
                _log_runtime_side_effects(
                    question, user_id, store, selected, progress,
                    reaction, confidence, voice_mode,
                )

        with traced_stage('runtime.synthesis', store=store, user_id=user_id):
            synthesis_data = synthesize(
                question, user_id=user_id, store=store,
                frame=selected, progress=progress,
            )
        log_event(
            'planner.synthesis_ready',
            store=store,
            user_id=user_id,
            backed_fields=(synthesis_data.get('grounding_report') or {}).get('backed_fields', []),
            missing_fields=(synthesis_data.get('grounding_report') or {}).get('missing_fields', []),
        )
        force_clarify, force_reason = _should_force_clarification(
            question, selected, validation, synthesis=synthesis_data,
        )
        if force_clarify:
            clarification = build_strict_clarification(synthesis_data, mode=mode)
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason=force_reason,
                validation=validation,
                selected=selected,
                synthesis=synthesis_data,
            )
            log_event(
                'planner.clarified_post_synthesis',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                backed_fields=decision.backed_fields,
                missing_fields=decision.missing_fields,
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                selection=selected,
                continuity=continuity,
                progress=progress,
                reaction=reaction,
                retrieval_validation=validation,
                synthesis=synthesis_data,
                voice_mode=voice_mode,
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        if not can_render_strict(synthesis_data, mode=mode):
            clarification = build_strict_clarification(synthesis_data, mode=mode)
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason='Strict renderer lacks DB-backed fields for full answer.',
                validation=validation,
                selected=selected,
                synthesis=synthesis_data,
            )
            log_event(
                'planner.strict_render_blocked',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                missing_fields=decision.missing_fields,
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                selection=selected,
                continuity=continuity,
                progress=progress,
                reaction=reaction,
                retrieval_validation=validation,
                synthesis=synthesis_data,
                voice_mode=voice_mode,
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        decision = _build_decision(
            action='respond-with-kb',
            mode=mode,
            use_kb=True,
            confidence=confidence,
            reason='KB-backed response',
            validation=validation,
            selected=selected,
            synthesis=synthesis_data,
        )
        log_event(
            'planner.answer_allowed',
            store=store,
            user_id=user_id,
            action=decision.action,
            route_name=decision.route_name,
            avg_relevance=decision.avg_relevance,
            backed_fields=decision.backed_fields,
            voice_mode=voice_mode,
        )
        return GroundedAnswerPlan(
            question=question,
            user_id=user_id,
            decision=decision,
            selection=selected,
            continuity=continuity,
            progress=progress,
            reaction=reaction,
            retrieval_validation=validation,
            synthesis=synthesis_data,
            voice_mode=voice_mode,
            user=question,
        )
