#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.mentor.delivery import prepare_delivery
from library._core.runtime.orchestrator import orchestrate_for_adapter


def main() -> None:
    with temp_store() as store:
        blocked_q = (
            'я не могу определиться, какой бренд трусиков лучше.. '
            'Викториас сикрет или Чебоксарский трикотаж?'
        )
        answer_q = 'Я потерял смысл, дисциплину и направление'

        blocked = orchestrate_for_adapter(
            blocked_q, user_id='telegram:63001', store=store,
        )
        answered = orchestrate_for_adapter(
            answer_q, user_id='telegram:63002', store=store,
        )

        evaluation = {
            'skip': False,
            'route': 'career-vocation',
            'question': 'Я потерял направление и опять ушёл в туман.',
            'selected_event': {
                'type': 'direction-check',
                'route': 'career-vocation',
                'summary': 'direction-check',
                'delivery': {
                    'delivery_class': 'canonical-proactive',
                    'requires_canonical': True,
                    'safe_to_send_direct': False,
                },
            },
        }
        mentor_delivery = prepare_delivery(
            evaluation, user_id='telegram:63003', store=store,
        )
        canonical_result = mentor_delivery.get('canonical_result') or {}

        results = [
            {
                'name': 'blocked_adapter_payload_resolves_to_final_text',
                'pass': blocked.get('delivery_mode') == 'final_text'
                and bool(blocked.get('message'))
                and blocked.get('adapter_contract', {}).get('must_not_call_model_when_blocked') is True,
            },
            {
                'name': 'controlled_existential_adapter_payload_resolves_to_final_text',
                'pass': answered.get('delivery_mode') == 'final_text'
                and answered.get('decision_type') == 'clarify'
                and bool(answered.get('message'))
                and not bool(answered.get('system'))
                and not bool(answered.get('user'))
                and answered.get('adapter_contract', {}).get('model_call_allowed') is False,
            },
            {
                'name': 'mentor_canonical_result_carries_adapter_contract',
                'pass': canonical_result.get('adapter_contract', {}).get('must_honor_decision_envelope') is True
                and canonical_result.get('decision_envelope', {}).get('decision_type') in {
                    'respond_kb', 'clarify', 'respond_policy_text',
                },
            },
        ]

        emit_report(
            results,
            samples={
                'blocked': blocked,
                'answered': {
                    'delivery_mode': answered.get('delivery_mode'),
                    'decision_type': answered.get('decision_type'),
                    'has_system': bool(answered.get('system')),
                    'has_user': bool(answered.get('user')),
                },
                'mentor_delivery_path_type': mentor_delivery.get('delivery_path_type'),
                'mentor_canonical_decision_type': canonical_result.get('decision_type'),
            },
        )


if __name__ == '__main__':
    main()
