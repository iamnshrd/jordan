#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.mentor.plans import ensure_plan, step_bonus, advance_plan, branch_plan_on_outcome
from library._core.state_store import KEY_MENTOR_STATE


def main() -> None:
    results = []
    passed = 0
    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('steps', [None])[0] == 'mentor-summary'
        results.append({'name': 'plan_init', 'pass': ok, 'plan': plan})
        passed += int(ok)

        bonus = step_bonus('career-vocation', 'mentor-summary', store=store, mentor_profile={'summary_response': 'strong'})
        ok = bonus > 0
        results.append({'name': 'stage_bonus', 'pass': ok, 'bonus': bonus})
        passed += int(ok)

        plan = advance_plan('mentor-summary', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = int(plan.get('stage', 0) or 0) == 1
        results.append({'name': 'advance_stage', 'pass': ok, 'stage': plan.get('stage')})
        passed += int(ok)

        plan = branch_plan_on_outcome('reflection', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = (plan.get('steps') or [None])[int(plan.get('stage', 0) or 0)] == 'micro-step-prompt'
        results.append({'name': 'reflection_branches_to_micro_step', 'pass': ok, 'plan': plan})
        passed += int(ok)

        plan = branch_plan_on_outcome('deflection', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = (plan.get('steps') or [None])[0] == 'resistance-soft-checkin'
        results.append({'name': 'deflection_branches_to_resistance_check', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'weak'})
        ok = (plan.get('steps') or [None])[0] == 'vagueness-challenge'
        results.append({'name': 'weak_summary_profile_changes_plan_entry', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong', 'clarity_of_ends': 'low'})
        ok = plan.get('plan_type') == 'clarity-of-ends-to-action' and plan.get('doctrine_family') == 'ends-first' and 'clarify telos' in (plan.get('objective') or '') and (plan.get('steps') or [None])[0] == 'ends-clarification-check'
        results.append({'name': 'low_clarity_of_ends_changes_plan_entry', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('self-deception', store=store, mentor_profile={'judgment_quality': 'low'})
        ok = plan.get('plan_type') == 'truth-through-judgment' and plan.get('doctrine_family') == 'judgment-first' and 'repair framing' in (plan.get('objective') or '') and (plan.get('steps') or [None])[0] == 'frame-setting-check'
        results.append({'name': 'low_judgment_quality_changes_self_deception_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('addiction-chaos', store=store, mentor_profile={'self_governance': 'low'})
        ok = plan.get('plan_type') == 'habit-to-action' and plan.get('doctrine_family') == 'habit-first' and 'surface the habit' in (plan.get('objective') or '') and (plan.get('steps') or [None])[0] == 'habit-formation-check'
        results.append({'name': 'low_self_governance_changes_habit_route_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('delay-with-intent', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('status') == 'paused'
        results.append({'name': 'delay_with_intent_pauses_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('status') == 'stalled'
        results.append({'name': 'repeated_resistance_stalls_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('movement', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('status') == 'reset'
        results.append({'name': 'mixed_signal_plan_resets', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        store.put_json('default', KEY_MENTOR_STATE, {
            'active_plan': {
                'plan_type': 'clarity-to-action',
                'route': 'career-vocation',
                'steps': ['mentor-summary', 'vagueness-challenge', 'micro-step-prompt', 'commitment-check'],
                'stage': 0,
                'status': 'failed',
                'status_reason': 'no-progress-under-repeated-resistance',
            }
        })
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('plan_type') == 'reorientation-career' and (plan.get('steps') or [None])[0] == 'direction-check'
        results.append({'name': 'failed_plan_forces_reorientation_rebuild', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        store.put_json('default', KEY_MENTOR_STATE, {
            'active_plan': {
                'plan_type': 'clarity-to-action',
                'route': 'career-vocation',
                'steps': ['mentor-summary', 'vagueness-challenge', 'micro-step-prompt', 'commitment-check'],
                'stage': 2,
                'status': 'reset',
                'status_reason': 'mixed-signal-replan',
            }
        })
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('plan_type') == 'reorientation-career'
        results.append({'name': 'reset_plan_forces_reorientation_rebuild', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        store.put_json('default', KEY_MENTOR_STATE, {
            'active_plan': {
                'plan_type': 'reorientation-career',
                'route': 'career-vocation',
                'steps': ['direction-check', 'micro-step-prompt', 'mentor-summary'],
                'stage': 0,
                'status': 'active',
                'status_reason': 'replanned-from-failed',
            }
        })
        plan = branch_plan_on_outcome('movement', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('status') == 'completed' and plan.get('status_reason') == 'reorientation-succeeded' and plan.get('handoff_to') == 'clarity-to-action' and plan.get('handoff_stage') == 1 and plan.get('handoff_mode') == 'gentle' and plan.get('handoff_ticks') == 2
        results.append({'name': 'reorientation_success_completes_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        store.put_json('default', KEY_MENTOR_STATE, {
            'active_plan': {
                'plan_type': 'reorientation-career',
                'route': 'career-vocation',
                'steps': ['direction-check', 'micro-step-prompt', 'mentor-summary'],
                'stage': 0,
                'status': 'active',
                'status_reason': 'replanned-from-failed',
            }
        })
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        plan = branch_plan_on_outcome('resistance', 'career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('status') == 'failed' and plan.get('status_reason') == 'reorientation-failed'
        results.append({'name': 'reorientation_failure_detected', 'pass': ok, 'plan': plan})
        passed += int(ok)

    with temp_store() as store:
        store.put_json('default', KEY_MENTOR_STATE, {
            'active_plan': {
                'plan_type': 'reorientation-career',
                'route': 'career-vocation',
                'steps': ['direction-check', 'micro-step-prompt', 'mentor-summary'],
                'stage': 1,
                'status': 'completed',
                'status_reason': 'reorientation-succeeded',
                'handoff_to': 'clarity-to-action',
                'handoff_stage': 1,
                'handoff_mode': 'gentle',
                'handoff_ticks': 2
            }
        })
        plan = ensure_plan('career-vocation', store=store, mentor_profile={'summary_response': 'strong'})
        ok = plan.get('plan_type') == 'clarity-to-action' and plan.get('status_reason') == 'handoff-from-reorientation-career' and plan.get('stage') == 1 and plan.get('handoff_mode') == 'gentle' and plan.get('handoff_ticks') == 2
        results.append({'name': 'completed_reorientation_handoffs_to_normal_plan', 'pass': ok, 'plan': plan})
        passed += int(ok)

    emit_report(results)


if __name__ == '__main__':
    main()
