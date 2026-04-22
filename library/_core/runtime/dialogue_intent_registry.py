"""Declarative registry for follow-up dialogue intent inference."""
from __future__ import annotations

from dataclasses import dataclass

from library._core.runtime.dialogue_family_registry import dialogue_contains_any
from library._core.runtime.dialogue_family_registry import normalize_dialogue_text


@dataclass(frozen=True)
class DialogueIntentSpec:
    name: str
    markers: tuple[str, ...]
    relation: str
    goal: str
    stance_shift: str = ''
    confidence: float = 0.91
    requires_active_topic: bool = True


DIALOGUE_INTENT_REGISTRY: tuple[DialogueIntentSpec, ...] = (
    DialogueIntentSpec(
        name='topic_shift',
        markers=(
            'другой вопрос',
            'другая тема',
            'ладно, другой вопрос',
            'ладно другой вопрос',
            'а теперь другой вопрос',
            'теперь другой вопрос',
            'давай теперь про',
            'а теперь про',
            'теперь про',
        ),
        relation='shift',
        goal='opening',
        requires_active_topic=False,
        confidence=0.93,
    ),
    DialogueIntentSpec(
        name='abstractify_previous_question',
        markers=(
            'абстрактно',
            'в общем виде',
            'в общем',
            'не конкретно у меня',
            'не конкретно',
            'не у меня',
            'не про меня',
        ),
        relation='reframe',
        goal='overview',
        stance_shift='general',
    ),
    DialogueIntentSpec(
        name='personalize_previous_question',
        markers=(
            'а если у меня',
            'а если у меня лично',
            'если у меня лично',
            'если это у меня',
            'а у меня лично',
            'вернемся ко мне',
            'вернёмся ко мне',
            'а как это у меня',
        ),
        relation='reframe',
        goal='clarify',
        stance_shift='personal',
    ),
    DialogueIntentSpec(
        name='reject_scope',
        markers=(
            'слишком общо',
            'это слишком общо',
            'слишком широко',
            'это слишком широко',
            'давай конкретнее',
            'можно конкретнее',
            'без общих слов',
            'слишком расплывчато',
        ),
        relation='reframe',
        goal='clarify',
        stance_shift='personal',
    ),
    DialogueIntentSpec(
        name='request_cause_list',
        markers=(
            'какие основные причины',
            'основные причины',
            'перечисли причины',
            'назови причины',
            'какие причины',
            'из-за чего это бывает',
            'от чего это бывает',
        ),
        relation='continue',
        goal='cause_list',
    ),
    DialogueIntentSpec(
        name='request_example',
        markers=(
            'приведи пример',
            'дай пример',
            'можешь привести пример',
            'а пример',
            'как это выглядит',
            'как это звучит',
        ),
        relation='continue',
        goal='example',
    ),
    DialogueIntentSpec(
        name='request_next_step',
        markers=(
            'и что с этим делать',
            'что с этим делать',
            'ну и что с этим делать',
            'и что теперь делать',
            'что теперь делать',
            'что делать дальше',
            'что дальше делать',
            'какой следующий шаг',
            'и какой следующий шаг',
        ),
        relation='continue',
        goal='next_step',
    ),
    DialogueIntentSpec(
        name='request_mini_analysis',
        markers=(
            'и что это значит',
            'что это значит',
            'ну и что это значит',
            'что это вообще значит',
            'что из этого следует',
            'и что из этого следует',
        ),
        relation='continue',
        goal='mini_analysis',
    ),
)


def all_dialogue_intent_markers(*, include_shift: bool = True) -> tuple[str, ...]:
    markers: list[str] = []
    for spec in DIALOGUE_INTENT_REGISTRY:
        if not include_shift and spec.name == 'topic_shift':
            continue
        markers.extend(spec.markers)
    return tuple(markers)


def infer_dialogue_intent(question: str, *, active_topic: str = '') -> DialogueIntentSpec | None:
    q = normalize_dialogue_text(question)
    if not q:
        return None

    best_spec: DialogueIntentSpec | None = None
    best_score = 0
    for spec in DIALOGUE_INTENT_REGISTRY:
        if spec.requires_active_topic and not active_topic:
            continue
        score = sum(1 for marker in spec.markers if marker in q)
        if score > best_score:
            best_score = score
            best_spec = spec

    if best_spec is None or best_score == 0:
        return None
    return best_spec


def question_has_dialogue_intent_marker(question: str, *, include_shift: bool = True) -> bool:
    return dialogue_contains_any(normalize_dialogue_text(question), all_dialogue_intent_markers(include_shift=include_shift))
