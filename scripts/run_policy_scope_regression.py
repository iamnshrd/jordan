#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime.orchestrator import orchestrate, orchestrate_for_llm
from library._core.runtime.planner import should_use_kb


def main() -> None:
    with temp_store() as store:
        shopping_q = (
            'я не могу определиться, какой бренд трусиков лучше.. '
            'Викториас сикрет или Чебоксарский трикотаж?'
        )
        weather_q = 'Какая завтра будет погода в Москве и нужен ли зонтик?'
        tech_q = 'Напиши regex для email и помоги отладить python traceback'
        in_domain_q = 'Я потерял смысл, дисциплину и направление'

        shopping = orchestrate(shopping_q, user_id='telegram:61001', store=store)
        shopping_prompt = orchestrate_for_llm(
            shopping_q, user_id='telegram:61002', store=store,
        )
        weather = orchestrate(weather_q, user_id='telegram:61003', store=store)
        tech = orchestrate(tech_q, user_id='telegram:61004', store=store)
        in_domain = orchestrate(in_domain_q, user_id='telegram:61005', store=store)

        results = [
            {
                'name': 'shopping_comparison_is_policy_blocked',
                'pass': shopping.get('guardrail', {}).get('kind') == 'shopping-comparison'
                and shopping.get('action') == 'answer-directly'
                and 'бренды' in (shopping.get('final_user_text') or '').lower(),
            },
            {
                'name': 'shopping_prompt_path_disables_model_call',
                'pass': shopping_prompt.get('guardrail', {}).get('kind') == 'shopping-comparison'
                and shopping_prompt.get('allow_model_call') is False
                and bool(shopping_prompt.get('system'))
                and bool(shopping_prompt.get('final_user_text')),
            },
            {
                'name': 'weather_request_is_blocked_before_retrieval',
                'pass': weather.get('guardrail', {}).get('kind') == 'weather-request'
                and weather.get('action') == 'answer-directly'
                and not weather.get('selection'),
            },
            {
                'name': 'technical_help_is_out_of_scope',
                'pass': tech.get('guardrail', {}).get('kind') == 'technical-help'
                and tech.get('action') == 'answer-directly',
            },
            {
                'name': 'kb_helper_respects_policy_scope',
                'pass': should_use_kb(shopping_q) is False
                and should_use_kb(weather_q) is False
                and should_use_kb(in_domain_q) is True,
            },
            {
                'name': 'in_domain_question_is_not_policy_blocked',
                'pass': not in_domain.get('guardrail')
                and in_domain.get('action') in {
                    'respond-with-kb',
                    'ask-clarifying-question',
                },
            },
        ]
        emit_report(
            results,
            samples={
                'shopping': shopping.get('final_user_text'),
                'shopping_prompt_system': shopping_prompt.get('system'),
                'weather': weather.get('final_user_text'),
                'tech': tech.get('final_user_text'),
                'in_domain_action': in_domain.get('action'),
            },
        )


if __name__ == '__main__':
    main()
