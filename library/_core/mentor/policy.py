"""Policy helpers for event-driven mentor follow-ups."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from library._core.mentor.commitments import commitment_summary, best_open_commitment

MODE_MIN_GAP_HOURS = {
    'gentle': 36,
    'standard': 18,
    'hard': 12,
    'silent': 10**9,
}

MODE_COOLDOWN_HOURS = {
    'gentle': 36,
    'standard': 24,
    'hard': 16,
    'silent': 10**9,
}

EVENT_COOLDOWN_HOURS = {
    'mentor-summary': 36,
    'open-loop-followup': 18,
    'micro-step-prompt': 12,
    'direction-check': 14,
    'commitment-check': 14,
    'broken-promise-check': 16,
    'vagueness-challenge': 16,
    'pattern-naming-check': 14,
    'decision-forcing-check': 16,
    'truth-demand-check': 16,
    'cost-of-delay-check': 16,
    'identity-vs-action-check': 16,
    'false-progress-check': 18,
    'excuse-collapse': 18,
}


def _dynamic_gap_hours(state: dict, mode: str) -> float:
    gap = float(MODE_MIN_GAP_HOURS.get(mode, MODE_MIN_GAP_HOURS['standard']))
    last_type = state.get('last_checkin_type', '')
    last_outcome = state.get('last_rich_outcome', 'neutral')
    unanswered = int(state.get('unanswered_checkins', 0) or 0)
    pressure_debt = int(state.get('pressure_debt', 0) or 0)

    if last_type in {'micro-step-prompt', 'direction-check', 'open-loop-followup'}:
        gap = min(gap, 12.0)
    if last_type == 'mentor-summary':
        gap = max(gap, 24.0)
    if last_type in {'broken-promise-check', 'decision-forcing-check', 'truth-demand-check', 'excuse-collapse'}:
        gap = max(gap, 14.0)

    if last_outcome in {'truthful-delay', 'delay-with-intent'}:
        gap = min(gap, 10.0)
    elif last_outcome in {'movement', 'movement-small', 'reflection-with-intent'}:
        gap = min(gap, 12.0)
    elif last_outcome in {'fragility', 'irritation'}:
        gap = max(gap, 24.0)

    if pressure_debt >= 3:
        gap = min(gap, 12.0)
    if unanswered >= 2:
        gap *= 2.0
    return gap



def _dynamic_cooldown_hours(state: dict, mode: str) -> float:
    cooldown = float(MODE_COOLDOWN_HOURS.get(mode, MODE_COOLDOWN_HOURS['standard']))
    last_type = state.get('last_checkin_type', '')
    last_outcome = state.get('last_rich_outcome', 'neutral')
    unanswered = int(state.get('unanswered_checkins', 0) or 0)
    pressure_debt = int(state.get('pressure_debt', 0) or 0)

    if last_type:
        cooldown = min(cooldown, float(EVENT_COOLDOWN_HOURS.get(last_type, cooldown)))

    if last_outcome in {'truthful-delay', 'delay-with-intent'}:
        cooldown = min(cooldown, 8.0)
    elif last_outcome in {'movement', 'movement-small', 'reflection-with-intent'}:
        cooldown = min(cooldown, 10.0)
    elif last_outcome in {'fragility', 'irritation'}:
        cooldown = max(cooldown, 24.0)

    if pressure_debt >= 3:
        cooldown = min(cooldown, 10.0)
    if unanswered >= 2:
        cooldown = max(cooldown, 24.0)
    return cooldown



def compute_next_cooldown_hours(state: dict) -> float:
    mode = state.get('mode') or 'standard'
    return _dynamic_cooldown_hours(state, mode)


def _urgency_override_reason(state: dict, *, now: datetime) -> str:
    unanswered = int(state.get('unanswered_checkins', 0) or 0)
    if unanswered >= 2:
        return ''

    pressure_debt = int(state.get('pressure_debt', 0) or 0)
    last_outcome = state.get('last_rich_outcome', 'neutral')
    top_commitment = best_open_commitment(store=state.get('_store')) if state.get('_store') else None
    summary = commitment_summary(store=state.get('_store')) if state.get('_store') else {}

    if top_commitment:
        due_at = _parse_iso(top_commitment.get('due_at'))
        strength = top_commitment.get('strength', 'standard')
        count = int(top_commitment.get('count', 1) or 1)
        if due_at and due_at <= now and strength == 'hard':
            return 'urgency-overdue-hard-commitment'
        if strength == 'hard' and count >= 2 and pressure_debt >= 2:
            return 'urgency-repeated-hard-commitment'

    if pressure_debt >= 4:
        return 'urgency-pressure-debt'

    if last_outcome == 'truthful-delay':
        return 'urgency-truthful-delay-window'

    if (summary or {}).get('overdue_hard', 0) >= 1:
        return 'urgency-overdue-hard-summary'
    return ''



def _parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


def should_skip_now(state: dict, *, now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    mode = state.get('mode') or 'standard'
    if mode == 'silent':
        return True, 'silent-mode'
    unanswered = int(state.get('unanswered_checkins', 0) or 0)
    last_at = _parse_iso(state.get('last_checkin_at'))
    urgency_reason = _urgency_override_reason(state, now=now)

    if unanswered >= 3:
        if last_at and now - last_at < timedelta(hours=72):
            return True, 'awaiting-user-reengagement'
        urgency_reason = urgency_reason or 'reengagement-escalation-window'

    cooldown_until = _parse_iso(state.get('cooldown_until'))
    if cooldown_until and now < cooldown_until and not urgency_reason:
        return True, 'cooldown-active'
    min_gap_hours = _dynamic_gap_hours(state, mode)
    if last_at and now - last_at < timedelta(hours=min_gap_hours) and not urgency_reason:
        return True, 'min-gap-not-reached'
    if urgency_reason:
        state['urgency_override_reason'] = urgency_reason
    else:
        state.pop('urgency_override_reason', None)
    return False, ''
