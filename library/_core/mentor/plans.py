"""Multi-step intervention planning for mentor flows."""

from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_MENTOR_STATE
from library.utils import now_iso


def _append_plan_trace(state: dict, entry: dict) -> None:
    trace = list(state.get('plan_debug_trace') or [])
    trace.append({'ts': now_iso(), **entry})
    state['plan_debug_trace'] = trace[-50:]


def current_plan(user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    return state.get('active_plan') or {}


def _plan_stats(plan: dict | None) -> dict:
    plan = plan or {}
    return dict(plan.get('stats') or {})


def _set_status(plan: dict, status: str, reason: str = '') -> dict:
    plan['status'] = status
    if reason:
        plan['status_reason'] = reason
    plan['updated_at'] = now_iso()
    return plan


def build_plan(route: str, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None, force_variant: str = '') -> dict:
    mentor_profile = mentor_profile or {}
    objective = ''
    doctrine_family = ''
    if force_variant == 'reorientation':
        if route == 'career-vocation':
            steps = ['direction-check', 'micro-step-prompt', 'mentor-summary']
            plan_type = 'reorientation-career'
            doctrine_family = 'reorientation'
            objective = 'restore orientation and reduce confusion before renewed action pressure'
        elif route == 'relationship-maintenance':
            steps = ['mentor-summary', 'repair-check', 'micro-step-prompt']
            plan_type = 'reorientation-relationship'
            doctrine_family = 'reorientation'
            objective = 'restore relational footing before renewed repair pressure'
        else:
            steps = ['mentor-summary', 'open-loop-followup', 'micro-step-prompt']
            plan_type = 'reorientation-general'
            doctrine_family = 'reorientation'
            objective = 'stabilize context and reopen a workable path'
    elif route == 'career-vocation':
        if mentor_profile.get('clarity_of_ends') == 'low':
            steps = ['ends-clarification-check', 'frame-setting-check', 'micro-step-prompt', 'commitment-check']
            plan_type = 'clarity-of-ends-to-action'
            doctrine_family = 'ends-first'
            objective = 'clarify telos and decision frame before action pressure'
        elif mentor_profile.get('judgment_quality') == 'low':
            steps = ['frame-setting-check', 'vagueness-challenge', 'micro-step-prompt', 'commitment-check']
            plan_type = 'judgment-to-action'
            doctrine_family = 'judgment-first'
            objective = 'repair reasoning quality before commitment pressure'
        elif mentor_profile.get('summary_response') == 'weak':
            steps = ['vagueness-challenge', 'micro-step-prompt', 'commitment-check']
            plan_type = 'clarity-direct-to-action'
            doctrine_family = 'direct-action'
            objective = 'cut through vagueness and force movement quickly'
        else:
            steps = ['mentor-summary', 'vagueness-challenge', 'micro-step-prompt', 'commitment-check']
            plan_type = 'clarity-to-action'
            doctrine_family = 'summary-to-action'
            objective = 'summarize the field, increase clarity, then force action'
    elif route == 'relationship-maintenance':
        if mentor_profile.get('clarity_of_ends') == 'low':
            steps = ['ends-clarification-check', 'repair-check', 'commitment-check']
            plan_type = 'relationship-ends-to-repair'
            doctrine_family = 'ends-first'
            objective = 'clarify what kind of relationship order is sought before repair pressure'
        elif mentor_profile.get('pressure_tolerance') == 'low':
            steps = ['mentor-summary', 'repair-check', 'commitment-check']
            plan_type = 'soft-repair-to-closure'
            doctrine_family = 'soft-repair'
            objective = 'reopen repair without triggering defensive collapse'
        else:
            steps = ['repair-check', 'commitment-check', 'broken-promise-check']
            plan_type = 'repair-to-closure'
            doctrine_family = 'repair-to-closure'
            objective = 'move from repair intent into accountable closure'
    elif route in {'addiction-chaos', 'resentment', 'shame-self-contempt'} and mentor_profile.get('self_governance') == 'low':
        steps = ['habit-formation-check', 'micro-step-prompt', 'commitment-check']
        plan_type = 'habit-to-action'
        doctrine_family = 'habit-first'
        objective = 'surface the habit being built, then push concrete action'
    elif route == 'self-deception' and mentor_profile.get('judgment_quality') == 'low':
        steps = ['frame-setting-check', 'truth-demand-check', 'commitment-check']
        plan_type = 'truth-through-judgment'
        doctrine_family = 'judgment-first'
        objective = 'repair framing and expose rationalization before action'
    else:
        steps = ['open-loop-followup', 'micro-step-prompt', 'commitment-check']
        plan_type = 'followup-to-action'
        doctrine_family = 'followup-to-action'
        objective = 're-engage the open loop and move it toward action'
    return {
        'plan_type': plan_type,
        'doctrine_family': doctrine_family,
        'objective': objective,
        'route': route,
        'steps': steps,
        'stage': 0,
        'status': 'active',
        'status_reason': '',
        'handoff_to': '',
        'handoff_stage': 0,
        'handoff_mode': '',
        'handoff_ticks': 0,
        'updated_at': now_iso(),
        'stats': {
            'sent_count': 0,
            'movement_count': 0,
            'resistance_count': 0,
            'fragility_count': 0,
            'stall_count': 0,
            'last_event_type': '',
            'last_rich_outcome': '',
        },
    }


def ensure_plan(route: str, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    plan = state.get('active_plan') or {}
    if not plan or plan.get('route') != route:
        plan = build_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
        state['active_plan'] = plan
        _append_plan_trace(state, {'decision': 'build-plan', 'route': route, 'plan_type': plan.get('plan_type', ''), 'doctrine_family': plan.get('doctrine_family', ''), 'objective': plan.get('objective', '')})
        store.put_json(user_id, KEY_MENTOR_STATE, state)
    elif plan.get('status') == 'completed':
        prev = state.get('active_plan') or {}
        handoff = prev.get('handoff_to', '')
        handoff_stage = int(prev.get('handoff_stage', 0) or 0)
        handoff_mode = prev.get('handoff_mode', '')
        handoff_ticks = int(prev.get('handoff_ticks', 0) or 0)
        plan = build_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
        if handoff == 'clarity-direct-to-action':
            plan = build_plan(route, user_id=user_id, store=store, mentor_profile={**(mentor_profile or {}), 'summary_response': 'weak'})
        elif handoff == 'soft-repair-to-closure':
            plan = build_plan(route, user_id=user_id, store=store, mentor_profile={**(mentor_profile or {}), 'pressure_tolerance': 'low'})
        plan['stage'] = min(handoff_stage, len(plan.get('steps') or []))
        plan['status_reason'] = f"handoff-from-{prev.get('plan_type', '')}"
        if handoff_mode:
            plan['handoff_mode'] = handoff_mode
            plan['handoff_ticks'] = handoff_ticks
        state['active_plan'] = plan
        if handoff_mode:
            state['handoff_mode'] = handoff_mode
            state['handoff_ticks'] = handoff_ticks
        _append_plan_trace(state, {'decision': 'handoff-plan', 'route': route, 'plan_type': plan.get('plan_type', ''), 'doctrine_family': plan.get('doctrine_family', ''), 'objective': plan.get('objective', ''), 'source_handoff': handoff})
        store.put_json(user_id, KEY_MENTOR_STATE, state)
    elif plan.get('status') in {'failed', 'reset'}:
        prior_status = (state.get('active_plan') or {}).get('status', '')
        plan = build_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile, force_variant='reorientation')
        plan['status'] = 'active'
        plan['status_reason'] = f"replanned-from-{prior_status}"
        state['active_plan'] = plan
        _append_plan_trace(state, {'decision': 'rebuild-reorientation', 'route': route, 'from_status': prior_status, 'plan_type': plan.get('plan_type', ''), 'doctrine_family': plan.get('doctrine_family', ''), 'objective': plan.get('objective', '')})
        store.put_json(user_id, KEY_MENTOR_STATE, state)
    return plan


def step_bonus(route: str, event_type: str, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None) -> int:
    plan = ensure_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
    steps = plan.get('steps') or []
    stage = int(plan.get('stage', 0) or 0)
    if stage < len(steps) and steps[stage] == event_type:
        return 18
    if event_type in steps[max(0, stage - 1): stage + 2]:
        return 6
    return 0


def advance_plan(event_type: str, route: str, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    plan = ensure_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
    steps = plan.get('steps') or []
    stage = int(plan.get('stage', 0) or 0)
    stats = _plan_stats(plan)
    stats['sent_count'] = int(stats.get('sent_count', 0) or 0) + 1
    stats['last_event_type'] = event_type
    if stage < len(steps) and steps[stage] == event_type:
        plan['stage'] = stage + 1
    else:
        stats['stall_count'] = int(stats.get('stall_count', 0) or 0) + 1
    plan['stats'] = stats
    plan['updated_at'] = now_iso()
    if plan.get('stage', 0) >= len(steps):
        _set_status(plan, 'completed', 'all-steps-covered')
    elif int(stats.get('stall_count', 0) or 0) >= 2 and int(stats.get('movement_count', 0) or 0) == 0:
        _set_status(plan, 'stalled', 'repeated-off-path-events')
    state['active_plan'] = plan
    _append_plan_trace(state, {'decision': 'advance-plan', 'route': route, 'event_type': event_type, 'plan_type': plan.get('plan_type', ''), 'stage': plan.get('stage', 0), 'status': plan.get('status', '')})
    store.put_json(user_id, KEY_MENTOR_STATE, state)
    return plan


def branch_plan_on_outcome(rich_outcome: str, route: str, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    plan = ensure_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
    stage = int(plan.get('stage', 0) or 0)
    stats = _plan_stats(plan)
    stats['last_rich_outcome'] = rich_outcome

    if rich_outcome in {'movement', 'movement-small', 'reflection-with-intent', 'judgment-clarified', 'ends-clarified', 'virtue-recognition', 'habit-recognition', 'rationalization-exposed'}:
        stats['movement_count'] = int(stats.get('movement_count', 0) or 0) + 1
    if rich_outcome in {'deflection', 'resistance', 'delay-with-intent'}:
        stats['resistance_count'] = int(stats.get('resistance_count', 0) or 0) + 1
    if rich_outcome in {'fragility', 'irritation'}:
        stats['fragility_count'] = int(stats.get('fragility_count', 0) or 0) + 1

    if rich_outcome in {'movement', 'movement-small', 'reflection-with-intent', 'judgment-clarified', 'ends-clarified', 'virtue-recognition', 'habit-recognition', 'rationalization-exposed'}:
        plan['stage'] = min(stage + 1, len(plan.get('steps') or []))
    elif rich_outcome == 'reflection':
        if 'micro-step-prompt' in (plan.get('steps') or []) and stage < len(plan['steps']):
            idx = plan['steps'].index('micro-step-prompt')
            plan['stage'] = min(idx, len(plan['steps']))
    elif rich_outcome in {'deflection', 'resistance'}:
        plan['steps'] = ['resistance-soft-checkin'] + [x for x in plan.get('steps', []) if x != 'resistance-soft-checkin']
        plan['stage'] = 0
    elif rich_outcome == 'delay-with-intent':
        _set_status(plan, 'paused', 'delay-with-intent')
    elif rich_outcome in {'fragility', 'irritation'}:
        preferred = 'mentor-summary' if (mentor_profile or {}).get('summary_response') != 'weak' else 'micro-step-prompt'
        plan['steps'] = [preferred] + [x for x in plan.get('steps', []) if x != preferred]
        plan['stage'] = 0
        if int(stats.get('fragility_count', 0) or 0) >= 2:
            _set_status(plan, 'paused', 'fragility-soft-pause')
    elif rich_outcome == 'moral-posturing':
        preferred = 'frame-setting-check' if 'frame-setting-check' in (plan.get('steps') or []) else 'micro-step-prompt'
        plan['steps'] = [preferred] + [x for x in plan.get('steps', []) if x != preferred]
        plan['stage'] = 0

    if plan.get('plan_type', '').startswith('reorientation-'):
        if int(stats.get('movement_count', 0) or 0) >= 1:
            _set_status(plan, 'completed', 'reorientation-succeeded')
            if route == 'career-vocation':
                plan['handoff_to'] = 'clarity-direct-to-action' if (mentor_profile or {}).get('summary_response') == 'weak' else 'clarity-to-action'
                plan['handoff_stage'] = 1
                plan['handoff_mode'] = 'gentle'
                plan['handoff_ticks'] = 3 if (mentor_profile or {}).get('pressure_tolerance') == 'low' else 2
            elif route == 'relationship-maintenance':
                plan['handoff_to'] = 'soft-repair-to-closure' if (mentor_profile or {}).get('pressure_tolerance') == 'low' else 'repair-to-closure'
                plan['handoff_stage'] = 1
                plan['handoff_mode'] = 'gentle'
                plan['handoff_ticks'] = 3 if (mentor_profile or {}).get('pressure_tolerance') == 'low' else 2
            else:
                plan['handoff_to'] = 'followup-to-action'
                plan['handoff_stage'] = 0
                plan['handoff_mode'] = 'gentle'
                plan['handoff_ticks'] = 2
        elif int(stats.get('resistance_count', 0) or 0) >= 2 and int(stats.get('movement_count', 0) or 0) == 0:
            _set_status(plan, 'failed', 'reorientation-failed')
        elif int(stats.get('fragility_count', 0) or 0) >= 2:
            _set_status(plan, 'paused', 'reorientation-fragility')
    elif int(stats.get('resistance_count', 0) or 0) >= 3 and int(stats.get('movement_count', 0) or 0) == 0:
        _set_status(plan, 'failed', 'no-progress-under-repeated-resistance')
    elif plan.get('status') == 'active' and int(stats.get('movement_count', 0) or 0) >= 1 and int(stats.get('resistance_count', 0) or 0) >= 2:
        _set_status(plan, 'reset', 'mixed-signal-replan')
    elif plan.get('status') == 'active' and int(stats.get('resistance_count', 0) or 0) >= 2:
        _set_status(plan, 'stalled', 'repeated-resistance')

    if plan.get('stage', 0) >= len(plan.get('steps') or []):
        _set_status(plan, 'completed', 'outcome-advanced-to-end')

    plan['stats'] = stats
    plan['updated_at'] = now_iso()
    state['active_plan'] = plan
    _append_plan_trace(state, {'decision': 'branch-on-outcome', 'route': route, 'rich_outcome': rich_outcome, 'plan_type': plan.get('plan_type', ''), 'doctrine_family': plan.get('doctrine_family', ''), 'stage': plan.get('stage', 0), 'status': plan.get('status', ''), 'status_reason': plan.get('status_reason', '')})
    store.put_json(user_id, KEY_MENTOR_STATE, state)
    return plan
