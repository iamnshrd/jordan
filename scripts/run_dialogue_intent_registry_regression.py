#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.runtime.dialogue_intent_registry import infer_dialogue_intent
from library._core.runtime.dialogue_intent_registry import question_has_dialogue_intent_marker


def main() -> None:
    next_step = infer_dialogue_intent('ну и какой следующий шаг?', active_topic='relationship-loss-of-feeling')
    example = infer_dialogue_intent('как это звучит в жизни?', active_topic='self-diagnosis')
    reject_scope = infer_dialogue_intent('без общих слов', active_topic='relationship-loss-of-feeling')
    abstractify = infer_dialogue_intent('давай абстрактно, не про меня', active_topic='relationship-loss-of-feeling')
    topic_shift = infer_dialogue_intent('ладно, другой вопрос', active_topic='psychological-portrait')

    results = [
        {
            'name': 'intent_registry_maps_next_step_and_example',
            'pass': (
                next_step is not None
                and next_step.name == 'request_next_step'
                and next_step.goal == 'next_step'
                and example is not None
                and example.name == 'request_example'
                and example.goal == 'example'
            ),
        },
        {
            'name': 'intent_registry_maps_reframe_intents',
            'pass': (
                reject_scope is not None
                and reject_scope.name == 'reject_scope'
                and reject_scope.stance_shift == 'personal'
                and abstractify is not None
                and abstractify.name == 'abstractify_previous_question'
                and abstractify.stance_shift == 'general'
            ),
        },
        {
            'name': 'intent_registry_maps_topic_shift_and_marker_presence',
            'pass': (
                topic_shift is not None
                and topic_shift.name == 'topic_shift'
                and question_has_dialogue_intent_marker('ну и какой следующий шаг?')
                and question_has_dialogue_intent_marker('ладно, другой вопрос')
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'next_step': next_step.name if next_step else '',
            'example': example.name if example else '',
            'reject_scope': reject_scope.name if reject_scope else '',
            'abstractify': abstractify.name if abstractify else '',
            'topic_shift': topic_shift.name if topic_shift else '',
        },
    )


if __name__ == '__main__':
    main()
