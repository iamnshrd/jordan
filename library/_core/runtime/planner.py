"""Controlled runtime planning for all user-facing answer paths."""
from __future__ import annotations

import logging

from library._core.mentor.checkins import record_reply
from library._core.mentor.commitments import maybe_resolve_from_reply
from library._core.registry import get_default_assistant
from library._core.runtime.clarify_human import build_clarification
from library._core.runtime.dialogue_acts import (
    extract_dialogue_detail,
    extract_dialogue_axis,
    infer_dialogue_act,
)
from library._core.runtime.dialogue_frame import (
    build_frame_metadata,
    dialogue_act_from_frame,
    frame_from_state,
    mode_from_goal,
)
from library._core.runtime.dialogue_family_registry import resolve_dialogue_transition
from library._core.runtime.dialogue_state import (
    advance_dialogue_state,
    build_dialogue_metadata,
)
from library._core.runtime.dialogue_update import (
    apply_dialogue_update,
    infer_dialogue_update,
)
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
from library._core.session.dialogue import (
    load as load_dialogue_state,
    save as save_dialogue_state,
)
from library._core.session.dialogue_frame import (
    load as load_dialogue_frame,
    save as save_dialogue_frame,
)
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
                          stage: str = '',
                          dialogue_state: dict | None = None,
                          dialogue_frame: dict | None = None,
                          dialogue_act: str = '',
                          selected_axis: str = '',
                          selected_detail: str = '') -> tuple[str, dict]:
    clarification = build_clarification(
        question,
        selected=selected,
        fallback_text=fallback_text,
        dialogue_state=dialogue_state,
        dialogue_frame=dialogue_frame,
        dialogue_act=dialogue_act,
        selected_axis=selected_axis,
        selected_detail=selected_detail,
    )
    metadata = dict(clarification.metadata or {})
    if stage:
        metadata['clarify_stage'] = stage
    if validation is not None:
        metadata.setdefault('clarify_avg_relevance', validation.get('avg_relevance'))
    return clarification.text, metadata


def _merge_dialogue_metadata(metadata: dict | None,
                             dialogue_state: dict | None,
                             dialogue_frame: dict | None,
                             dialogue_act: str,
                             *,
                             question: str,
                             route_name: str = '',
                             decision_type: str = '',
                             reason_code: str = '',
                             final_user_text: str = '',
                             topic_reused: bool = False,
                             confidence: str = '',
                             selected_axis: str = '',
                             selected_detail: str = '') -> tuple[dict, dict, dict]:
    payload = dict(metadata or {})
    next_state = advance_dialogue_state(
        dialogue_state,
        question=question,
        dialogue_act=dialogue_act,
        route_name=route_name,
        clarify_profile=payload.get('clarify_profile', ''),
        reason_code=reason_code or payload.get('clarify_reason_code', ''),
        decision_type=decision_type,
        final_user_text=final_user_text,
        question_kind=payload.get('clarify_question_kind', ''),
        confidence=confidence,
        selected_axis=selected_axis,
        selected_detail=selected_detail,
    )
    next_frame = frame_from_state(next_state, dialogue_act=dialogue_act).as_dict()
    next_frame.update(
        apply_dialogue_update(
            dialogue_frame or next_frame,
            infer_dialogue_update(
                question,
                dialogue_act=dialogue_act,
                dialogue_state=next_state,
                dialogue_frame=dialogue_frame,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            ),
            fallback_state=next_state,
        ).as_dict(),
    )
    transition = {}
    if next_frame.get('topic', '') and next_frame.get('transition_kind', ''):
        transition = resolve_dialogue_transition(
            next_frame.get('topic', ''),
            next_frame.get('transition_kind', ''),
            goal=frame_from_state(dialogue_state, dialogue_act=dialogue_act).goal if dialogue_state else '',
            dialogue_mode=(dialogue_state or {}).get('dialogue_mode', ''),
            pending_slot=(dialogue_state or {}).get('pending_slot', ''),
            abstraction_level=(dialogue_state or {}).get('abstraction_level', ''),
        )
    if transition:
        next_frame['goal'] = transition.get('goal', '') or next_frame.get('goal', '')
        next_frame['stance'] = transition.get('stance', '') or next_frame.get('stance', '')
        next_frame['pending_slot'] = transition.get('pending_slot', '') or next_frame.get('pending_slot', '')
        if transition.get('clear_axis'):
            next_frame['axis'] = ''
        if transition.get('clear_detail'):
            next_frame['detail'] = ''
    next_state.active_topic = next_frame.get('topic', '') or next_state.active_topic
    next_state.active_route = next_frame.get('route', '') or next_state.active_route
    next_state.abstraction_level = next_frame.get('stance', '') or next_state.abstraction_level
    next_state.pending_slot = next_frame.get('pending_slot', '') or next_state.pending_slot
    next_state.dialogue_mode = transition.get('dialogue_mode', '') or mode_from_goal(next_frame.get('goal', '') or '')
    next_state.active_axis = next_frame.get('axis', '') or next_state.active_axis
    next_state.active_detail = next_frame.get('detail', '') or next_state.active_detail
    next_state.topic_confidence = next_frame.get('confidence', '') or next_state.topic_confidence
    synchronized_act = dialogue_act_from_frame(next_frame, fallback=dialogue_act)
    payload.update(
        build_dialogue_metadata(
            next_state,
            dialogue_act=synchronized_act,
            topic_reused=topic_reused,
        ),
    )
    payload.update(build_frame_metadata(next_frame))
    if selected_axis:
        payload['selected_axis'] = selected_axis
    if selected_detail:
        payload['selected_detail'] = selected_detail
    return payload, next_state.as_dict(), next_frame


def _finalize_plan(plan: GroundedAnswerPlan, *,
                   dialogue_state: dict,
                   dialogue_frame: dict,
                   user_id: str,
                   store: StateStore | None = None) -> GroundedAnswerPlan:
    plan.dialogue_state = dict(dialogue_state or {})
    plan.dialogue_frame = dict(dialogue_frame or {})
    save_dialogue_state(plan.dialogue_state, user_id=user_id, store=store)
    save_dialogue_frame(plan.dialogue_frame, user_id=user_id, store=store)
    return plan


def _compute_topic_reused(dialogue_state: dict | None,
                          interpreted_frame: dict | None) -> bool:
    state = dict(dialogue_state or {})
    frame = dict(interpreted_frame or {})
    previous_topic = state.get('active_topic', '') or ''
    next_topic = frame.get('topic', '') or ''
    relation = frame.get('relation_to_previous', '') or ''
    if not previous_topic or not next_topic:
        return False
    if previous_topic != next_topic:
        return False
    return relation in {'continue', 'reframe', 'answer_slot'}


def _should_render_frame_directly(interpreted_frame: dict | None) -> bool:
    frame = dict(interpreted_frame or {})
    return (
        (
            frame.get('topic', '') == 'relationship-foundations'
            and frame.get('goal', '') == 'overview'
            and frame.get('stance', '') == 'general'
        )
        or (
            frame.get('topic', '') == 'scope-topics'
            and frame.get('goal', '') == 'menu'
            and frame.get('stance', '') == 'general'
        )
        or (
            frame.get('topic', '') == 'lost-and-aimless'
            and frame.get('goal', '') == 'clarify'
            and frame.get('stance', '') == 'personal'
        )
        or (
            frame.get('topic', '') == 'self-evaluation'
            and frame.get('goal', '') == 'clarify'
            and frame.get('stance', '') == 'personal'
        )
        or (
            frame.get('topic', '') == 'shame-self-contempt'
            and frame.get('goal', '') == 'clarify'
            and frame.get('stance', '') == 'personal'
        )
        or (
            frame.get('topic', '') in {
                'resentment-conflict',
                'self-deception',
                'fear-and-price',
                'loneliness-rejection',
                'parenting-boundaries',
                'tragedy-bitterness',
                'greeting',
            }
            and frame.get('goal', '') in {'clarify', 'opening'}
        )
    )


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
        dialogue_state = load_dialogue_state(user_id=user_id, store=store)
        dialogue_frame = load_dialogue_frame(user_id=user_id, store=store)
        dialogue_act = infer_dialogue_act(question, dialogue_state)
        selected_axis = extract_dialogue_axis(question, dialogue_state)
        selected_detail = extract_dialogue_detail(question, dialogue_state)
        dialogue_update = infer_dialogue_update(
            question,
            dialogue_act=dialogue_act,
            dialogue_state=dialogue_state,
            dialogue_frame=dialogue_frame,
            selected_axis=selected_axis,
            selected_detail=selected_detail,
        )
        interpreted_frame = apply_dialogue_update(
            dialogue_frame,
            dialogue_update,
            fallback_state=dialogue_state,
        ).as_dict()
        topic_reused = _compute_topic_reused(dialogue_state, interpreted_frame)
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
        log_event(
            'planner.dialogue_interpreted',
            store=store,
            user_id=user_id,
            dialogue_act=dialogue_act,
            active_topic=dialogue_state.get('active_topic', ''),
            active_route=dialogue_state.get('active_route', ''),
            abstraction_level=dialogue_state.get('abstraction_level', ''),
            pending_slot=dialogue_state.get('pending_slot', ''),
            selected_axis=selected_axis,
            selected_detail=selected_detail,
            topic_reused=topic_reused,
        )
        log_event(
            'planner.dialogue_frame_interpreted',
            store=store,
            user_id=user_id,
            frame_topic=interpreted_frame.get('topic', ''),
            frame_type=interpreted_frame.get('frame_type', ''),
            frame_stance=interpreted_frame.get('stance', ''),
            frame_goal=interpreted_frame.get('goal', ''),
            frame_relation_to_previous=interpreted_frame.get('relation_to_previous', ''),
            frame_transition_kind=interpreted_frame.get('transition_kind', ''),
            frame_axis=interpreted_frame.get('axis', ''),
            frame_detail=interpreted_frame.get('detail', ''),
            frame_pending_slot=interpreted_frame.get('pending_slot', ''),
            frame_confidence=interpreted_frame.get('confidence', ''),
            frame_update_source=interpreted_frame.get('update_source', ''),
        )

        if question.strip() and record_user_reply and purpose == 'response':
            with traced_stage('mentor.reply_record', store=store, user_id=user_id):
                record_reply(question, user_id=user_id, store=store)
                maybe_resolve_from_reply(question, user_id=user_id, store=store)

        guardrail = run_policy_stage(question, user_id=user_id, store=store)
        if guardrail:
            dialogue_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                {},
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=dialogue_state.get('active_route', ''),
                decision_type='respond_policy_text',
                reason_code=guardrail['kind'],
                final_user_text=guardrail['message'],
                topic_reused=topic_reused,
                confidence='high',
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            decision = _build_decision(
                action='answer-directly',
                mode=mode,
                use_kb=False,
                confidence='high',
                reason=guardrail['kind'],
                metadata=dialogue_metadata,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

        if not should_use_kb(question):
            clarification, clarify_metadata = _select_clarification(
                question,
                fallback_text=_build_kb_only_clarification(question),
                stage='kb_rejected',
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=dialogue_state.get('active_route', ''),
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence='low',
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

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
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence='low',
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

        confidence = selected.get('confidence', 'low')
        continuity, progress, reaction = run_user_state_stage(
            question, user_id=user_id, store=store, purpose=purpose,
        )
        validation = run_retrieval_validation_stage(
            question, selected=selected, user_id=user_id, store=store,
        )

        if _should_render_frame_directly(interpreted_frame):
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=_build_kb_only_clarification(
                    question, validation=validation, selected=selected,
                ),
                stage='frame_direct_overview',
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=selected.get('route_name') or '',
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence=confidence,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            decision = _build_decision(
                action='ask-clarifying-question',
                mode=mode,
                use_kb=True,
                confidence=confidence,
                reason='Frame-driven overview chosen instead of freeform synthesis.',
                validation=validation,
                selected=selected,
                metadata=clarify_metadata,
            )
            log_event(
                'planner.frame_direct_overview',
                store=store,
                user_id=user_id,
                action=decision.action,
                reason=decision.reason,
                route_name=selected.get('route_name') or 'general',
                frame_topic=interpreted_frame.get('topic', ''),
                frame_goal=interpreted_frame.get('goal', ''),
                clarify_type=clarify_metadata.get('clarify_type', ''),
                clarify_profile=clarify_metadata.get('clarify_profile', ''),
            )
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

        if confidence == 'low' or (not validation['valid'] and confidence != 'high'):
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=_build_kb_only_clarification(
                    question, validation=validation, selected=selected,
                ),
                stage='pre_synthesis',
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=selected.get('route_name') or '',
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence=confidence,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

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
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=selected.get('route_name') or '',
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence=confidence,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

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
                dialogue_state=dialogue_state,
                dialogue_frame=interpreted_frame,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=selected.get('route_name') or '',
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence=confidence,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

        if not can_render_strict(synthesis_data, mode=mode):
            clarification, clarify_metadata = _select_clarification(
                question,
                selected=selected,
                validation=validation,
                fallback_text=build_strict_clarification(synthesis_data, mode=mode),
                stage='strict_render',
                dialogue_state=dialogue_state,
                dialogue_act=dialogue_act,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
            )
            clarify_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
                clarify_metadata,
                dialogue_state,
                interpreted_frame,
                dialogue_act,
                question=question,
                route_name=selected.get('route_name') or '',
                decision_type='clarify',
                reason_code=clarify_metadata.get('clarify_reason_code', ''),
                final_user_text=clarification,
                topic_reused=topic_reused,
                confidence=confidence,
                selected_axis=selected_axis,
                selected_detail=selected_detail,
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
            return _finalize_plan(GroundedAnswerPlan(
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
            ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)

        answer_metadata, next_dialogue_state, next_dialogue_frame = _merge_dialogue_metadata(
            {},
            dialogue_state,
            interpreted_frame,
            dialogue_act,
            question=question,
            route_name=selected.get('route_name') or '',
            decision_type='respond_kb',
            reason_code='respond-with-kb',
            topic_reused=topic_reused,
            confidence=confidence,
            selected_axis=selected_axis,
            selected_detail=selected_detail,
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
            metadata=answer_metadata,
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
        return _finalize_plan(GroundedAnswerPlan(
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
        ), dialogue_state=next_dialogue_state, dialogue_frame=next_dialogue_frame, user_id=user_id, store=store)
