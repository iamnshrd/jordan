"""Mentor persona / user-fit profile derivation."""

from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_MENTOR_STATE, KEY_COMMITMENTS


def build_profile(user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    mentor_state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    commitments = store.get_json(user_id, KEY_COMMITMENTS, default={'items': []}) or {'items': []}
    outcomes = mentor_state.get('event_outcomes') or {}

    def g(key: str, field: str) -> int:
        return int((outcomes.get(key) or {}).get(field, 0) or 0)

    helpful_summary = g('career-vocation::mentor-summary', 'helpful')
    resisted_summary = g('career-vocation::mentor-summary', 'resisted')
    helpful_micro = g('career-vocation::micro-step-prompt', 'helpful')
    movement_small_micro = g('career-vocation::micro-step-prompt', 'movement-small')
    reflection_micro = g('career-vocation::micro-step-prompt', 'reflection') + g('career-vocation::micro-step-prompt', 'reflection-with-intent')
    helpful_commitment = g('career-vocation::commitment-check', 'helpful')
    delay_commitment = g('career-vocation::commitment-check', 'delay-with-intent') + g('career-vocation::commitment-check', 'truthful-delay')
    lazy_delay_commitment = g('career-vocation::commitment-check', 'lazy-delay')
    resisted_broken = g('career-vocation::broken-promise-check', 'resisted')
    fragility_any = sum(int((payload or {}).get('fragility', 0) or 0) for payload in outcomes.values())
    manipulative_fragility_any = sum(int((payload or {}).get('manipulative-fragility', 0) or 0) for payload in outcomes.values())
    irritation_any = sum(int((payload or {}).get('irritation', 0) or 0) for payload in outcomes.values())
    compliance_theater_any = sum(int((payload or {}).get('compliance-theater', 0) or 0) for payload in outcomes.values())
    movement_theater_any = sum(int((payload or {}).get('movement-theater', 0) or 0) for payload in outcomes.values())
    defensive_intelligence_any = sum(int((payload or {}).get('defensive-intelligence', 0) or 0) for payload in outcomes.values())

    items = commitments.get('items') or []
    open_items = [x for x in items if x.get('status') == 'open']
    resolved_items = [x for x in items if x.get('status') == 'resolved']
    hard_open = len([x for x in open_items if x.get('strength') == 'hard'])
    soft_open = len([x for x in open_items if x.get('strength') == 'soft'])

    judgment_clarified = sum(int((payload or {}).get('judgment-clarified', 0) or 0) for payload in outcomes.values())
    ends_clarified = sum(int((payload or {}).get('ends-clarified', 0) or 0) for payload in outcomes.values())
    habit_recognition = sum(int((payload or {}).get('habit-recognition', 0) or 0) for payload in outcomes.values())
    virtue_recognition = sum(int((payload or {}).get('virtue-recognition', 0) or 0) for payload in outcomes.values())
    rationalization_exposed = sum(int((payload or {}).get('rationalization-exposed', 0) or 0) for payload in outcomes.values())

    profile = {
        'pressure_tolerance': 'low' if (fragility_any >= 2 or irritation_any >= 1 or resisted_broken >= 2) else ('high' if helpful_commitment >= 2 and delay_commitment == 0 and lazy_delay_commitment == 0 else 'medium'),
        'summary_response': 'strong' if helpful_summary >= 2 and resisted_summary == 0 else ('weak' if resisted_summary >= 2 or compliance_theater_any >= 2 else 'medium'),
        'micro_step_response': 'strong' if (helpful_micro + movement_small_micro + reflection_micro) >= 2 and movement_theater_any == 0 else ('weak' if movement_theater_any >= 2 else 'medium'),
        'accountability_response': 'strong' if helpful_commitment >= 2 else ('medium' if delay_commitment >= 1 and lazy_delay_commitment == 0 else 'weak'),
        'followthrough_reliability': 'high' if len(resolved_items) >= len(open_items) and resolved_items else ('low' if hard_open >= 2 or lazy_delay_commitment >= 2 else 'medium'),
        'clarity_need': 'high' if soft_open >= 2 or defensive_intelligence_any >= 2 else 'medium',
        'shame_fragility': 'high' if fragility_any >= 2 else ('medium' if fragility_any >= 1 else 'low'),
        'clarity_of_ends': 'high' if ends_clarified >= 2 else ('medium' if ends_clarified >= 1 else 'low'),
        'judgment_quality': 'high' if judgment_clarified >= 2 and rationalization_exposed >= 1 and defensive_intelligence_any == 0 else ('medium' if judgment_clarified >= 1 or rationalization_exposed >= 1 else 'low'),
        'self_governance': 'high' if habit_recognition >= 2 and len(resolved_items) >= 1 and lazy_delay_commitment == 0 else ('medium' if habit_recognition >= 1 else 'low'),
        'virtue_gap': 'high' if virtue_recognition == 0 and fragility_any + irritation_any + manipulative_fragility_any >= 2 else ('medium' if virtue_recognition == 0 else 'low'),
        'confrontation_receptivity': 'low' if manipulative_fragility_any >= 2 or irritation_any >= 2 else ('high' if helpful_commitment >= 2 and resisted_broken == 0 else 'medium'),
        'truth_tolerance': 'low' if defensive_intelligence_any >= 2 else ('high' if rationalization_exposed >= 2 else 'medium'),
        'excuse_density': 'high' if compliance_theater_any + defensive_intelligence_any + movement_theater_any >= 3 else ('medium' if compliance_theater_any + defensive_intelligence_any >= 1 else 'low'),
        'collapse_tendency': 'high' if fragility_any >= 2 else ('medium' if fragility_any >= 1 or manipulative_fragility_any >= 1 else 'low'),
        'recovery_speed': 'fast' if len(resolved_items) >= 2 and fragility_any == 0 else ('slow' if fragility_any >= 2 or lazy_delay_commitment >= 2 else 'medium'),
        'promise_inflation_tendency': 'high' if hard_open >= 2 and len(resolved_items) == 0 else ('medium' if hard_open >= 1 else 'low'),
    }
    mentor_state['mentor_profile'] = profile
    store.put_json(user_id, KEY_MENTOR_STATE, mentor_state)
    return profile
