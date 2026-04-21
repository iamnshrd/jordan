"""Controlled runtime planning for all user-facing answer paths."""
from __future__ import annotations

import logging

from library._core.mentor.checkins import record_reply
from library._core.mentor.commitments import maybe_resolve_from_reply
from library._core.registry import get_default_assistant
from library._core.runtime.clarify_human import build_clarification
from library._core.runtime.grounding import (
    GroundedAnswerPlan, GroundingDecision,
    build_strict_clarification, can_render_strict,
)
from library._core.runtime.policy import detect_policy_block
from library._core.runtime.routes import is_broad_question
from library._core.runtime.stages import (
    run_frame_stage,
    run_policy_stage,
    run_profile_context_stage,
    run_retrieval_validation_stage,
    run_runtime_side_effects_stage,
    run_synthesis_stage,
    run_user_state_stage,
    run_voice_stage,
)
from library._core.session.continuity import load as load_continuity
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
    """Return whether this question should enter the KB pipeline at all."""
    q = (question or '').strip()
    if not q:
        return False
    if detect_policy_block(question) is not None:
        return False
    if _kb_classifier is not None:
        try:
            decision = _kb_classifier(question)
            if decision is False:
                log.debug('KB classifier requested direct path, disabling retrieval')
                return False
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
                    synthesis: dict | None = None,
                    metadata: dict | None = None) -> GroundingDecision:
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
        metadata=dict(metadata or {}),
    )


def _select_clarification(question: str, *,
                          selected: dict | None = None,
                          validation: dict | None = None,
                          fallback_text: str = '',
                          stage: str = '') -> tuple[str, dict]:
    clarification = build_clarification(
        question,
        selected=selected,
        fallback_text=fallback_text,
    )
    metadata = dict(clarification.metadata or {})
    if stage:
        metadata['clarify_stage'] = stage
    if validation is not None:
        metadata.setdefault('clarify_avg_relevance', validation.get('avg_relevance'))
    return clarification.text, metadata


def build_answer_plan(question: str, user_id: str = 'default',
                      store: StateStore | None = None,
                      purpose: str = 'response',
                      record_user_reply: bool = True) -> GroundedAnswerPlan:
    """Build the single authoritative plan for answer/prompt generation."""
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose=purpose, question=question):
        assistant = get_default_assistant()
        mode = detect_mode(question)
        log_event(
            'planner.request_received',
            store=store,
            user_id=user_id,
            question=question,
            mode=mode,
            purpose=purpose,
            assistant_id=assistant.assistant_id,
            knowledge_set_id=assistant.knowledge_set_id,
        )

        if question.strip() and record_user_reply and purpose == 'response':
            with traced_stage('mentor.reply_record', store=store, user_id=user_id):
                record_reply(question, user_id=user_id, store=store)
                maybe_resolve_from_reply(question, user_id=user_id, store=store)

        guardrail = run_policy_stage(question, user_id=user_id, store=store)
        if guardrail:
            decision = _build_decision(
                action='answer-directly',
                mode=mode,
                use_kb=False,
                confidence='high',
                reason=guardrail['kind'],
            )
            log_event(
                'planner.policy_blocked',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                policy_kind=guardrail['kind'],
                policy_source=guardrail.get('policy_source', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
                continuity=load_continuity(user_id=user_id, store=store),
                guardrail=guardrail,
                direct_response=guardrail['message'],
                user=question,
            )

        if not should_use_kb(question):
            clarification, clarify_metadata = _select_clarification(
                question,
                fallback_text=_build_kb_only_clarification(question),
                stage='kb_rejected',
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence='low',
                reason='Question is too underspecified for KB grounding.',
                metadata=clarify_metadata,
            )
            log_event(
                'planner.kb_rejected',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
                continuity=load_continuity(user_id=user_id, store=store),
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        run_profile_context_stage(user_id=user_id, store=store)

        try:
            selected = run_frame_stage(
                question, user_id=user_id, store=store, purpose=purpose,
            )
        except Exception as exc:
            log.exception('select_frame failed: %s', exc)
            reason = f'KB retrieval error: {exc}'
            clarification, clarify_metadata = _select_clarification(
                question,
                fallback_text=_build_kb_only_clarification(question, reason=reason),
                stage='frame_failed',
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence='low',
                reason=reason,
                metadata=clarify_metadata,
            )
            log_event(
                'planner.frame_failed',
                level=logging.ERROR,
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                error=str(exc),
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
                continuity=load_continuity(user_id=user_id, store=store),
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        confidence = selected.get('confidence', 'low')
        continuity, progress, reaction = run_user_state_stage(
            question, user_id=user_id, store=store, purpose=purpose,
        )
        validation = run_retrieval_validation_stage(
            question, selected=selected, user_id=user_id, store=store,
        )

        if confidence == 'low' or (not validation['valid'] and confidence != 'high'):
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=_build_kb_only_clarification(
                    question, validation=validation, selected=selected,
                ),
                stage='pre_synthesis',
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
                metadata=clarify_metadata,
            )
            log_event(
                'planner.clarified_pre_synthesis',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                avg_relevance=validation.get('avg_relevance'),
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
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
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=_build_kb_only_clarification(
                    question, validation=validation, selected=selected,
                ),
                stage='pre_synthesis_gate',
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason=force_reason,
                validation=validation,
                selected=selected,
                metadata=clarify_metadata,
            )
            log_event(
                'planner.clarified_by_gate',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                route_name=selected.get('route_name') or 'general',
                avg_relevance=validation.get('avg_relevance'),
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
                selection=selected,
                continuity=continuity,
                progress=progress,
                reaction=reaction,
                retrieval_validation=validation,
                direct_response=clarification,
                clarifying_question=clarification,
                user=question,
            )

        voice_mode = run_voice_stage(
            question, selected=selected, progress=progress,
            user_id=user_id, store=store,
        )

        if purpose == 'response':
            run_runtime_side_effects_stage(
                question,
                user_id=user_id,
                store=store,
                selected=selected,
                progress=progress,
                reaction=reaction,
                confidence=confidence,
                voice_mode=voice_mode,
            )

        synthesis_data = run_synthesis_stage(
            question, user_id=user_id, store=store,
            selected=selected, progress=progress,
        )
        force_clarify, force_reason = _should_force_clarification(
            question, selected, validation, synthesis=synthesis_data,
        )
        if force_clarify:
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=build_strict_clarification(synthesis_data, mode=mode),
                stage='post_synthesis_gate',
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason=force_reason,
                validation=validation,
                selected=selected,
                synthesis=synthesis_data,
                metadata=clarify_metadata,
            )
            log_event(
                'planner.clarified_post_synthesis',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                backed_fields=decision.backed_fields,
                missing_fields=decision.missing_fields,
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
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
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=build_strict_clarification(synthesis_data, mode=mode),
                stage='strict_render',
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason='Strict renderer lacks DB-backed fields for full answer.',
                validation=validation,
                selected=selected,
                synthesis=synthesis_data,
                metadata=clarify_metadata,
            )
            log_event(
                'planner.strict_render_blocked',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                missing_fields=decision.missing_fields,
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return GroundedAnswerPlan(
                question=question,
                user_id=user_id,
                decision=decision,
                assistant_id=assistant.assistant_id,
                knowledge_set_id=assistant.knowledge_set_id,
                purpose=purpose,
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
            assistant_id=assistant.assistant_id,
            knowledge_set_id=assistant.knowledge_set_id,
            purpose=purpose,
            selection=selected,
            continuity=continuity,
            progress=progress,
            reaction=reaction,
            retrieval_validation=validation,
            synthesis=synthesis_data,
            voice_mode=voice_mode,
            user=question,
        )
