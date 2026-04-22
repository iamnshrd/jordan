"""Grounding plan objects and strict rendering gates.

This module centralizes the allow/deny decision for all user-facing answer
paths so renderers and prompt builders cannot silently diverge.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from library._core.runtime.decision import attach_adapter_contract, envelope_from_plan
from library.utils import current_trace_id


_STRICT_REQUIRED_FIELDS = {
    'quick': ['core_problem', 'practical_next_step'],
    'practical': ['core_problem', 'guiding_principle', 'practical_next_step'],
    'deep': [
        'core_problem',
        'relevant_pattern',
        'responsibility_avoided',
        'guiding_principle',
        'practical_next_step',
        'longer_term_correction',
    ],
}


@dataclass(frozen=True)
class GroundingDecision:
    action: str
    mode: str
    use_kb: bool
    confidence: str = ''
    reason: str = ''
    route_name: str = 'general'
    evidence_count: int = 0
    quote_count: int = 0
    avg_relevance: float | None = None
    degradation_mode: str = 'none'
    backed_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def allow_answer(self) -> bool:
        return self.action == 'respond-with-kb'

    @property
    def allow_llm_prompt(self) -> bool:
        return self.action == 'respond-with-kb'

    def as_dict(self) -> dict:
        return {
            'action': self.action,
            'mode': self.mode,
            'use_kb': self.use_kb,
            'confidence': self.confidence,
            'reason': self.reason,
            'route_name': self.route_name,
            'evidence_count': self.evidence_count,
            'quote_count': self.quote_count,
            'avg_relevance': self.avg_relevance,
            'degradation_mode': self.degradation_mode,
            'backed_fields': list(self.backed_fields),
            'missing_fields': list(self.missing_fields),
            'metadata': dict(self.metadata),
            'allow_answer': self.allow_answer,
            'allow_llm_prompt': self.allow_llm_prompt,
        }


@dataclass
class GroundedAnswerPlan:
    question: str
    user_id: str
    decision: GroundingDecision
    assistant_id: str = 'jordan'
    knowledge_set_id: str = 'jordan-kb'
    purpose: str = 'response'
    selection: dict = field(default_factory=dict)
    continuity: dict = field(default_factory=dict)
    progress: dict = field(default_factory=dict)
    reaction: dict = field(default_factory=dict)
    retrieval_validation: dict = field(default_factory=dict)
    dialogue_state: dict = field(default_factory=dict)
    dialogue_frame: dict = field(default_factory=dict)
    synthesis: dict | None = None
    voice_mode: str = 'default'
    guardrail: dict | None = None
    direct_response: str = ''
    clarifying_question: str = ''
    system: str = ''
    user: str = ''

    @property
    def action(self) -> str:
        return self.decision.action

    @property
    def mode(self) -> str:
        return self.decision.mode

    @property
    def use_kb(self) -> bool:
        return self.decision.use_kb

    @property
    def confidence(self) -> str:
        return self.decision.confidence

    @property
    def reason(self) -> str:
        return self.decision.reason

    @property
    def final_user_text(self) -> str:
        return self.direct_response or self.clarifying_question or ''

    def runtime_result(self, response: str = '') -> dict:
        final_text = response or self.final_user_text
        envelope = envelope_from_plan(
            self,
            trace_id=current_trace_id(),
            final_user_text=final_text,
        ).as_dict()
        result = {
            'question': self.question,
            'mode': self.mode,
            'use_kb': self.use_kb,
            'confidence': self.confidence,
            'action': self.action,
            'reason': self.reason,
            'selection': self.selection,
            'continuity': self.continuity,
            'progress': self.progress,
            'reaction': self.reaction,
            'retrieval_validation': self.retrieval_validation,
            'dialogue_state': self.dialogue_state,
            'dialogue_frame': self.dialogue_frame,
            'guardrail': self.guardrail,
            'response': final_text,
            'direct_response': self.direct_response,
            'clarifying_question': self.clarifying_question,
            'final_user_text': final_text,
            'allow_model_call': envelope['allow_model_call'],
            'decision_type': envelope['decision_type'],
            'assistant_id': envelope['assistant_id'],
            'knowledge_set_id': self.knowledge_set_id,
            'domain_status': envelope['domain_status'],
            'reason_code': envelope['reason_code'],
            'decision_envelope': envelope,
            'decision_meta': self.decision.as_dict(),
            'purpose': self.purpose,
            'trace_id': current_trace_id(),
        }
        if self.synthesis is not None:
            result['synthesis'] = self.synthesis
        return attach_adapter_contract(result)

    def prompt_result(self) -> dict:
        final_user_text = self.final_user_text
        envelope = envelope_from_plan(
            self,
            trace_id=current_trace_id(),
            final_user_text=final_user_text,
        ).as_dict()
        system = self.system
        user = self.user or self.question
        if not envelope['allow_model_call'] and final_user_text:
            # If an adapter mistakenly sends this to a model instead of honoring
            # the decision, bias it toward returning the already-approved text.
            system = (
                'POLICY DECISION. Do not answer the original user question. '
                'Return exactly the provided Russian message and nothing else.'
            )
            user = final_user_text
        return attach_adapter_contract({
            'system': system,
            'user': user,
            'synthesis': self.synthesis,
            'continuity': self.continuity,
            'mode': self.mode,
            'use_kb': self.use_kb,
            'action': self.action,
            'voice_mode': self.voice_mode,
            'guardrail': self.guardrail,
            'direct_response': self.direct_response,
            'clarifying_question': self.clarifying_question,
            'final_user_text': final_user_text,
            'allow_model_call': envelope['allow_model_call'],
            'decision_type': envelope['decision_type'],
            'assistant_id': envelope['assistant_id'],
            'knowledge_set_id': self.knowledge_set_id,
            'domain_status': envelope['domain_status'],
            'reason_code': envelope['reason_code'],
            'decision_envelope': envelope,
            'retrieval_validation': self.retrieval_validation,
            'dialogue_state': self.dialogue_state,
            'dialogue_frame': self.dialogue_frame,
            'decision_meta': self.decision.as_dict(),
            'purpose': self.purpose,
            'trace_id': current_trace_id(),
        })


def missing_required_grounding(data: dict, mode: str = 'deep') -> list[str]:
    report = data.get('grounding_report') or {}
    fields = report.get('fields') or {}
    required = _STRICT_REQUIRED_FIELDS.get(mode, _STRICT_REQUIRED_FIELDS['deep'])
    missing = []
    for field in required:
        meta = fields.get(field) or {}
        if not meta.get('backed'):
            missing.append(field)
    return missing


def can_render_strict(data: dict, mode: str = 'deep') -> bool:
    return not missing_required_grounding(data, mode=mode)


def build_strict_clarification(data: dict, mode: str = 'deep') -> str:
    missing = missing_required_grounding(data, mode=mode)
    readable = ', '.join(missing) if missing else 'grounding'
    return (
        'Сейчас у меня недостаточно опоры в базе, чтобы честно собрать '
        f'полный ответ в режиме {mode}. Не хватает DB-backed опоры для: '
        f'{readable}. Сузь вопрос до одной цитаты, книги, конфликта или '
        'паттерна, который нужно разобрать.'
    )
