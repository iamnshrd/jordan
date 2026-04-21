"""Canonical decision envelope for runtime and integration boundaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DecisionEnvelope:
    """Single integration-safe description of what the runtime decided."""

    decision_type: str
    assistant_id: str = 'jordan'
    knowledge_set_id: str = 'jordan-kb'
    action: str = ''
    reason: str = ''
    domain_status: str = 'in_domain'
    reason_code: str = ''
    allow_model_call: bool = False
    allow_retrieval: bool = False
    final_user_text: str = ''
    trace_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'decision_type': self.decision_type,
            'assistant_id': self.assistant_id,
            'knowledge_set_id': self.knowledge_set_id,
            'action': self.action,
            'reason': self.reason,
            'domain_status': self.domain_status,
            'reason_code': self.reason_code,
            'allow_model_call': self.allow_model_call,
            'allow_retrieval': self.allow_retrieval,
            'final_user_text': self.final_user_text,
            'trace_id': self.trace_id,
            'metadata': dict(self.metadata),
        }


def infer_decision_type(*, action: str, allow_model_call: bool,
                        final_user_text: str = '') -> str:
    """Normalize legacy runtime actions into one integration-facing type."""
    if action == 'respond-with-kb':
        return 'respond_kb'
    if action == 'ask-clarifying-question':
        return 'clarify'
    if action == 'answer-directly':
        return 'respond_policy_text' if final_user_text else 'deny'
    if allow_model_call:
        return 'respond_kb'
    return 'deny'


def envelope_from_plan(plan, *, trace_id: str = '',
                       final_user_text: str = '') -> DecisionEnvelope:
    """Create a decision envelope from a GroundedAnswerPlan-like object."""
    guardrail = getattr(plan, 'guardrail', None) or {}
    decision = getattr(plan, 'decision', None)
    action = getattr(plan, 'action', '') or ''
    allow_model_call = bool(getattr(decision, 'allow_llm_prompt', False))
    if not final_user_text:
        final_user_text = (
            getattr(plan, 'direct_response', '') or ''
        ) or (
            getattr(plan, 'clarifying_question', '') or ''
        )

    metadata = {
        'mode': getattr(plan, 'mode', ''),
        'confidence': getattr(plan, 'confidence', ''),
        'use_kb': getattr(plan, 'use_kb', False),
        'route_name': getattr(decision, 'route_name', ''),
        'avg_relevance': getattr(decision, 'avg_relevance', None),
        'evidence_count': getattr(decision, 'evidence_count', 0),
        'quote_count': getattr(decision, 'quote_count', 0),
        'degradation_mode': getattr(decision, 'degradation_mode', ''),
        'purpose': getattr(plan, 'purpose', ''),
        'guardrail_kind': guardrail.get('kind', ''),
        'guardrail_source': guardrail.get('policy_source', ''),
    }

    return DecisionEnvelope(
        decision_type=infer_decision_type(
            action=action,
            allow_model_call=allow_model_call,
            final_user_text=final_user_text,
        ),
        assistant_id=getattr(plan, 'assistant_id', 'jordan') or 'jordan',
        knowledge_set_id=(
            getattr(plan, 'knowledge_set_id', 'jordan-kb') or 'jordan-kb'
        ),
        action=action,
        reason=getattr(plan, 'reason', '') or '',
        domain_status=guardrail.get('domain_status') or 'in_domain',
        reason_code=guardrail.get('kind') or action,
        allow_model_call=allow_model_call,
        allow_retrieval=bool(getattr(plan, 'use_kb', False)),
        final_user_text=final_user_text,
        trace_id=trace_id,
        metadata=metadata,
    )


def coerce_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the decision envelope dict from a runtime/prompt payload."""
    env = payload.get('decision_envelope')
    if isinstance(env, dict):
        return env
    return {
        'decision_type': payload.get('decision_type', ''),
        'assistant_id': payload.get('assistant_id', ''),
        'knowledge_set_id': payload.get('knowledge_set_id', ''),
        'action': payload.get('action', ''),
        'reason': payload.get('reason', ''),
        'domain_status': payload.get('domain_status', ''),
        'reason_code': payload.get('reason_code', ''),
        'allow_model_call': payload.get('allow_model_call', False),
        'allow_retrieval': payload.get('use_kb', False),
        'final_user_text': payload.get('final_user_text', ''),
        'trace_id': payload.get('trace_id', ''),
        'metadata': payload.get('decision_meta', {}),
    }


def should_call_model(payload: dict[str, Any]) -> bool:
    """Single helper integrations can use instead of improvising branching."""
    envelope = coerce_envelope(payload)
    return bool(envelope.get('allow_model_call'))


def build_adapter_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the integration contract every adapter must honor."""
    envelope = coerce_envelope(payload)
    allow_model_call = bool(envelope.get('allow_model_call'))
    final_user_text = envelope.get('final_user_text') or payload.get('final_user_text', '')
    return {
        'must_honor_decision_envelope': True,
        'must_not_call_model_when_blocked': not allow_model_call,
        'model_call_allowed': allow_model_call,
        'delivery_mode': 'model' if allow_model_call else 'final_text',
        'final_user_text_required_when_blocked': (
            not allow_model_call and bool(final_user_text)
        ),
    }


def attach_adapter_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the canonical adapter contract to a runtime or prompt payload."""
    payload['adapter_contract'] = build_adapter_contract(payload)
    return payload


def build_adapter_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Materialize the only two valid adapter execution modes.

    Adapters must either deliver the final approved text directly or execute a
    model call using the provided prompt payload. They should not invent a third
    branch based on missing fields.
    """
    envelope = coerce_envelope(payload)
    contract = build_adapter_contract(payload)
    final_user_text = (
        envelope.get('final_user_text')
        or payload.get('final_user_text', '')
        or payload.get('response', '')
        or payload.get('direct_response', '')
        or payload.get('clarifying_question', '')
    )
    result = {
        'delivery_mode': contract['delivery_mode'],
        'assistant_id': envelope.get('assistant_id', ''),
        'knowledge_set_id': envelope.get('knowledge_set_id', ''),
        'decision_type': envelope.get('decision_type', ''),
        'domain_status': envelope.get('domain_status', ''),
        'reason_code': envelope.get('reason_code', ''),
        'trace_id': envelope.get('trace_id') or payload.get('trace_id', ''),
        'decision_envelope': envelope,
        'adapter_contract': contract,
    }
    if contract['model_call_allowed']:
        result.update({
            'system': payload.get('system', ''),
            'user': payload.get('user', ''),
            'final_user_text': '',
        })
    else:
        result.update({
            'message': final_user_text,
            'final_user_text': final_user_text,
            'system': '',
            'user': '',
        })
    return result
