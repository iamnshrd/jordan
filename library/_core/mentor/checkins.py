"""Event-driven mentor trigger engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from library.config import canonical_user_id, get_default_store
from library._core.state_store import (
    StateStore,
    KEY_MENTOR_STATE,
    KEY_MENTOR_EVENTS,
    KEY_MENTOR_DELAYS,
)
from library._core.session.continuity import read as read_continuity
from library._core.session.progress import estimate as estimate_progress
from library._core.session.reaction import estimate as estimate_reaction
from library._core.session.state import build_user_profile
from library._core.runtime.routes import infer_route
from library._core.mentor.policy import should_skip_now, compute_next_cooldown_hours
from library._core.mentor.commitments import best_open_commitment, mark_commitment_prompted, commitment_prompt_style, commitment_summary
from library._core.mentor.effectiveness import summarize as summarize_effectiveness
from library._core.mentor.profile import build_profile
from library._core.mentor.outcome import classify_reply
from library._core.mentor.plans import current_plan, ensure_plan, step_bonus, advance_plan, branch_plan_on_outcome
from library.utils import now_iso


AUDIT_SCORE_KEYS = [
    'base',
    'last_type_penalty',
    'fit_bonus',
    'route_penalty',
    'route_bonus',
    'step_bonus',
    'lifecycle_adjust',
    'cop_adjust',
    'effectiveness_adjust',
    'confrontation_penalty',
    'final_priority',
]

AUDIT_FACTOR_LABELS = {
    'base': 'base priority',
    'last_type_penalty': 'repeat-type penalty',
    'fit_bonus': 'profile fit',
    'route_penalty': 'overuse penalty',
    'route_bonus': 'historical route yield',
    'step_bonus': 'plan step alignment',
    'lifecycle_adjust': 'plan lifecycle bias',
    'cop_adjust': 'pressure calibration',
    'effectiveness_adjust': 'historical behavioral yield',
    'confrontation_penalty': 'confrontation backfire memory',
}


def _factor_label(key: str) -> str:
    return AUDIT_FACTOR_LABELS.get(key, key)


def _top_score_factors(score_breakdown: dict, limit: int = 3) -> list[dict]:
    factors: list[dict] = []
    for key in AUDIT_SCORE_KEYS:
        if key == 'final_priority':
            continue
        value = int(score_breakdown.get(key, 0) or 0)
        if value == 0:
            continue
        factors.append({
            'factor': key,
            'label': _factor_label(key),
            'value': value,
            'direction': 'helped' if value > 0 else 'hurt',
            'abs_value': abs(value),
        })
    factors.sort(key=lambda x: (-x['abs_value'], x['factor']))
    return factors[:limit]


def _render_audit_reason(row: dict, perspective: str = 'winner') -> str:
    label = row.get('label', row.get('factor', 'factor'))
    delta = int(row.get('delta', 0) or 0)
    if perspective == 'winner':
        if delta > 0:
            return f"{label} helped the winner more (+{delta})"
        return f"{label} hurt the winner less ({delta})"
    if delta > 0:
        return f"{label} helped the runner-up more (+{delta})"
    return f"{label} hurt the runner-up less ({delta})"



def _selection_audit_summary(events: list[dict]) -> dict:
    if not events:
        return {}
    winner = dict(events[0])
    runner_up = dict(events[1]) if len(events) > 1 else {}
    winner_score = dict(winner.get('score_breakdown') or {})
    runner_score = dict(runner_up.get('score_breakdown') or {})
    winner_priority = int(winner.get('priority', 0) or 0)
    runner_priority = int(runner_up.get('priority', 0) or 0)
    diff_keys = [key for key in AUDIT_SCORE_KEYS if key != 'final_priority' and int(winner_score.get(key, 0) or 0) != int(runner_score.get(key, 0) or 0)]
    diff_rows = []
    for key in diff_keys:
        winner_val = int(winner_score.get(key, 0) or 0)
        runner_val = int(runner_score.get(key, 0) or 0)
        delta = winner_val - runner_val
        diff_rows.append({
            'factor': key,
            'label': _factor_label(key),
            'winner_value': winner_val,
            'runner_up_value': runner_val,
            'delta': delta,
            'winner_effect': 'helped winner more' if delta > 0 else 'hurt winner less',
        })
    diff_rows.sort(key=lambda x: (-abs(int(x.get('delta', 0) or 0)), x.get('factor', '')))
    why_won = diff_rows[:3]
    why_lost = [
        {
            'factor': row['factor'],
            'label': row['label'],
            'winner_value': row['runner_up_value'],
            'runner_up_value': row['winner_value'],
            'delta': row['runner_up_value'] - row['winner_value'],
            'winner_effect': 'helped runner-up more' if (row['runner_up_value'] - row['winner_value']) > 0 else 'hurt runner-up less',
        }
        for row in diff_rows[:3]
    ] if runner_up else []
    winner_summary = ''
    runner_summary = ''
    if runner_up:
        winner_summary = f"Selected {winner.get('type', '')} over {runner_up.get('type', '')} by {winner_priority - runner_priority} points. "
        if why_won:
            winner_summary += '; '.join(_render_audit_reason(row, perspective='winner') for row in why_won[:2])
        runner_summary = f"Runner-up {runner_up.get('type', '')} lost to {winner.get('type', '')}. "
        if why_lost:
            runner_summary += '; '.join(_render_audit_reason(row, perspective='runner_up') for row in why_lost[:2])
    else:
        winner_summary = f"Selected {winner.get('type', '')} with no close runner-up."
    return {
        'winner': {
            'event_type': winner.get('type', ''),
            'route': winner.get('route', ''),
            'priority': winner_priority,
            'top_factors': _top_score_factors(winner_score),
            'summary': winner_summary,
        },
        'runner_up': {
            'event_type': runner_up.get('type', ''),
            'route': runner_up.get('route', ''),
            'priority': runner_priority,
            'top_factors': _top_score_factors(runner_score),
            'summary': runner_summary,
        } if runner_up else {},
        'margin': winner_priority - runner_priority,
        'why_won': why_won,
        'why_lost': why_lost,
        'plain_summary': winner_summary,
        'runner_up_summary': runner_summary,
    }


def load_state(user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    state.setdefault('mode', 'standard')
    state.setdefault('event_type_counts', {})
    state.setdefault('route_event_type_counts', {})
    state.setdefault('event_outcomes', {})
    state.setdefault('last_rich_outcome', 'neutral')
    state.setdefault('pressure_debt', 0)
    state.setdefault('softness_budget', 0)
    state.setdefault('handoff_mode', '')
    state.setdefault('handoff_ticks', 0)
    state.setdefault('pressure_rationale', [])
    state.setdefault('softness_rationale', [])
    state.setdefault('handoff_rationale', [])
    state.setdefault('plan_debug_trace', [])
    return state


def save_state(state: dict, user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state['updated_at'] = now_iso()
    store.put_json(user_id, KEY_MENTOR_STATE, state)
    return state


def _route_fit(route: str, summary: str) -> int:
    s = (summary or '').lower()
    if route == 'career-vocation':
        if any(x in s for x in ['смысл', 'ориентац', 'туман', 'бремя', 'направлен']):
            return 30
        if any(x in s for x in ['обида', 'горечь']):
            return -20
    if route == 'relationship-maintenance':
        if any(x in s for x in ['отнош', 'обида', 'невысказан', 'конфликт']):
            return 25
    if route == 'shame-self-contempt':
        if any(x in s for x in ['саморазруш', 'провал', 'стыд', 'боль']):
            return 25
    if route == 'self-deception':
        if any(x in s for x in ['самообман', 'неясности', 'честн', 'лож']):
            return 25
    if route == 'addiction-chaos':
        if any(x in s for x in ['хаос', 'структура распалась', 'зависим']):
            return 25
    return 0


def _best_open_loop(route: str, continuity: dict) -> dict | None:
    loops = continuity.get('open_loops') or []
    if not loops:
        return None
    ranked = []
    for item in loops:
        salience = int(item.get('salience', 0) or 0)
        fit = _route_fit(route, item.get('summary', ''))
        ranked.append((salience + fit, salience, item))
    ranked.sort(key=lambda x: (-x[0], -x[1]))
    return ranked[0][2] if ranked else None


def _route_prompt(route: str, event_type: str, summary: str, mode: str) -> str:
    if route == 'career-vocation':
        if event_type == 'micro-step-prompt':
            return 'Назови один шаг на 10–15 минут, который ты сделаешь сегодня, чтобы выйти из тумана.' if mode != 'hard' else 'Без общих слов: какой конкретный шаг на 10–15 минут ты сделаешь сегодня?'
        if mode == 'hard':
            return 'Хватит жить в тумане. Какой один конкретный шаг ты сделал, чтобы выбрать направление?'
        if mode == 'gentle':
            return f'Это всё ещё висит: {summary}. Есть хоть небольшой сдвиг?' if event_type == 'open-loop-followup' else 'Какой маленький шаг ты уже сделал, чтобы стало яснее, куда двигаться?'
        if event_type == 'open-loop-followup':
            return f'Ты так и не закрыл это: {summary}. Что сдвинулось?'
        return 'Какой один шаг ты реально сделал, чтобы выйти из тумана и двинуться дальше?'
    if route == 'relationship-maintenance':
        if event_type == 'repair-check':
            return 'Какой честный разговор или маленький акт прояснения ты уже сделал?' if mode != 'hard' else 'Что ты честно проговорил, вместо того чтобы снова копить напряжение?'
        if mode == 'hard':
            return 'Ты продолжаешь носить это напряжение в отношениях. Что ты сказал честно, а не утаил?'
        if mode == 'gentle':
            return f'Это всё ещё висит между вами: {summary}. Ты что-то мягко прояснил?' if event_type == 'open-loop-followup' else 'Что ты сделал, чтобы не оставить это снова в недосказанности?'
        if event_type == 'open-loop-followup':
            return f'Это всё ещё висит между вами: {summary}. Что ты прояснил?'
        return 'Что ты сделал, чтобы не дать обиде и дальше управлять разговором?'
    if route == 'shame-self-contempt':
        if event_type == 'micro-step-prompt':
            return 'Какой один посильный и честный шаг ты сделал вместо очередного удара по себе?' if mode != 'hard' else 'Что ты сделал на деле, кроме того что снова себя добил?'
        if mode == 'hard':
            return 'Хватит растворяться в самоуничижении. Что ты сделал, кроме того что снова ударил по себе?'
        if mode == 'gentle':
            return f'Это всё ещё болит: {summary}. Ты сделал хоть один бережный, но честный шаг?' if event_type == 'open-loop-followup' else 'Ты сделал хоть один небольшой шаг в сторону порядка, а не самонаказания?'
        if event_type == 'open-loop-followup':
            return f'Ты всё ещё не закрыл это: {summary}. Что изменилось на деле?'
        return 'Ты сделал хоть один честный и посильный шаг вместо очередного удара по себе?'
    if route == 'self-deception':
        return 'Что ты уже перестал себе врать насчёт этой ситуации?' if mode != 'gentle' else 'Что здесь стало для тебя чуть честнее и яснее?'
    if route == 'addiction-chaos':
        return 'Что ты сделал, чтобы внести хоть немного порядка туда, где всё снова расползается?' if mode != 'gentle' else 'Удалось ли тебе вернуть хоть немного порядка туда, где всё расползается?'
    if event_type == 'open-loop-followup':
        return f'Ты так и не закрыл это: {summary}. Что сдвинулось?'
    return 'Какой реальный сдвиг у тебя произошёл с прошлого раза?'


def _candidate_events(question: str, continuity: dict, progress: dict, reaction: dict, mode: str = 'standard', state: dict | None = None, user_id: str = 'default', store: StateStore | None = None, mentor_profile: dict | None = None) -> list[dict]:
    route = infer_route(question) if question else 'general'
    events: list[dict] = []
    debug_trace: list[dict] = []

    state = state or {}
    mentor_profile = mentor_profile or {}
    last_route = state.get('last_checkin_route', '')
    last_type = state.get('last_checkin_type', '')
    event_counts = state.get('event_type_counts') or {}
    route_counts = state.get('route_event_type_counts') or {}
    event_outcomes = state.get('event_outcomes') or {}
    last_rich_outcome = state.get('last_rich_outcome', 'neutral')
    softness_budget = int(state.get('softness_budget', 0) or 0)
    pressure_debt = int(state.get('pressure_debt', 0) or 0)

    def route_event_penalty(rt: str, et: str) -> int:
        total = int(event_counts.get(et, 0) or 0)
        routed = int(route_counts.get(f'{rt}::{et}', 0) or 0)
        return total * 3 + routed * 5

    def route_event_bonus(rt: str, et: str) -> int:
        payload = dict(event_outcomes.get(f'{rt}::{et}') or event_outcomes.get(et) or {})
        helpful = int(payload.get('helpful', 0) or 0)
        neutral = int(payload.get('neutral', 0) or 0)
        resisted = int(payload.get('resisted', 0) or 0)
        ignored = int(payload.get('ignored', 0) or 0)
        return helpful * 8 + neutral * 2 - resisted * 6 - ignored * 4

    effectiveness_summary = summarize_effectiveness(user_id=user_id, store=store)
    effectiveness_by_key = {row.get('key', ''): row for row in (effectiveness_summary.get('best', []) + effectiveness_summary.get('worst', [])) if row.get('key')}
    effectiveness_by_route = {row.get('route', ''): row for row in effectiveness_summary.get('by_route', []) if row.get('route')}

    def effectiveness_adjust(rt: str, et: str) -> int:
        row = dict(effectiveness_by_key.get(f'{rt}::{et}') or {})
        route_row = dict(effectiveness_by_route.get(rt) or {})
        score = 0
        used = int(row.get('used', 0) or 0)
        if used >= 2:
            score += int(round(float(row.get('followthrough_ratio', 0.0) or 0.0) * 20))
            score -= int(round(float(row.get('theater_ratio', 0.0) or 0.0) * 24))
            score += min(6, int(row.get('truthful_delay', 0) or 0) * 2)
            score -= min(10, int(row.get('lazy_delay', 0) or 0) * 3)
        resolved_delay = int(row.get('resolved_delayed_followthrough', 0) or 0)
        pending_delay = int(row.get('pending_delayed_followthrough', 0) or 0)
        if (resolved_delay + pending_delay) >= 2:
            score += int(round(float(row.get('delayed_followthrough_ratio', 0.0) or 0.0) * 12))
            if pending_delay > resolved_delay:
                score -= min(10, (pending_delay - resolved_delay) * 2)
        route_used = int(route_row.get('used', 0) or 0)
        if route_used >= 4:
            score += int(round(float(route_row.get('followthrough_ratio', 0.0) or 0.0) * 8))
            score -= int(round(float(route_row.get('theater_ratio', 0.0) or 0.0) * 10))
        route_resolved_delay = int(route_row.get('resolved_delayed_followthrough', 0) or 0)
        route_pending_delay = int(route_row.get('pending_delayed_followthrough', 0) or 0)
        if (route_resolved_delay + route_pending_delay) >= 3:
            score += int(round(float(route_row.get('delayed_followthrough_ratio', 0.0) or 0.0) * 6))
            if route_pending_delay > route_resolved_delay:
                score -= min(8, route_pending_delay - route_resolved_delay)
        return score

    def confrontation_penalty(rt: str, et: str) -> int:
        payload = dict(event_outcomes.get(f'{rt}::{et}') or {})
        used = int(payload.get('used', 0) or 0)
        helpful = int(payload.get('helpful', 0) or 0)
        resisted = int(payload.get('resisted', 0) or 0)
        irritation = int(payload.get('irritation', 0) or 0)
        fragility = int(payload.get('fragility', 0) or 0)
        if used == 0:
            return 0
        return resisted * 10 + irritation * 14 + fragility * 12 - helpful * 6

    def cop_adjust(event_type: str) -> int:
        score = 0
        soft_types = {'mentor-summary', 'micro-step-prompt', 'open-loop-followup', 'resistance-soft-checkin'}
        hard_types = {'broken-promise-check', 'vagueness-challenge', 'commitment-check', 'pattern-naming-check', 'decision-forcing-check', 'truth-demand-check', 'cost-of-delay-check', 'identity-vs-action-check', 'false-progress-check', 'excuse-collapse'}
        if softness_budget >= 2 and event_type in soft_types:
            score -= 14
        if softness_budget >= 2 and event_type in hard_types:
            score += 10
        if pressure_debt >= 2 and event_type in hard_types:
            score += 16
        if pressure_debt >= 2 and event_type in soft_types:
            score -= 8
        return score

    plan = (state.get('active_plan') or {}) if (state.get('active_plan') or {}).get('route') == route else ensure_plan(route, user_id=user_id, store=store, mentor_profile=mentor_profile)
    plan_status = plan.get('status', 'active')
    plan_reason = plan.get('status_reason', '')
    handoff_mode = state.get('handoff_mode', '')
    handoff_ticks = int(state.get('handoff_ticks', 0) or 0)
    plan_stage = int(plan.get('stage', 0) or 0)
    plan_steps = plan.get('steps') or []
    preferred_next = plan_steps[plan_stage] if plan_stage < len(plan_steps) else ''
    confrontation_debug: list[dict] = []

    def lifecycle_adjust(event_type: str) -> int:
        score = 0
        if plan_status == 'paused':
            if event_type in {'mentor-summary', 'micro-step-prompt', 'open-loop-followup'}:
                score += 24
            if event_type in {'broken-promise-check', 'vagueness-challenge'}:
                score -= 28
        elif plan_status == 'stalled':
            if event_type in {'mentor-summary', 'micro-step-prompt', 'direction-check', 'resistance-soft-checkin'}:
                score += 18
            if event_type in {'broken-promise-check', 'commitment-check'}:
                score -= 18
        elif plan_status == 'failed':
            if event_type in {'mentor-summary', 'direction-check'}:
                score += 26
            if event_type in {'broken-promise-check', 'commitment-check', 'vagueness-challenge'}:
                score -= 36
        if preferred_next and event_type == preferred_next and plan_status == 'active':
            score += 10
        return score

    def lifecycle_blocked(event_type: str) -> bool:
        if handoff_mode == 'gentle' and handoff_ticks > 0:
            if handoff_ticks >= 2:
                if event_type in {'broken-promise-check', 'commitment-check'}:
                    return True
            elif handoff_ticks == 1:
                if event_type in {'broken-promise-check'}:
                    return True
        if plan_status == 'paused':
            return event_type in {'broken-promise-check'}
        if plan_status == 'failed':
            return event_type in {'broken-promise-check', 'commitment-check', 'vagueness-challenge'}
        if plan_status == 'stalled' and plan_reason == 'repeated-resistance':
            return event_type in {'broken-promise-check'}
        return False

    def compose_score(event_type: str, rt: str, *, base: int, last_type_penalty: int = 0, fit_bonus: int = 0, use_step_bonus: bool = False, use_lifecycle_adjust: bool = False, use_cop_adjust: bool = False, use_confrontation_penalty: bool = False, use_effectiveness_adjust: bool = False) -> tuple[int, dict]:
        route_pen = route_event_penalty(rt, event_type)
        route_bonus = route_event_bonus(rt, event_type)
        step_adj = step_bonus(rt, event_type, user_id=user_id, store=store, mentor_profile=mentor_profile) if use_step_bonus else 0
        lifecycle_adj = lifecycle_adjust(event_type) if use_lifecycle_adjust else 0
        cop_adj = cop_adjust(event_type) if use_cop_adjust else 0
        confrontation_pen = confrontation_penalty(rt, event_type) if use_confrontation_penalty else 0
        effectiveness_adj = effectiveness_adjust(rt, event_type) if use_effectiveness_adjust else 0
        final_priority = base - last_type_penalty + fit_bonus - route_pen + route_bonus + step_adj + lifecycle_adj + cop_adj + effectiveness_adj - confrontation_pen
        breakdown = {
            'base': base,
            'last_type_penalty': last_type_penalty,
            'fit_bonus': fit_bonus,
            'route_penalty': route_pen,
            'route_bonus': route_bonus,
            'step_bonus': step_adj,
            'lifecycle_adjust': lifecycle_adj,
            'cop_adjust': cop_adj,
            'effectiveness_adjust': effectiveness_adj,
            'confrontation_penalty': confrontation_pen,
            'final_priority': final_priority,
        }
        return final_priority, breakdown

    def maybe_add(event: dict) -> None:
        if not event:
            return
        et = event.get('type', '')
        blocked = lifecycle_blocked(et)
        penalty = confrontation_penalty(event.get('route', route), et) if et in {'pattern-naming-check', 'decision-forcing-check', 'truth-demand-check', 'cost-of-delay-check', 'identity-vs-action-check', 'false-progress-check', 'excuse-collapse'} else 0
        breakdown = dict(event.get('score_breakdown') or {})
        if penalty:
            confrontation_debug.append({'event_type': et, 'route': event.get('route', route), 'decision': 'penalty-applied', 'penalty': penalty, 'base_priority': event.get('priority', 0)})
        if blocked:
            debug_trace.append({'event_type': et, 'decision': 'blocked', 'reason': 'lifecycle-blocked', 'route': event.get('route', route), 'priority': event.get('priority', 0), 'score_breakdown': breakdown})
            return
        if et in {'pattern-naming-check', 'decision-forcing-check', 'truth-demand-check', 'cost-of-delay-check', 'identity-vs-action-check', 'false-progress-check', 'excuse-collapse'} and penalty >= 20:
            debug_trace.append({'event_type': et, 'decision': 'blocked', 'reason': 'confrontation-penalty', 'route': event.get('route', route), 'priority': event.get('priority', 0), 'penalty': penalty, 'score_breakdown': breakdown})
            confrontation_debug.append({'event_type': et, 'route': event.get('route', route), 'decision': 'blocked', 'reason': 'confrontation-penalty', 'penalty': penalty})
            return
        debug_trace.append({'event_type': et, 'decision': 'added', 'route': event.get('route', route), 'priority': event.get('priority', 0), 'summary': event.get('summary', ''), 'score_breakdown': breakdown})
        events.append(event)

    top_loop = _best_open_loop(route, continuity)
    commitment = best_open_commitment(route=route, user_id=user_id, store=store)
    if top_loop and int(top_loop.get('salience', 0) or 0) >= 3:
        fit_bonus = _route_fit(route, top_loop.get('summary', ''))
        last_type_penalty = (18 if last_route == route else 0) + (10 if last_type == 'open-loop-followup' else 0) + (6 if mentor_profile.get('summary_response') == 'strong' else 0)
        priority, score_breakdown = compose_score('open-loop-followup', route, base=80 + int(top_loop.get('salience', 0) or 0), last_type_penalty=last_type_penalty, fit_bonus=fit_bonus, use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'open-loop-followup',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': top_loop.get('summary', ''),
            'prompt': _route_prompt(route, 'open-loop-followup', top_loop.get('summary', ''), mode),
        })

    if progress.get('progress_state') == 'stuck' and int(progress.get('repeat_count', 0) or 0) >= 2:
        priority, score_breakdown = compose_score('stuckness-check', route, base=95 + int(progress.get('stuckness_score', 0) or 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'stuckness-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'stuckness',
            'prompt': 'Ты опять крутишься вокруг той же проблемы. Что ты сделал конкретно с прошлого раза?' if mode == 'hard' else 'Похоже, ты снова топчешься на месте. Что у тебя реально сдвинулось?',
        })

    if reaction.get('user_reaction_estimate') == 'resisting' or last_rich_outcome in {'deflection', 'resistance', 'lazy-delay', 'compliance-theater', 'movement-theater', 'defensive-intelligence'}:
        prompt = 'Не буду давить. Просто скажи честно: ты двигаешься или снова начал уходить в сторону?' if mode != 'hard' else 'Ты снова уходишь в сторону или всё-таки двигаешься?'
        if last_rich_outcome == 'deflection':
            prompt = 'Ты ответил, но ушёл в сторону. Что здесь на самом деле произошло?' if mode == 'gentle' else 'Ты ответил, но ушёл в сторону. Что ты реально сделал или не сделал?'
        priority, score_breakdown = compose_score('resistance-soft-checkin', route, base=60, use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'resistance-soft-checkin',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'resistance',
            'prompt': prompt,
        })

    if commitment:
        fit_bonus = 10 if mentor_profile.get('accountability_response') == 'strong' else (-10 if mentor_profile.get('accountability_response') == 'weak' else 0)
        last_type_penalty = (18 if last_type == 'commitment-check' else 0) + (8 if last_route == route else 0)
        priority, score_breakdown = compose_score('commitment-check', commitment.get('route') or route, base=102, last_type_penalty=last_type_penalty, fit_bonus=fit_bonus, use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        action_core = commitment.get('action_core') or commitment.get('summary', '')
        due_hint = commitment.get('due_hint') or ''
        prompt_style = commitment_prompt_style(commitment)
        if prompt_style == 'hard':
            prompt = f"Ты сам обещал это сделать{(' ' + due_hint) if due_hint else ''}: {action_core}. Сделал или снова оставил только в голове?"
        elif prompt_style == 'gentle':
            prompt = f"Ты собирался{(' ' + due_hint) if due_hint else ''} сделать вот это: {action_core}. Получилось хоть немного сдвинуться?"
        else:
            due_prefix = f"Ты собирался {due_hint} вот это сделать" if due_hint else 'Ты собирался вот это сделать'
            prompt = f"{due_prefix}: {action_core}. Сделал или снова оставил в голове?"
        maybe_add({
            'type': 'commitment-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': commitment.get('route') or route,
            'summary': commitment.get('summary', ''),
            'prompt': prompt,
        })

    if route in {'career-vocation', 'avoidance-paralysis'}:
        priority, score_breakdown = compose_score('direction-check', route, base=70, last_type_penalty=(12 if last_type == 'direction-check' else 0), fit_bonus=(-6 if mentor_profile.get('clarity_of_ends') == 'low' else 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'direction-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': route,
            'prompt': _route_prompt(route, 'direction-check', route, mode),
        })

    if route in {'career-vocation', 'self-deception'} and mentor_profile.get('judgment_quality') == 'low':
        priority, score_breakdown = compose_score('frame-setting-check', route, base=87, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'frame-setting-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'frame-setting',
            'prompt': 'Прежде чем снова реагировать, задай правильную рамку. С чем ты реально имеешь дело: с нехваткой ясности, с ложью себе, с избеганием или с отсутствием структуры?',
        })

    if route in {'career-vocation', 'relationship-maintenance'} and mentor_profile.get('clarity_of_ends') == 'low':
        priority, score_breakdown = compose_score('ends-clarification-check', route, base=89, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'ends-clarification-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'ends-clarification',
            'prompt': 'Прежде чем выбирать следующий шаг, проясни конец. К какой хорошей жизни, связи или порядку ты вообще пытаешься прийти здесь?'
        })

    if route in {'addiction-chaos', 'resentment', 'shame-self-contempt'} and mentor_profile.get('self_governance') == 'low':
        priority, score_breakdown = compose_score('habit-formation-check', route, base=90, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'habit-formation-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'habit-formation',
            'prompt': 'Не смотри только на этот эпизод. Какую привычку и какой тип человека ты сейчас строишь повторением этого поведения?'
        })

    if route in {'career-vocation', 'avoidance-paralysis'} and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=92, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'У тебя повторяется один и тот же паттерн: ты оставляешь всё в тумане, обещаешь себе сдвиг и не выбираешь. Что ты прекращаешь делать прямо сейчас: тянуть, объяснять или притворяться, что решение уже почти принято?'
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'pattern-naming',
            'prompt': prompt,
        })

    if route in {'career-vocation', 'avoidance-paralysis'} and pressure_debt >= 3:
        priority, score_breakdown = compose_score('decision-forcing-check', route, base=96, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Хватит держать это в режиме бесконечного размышления. Что правда: ты выбираешь один конкретный шаг сегодня или честно признаёшь, что пока не выбираешь ничего? Ответ без тумана.'
        maybe_add({
            'type': 'decision-forcing-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'decision-forcing',
            'prompt': prompt,
        })

    if route == 'relationship-maintenance' and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=90, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'У тебя здесь повторяется паттерн: ты держишь напряжение и недосказанность, вместо того чтобы назвать правду прямо. Что ты перестаёшь делать: копить обиду, ждать идеального момента или прятаться за тишиной?'
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'relationship-pattern-naming',
            'prompt': prompt,
        })

    if route == 'relationship-maintenance' and pressure_debt >= 3:
        priority, score_breakdown = compose_score('decision-forcing-check', route, base=95, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Хватит держать отношения в подвешенном состоянии. Что ты делаешь в ближайшее время: отправляешь честное сообщение, инициируешь разговор или прямо признаёшь, что продолжаешь избегать?'
        maybe_add({
            'type': 'decision-forcing-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'relationship-decision-forcing',
            'prompt': prompt,
        })

    if route == 'shame-self-contempt' and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=88, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Сейчас ты рискуешь снова уйти в знакомый паттерн: избить себя словами вместо того, чтобы назвать один реальный изъян и один следующий шаг. Что ты прекращаешь прямо сейчас: самоунижение, драму или бегство от действия?'
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'shame-pattern-naming',
            'prompt': prompt,
        })

    if route == 'shame-self-contempt' and pressure_debt >= 3:
        priority, score_breakdown = compose_score('decision-forcing-check', route, base=93, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Хватит превращать стыд в идентичность. Что ты делаешь дальше: называешь один исправимый провал и конкретное действие по исправлению, или честно признаёшь, что прямо сейчас выбираешь оставаться в самобичевании?'
        maybe_add({
            'type': 'decision-forcing-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'shame-decision-forcing',
            'prompt': prompt,
        })

    if route == 'self-deception' and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=91, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Похоже, ты снова пытаешься прикрыть неудобную правду красивым объяснением. Где именно ты врёшь себе сейчас: в мотивах, в сроках или в цене своего выбора?'
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'self-deception-pattern-naming',
            'prompt': prompt,
        })

    if route == 'self-deception' and pressure_debt >= 3:
        priority, score_breakdown = compose_score('truth-demand-check', route, base=96, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Без красивых формулировок: какую правду ты избегаешь произнести вслух? Один честный тезис, без оправданий и украшений.'
        maybe_add({
            'type': 'truth-demand-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'self-deception-truth-demand',
            'prompt': prompt,
        })

    if route == 'self-deception' and pressure_debt >= 4:
        priority, score_breakdown = compose_score('excuse-collapse', route, base=99, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Сейчас мне не нужно ещё одно умное объяснение. Что из твоих оправданий рушится первым, если смотреть только на факты твоего поведения?'
        maybe_add({
            'type': 'excuse-collapse',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'self-deception-excuse-collapse',
            'prompt': prompt,
        })

    if route == 'resentment' and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=89, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Ты можешь и дальше держаться за обиду как за моральное оправдание, но это уже стало паттерном. Что ты подпитываешь прямо сейчас: ясность, границы или сладкое чувство собственной правоты?'
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'resentment-pattern-naming',
            'prompt': prompt,
        })

    if route == 'resentment' and pressure_debt >= 3:
        priority, score_breakdown = compose_score('cost-of-delay-check', route, base=94, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Назови цену, которую ты уже платишь за удержание этой обиды: в энергии, времени, отношениях или действии. Без моральной позы.'
        maybe_add({
            'type': 'cost-of-delay-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'resentment-cost-of-delay',
            'prompt': prompt,
        })

    if route == 'resentment' and pressure_debt >= 4:
        priority, score_breakdown = compose_score('false-progress-check', route, base=98, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Ты можешь бесконечно разбирать эту обиду, но это ещё не движение. Что здесь является ложным прогрессом: повторный анализ, моральная поза или отсутствие реального решения?'
        maybe_add({
            'type': 'false-progress-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'resentment-false-progress',
            'prompt': prompt,
        })

    if route == 'addiction-chaos' and pressure_debt >= 2:
        priority, score_breakdown = compose_score('pattern-naming-check', route, base=92, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Здесь уже не туман, а повторяющийся цикл хаоса. Что ты снова называешь случайностью, хотя это уже устоявшийся паттерн?' 
        maybe_add({
            'type': 'pattern-naming-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'addiction-pattern-naming',
            'prompt': prompt,
        })

    if route == 'addiction-chaos' and pressure_debt >= 3:
        priority, score_breakdown = compose_score('identity-vs-action-check', route, base=98, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Хватит говорить о намерениях. Что ты меняешь в поведении сегодня, чтобы цикл реально прервался, или честно признаёшь, что пока выбираешь хаос?'
        maybe_add({
            'type': 'identity-vs-action-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'addiction-identity-vs-action',
            'prompt': prompt,
        })

    if route == 'addiction-chaos' and pressure_debt >= 4:
        priority, score_breakdown = compose_score('excuse-collapse', route, base=101, use_cop_adjust=True, use_confrontation_penalty=True, use_effectiveness_adjust=True)
        prompt = 'Здесь уже не работает ссылка на обстоятельства. Какое оправдание ты должен выбросить первым, если смотреть только на повторяющийся результат твоих действий?'
        maybe_add({
            'type': 'excuse-collapse',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'addiction-excuse-collapse',
            'prompt': prompt,
        })

    if route in {'career-vocation', 'avoidance-paralysis', 'shame-self-contempt'} and (progress.get('progress_state') in {'stuck', 'fragile'} or last_rich_outcome in {'reflection', 'reflection-with-intent', 'movement-small'}):
        priority, score_breakdown = compose_score('micro-step-prompt', route, base=88, last_type_penalty=(16 if last_type == 'micro-step-prompt' else 0), fit_bonus=(10 if mentor_profile.get('micro_step_response') == 'strong' else 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'micro-step-prompt',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': route,
            'prompt': _route_prompt(route, 'micro-step-prompt', route, mode),
        })

    if route == 'relationship-maintenance':
        priority, score_breakdown = compose_score('repair-check', route, base=82, last_type_penalty=(14 if last_type == 'repair-check' else 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'repair-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': route,
            'prompt': _route_prompt(route, 'repair-check', route, mode),
        })

    summary = commitment_summary(user_id=user_id, store=store)
    effectiveness = summarize_effectiveness(user_id=user_id, store=store)
    mentor_profile = build_profile(user_id=user_id, store=store)
    if summary.get('overdue_hard', 0) >= 1:
        priority, score_breakdown = compose_score('broken-promise-check', route, base=104, last_type_penalty=(14 if last_type == 'broken-promise-check' else 0), fit_bonus=(-14 if mentor_profile.get('pressure_tolerance') == 'low' else 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        repeated_hard = int(summary.get('repeated_hard', 0) or 0)
        if route == 'relationship-maintenance':
            prompt = 'Ты уже оставил хотя бы одно жёсткое обещание в отношениях просроченным. Что ты честно закроешь сегодня: сообщение, разговор или признание?' if repeated_hard < 2 else 'Ты снова дал жёсткое обещание в отношениях и снова не закрыл его. Что ты отправишь или скажешь сегодня без очередной отсрочки?'
        elif route in {'career-vocation', 'avoidance-paralysis'}:
            prompt = 'У тебя висит жёсткое обещание самому себе, и срок уже прошёл. Какой конкретный шаг ты закроешь сегодня?' if repeated_hard < 2 else 'Ты повторяешь жёсткие обещания себе и не закрываешь их. Что ты реально доведёшь до конца сегодня, а не снова оставишь в тумане?'
        else:
            prompt = 'У тебя уже висит как минимум одно жёсткое обещание с просроченным сроком. Что ты реально закрываешь сегодня, а не снова откладываешь?'
        maybe_add({
            'type': 'broken-promise-check',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'broken-promise',
            'prompt': prompt,
            'commitment_summary': summary,
        })

    if summary.get('vague_soft', 0) >= 2:
        priority, score_breakdown = compose_score('vagueness-challenge', route, base=83, last_type_penalty=(12 if last_type == 'vagueness-challenge' else 0), fit_bonus=(10 if mentor_profile.get('clarity_need') == 'high' else 0), use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        if route in {'career-vocation', 'avoidance-paralysis'}:
            prompt = 'У тебя копятся мягкие намерения без ясного решения. Что ты переведёшь из "может быть" в конкретное обязательство?' 
        elif route == 'relationship-maintenance':
            prompt = 'Ты держишь отношения в режиме мягких намерений и недосказанности. Что ты переведёшь из неопределённости в конкретный разговор?'
        else:
            prompt = 'У тебя копятся мягкие намерения без ясного решения. Что ты переведёшь из "может быть" в конкретное обязательство?'
        maybe_add({
            'type': 'vagueness-challenge',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'vague-soft-commitments',
            'prompt': prompt,
            'commitment_summary': summary,
        })

    if summary.get('open_total', 0) >= 2:
        fit_bonus = (14 if mentor_profile.get('summary_response') == 'strong' else (-10 if mentor_profile.get('summary_response') == 'weak' else 0)) + (10 if summary.get('hard_open', 0) >= 2 else 0) + (6 if mentor_profile.get('summary_response') == 'strong' else 0)
        priority, score_breakdown = compose_score('mentor-summary', route, base=76, last_type_penalty=(18 if last_type == 'mentor-summary' else 0), fit_bonus=fit_bonus, use_step_bonus=True, use_lifecycle_adjust=True, use_cop_adjust=True, use_effectiveness_adjust=True)
        maybe_add({
            'type': 'mentor-summary',
            'priority': priority,
            'score_breakdown': score_breakdown,
            'route': route,
            'summary': 'commitment-summary',
            'prompt': '',
            'commitment_summary': summary,
            'effectiveness_summary': effectiveness,
            'mentor_profile': mentor_profile,
        })

    ranked = sorted(events, key=lambda x: (-x['priority'], x['type']))
    for idx, event in enumerate(ranked, 1):
        debug_trace.append({'event_type': event.get('type', ''), 'decision': 'ranked', 'rank': idx, 'route': event.get('route', route), 'priority': event.get('priority', 0), 'score_breakdown': dict(event.get('score_breakdown') or {})})
    state['selection_debug_trace'] = debug_trace
    return ranked


def _background_loop_score(item: dict, continuity: dict) -> int:
    summary = (item.get('summary') or '').lower()
    salience = int(item.get('salience', 0) or 0)
    score = salience

    top_themes = [x.get('name', '') for x in (continuity.get('top_themes') or [])[:3] if isinstance(x, dict)]
    top_patterns = [x.get('name', '') for x in (continuity.get('top_patterns') or [])[:3] if isinstance(x, dict)]

    if 'meaning' in top_themes and any(x in summary for x in ['смысл', 'ориентац', 'туман', 'бремя', 'направлен']):
        score += 35
    if 'suffering' in top_themes and any(x in summary for x in ['провал', 'саморазруш', 'боль', 'стыд']):
        score += 30
    if 'avoidance-loop' in top_patterns and any(x in summary for x in ['избег', 'туман', 'неясности', 'структура']):
        score += 20
    if 'resentment' in top_themes and any(x in summary for x in ['обида', 'горечь']):
        score += 15
    return score


def _infer_background_question(continuity: dict, progress: dict) -> str:
    open_loops = continuity.get('open_loops') or []
    if open_loops:
        ranked = sorted(
            open_loops,
            key=lambda x: (-_background_loop_score(x, continuity), -(int(x.get('salience', 0) or 0))),
        )
        picked = ranked[0]
        return picked.get('summary', '') or ''
    if progress.get('question'):
        return progress.get('question', '')
    top_themes = continuity.get('top_themes') or []
    if top_themes:
        return top_themes[0].get('name', '') or ''
    return ''


def evaluate(question: str = '', user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    build_user_profile(user_id=user_id, store=store)
    continuity = read_continuity(user_id=user_id, store=store)
    background_question = question or _infer_background_question(continuity, {})
    progress = estimate_progress(background_question, user_id=user_id, store=store)
    if not question:
        background_question = background_question or _infer_background_question(continuity, progress)
    reaction = estimate_reaction(background_question, user_id=user_id, store=store)
    state = load_state(user_id=user_id, store=store)
    state['_store'] = store
    mentor_profile = build_profile(user_id=user_id, store=store)

    skip, reason = should_skip_now(state)
    auto_mode = state.get('mode', 'standard')
    mode_rationale: list[dict] = [{'decision': 'start-mode', 'mode': auto_mode, 'reason': 'state-mode'}]
    if reaction.get('user_reaction_estimate') == 'resisting' and auto_mode == 'hard':
        auto_mode = 'standard'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'resistance-soften-hard'})
    if int(state.get('unanswered_checkins', 0) or 0) >= 2 and auto_mode in {'hard', 'standard'}:
        auto_mode = 'gentle'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'unanswered-checkins'})
    rich_outcome = state.get('last_rich_outcome', 'neutral')
    if state.get('handoff_mode') == 'gentle' and int(state.get('handoff_ticks', 0) or 0) > 0:
        auto_mode = 'gentle'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'gentle-handoff'})
    if mentor_profile.get('pressure_tolerance') == 'low':
        auto_mode = 'gentle'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'low-pressure-tolerance'})
    if rich_outcome in {'fragility', 'irritation', 'delay-with-intent', 'truthful-delay'}:
        auto_mode = 'gentle'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': f'rich-outcome-{rich_outcome}'})
    if mentor_profile.get('pressure_tolerance') == 'high' and mentor_profile.get('accountability_response') == 'strong' and rich_outcome == 'movement':
        auto_mode = 'standard'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'high-tolerance-post-movement'})

    plan = current_plan(user_id=user_id, store=store)
    if plan.get('status') == 'failed':
        auto_mode = 'gentle'
        mode_rationale.append({'decision': 'mode-shift', 'mode': auto_mode, 'reason': 'failed-plan'})
    events = _candidate_events(background_question, continuity, progress, reaction, mode=auto_mode, state=state, user_id=user_id, store=store, mentor_profile=mentor_profile)
    selected = events[0] if events else None
    route = infer_route(background_question) if background_question else 'general'

    selection_audit = _selection_audit_summary(events)

    result = {
        'question': background_question,
        'input_question': question,
        'route': route,
        'skip': skip,
        'skip_reason': reason,
        'events': events,
        'selected_event': None if skip else selected,
        'continuity': continuity,
        'progress': progress,
        'reaction': reaction,
        'effective_mode': auto_mode,
        'selection_debug_trace': state.get('selection_debug_trace', []),
        'selection_context': {
            'selection_audit': selection_audit,
            'pressure_debt': int(state.get('pressure_debt', 0) or 0),
            'softness_budget': int(state.get('softness_budget', 0) or 0),
            'last_rich_outcome': state.get('last_rich_outcome', 'neutral'),
            'mentor_profile': mentor_profile,
            'active_plan': plan,
            'plan_debug_trace': state.get('plan_debug_trace', []),
            'mode_rationale': mode_rationale,
            'pressure_rationale': state.get('pressure_rationale', []),
            'softness_rationale': state.get('softness_rationale', []),
            'handoff_rationale': state.get('handoff_rationale', []),
            'urgency_override_reason': state.get('urgency_override_reason', ''),
        },
    }
    return result


def record_sent(event: dict, user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = load_state(user_id=user_id, store=store)
    prev_unanswered = int(state.get('unanswered_checkins', 0) or 0)
    unanswered = prev_unanswered + 1
    now = datetime.now(timezone.utc)
    mode = state.get('mode', 'standard')
    cooldown_hours = compute_next_cooldown_hours(state)
    event_type = event.get('type', '')
    route = event.get('route', '')
    event_counts = dict(state.get('event_type_counts') or {})
    route_counts = dict(state.get('route_event_type_counts') or {})
    outcomes = dict(state.get('event_outcomes') or {})

    if prev_unanswered >= 1:
        prev_type = state.get('last_checkin_type', '')
        prev_route = state.get('last_checkin_route', '')
        prev_key = f"{prev_route}::{prev_type}" if prev_route and prev_type else prev_type
        if prev_key:
            payload = dict(outcomes.get(prev_key) or {'used': 0, 'helpful': 0, 'resisted': 0, 'ignored': 0})
            payload['ignored'] = int(payload.get('ignored', 0) or 0) + 1
            outcomes[prev_key] = payload
    event_counts[event_type] = int(event_counts.get(event_type, 0) or 0) + 1
    route_key = f"{route}::{event_type}" if route and event_type else ''
    if route_key:
        route_counts[route_key] = int(route_counts.get(route_key, 0) or 0) + 1
        payload = dict(outcomes.get(route_key) or {'used': 0, 'helpful': 0, 'resisted': 0, 'ignored': 0})
        payload['used'] = int(payload.get('used', 0) or 0) + 1
        outcomes[route_key] = payload
    elif event_type:
        payload = dict(outcomes.get(event_type) or {'used': 0, 'helpful': 0, 'resisted': 0, 'ignored': 0})
        payload['used'] = int(payload.get('used', 0) or 0) + 1
        outcomes[event_type] = payload

    soft_types = {'mentor-summary', 'micro-step-prompt', 'open-loop-followup', 'resistance-soft-checkin'}
    hard_types = {'broken-promise-check', 'vagueness-challenge', 'commitment-check', 'pattern-naming-check', 'decision-forcing-check', 'truth-demand-check', 'cost-of-delay-check', 'identity-vs-action-check', 'false-progress-check', 'excuse-collapse'}
    softness_budget = int(state.get('softness_budget', 0) or 0)
    softness_rationale: list[dict] = [{'decision': 'start-softness-budget', 'value': softness_budget}]
    if event_type in soft_types:
        softness_budget += 1
        softness_rationale.append({'decision': 'softness-budget-change', 'value': softness_budget, 'reason': f'soft-event-{event_type}'})
    elif event_type in hard_types:
        softness_budget = max(0, softness_budget - 1)
        softness_rationale.append({'decision': 'softness-budget-change', 'value': softness_budget, 'reason': f'hard-event-{event_type}'})

    state.update({
        'mode': mode,
        'last_checkin_at': now_iso(),
        'last_checkin_type': event_type,
        'last_checkin_route': route,
        'last_checkin_summary': event.get('summary', ''),
        'unanswered_checkins': unanswered,
        'cooldown_until': (now + timedelta(hours=cooldown_hours)).isoformat(),
        'event_type_counts': event_counts,
        'route_event_type_counts': route_counts,
        'event_outcomes': outcomes,
        'softness_budget': softness_budget,
        'softness_rationale': softness_rationale,
    })
    handoff_rationale: list[dict] = [{'decision': 'start-handoff', 'mode': state.get('handoff_mode', ''), 'ticks': int(state.get('handoff_ticks', 0) or 0)}]
    if state.get('handoff_mode') == 'gentle' and int(state.get('handoff_ticks', 0) or 0) > 0:
        state['handoff_ticks'] = max(0, int(state.get('handoff_ticks', 0) or 0) - 1)
        handoff_rationale.append({'decision': 'handoff-decay', 'mode': 'gentle', 'ticks': int(state.get('handoff_ticks', 0) or 0), 'reason': 'sent-checkin'})
        if int(state.get('handoff_ticks', 0) or 0) == 0:
            state['handoff_mode'] = ''
            handoff_rationale.append({'decision': 'handoff-cleared', 'mode': '', 'ticks': 0, 'reason': 'ticks-exhausted'})
    state['handoff_rationale'] = handoff_rationale
    save_state(state, user_id=user_id, store=store)
    if event.get('type') == 'commitment-check' and event.get('summary'):
        mark_commitment_prompted(event.get('summary', ''), user_id=user_id, store=store)
    if event.get('type') and event.get('route'):
        advance_plan(event.get('type', ''), event.get('route', ''), user_id=user_id, store=store, mentor_profile=build_profile(user_id=user_id, store=store))
    store.append_jsonl(user_id, KEY_MENTOR_EVENTS, {
        'ts': now_iso(),
        'event': event,
        'kind': 'sent',
    })
    return state


def record_reply(question: str = '', user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = load_state(user_id=user_id, store=store)
    state['unanswered_checkins'] = 0
    state['cooldown_until'] = ''

    route = state.get('last_checkin_route', '')
    rich_outcome = classify_reply(question, route=route)
    outcome_map = {
        'movement': 'helpful',
        'movement-small': 'helpful',
        'movement-theater': 'resisted',
        'reflection': 'neutral',
        'reflection-with-intent': 'helpful',
        'compliance': 'neutral',
        'compliance-theater': 'resisted',
        'deflection': 'resisted',
        'delay-with-intent': 'neutral',
        'truthful-delay': 'neutral',
        'lazy-delay': 'resisted',
        'resistance': 'resisted',
        'irritation': 'resisted',
        'fragility': 'neutral',
        'manipulative-fragility': 'resisted',
        'defensive-intelligence': 'resisted',
        'judgment-clarified': 'helpful',
        'ends-clarified': 'helpful',
        'virtue-recognition': 'helpful',
        'habit-recognition': 'helpful',
        'rationalization-exposed': 'helpful',
        'moral-posturing': 'resisted',
        'neutral': 'neutral',
    }
    outcome_name = outcome_map.get(rich_outcome, 'neutral')

    last_type = state.get('last_checkin_type', '')
    last_route = state.get('last_checkin_route', '')
    outcomes = dict(state.get('event_outcomes') or {})
    if last_type:
        key = f"{last_route}::{last_type}" if last_route else last_type
        payload = dict(outcomes.get(key) or {'used': 0, 'helpful': 0, 'neutral': 0, 'resisted': 0, 'ignored': 0, 'movement': 0, 'movement-small': 0, 'movement-theater': 0, 'reflection': 0, 'reflection-with-intent': 0, 'compliance': 0, 'compliance-theater': 0, 'deflection': 0, 'delay-with-intent': 0, 'truthful-delay': 0, 'lazy-delay': 0, 'irritation': 0, 'fragility': 0, 'manipulative-fragility': 0, 'defensive-intelligence': 0, 'judgment-clarified': 0, 'ends-clarified': 0, 'virtue-recognition': 0, 'habit-recognition': 0, 'rationalization-exposed': 0, 'moral-posturing': 0})
        payload[outcome_name] = int(payload.get(outcome_name, 0) or 0) + 1
        if rich_outcome in payload:
            payload[rich_outcome] = int(payload.get(rich_outcome, 0) or 0) + 1
        outcomes[key] = payload
        state['event_outcomes'] = outcomes
    state['last_rich_outcome'] = rich_outcome
    handoff_rationale: list[dict] = [{'decision': 'start-handoff', 'mode': state.get('handoff_mode', ''), 'ticks': int(state.get('handoff_ticks', 0) or 0)}]
    if rich_outcome in {'movement', 'movement-small', 'reflection-with-intent', 'judgment-clarified', 'ends-clarified', 'habit-recognition'} and state.get('handoff_mode') == 'gentle':
        state['handoff_mode'] = ''
        state['handoff_ticks'] = 0
        handoff_rationale.append({'decision': 'handoff-cleared', 'mode': '', 'ticks': 0, 'reason': f'helpful-outcome-{rich_outcome}'})

    pressure_debt = int(state.get('pressure_debt', 0) or 0)
    pressure_rationale: list[dict] = [{'decision': 'start-pressure-debt', 'value': pressure_debt}]
    if rich_outcome in {'deflection', 'resistance', 'moral-posturing', 'lazy-delay', 'compliance-theater', 'movement-theater', 'manipulative-fragility', 'defensive-intelligence'}:
        pressure_debt += 1
        pressure_rationale.append({'decision': 'pressure-debt-change', 'value': pressure_debt, 'reason': f'negative-outcome-{rich_outcome}'})
    elif rich_outcome in {'movement', 'movement-small', 'reflection-with-intent', 'judgment-clarified', 'ends-clarified', 'habit-recognition', 'virtue-recognition', 'rationalization-exposed'}:
        pressure_debt = max(0, pressure_debt - 1)
        pressure_rationale.append({'decision': 'pressure-debt-change', 'value': pressure_debt, 'reason': f'helpful-outcome-{rich_outcome}'})
    state['pressure_debt'] = pressure_debt
    state['pressure_rationale'] = pressure_rationale
    state['handoff_rationale'] = handoff_rationale

    delay_memory = store.get_json(user_id, KEY_MENTOR_DELAYS, default={'items': []}) or {'items': []}
    delay_items = list(delay_memory.get('items') or [])
    if rich_outcome == 'truthful-delay' and last_type:
        delay_items.append({
            'ts': now_iso(),
            'route': last_route,
            'event_type': last_type,
            'status': 'pending',
        })
        delay_memory['items'] = delay_items
        store.put_json(user_id, KEY_MENTOR_DELAYS, delay_memory)
    elif rich_outcome in {'movement', 'movement-small', 'reflection-with-intent'}:
        resolved = False
        updated_rows = []
        for row in delay_items:
            payload = dict(row or {})
            if not resolved and payload.get('status') == 'pending':
                payload['status'] = 'resolved-helpful'
                payload['resolved_at'] = now_iso()
                payload['resolved_by'] = rich_outcome
                resolved = True
            updated_rows.append(payload)
        if delay_items:
            delay_memory['items'] = updated_rows
            store.put_json(user_id, KEY_MENTOR_DELAYS, delay_memory)

    if last_route:
        branch_plan_on_outcome(rich_outcome, last_route, user_id=user_id, store=store, mentor_profile=build_profile(user_id=user_id, store=store))

    save_state(state, user_id=user_id, store=store)
    store.append_jsonl(user_id, KEY_MENTOR_EVENTS, {
        'ts': now_iso(),
        'kind': 'reply',
        'outcome': outcome_name,
        'rich_outcome': rich_outcome,
    })
    return state
