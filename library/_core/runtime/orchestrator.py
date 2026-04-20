"""Unified runtime orchestrator backed by the controlled planning pipeline."""
from __future__ import annotations

from library._core.runtime.llm_prompt import build_prompt
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
    current_trace_id, ensure_trace_context, log_event,
    timing_context, traced_stage,
)


def orchestrate(question, user_id: str = 'default',
                store: StateStore | None = None):
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='response', question=question):
        trace_id = current_trace_id()
        log_event('orchestrator.started', store=store, user_id=user_id,
                  entrypoint='orchestrate')
        with timing_context() as timings:
            with traced_stage('orchestrator.plan', store=store, user_id=user_id):
                plan = build_answer_plan(
                    question, user_id=user_id, store=store, purpose='response',
                )
            response = render_plan(plan)
            result = plan.runtime_result(response=response)
        log_event(
            'orchestrator.finished',
            store=store,
            user_id=user_id,
            action=result.get('action', ''),
            response_length=len(result.get('response', '') or ''),
            timings=timings,
        )
    result['_timings'] = timings
    result['trace_id'] = trace_id
    return result


def orchestrate_for_llm(question: str, user_id: str = 'default',
                        store: StateStore | None = None) -> dict:
    question = question or ''
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='prompt', question=question):
        trace_id = current_trace_id()
        log_event('orchestrator.started', store=store, user_id=user_id,
                  entrypoint='orchestrate_for_llm')
        with traced_stage('orchestrator.plan', store=store, user_id=user_id):
            plan = build_answer_plan(
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
        log_event(
            'orchestrator.finished',
            store=store,
            user_id=user_id,
            action=result.get('action', ''),
            system_length=len(result.get('system', '') or ''),
        )
    result['trace_id'] = trace_id
    return result
