#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime.decision import should_call_model
from library._core.runtime.orchestrator import orchestrate, orchestrate_for_llm


def main() -> None:
    with temp_store() as store:
        blocked_q = (
            'я не могу определиться, какой бренд трусиков лучше.. '
            'Викториас сикрет или Чебоксарский трикотаж?'
        )
        clarify_q = 'Разбери тезис: Прежде чем критиковать мир, наведите идеальный порядок у себя дома'
        answer_q = 'Я потерял смысл, дисциплину и направление'

        blocked_run = orchestrate(blocked_q, user_id='telegram:62001', store=store)
        blocked_prompt = orchestrate_for_llm(
            blocked_q, user_id='telegram:62002', store=store,
        )
        clarify_run = orchestrate(clarify_q, user_id='telegram:62003', store=store)
        clarify_prompt = orchestrate_for_llm(
            clarify_q, user_id='telegram:62004', store=store,
        )
        answer_run = orchestrate(answer_q, user_id='telegram:62005', store=store)
        answer_prompt = orchestrate_for_llm(
            answer_q, user_id='telegram:62006', store=store,
        )

        blocked_env = blocked_prompt.get('decision_envelope') or {}
        clarify_env = clarify_prompt.get('decision_envelope') or {}
        answer_env = answer_prompt.get('decision_envelope') or {}

        results = [
            {
                'name': 'blocked_run_and_prompt_share_decision_type',
                'pass': blocked_run.get('decision_type') == 'respond_policy_text'
                and blocked_prompt.get('decision_type') == 'respond_policy_text'
                and blocked_run.get('adapter_contract', {}).get('model_call_allowed') is False,
            },
            {
                'name': 'blocked_prompt_exposes_no_model_call_contract',
                'pass': should_call_model(blocked_prompt) is False
                and blocked_env.get('allow_model_call') is False
                and blocked_prompt.get('adapter_contract', {}).get('must_honor_decision_envelope') is True,
            },
            {
                'name': 'clarify_run_and_prompt_share_decision_type',
                'pass': clarify_run.get('decision_type') == 'clarify'
                and clarify_prompt.get('decision_type') == 'clarify'
                and clarify_env.get('decision_type') == 'clarify'
                and clarify_run.get('adapter_contract', {}).get('delivery_mode') == 'final_text',
            },
            {
                'name': 'controlled_existential_run_and_prompt_share_decision_type',
                'pass': answer_run.get('decision_type') == 'clarify'
                and answer_prompt.get('decision_type') == 'clarify'
                and answer_env.get('allow_model_call') is False
                and answer_env.get('reason_code') == 'lost-and-aimless'
                and answer_run.get('adapter_contract', {}).get('model_call_allowed') is False,
            },
            {
                'name': 'contracts_keep_final_text_and_trace_consistent',
                'pass': bool(blocked_prompt.get('final_user_text'))
                and bool(clarify_prompt.get('final_user_text'))
                and blocked_prompt.get('trace_id') == blocked_env.get('trace_id')
                and clarify_prompt.get('trace_id') == clarify_env.get('trace_id')
                and answer_prompt.get('trace_id') == answer_env.get('trace_id'),
            },
        ]

        emit_report(
            results,
            samples={
                'blocked_envelope': blocked_env,
                'clarify_envelope': clarify_env,
                'answer_envelope': answer_env,
            },
        )


if __name__ == '__main__':
    main()
