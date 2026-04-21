"""Safe outbound delivery for mentor proactive messages.

Mentor scoring may propose proactive events, but actual outbound delivery must
either go through a canonical grounded runtime plan or stay within a strictly
safe direct-summary class.
"""

from __future__ import annotations

from library._core.mentor.render import render_event
from library._core.runtime.orchestrator import build_runtime_plan
from library._core.state_store import KEY_MENTOR_EVENTS, StateStore
from library.config import canonical_user_id, get_default_store
from library.utils import (
    current_trace_id, ensure_trace_context, log_event, now_iso, traced_stage,
)

_ROUTE_HINTS = {
    'career-vocation': 'выбор направления и несение выбранного бремени',
    'avoidance-paralysis': 'избегание решения и жизнь в тумане',
    'relationship-maintenance': 'честный разговор, прояснение и поддержание связи',
    'self-deception': 'самообман, неудобная правда и цена оправданий',
    'shame-self-contempt': 'стыд, самоунижение и возвращение к порядку',
    'resentment': 'обида, горечь и застревание в моральной позе',
    'addiction-chaos': 'цикл хаоса, утраты управления и повторяющихся срывов',
}

_EVENT_HINTS = {
    'frame-setting-check': 'точнее назвать, с чем человек реально имеет дело',
    'ends-clarification-check': 'прояснить, к какому добру и порядку человек идёт',
    'direction-check': 'уточнить направление и следующий выбор',
    'micro-step-prompt': 'собрать маленький выполнимый шаг',
    'repair-check': 'сдвинуться к честному ремонту связи',
    'pattern-naming-check': 'назвать повторяющийся разрушительный паттерн',
    'decision-forcing-check': 'перевести туман в решение',
    'truth-demand-check': 'сформулировать неудобную правду без украшений',
    'cost-of-delay-check': 'назвать цену отсрочки и удержания проблемы',
    'identity-vs-action-check': 'связать идентичность с реальным действием',
    'false-progress-check': 'отделить ложный прогресс от настоящего движения',
    'excuse-collapse': 'увидеть, какое оправдание больше не работает',
}


def _build_intent(event: dict, evaluation: dict) -> dict:
    delivery = dict(event.get('delivery') or {})
    route = (event.get('route') or evaluation.get('route') or 'general').strip()
    event_type = (event.get('type') or '').strip()
    source_question = (evaluation.get('question') or '').strip()
    summary = (event.get('summary') or '').strip()
    return {
        'event_type': event_type,
        'route': route,
        'summary': summary,
        'source_question': source_question,
        'delivery_class': delivery.get('delivery_class') or 'canonical-proactive',
        'requires_canonical': bool(delivery.get('requires_canonical', True)),
        'safe_to_send_direct': bool(delivery.get('safe_to_send_direct', False)),
        'goal': delivery.get('goal') or 'mentor-followup',
        'allowed_tone': delivery.get('allowed_tone') or 'grounded-mentor',
        'prompt_preview': delivery.get('prompt_preview') or '',
    }


def _build_canonical_question(intent: dict) -> str:
    parts: list[str] = []
    source_question = (intent.get('source_question') or '').strip()
    route_hint = _ROUTE_HINTS.get(intent.get('route') or '', '')
    event_hint = _EVENT_HINTS.get(intent.get('event_type') or '', '')
    summary = (intent.get('summary') or '').strip()

    if source_question:
        parts.append(f'Контекст: {source_question}')
    if route_hint:
        parts.append(f'Тема для разбора: {route_hint}')
    if event_hint:
        parts.append(f'Фокус mentor follow-up: {event_hint}')
    elif summary and summary not in {intent.get('route') or '', 'commitment-summary'}:
        parts.append(f'Фокус mentor follow-up: {summary}')

    parts.append(
        'По материалам базы коротко назови ядро проблемы, опорный принцип и '
        'один следующий шаг без свободной импровизации.'
    )
    return '. '.join([part for part in parts if part]).strip()


def _render_canonical_proactive(plan) -> str:
    data = plan.synthesis or {}
    report = (data.get('grounding_report') or {}).get('fields') or {}
    lines: list[str] = []

    core_problem = (data.get('core_problem') or '').strip()
    principle = (data.get('guiding_principle') or '').strip()
    next_step = (data.get('practical_next_step') or '').strip()

    if core_problem and (report.get('core_problem') or {}).get('backed'):
        lines.append(core_problem)
    if principle and (report.get('guiding_principle') or {}).get('backed'):
        lines.extend(['', 'Опорный принцип: ' + principle])
    if next_step and (report.get('practical_next_step') or {}).get('backed'):
        lines.extend(['', 'Следующий шаг: ' + next_step])

    return '\n'.join(lines).strip()


def _suppressed_payload(event: dict, reason: str, trace_id: str) -> dict:
    return {
        'ts': now_iso(),
        'kind': 'suppressed',
        'trace_id': trace_id,
        'reason': reason,
        'event': {
            'type': event.get('type', ''),
            'route': event.get('route', ''),
            'summary': event.get('summary', ''),
        },
    }


def prepare_delivery(evaluation: dict, *, user_id: str = 'default',
                     store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    event = dict(evaluation.get('selected_event') or {})

    if evaluation.get('skip') or not event:
        return {
            'should_send': False,
            'rendered_message': '',
            'delivery_path_type': 'suppressed',
            'suppressed_reason': evaluation.get('skip_reason') or 'No mentor event selected',
            'mentor_intent': {},
            'trace_id': '',
        }

    intent = _build_intent(event, evaluation)
    trace_question = intent.get('source_question') or event.get('summary') or event.get('type') or ''
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='mentor-proactive', question=trace_question):
        trace_id = current_trace_id()
        log_event(
            'mentor.delivery.started',
            store=store,
            user_id=user_id,
            event_type=event.get('type', ''),
            route=event.get('route', ''),
            delivery_class=intent.get('delivery_class', ''),
        )

        if intent.get('safe_to_send_direct'):
            msg = render_event(event).strip()
            should_send = bool(msg)
            log_event(
                'mentor.delivery.direct_allowed',
                store=store,
                user_id=user_id,
                should_send=should_send,
                response_length=len(msg),
            )
            return {
                'should_send': should_send,
                'rendered_message': msg,
                'delivery_path_type': 'direct-summary',
                'suppressed_reason': '' if should_send else 'Direct summary rendered empty',
                'mentor_intent': intent,
                'canonical_result': {},
                'trace_id': trace_id,
            }

        canonical_question = _build_canonical_question(intent)
        with traced_stage('mentor.delivery.plan', store=store, user_id=user_id):
            plan = build_runtime_plan(
                canonical_question,
                user_id=user_id,
                store=store,
                purpose='mentor-proactive',
                record_user_reply=False,
            )
        setattr(plan, 'store', store)
        rendered = ''
        suppressed_reason = ''
        if plan.decision.allow_answer:
            rendered = _render_canonical_proactive(plan)
        if not rendered:
            suppressed_reason = (
                plan.reason
                or 'Canonical mentor plan did not produce a safe DB-backed proactive message'
            )
            store.append_jsonl(
                user_id,
                KEY_MENTOR_EVENTS,
                _suppressed_payload(event, suppressed_reason, trace_id),
            )
            log_event(
                'mentor.delivery.suppressed',
                store=store,
                user_id=user_id,
                action=plan.action,
                reason=suppressed_reason,
                canonical_question=canonical_question,
            )
        else:
            log_event(
                'mentor.delivery.canonical_allowed',
                store=store,
                user_id=user_id,
                action=plan.action,
                response_length=len(rendered),
                canonical_question=canonical_question,
            )

        return {
            'should_send': bool(rendered),
            'rendered_message': rendered,
            'delivery_path_type': 'canonical-proactive' if rendered else 'suppressed',
            'suppressed_reason': suppressed_reason,
            'mentor_intent': intent,
            'canonical_question': canonical_question,
            'canonical_result': plan.runtime_result(response=rendered),
            'trace_id': trace_id,
        }
