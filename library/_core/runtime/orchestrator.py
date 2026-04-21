"""Unified runtime orchestrator backed by the controlled planning pipeline."""
from __future__ import annotations

from library._core.runtime.llm_prompt import build_prompt
from library._core.runtime.decision import (
    attach_adapter_contract,
    build_adapter_payload,
    coerce_envelope,
)
from library._core.runtime.planner import (
    build_answer_plan,
    detect_mode,
    set_kb_classifier,
    set_mode_classifier,
    should_use_kb,
)
from library._core.runtime.respond import render_plan
from library._core.state_store import StateStore
from library.config import canonical_user_id, get_default_store
from library.utils import (
    audit_event, current_trace_id, ensure_trace_context, log_event,
    timing_context, traced_stage,
)


def _log_conversation_inbound(*, question: str, store, user_id: str,
                              entrypoint: str) -> None:
    audit_event(
        'conversation.inbound',
        user_id=user_id,
        entrypoint=entrypoint,
        question=question,
        question_length=len(question or ''),
    )


def _log_conversation_outbound(*, question: str, result: dict, store,
                               user_id: str, entrypoint: str) -> None:
    envelope = coerce_envelope(result)
    response_text = (
        result.get('response')
        or envelope.get('final_user_text')
        or result.get('final_user_text', '')
        or ''
    )
    audit_event(
        'conversation.outbound',
        user_id=user_id,
        entrypoint=entrypoint,
        question=question,
        response=response_text,
        response_length=len(response_text),
        decision_type=envelope.get('decision_type', ''),
        domain_status=envelope.get('domain_status', ''),
        reason_code=envelope.get('reason_code', ''),
        allow_model_call=bool(envelope.get('allow_model_call')),
        assistant_id=result.get('assistant_id', ''),
        knowledge_set_id=result.get('knowledge_set_id', ''),
    )


def _log_prompt_prepared(*, question: str, result: dict, store,
                         user_id: str, entrypoint: str) -> None:
    envelope = coerce_envelope(result)
    audit_event(
        'conversation.prompt_prepared',
        user_id=user_id,
        entrypoint=entrypoint,
        question=question,
        final_user_text=envelope.get('final_user_text', ''),
        final_user_text_length=len(envelope.get('final_user_text', '') or ''),
        system_length=len(result.get('system', '') or ''),
        delivery_mode=(result.get('adapter_contract') or {}).get('delivery_mode', ''),
        decision_type=envelope.get('decision_type', ''),
        domain_status=envelope.get('domain_status', ''),
        reason_code=envelope.get('reason_code', ''),
        allow_model_call=bool(envelope.get('allow_model_call')),
        assistant_id=result.get('assistant_id', ''),
        knowledge_set_id=result.get('knowledge_set_id', ''),
    )


def _finalize_result(result: dict, *, trace_id: str, store, user_id: str,
                     entrypoint: str) -> dict:
    attach_adapter_contract(result)
    result['trace_id'] = trace_id
    envelope = coerce_envelope(result)
    log_event(
        'orchestrator.decision_resolved',
        store=store,
        user_id=user_id,
        entrypoint=entrypoint,
        decision_type=envelope.get('decision_type', ''),
        domain_status=envelope.get('domain_status', ''),
        reason_code=envelope.get('reason_code', ''),
        allow_model_call=bool(envelope.get('allow_model_call')),
        final_user_text_present=bool(envelope.get('final_user_text')),
    )
    return result


def orchestrate(question, user_id: str = 'default',
                store: StateStore | None = None):
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='response', question=question):
        trace_id = current_trace_id()
        _log_conversation_inbound(
            question=question,
            store=store,
            user_id=user_id,
            entrypoint='orchestrate',
        )
        log_event('orchestrator.started', store=store, user_id=user_id,
                  entrypoint='orchestrate')
        with timing_context() as timings:
            with traced_stage('orchestrator.plan', store=store, user_id=user_id):
                plan = build_answer_plan(
                    question, user_id=user_id, store=store, purpose='response',
                )
            response = render_plan(plan)
            result = plan.runtime_result(response=response)
            _finalize_result(
                result,
                trace_id=trace_id,
                store=store,
                user_id=user_id,
                entrypoint='orchestrate',
            )
            _log_conversation_outbound(
                question=question,
                result=result,
                store=store,
                user_id=user_id,
                entrypoint='orchestrate',
            )
        log_event(
            'orchestrator.finished',
            store=store,
            user_id=user_id,
            action=result.get('action', ''),
            response_length=len(result.get('response', '') or ''),
            decision_type=result.get('decision_type', ''),
            domain_status=result.get('domain_status', ''),
            reason_code=result.get('reason_code', ''),
            allow_model_call=result.get('allow_model_call', False),
            timings=timings,
        )
    result['_timings'] = timings
    return result


def build_runtime_plan(question: str, *, user_id: str = 'default',
                       store: StateStore | None = None,
                       purpose: str = 'prompt',
                       record_user_reply: bool = True):
    """Build the canonical runtime plan for internal runtime modules."""
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    return build_answer_plan(
        question,
        user_id=user_id,
        store=store,
        purpose=purpose,
        record_user_reply=record_user_reply,
    )


def orchestrate_for_llm(question: str, user_id: str = 'default',
                        store: StateStore | None = None) -> dict:
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='prompt', question=question):
        trace_id = current_trace_id()
        _log_conversation_inbound(
            question=question,
            store=store,
            user_id=user_id,
            entrypoint='orchestrate_for_llm',
        )
        log_event('orchestrator.started', store=store, user_id=user_id,
                  entrypoint='orchestrate_for_llm')
        with traced_stage('orchestrator.plan', store=store, user_id=user_id):
            plan = build_runtime_plan(
                question, user_id=user_id, store=store, purpose='prompt',
            )
        if plan.decision.allow_llm_prompt:
            result = build_prompt(
                question,
                user_id=user_id,
                store=store,
                voice_mode=plan.voice_mode,
                plan=plan,
            )
        else:
            result = plan.prompt_result()
        _finalize_result(
            result,
            trace_id=trace_id,
            store=store,
            user_id=user_id,
            entrypoint='orchestrate_for_llm',
        )
        _log_prompt_prepared(
            question=question,
            result=result,
            store=store,
            user_id=user_id,
            entrypoint='orchestrate_for_llm',
        )
        log_event(
            'orchestrator.finished',
            store=store,
            user_id=user_id,
            action=result.get('action', ''),
            system_length=len(result.get('system', '') or ''),
            decision_type=result.get('decision_type', ''),
            domain_status=result.get('domain_status', ''),
            reason_code=result.get('reason_code', ''),
            allow_model_call=result.get('allow_model_call', False),
        )
    return result


def orchestrate_for_adapter(question: str, user_id: str = 'default',
                            store: StateStore | None = None) -> dict:
    """Return the only adapter-safe execution payload for a question."""
    prompt_result = orchestrate_for_llm(question, user_id=user_id, store=store)
    adapter_payload = build_adapter_payload(prompt_result)
    audit_event(
        'conversation.adapter_payload',
        user_id=canonical_user_id(user_id),
        question=question or '',
        message=adapter_payload.get('message', ''),
        message_length=len(adapter_payload.get('message', '') or ''),
        delivery_mode=adapter_payload.get('delivery_mode', ''),
        decision_type=adapter_payload.get('decision_type', ''),
        domain_status=adapter_payload.get('domain_status', ''),
        reason_code=adapter_payload.get('reason_code', ''),
    )
    log_event(
        'orchestrator.adapter_payload_built',
        store=store,
        user_id=canonical_user_id(user_id),
        delivery_mode=adapter_payload.get('delivery_mode', ''),
        decision_type=adapter_payload.get('decision_type', ''),
        domain_status=adapter_payload.get('domain_status', ''),
        reason_code=adapter_payload.get('reason_code', ''),
    )
    return adapter_payload


def orchestrate_diagnostics(question: str, *, user_id: str = 'default',
                            store: StateStore | None = None,
                            purpose: str = 'prompt') -> dict:
    """Return safe diagnostic data derived from the canonical plan."""
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose=f'diagnostic:{purpose}', question=question):
        trace_id = current_trace_id()
        log_event('orchestrator.started', store=store, user_id=user_id,
                  entrypoint='orchestrate_diagnostics')
        with traced_stage('orchestrator.plan', store=store, user_id=user_id):
            plan = build_runtime_plan(
                question, user_id=user_id, store=store, purpose=purpose,
            )
        result = {
            'question': question,
            'assistant_id': plan.assistant_id,
            'knowledge_set_id': plan.knowledge_set_id,
            'selection': plan.selection,
            'bundle': (plan.selection or {}).get('bundle', {}),
            'synthesis': plan.synthesis,
            'decision': plan.decision.as_dict(),
            'guardrail': plan.guardrail,
            'trace_id': trace_id,
        }
        log_event(
            'orchestrator.finished',
            store=store,
            user_id=user_id,
            entrypoint='orchestrate_diagnostics',
            action=plan.action,
            assistant_id=plan.assistant_id,
            knowledge_set_id=plan.knowledge_set_id,
        )
        return result
