"""Heuristic-first dialogue-frame updates for migration away from rigid acts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from library._core.runtime.dialogue_family_registry import (
    DIALOGUE_FAMILY_REGISTRY,
    build_dialogue_family_candidates,
    dialogue_contains_any,
    get_dialogue_family_spec,
    infer_dialogue_family,
    is_dialogue_transition_allowed,
    normalize_dialogue_text,
    resolve_dialogue_transition,
)
from library._core.runtime.dialogue_frame import DialogueFrame, coerce_frame, infer_frame_type, relation_from_act
from library._core.runtime.dialogue_intent_registry import infer_dialogue_intent
from library._core.runtime.dialogue_intent_registry import question_has_dialogue_intent_marker
from library._core.runtime.dialogue_acts import extract_dialogue_axis, extract_dialogue_detail
from library._core.runtime.llm_classifiers import (
    LLMControlCommandRequest,
    LLMFamilyClassificationRequest,
    LLMMarginalRouteRequest,
    maybe_classify_control_command,
    maybe_classify_dialogue_family,
    maybe_route_marginal_turn,
)
from library._core.runtime.policy import detect_policy_block
from library._core.runtime.routes import infer_route
from library._core.runtime.dialogue_state import DialogueState
from library._core.runtime.dialogue_state import infer_active_topic


@dataclass
class DialogueUpdate:
    relation_to_previous: str = 'new'
    is_new_topic: bool = False
    topic_candidate: str = ''
    route_candidate: str = ''
    frame_type_candidate: str = ''
    stance_shift: str = ''
    goal_candidate: str = ''
    transition_kind: str = ''
    slot_fill: dict = field(default_factory=dict)
    classifier_metadata: dict = field(default_factory=dict)
    confidence: float = 0.0
    update_source: str = ''

    def as_dict(self) -> dict:
        return asdict(self)


def _normalize(text: str) -> str:
    return normalize_dialogue_text(text)


def _contains_any(text: str, markers: list[str]) -> bool:
    return dialogue_contains_any(text, markers)


_TOPIC_SHIFT_MARKERS = [
    'другой вопрос',
    'другая тема',
    'ладно, другой вопрос',
    'ладно другой вопрос',
    'а теперь другой вопрос',
    'теперь другой вопрос',
    'давай теперь про',
    'а теперь про',
    'теперь про',
]

_TOPIC_OPENING_PREFIXES = [
    'какие ',
    'почему ',
    'что ',
    'как ',
    'зачем ',
    'от чего ',
    'из-за чего ',
    'можно ли ',
    'о чем ',
    'о чём ',
    'давайте ',
    'расскажи ',
    'в чем ',
    'в чём ',
    'из чего ',
    'на чем ',
    'на чём ',
]

_SLOT_FOLLOWUP_PREFIXES = [
    'скорее ',
    'скорее, ',
    'больше ',
    'главнее ',
    'прежде всего ',
    'скорее из ',
    'скорее от ',
]

_MARGINAL_ROUTE_MARKERS = {
    'repair_misunderstanding': (
        'я не понимаю',
        'не понимаю о чем',
        'не понимаю о чём',
        'не понял',
        'не поняла',
        'объясни проще',
        'скажи проще',
        'ты не туда пошёл',
        'ты сейчас не туда пошел',
        'ты сейчас не туда пошёл',
    ),
    'repair_meta_friction': (
        'так разговора не получится',
        'так разговора у нас не получится',
        'ты меня не слышишь',
        'это мимо',
        'это вообще мимо',
        'разговор не получается',
    ),
    'repair_wrong_level': (
        'слишком абстрактно',
        'слишком резко',
        'без этих общих слов',
        'слишком общо',
    ),
    'vague_help_request': (
        'предложи что делать',
        'что теперь',
        'и как дальше',
        'ну и что теперь',
    ),
    'symptom_self_report': (
        'я подозреваю, что у меня',
        'кажется, что у меня',
        'похоже, что у меня',
        'мне кажется, я выгорел',
        'у меня ангедония',
        'у меня тревога',
    ),
    'scope_shift_meta': (
        'я имею в виду в общем',
        'я имею ввиду в общем',
        'а если абстрактно',
        'не про меня',
        'в общем виде',
    ),
    'relationship_opening_broad': (
        'давай обсудим отношения',
        'хочу поговорить про брак',
        'поговорить про отношения',
        'что делает отношения крепкими',
        'на чем держится брак',
        'на чём держится брак',
    ),
    'summon_soft_opening': (
        'джордан...',
        'я тебе пишу сообщение',
        'проверяем рендерер',
    ),
    'teasing_or_guessing_opening': (
        'угадай, что я хочу спросить',
        'попробуй сам догадаться',
        'догадайся сам',
    ),
}

_SPECIAL_ROUTE_ALLOWED = {
    'repair_misunderstanding',
    'repair_meta_friction',
    'repair_wrong_level',
    'repair_wrong_topic',
    'vague_help_request',
    'symptom_self_report',
    'scope_shift_meta',
    'relationship_opening_broad',
    'summon_soft_opening',
    'teasing_or_guessing_opening',
    'no_special_route',
}

_SPECIAL_ROUTE_ALLOWED_STRATEGIES = {
    '',
    'ack_and_rephrase',
    'ack_and_restart',
    'simplify_and_focus',
    'reframe_topic',
    'offer_axis_menu',
    'convert_to_human_problem_clarify',
}

_SPECIAL_ROUTE_ALLOWED_GOALS = {
    '',
    'opening',
    'menu',
    'clarify',
    'overview',
    'cause_list',
    'mini_analysis',
    'next_step',
    'example',
}

_CONTROL_COMMAND_ALLOWED = {
    'start_social_opening',
    'start_broad_help_opening',
    'start_human_problem_opening',
    'start_relationship_broad_opening',
    'start_symptom_self_report_opening',
    'repair_misunderstanding',
    'repair_meta_friction',
    'repair_wrong_level',
    'repair_wrong_topic',
    'shift_scope_more_general',
    'shift_scope_more_personal',
    'request_kb_grounding',
    'continue_current_flow',
    'no_command',
}

_CONTROL_COMMAND_ALLOWED_KB_POSTURE = {'', 'skip_kb', 'optional_kb', 'require_kb'}
_CONTROL_COMMAND_ALLOWED_ABSTRACTION = {'', 'preserve', 'more_general', 'more_personal', 'simplify'}

_CONTROL_COMMAND_TOPIC_DEFAULTS = {
    'start_social_opening': {
        'topic': 'social-small-talk',
        'route': 'general',
        'stance': 'general',
        'goal': 'opening',
        'relation': 'new',
        'pending_slot': '',
        'bypass_kb': True,
    },
    'start_broad_help_opening': {
        'topic': 'problem-sharing-opening',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'new',
        'pending_slot': 'topic_selection',
        'bypass_kb': True,
    },
    'start_human_problem_opening': {
        'topic': 'problem-sharing-opening',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'new',
        'pending_slot': 'topic_selection',
        'bypass_kb': True,
    },
    'start_relationship_broad_opening': {
        'topic': 'relationship-opening-broad',
        'route': 'relationship-maintenance',
        'stance': 'general',
        'goal': 'opening',
        'relation': 'reframe',
        'pending_slot': 'pattern_family',
        'bypass_kb': True,
    },
    'start_symptom_self_report_opening': {
        'topic': 'self-diagnosis',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': 'symptom_narrowing',
        'bypass_kb': True,
    },
    'repair_misunderstanding': {
        'topic': 'repair-misunderstanding',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
        'bypass_kb': True,
    },
    'repair_meta_friction': {
        'topic': 'repair-meta-friction',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
        'bypass_kb': True,
    },
    'repair_wrong_level': {
        'topic': 'repair-wrong-level',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
        'bypass_kb': True,
    },
    'repair_wrong_topic': {
        'topic': 'repair-wrong-topic',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
        'bypass_kb': True,
    },
    'shift_scope_more_general': {
        'topic': 'scope-shift-meta',
        'route': 'general',
        'stance': 'general',
        'goal': 'overview',
        'relation': 'reframe',
        'pending_slot': 'topic_selection',
        'bypass_kb': True,
    },
    'shift_scope_more_personal': {
        'topic': '',
        'route': '',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': 'narrowing_axis',
        'bypass_kb': True,
    },
    'request_kb_grounding': {
        'topic': '',
        'route': '',
        'stance': '',
        'goal': '',
        'relation': 'continue',
        'pending_slot': '',
        'bypass_kb': False,
    },
    'continue_current_flow': {
        'topic': '',
        'route': '',
        'stance': '',
        'goal': '',
        'relation': 'continue',
        'pending_slot': '',
        'bypass_kb': False,
    },
}

_HEURISTIC_CONTROL_COMMAND_PATTERNS = (
    ('repair_misunderstanding', _MARGINAL_ROUTE_MARKERS['repair_misunderstanding']),
    ('repair_meta_friction', _MARGINAL_ROUTE_MARKERS['repair_meta_friction']),
    ('repair_wrong_level', _MARGINAL_ROUTE_MARKERS['repair_wrong_level']),
    ('start_broad_help_opening', (
        'помогите мне',
        'помоги мне',
        'наладить жизнь',
        'как мне дальше жить',
        'как дальше жить',
        'не знаю как жить',
        'помогите наладить жизнь',
    )),
    ('start_human_problem_opening', (
        'у меня есть некоторые проблемы',
        'я хочу поделиться',
        'у меня проблемы',
        'мне тяжело',
    )),
    ('start_symptom_self_report_opening', _MARGINAL_ROUTE_MARKERS['symptom_self_report']),
    ('shift_scope_more_general', _MARGINAL_ROUTE_MARKERS['scope_shift_meta']),
    ('start_relationship_broad_opening', _MARGINAL_ROUTE_MARKERS['relationship_opening_broad']),
    ('start_social_opening', (
        'добрый вечер',
        'добрый день',
        'доброе утро',
        'привет',
        'здарова',
        'здорова',
        'как ваши дела',
        'как дела',
        'джордан...',
        'я тебе пишу сообщение',
        'проверяем рендерер',
    )),
    ('start_social_opening', _MARGINAL_ROUTE_MARKERS['teasing_or_guessing_opening']),
    ('request_kb_grounding', (
        'по петерсону',
        'у петерсона',
        'в какой книге',
        'из какой книги',
        'цитат',
        'цитату',
        'где он пишет',
        'beyond order',
        '12 rules',
        'maps of meaning',
    )),
)

_SPECIAL_ROUTE_TOPIC_DEFAULTS = {
    'repair_misunderstanding': {
        'topic': 'repair-misunderstanding',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
    },
    'repair_meta_friction': {
        'topic': 'repair-meta-friction',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
    },
    'repair_wrong_level': {
        'topic': 'repair-wrong-level',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
    },
    'repair_wrong_topic': {
        'topic': 'repair-wrong-topic',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': '',
    },
    'vague_help_request': {
        'topic': 'vague-help-request',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': 'narrowing_axis',
    },
    'symptom_self_report': {
        'topic': 'self-diagnosis',
        'route': 'general',
        'stance': 'personal',
        'goal': 'clarify',
        'relation': 'reframe',
        'pending_slot': 'symptom_narrowing',
    },
    'scope_shift_meta': {
        'topic': 'scope-shift-meta',
        'route': 'general',
        'stance': 'general',
        'goal': 'overview',
        'relation': 'reframe',
        'pending_slot': 'topic_selection',
    },
    'relationship_opening_broad': {
        'topic': 'relationship-opening-broad',
        'route': 'relationship-maintenance',
        'stance': 'general',
        'goal': 'opening',
        'relation': 'reframe',
        'pending_slot': 'pattern_family',
    },
    'summon_soft_opening': {
        'topic': 'social-small-talk',
        'route': 'general',
        'stance': 'general',
        'goal': 'opening',
        'relation': 'new',
        'pending_slot': '',
    },
    'teasing_or_guessing_opening': {
        'topic': 'teasing-opening',
        'route': 'general',
        'stance': 'general',
        'goal': 'opening',
        'relation': 'new',
        'pending_slot': '',
    },
}

_HEURISTIC_MARGINAL_ROUTE_PATTERNS = (
    ('repair_misunderstanding', _MARGINAL_ROUTE_MARKERS['repair_misunderstanding']),
    ('repair_meta_friction', _MARGINAL_ROUTE_MARKERS['repair_meta_friction']),
    ('repair_wrong_level', _MARGINAL_ROUTE_MARKERS['repair_wrong_level']),
    ('vague_help_request', _MARGINAL_ROUTE_MARKERS['vague_help_request']),
    ('symptom_self_report', _MARGINAL_ROUTE_MARKERS['symptom_self_report']),
    ('scope_shift_meta', _MARGINAL_ROUTE_MARKERS['scope_shift_meta']),
    ('relationship_opening_broad', _MARGINAL_ROUTE_MARKERS['relationship_opening_broad']),
    ('summon_soft_opening', _MARGINAL_ROUTE_MARKERS['summon_soft_opening']),
    ('teasing_or_guessing_opening', _MARGINAL_ROUTE_MARKERS['teasing_or_guessing_opening']),
)


def _looks_like_fresh_topic_opening(text: str) -> bool:
    if not text:
        return False
    if question_has_dialogue_intent_marker(text):
        return False
    if len(text.split()) < 4:
        return False
    if any(text.startswith(prefix) for prefix in _TOPIC_OPENING_PREFIXES):
        return True
    return text.endswith('?')


def _looks_like_slot_followup_candidate(text: str) -> bool:
    if not text:
        return False
    if any(text.startswith(prefix) for prefix in _SLOT_FOLLOWUP_PREFIXES):
        return True
    return len(text.split()) <= 4 and text.startswith('из ')


def _looks_like_social_opening(text: str) -> bool:
    return _contains_any(text, _HEURISTIC_CONTROL_COMMAND_PATTERNS[7][1])


def _looks_like_greeting_only(text: str) -> bool:
    return _contains_any(text, ('добрый вечер', 'добрый день', 'доброе утро', 'привет', 'здарова', 'здорова'))


def _broad_help_topic_for(question: str) -> str:
    q = _normalize(question)
    if any(marker in q for marker in ('наладить жизнь', 'как мне дальше жить', 'как дальше жить', 'не знаю как жить')):
        return 'life-direction-opening'
    return 'problem-sharing-opening'


def _control_command_defaults(command_name: str, *, question: str, state: dict, frame: DialogueFrame) -> dict:
    defaults = dict(_CONTROL_COMMAND_TOPIC_DEFAULTS.get(command_name) or {})
    if command_name == 'start_social_opening':
        normalized = _normalize(question)
        defaults['topic'] = 'greeting' if _looks_like_greeting_only(normalized) else 'social-small-talk'
    elif command_name == 'start_broad_help_opening':
        defaults['topic'] = _broad_help_topic_for(question)
        defaults['pending_slot'] = _family_opening_pending_slot(defaults['topic'])
        defaults['goal'] = 'clarify'
    elif command_name == 'shift_scope_more_personal':
        active_topic = frame.topic or state.get('active_topic', '')
        if active_topic:
            defaults['topic'] = active_topic
            defaults['route'] = frame.route or state.get('active_route', '')
            defaults['pending_slot'] = state.get('pending_slot', '') or frame.pending_slot or _family_opening_pending_slot(active_topic)
    return defaults


def _family_stance_goal(topic: str) -> tuple[str, str]:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return '', ''
    return spec.stance, spec.goal


def _transition_kind_for_act(dialogue_act: str) -> str:
    return {
        'abstractify_previous_question': 'reframe_general',
        'confirm_scope': 'reframe_general',
        'personalize_previous_question': 'reframe_personal',
        'reject_scope': 'reject_scope',
        'request_cause_list': 'cause_list',
        'request_example': 'example',
        'request_next_step': 'next_step',
        'request_mini_analysis': 'mini_analysis',
        'supply_narrowing_axis': 'axis_answer',
        'supply_concrete_manifestation': 'detail_answer',
        'topic_shift': 'topic_shift',
    }.get(dialogue_act, 'opening')


def _family_opening_pending_slot(topic: str) -> str:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return ''
    return spec.opening_pending_slot


def _fallback_family_metadata(*, status: str = 'not_applicable', reason: str = '') -> dict:
    return {
        'family_classifier_used': False,
        'family_classifier_backend': 'none',
        'family_classifier_backend_detail': '',
        'family_classifier_status': status,
        'family_classifier_confidence': 0.0,
        'family_classifier_fallback_used': True,
        'family_classifier_result_topic': '',
        'family_classifier_result_goal': '',
        'family_classifier_deterministic_topic': '',
        'family_classifier_deterministic_goal': '',
        'family_classifier_reason': reason,
        'family_classifier_rejection_reason': '',
    }


def _fallback_marginal_metadata(*, status: str = 'not_applicable', reason: str = '') -> dict:
    return {
        'marginal_router_used': False,
        'marginal_router_backend': 'none',
        'marginal_router_backend_detail': '',
        'marginal_router_status': status,
        'marginal_router_confidence': 0.0,
        'marginal_router_result_route': '',
        'marginal_router_result_topic': '',
        'marginal_router_result_goal': '',
        'marginal_router_repair_strategy': '',
        'marginal_router_fallback_used': True,
        'marginal_router_rejection_reason': '',
        'marginal_router_reason': reason,
        'marginal_router_exception_detail': '',
    }


def _fallback_control_metadata(*, status: str = 'not_applicable', reason: str = '') -> dict:
    return {
        'control_command_used': False,
        'control_command_backend': 'none',
        'control_command_backend_detail': '',
        'control_command_status': status,
        'control_command_confidence': 0.0,
        'control_command_name': '',
        'control_command_reason': reason,
        'control_command_kb_posture': '',
        'control_command_abstraction_shift': '',
        'control_command_fallback_used': True,
        'control_command_rejection_reason': '',
        'control_command_exception_detail': '',
    }


def _build_family_shortlist(question: str, *,
                            state: dict,
                            frame: DialogueFrame,
                            deterministic_family: dict | None = None) -> list[dict]:
    route_name = state.get('active_route', '') or frame.route or infer_route(question)
    active_topic = frame.topic or state.get('active_topic', '')
    candidates = build_dialogue_family_candidates(
        question,
        route_name=route_name,
        active_topic=active_topic,
        limit=5,
    )
    seen_topics = {str(candidate.get('topic_candidate', '') or '') for candidate in candidates}
    if deterministic_family:
        topic = str(deterministic_family.get('topic_candidate', '') or '')
        if topic and topic not in seen_topics:
            candidates.insert(0, {
                'topic_candidate': topic,
                'route_candidate': deterministic_family.get('route_candidate', ''),
                'stance_shift': deterministic_family.get('stance_shift', ''),
                'goal_candidate': deterministic_family.get('goal_candidate', ''),
                'score': int((deterministic_family.get('confidence', 0.0) or 0.0) * 10),
                'threshold': 0,
                'description': 'deterministic_best_guess',
            })
            seen_topics.add(topic)
    if route_name:
        for spec in DIALOGUE_FAMILY_REGISTRY:
            if spec.topic in seen_topics:
                continue
            if spec.route != route_name:
                continue
            candidates.append({
                'topic_candidate': spec.topic,
                'route_candidate': spec.route,
                'stance_shift': spec.stance,
                'goal_candidate': spec.goal,
                'score': 0,
                'threshold': spec.threshold,
                'description': (
                    f'route={spec.route}; stance={spec.stance}; goal={spec.goal}; '
                    f'opening_mode={spec.opening_mode}'
                ),
            })
            seen_topics.add(spec.topic)
            if len(candidates) >= 5:
                break
    return candidates[:5]


def _looks_like_marginal_turn(question: str, *, state: dict, frame: DialogueFrame) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if any(_contains_any(q, markers) for markers in _MARGINAL_ROUTE_MARKERS.values()):
        return True
    active_topic = frame.topic or state.get('active_topic', '')
    if active_topic and len(q.split()) <= 8:
        return True
    return False


def _looks_like_control_turn(question: str, *, state: dict, frame: DialogueFrame) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if any(_contains_any(q, markers) for _, markers in _HEURISTIC_CONTROL_COMMAND_PATTERNS):
        return True
    if _looks_like_marginal_turn(question, state=state, frame=frame):
        return True
    if len(q.split()) <= 6 and state.get('recovery_state', ''):
        return True
    return False


def _should_use_control_command(question: str, *,
                                dialogue_act: str,
                                state: dict,
                                frame: DialogueFrame,
                                slotish_followup: bool) -> bool:
    if slotish_followup:
        return False
    if detect_policy_block(question) is not None:
        return False
    if dialogue_act in {
        'supply_narrowing_axis',
        'supply_concrete_manifestation',
        'abstractify_previous_question',
        'confirm_scope',
        'personalize_previous_question',
        'request_cause_list',
        'request_example',
        'request_next_step',
        'request_mini_analysis',
    }:
        return False
    return _looks_like_control_turn(question, state=state, frame=frame)


def _resolve_control_command(question: str, *,
                             dialogue_act: str,
                             state: dict,
                             frame: DialogueFrame,
                             slotish_followup: bool = False) -> tuple[dict, dict]:
    metadata = _fallback_control_metadata()

    def _heuristic_command(rejection_reason: str = '') -> tuple[dict, dict]:
        q = _normalize(question)
        command_name = 'no_command'
        for candidate_command, markers in _HEURISTIC_CONTROL_COMMAND_PATTERNS:
            if _contains_any(q, markers):
                command_name = candidate_command
                break
        if command_name == 'no_command':
            return {}, metadata
        defaults = _control_command_defaults(command_name, question=question, state=state, frame=frame)
        heuristic_metadata = dict(metadata)
        heuristic_metadata.update({
            'control_command_status': 'heuristic_fallback',
            'control_command_confidence': 0.87,
            'control_command_name': command_name,
            'control_command_reason': 'marker_match',
            'control_command_kb_posture': 'require_kb' if command_name == 'request_kb_grounding' else 'skip_kb',
            'control_command_abstraction_shift': 'more_general' if command_name == 'shift_scope_more_general' else '',
            'control_command_fallback_used': True,
            'control_command_rejection_reason': rejection_reason,
        })
        return {
            'command_name': command_name,
            'confidence': 0.87,
            'reason': 'marker_match',
            'abstraction_shift': heuristic_metadata.get('control_command_abstraction_shift', ''),
            'kb_posture': heuristic_metadata.get('control_command_kb_posture', ''),
            'topic_candidate': defaults.get('topic', ''),
            'route_candidate': defaults.get('route', ''),
            'stance_shift': defaults.get('stance', ''),
            'goal_candidate': defaults.get('goal', ''),
            'relation_to_previous': defaults.get('relation', 'reframe'),
            'pending_slot': defaults.get('pending_slot', ''),
            'bypass_kb': bool(defaults.get('bypass_kb', False)),
        }, heuristic_metadata

    if not _should_use_control_command(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
    ):
        return {}, metadata
    request = LLMControlCommandRequest(
        question=question,
        dialogue_act=dialogue_act,
        dialogue_state=dict(state or {}),
        dialogue_frame=frame.as_dict(),
        previous_topic=frame.topic or state.get('active_topic', ''),
        previous_route=frame.route or state.get('active_route', ''),
        previous_goal=frame.goal,
        previous_stance=frame.stance or state.get('abstraction_level', ''),
        previous_reason_code=state.get('last_reason_code', ''),
        recovery_state=state.get('recovery_state', ''),
    )
    result = maybe_classify_control_command(request)
    metadata.update(result.metadata())
    if not result.used:
        return _heuristic_command()
    if result.status == 'exception':
        metadata['control_command_rejection_reason'] = 'exception'
        return _heuristic_command('exception')
    if result.command_name not in _CONTROL_COMMAND_ALLOWED:
        metadata['control_command_status'] = 'rejected'
        metadata['control_command_rejection_reason'] = 'invalid_command'
        return _heuristic_command('invalid_command')
    if result.kb_posture and result.kb_posture not in _CONTROL_COMMAND_ALLOWED_KB_POSTURE:
        metadata['control_command_status'] = 'rejected'
        metadata['control_command_rejection_reason'] = 'invalid_kb_posture'
        return _heuristic_command('invalid_kb_posture')
    if result.abstraction_shift and result.abstraction_shift not in _CONTROL_COMMAND_ALLOWED_ABSTRACTION:
        metadata['control_command_status'] = 'rejected'
        metadata['control_command_rejection_reason'] = 'invalid_abstraction_shift'
        return _heuristic_command('invalid_abstraction_shift')
    if float(result.confidence or 0.0) < 0.78:
        metadata['control_command_status'] = 'rejected'
        metadata['control_command_rejection_reason'] = 'low_confidence'
        return _heuristic_command('low_confidence')
    if result.command_name in {'no_command', 'continue_current_flow'}:
        metadata['control_command_status'] = 'accepted'
        metadata['control_command_fallback_used'] = False
        return {
            'command_name': result.command_name,
            'confidence': float(result.confidence or 0.0),
            'reason': result.reason,
            'abstraction_shift': result.abstraction_shift,
            'kb_posture': result.kb_posture or '',
            'topic_candidate': '',
            'route_candidate': '',
            'stance_shift': '',
            'goal_candidate': '',
            'relation_to_previous': 'continue',
            'pending_slot': '',
            'bypass_kb': False,
        }, metadata
    defaults = _control_command_defaults(result.command_name, question=question, state=state, frame=frame)
    topic_candidate = defaults.get('topic', '')
    if topic_candidate and topic_candidate not in {spec.topic for spec in DIALOGUE_FAMILY_REGISTRY}:
        metadata['control_command_status'] = 'rejected'
        metadata['control_command_rejection_reason'] = 'invalid_topic'
        return _heuristic_command('invalid_topic')
    metadata['control_command_status'] = 'accepted'
    metadata['control_command_fallback_used'] = False
    return {
        'command_name': result.command_name,
        'confidence': float(result.confidence or 0.0),
        'reason': result.reason,
        'abstraction_shift': result.abstraction_shift,
        'kb_posture': result.kb_posture or ('require_kb' if result.command_name == 'request_kb_grounding' else 'skip_kb'),
        'topic_candidate': topic_candidate,
        'route_candidate': defaults.get('route', ''),
        'stance_shift': defaults.get('stance', ''),
        'goal_candidate': defaults.get('goal', ''),
        'relation_to_previous': defaults.get('relation', 'reframe'),
        'pending_slot': defaults.get('pending_slot', ''),
        'bypass_kb': bool(defaults.get('bypass_kb', False)),
    }, metadata


def _should_use_marginal_router(question: str, *,
                                dialogue_act: str,
                                state: dict,
                                frame: DialogueFrame,
                                slotish_followup: bool) -> bool:
    q = _normalize(question)
    if not q or slotish_followup:
        return False
    if detect_policy_block(question) is not None:
        return False
    if dialogue_act in {
        'supply_narrowing_axis',
        'supply_concrete_manifestation',
        'abstractify_previous_question',
        'confirm_scope',
        'personalize_previous_question',
        'request_cause_list',
        'request_example',
        'request_next_step',
        'request_mini_analysis',
    }:
        return False
    return _looks_like_marginal_turn(question, state=state, frame=frame)


def _resolve_marginal_route(question: str, *,
                            dialogue_act: str,
                            state: dict,
                            frame: DialogueFrame,
                            slotish_followup: bool = False) -> tuple[dict, dict]:
    def _heuristic_route() -> tuple[dict, dict]:
        q = _normalize(question)
        guessed_route = 'no_special_route'
        for route_name, markers in _HEURISTIC_MARGINAL_ROUTE_PATTERNS:
            if _contains_any(q, markers):
                guessed_route = route_name
                break
        if guessed_route == 'no_special_route':
            return {}, metadata
        defaults = dict(_SPECIAL_ROUTE_TOPIC_DEFAULTS.get(guessed_route) or {})
        topic_candidate = defaults.get('topic', '')
        if topic_candidate not in {spec.topic for spec in DIALOGUE_FAMILY_REGISTRY}:
            return {}, metadata
        heuristic_metadata = dict(metadata)
        heuristic_metadata.update({
            'marginal_router_status': 'heuristic_fallback',
            'marginal_router_confidence': 0.86,
            'marginal_router_result_route': guessed_route,
            'marginal_router_result_topic': topic_candidate,
            'marginal_router_result_goal': defaults.get('goal', ''),
            'marginal_router_repair_strategy': '',
            'marginal_router_fallback_used': True,
            'marginal_router_reason': 'marker_match',
        })
        return {
            'special_route': guessed_route,
            'topic_candidate': topic_candidate,
            'route_candidate': defaults.get('route', ''),
            'stance_shift': defaults.get('stance', ''),
            'goal_candidate': defaults.get('goal', ''),
            'confidence': 0.86,
            'reason': 'marker_match',
            'repair_strategy': '',
            'relation_to_previous': defaults.get('relation', 'reframe'),
            'pending_slot': defaults.get('pending_slot', ''),
        }, heuristic_metadata

    metadata = _fallback_marginal_metadata()
    if not _should_use_marginal_router(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
    ):
        return {}, metadata
    request = LLMMarginalRouteRequest(
        question=question,
        dialogue_act=dialogue_act,
        dialogue_state=dict(state or {}),
        dialogue_frame=frame.as_dict(),
        previous_topic=frame.topic or state.get('active_topic', ''),
        previous_route=frame.route or state.get('active_route', ''),
        previous_goal=frame.goal,
        previous_stance=frame.stance or state.get('abstraction_level', ''),
    )
    result = maybe_route_marginal_turn(request)
    metadata.update(result.metadata())
    if not result.used:
        return _heuristic_route()
    if result.status == 'exception':
        metadata['marginal_router_rejection_reason'] = 'exception'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata.setdefault('marginal_router_exception_detail', metadata.get('marginal_router_exception_detail', ''))
            heuristic_metadata['marginal_router_rejection_reason'] = 'exception'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    if result.special_route not in _SPECIAL_ROUTE_ALLOWED:
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'invalid_route'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'invalid_route'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    if result.special_route == 'no_special_route':
        metadata['marginal_router_status'] = 'deterministic_fallback'
        return _heuristic_route()
    if result.repair_strategy not in _SPECIAL_ROUTE_ALLOWED_STRATEGIES:
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'invalid_strategy'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'invalid_strategy'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    if result.goal_candidate and result.goal_candidate not in _SPECIAL_ROUTE_ALLOWED_GOALS:
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'invalid_goal'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'invalid_goal'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    if float(result.confidence or 0.0) < 0.78:
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'low_confidence'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'low_confidence'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    defaults = dict(_SPECIAL_ROUTE_TOPIC_DEFAULTS.get(result.special_route) or {})
    topic_candidate = result.topic_candidate or defaults.get('topic', '')
    goal_candidate = result.goal_candidate or defaults.get('goal', '')
    route_candidate = result.route_candidate or defaults.get('route', '')
    stance_shift = result.stance_shift or defaults.get('stance', '')
    if topic_candidate not in {spec.topic for spec in DIALOGUE_FAMILY_REGISTRY}:
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'invalid_topic'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'invalid_topic'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    if not resolve_dialogue_transition(topic_candidate, 'opening'):
        metadata['marginal_router_status'] = 'rejected'
        metadata['marginal_router_rejection_reason'] = 'transition_conflict'
        heuristic_route, heuristic_metadata = _heuristic_route()
        if heuristic_route:
            heuristic_metadata['marginal_router_rejection_reason'] = 'transition_conflict'
            return heuristic_route, heuristic_metadata
        return {}, metadata
    metadata['marginal_router_status'] = 'accepted'
    metadata['marginal_router_fallback_used'] = False
    metadata['marginal_router_result_route'] = result.special_route
    metadata['marginal_router_result_topic'] = topic_candidate
    metadata['marginal_router_result_goal'] = goal_candidate
    return {
        'special_route': result.special_route,
        'topic_candidate': topic_candidate,
        'route_candidate': route_candidate,
        'stance_shift': stance_shift,
        'goal_candidate': goal_candidate,
        'confidence': float(result.confidence or 0.0),
        'reason': result.reason,
        'repair_strategy': result.repair_strategy or '',
        'relation_to_previous': defaults.get('relation', 'reframe'),
        'pending_slot': defaults.get('pending_slot', ''),
    }, metadata


def _should_use_llm_family_classifier(question: str, *,
                                      dialogue_act: str,
                                      state: dict,
                                      frame: DialogueFrame,
                                      slotish_followup: bool,
                                      deterministic_family: dict | None = None) -> bool:
    q = _normalize(question)
    if not q or slotish_followup:
        return False
    if detect_policy_block(question) is not None:
        return False
    if dialogue_act in {'supply_narrowing_axis', 'supply_concrete_manifestation'}:
        return False
    if frame.topic and question_has_dialogue_intent_marker(q):
        return False
    deterministic_confidence = float((deterministic_family or {}).get('confidence', 0.0) or 0.0)
    if deterministic_confidence >= 0.95 and (deterministic_family or {}).get('topic_candidate'):
        return False
    if _looks_like_fresh_topic_opening(q):
        return True
    if len(q.split()) <= 6:
        return True
    if dialogue_act in {
        'open_topic',
        'topic_shift',
        'greeting_opening',
        'request_menu',
        'request_conversation_feedback',
        'request_psychological_portrait',
        'self_diagnosis_soft',
    }:
        return True
    return False


def _resolve_semantic_family(question: str, *,
                             dialogue_act: str,
                             state: dict,
                             frame: DialogueFrame,
                             slotish_followup: bool = False) -> tuple[dict, dict]:
    deterministic_family = {} if slotish_followup else infer_dialogue_family(question)
    deterministic_topic = str(deterministic_family.get('topic_candidate', '') or '')
    deterministic_goal = str(deterministic_family.get('goal_candidate', '') or '')
    metadata = _fallback_family_metadata(
        status='deterministic' if deterministic_family else 'not_configured',
    )
    metadata['family_classifier_deterministic_topic'] = deterministic_topic
    metadata['family_classifier_deterministic_goal'] = deterministic_goal
    if not _should_use_llm_family_classifier(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
        deterministic_family=deterministic_family,
    ):
        metadata['family_classifier_status'] = 'not_applicable'
        return deterministic_family, metadata
    candidates = _build_family_shortlist(
        question,
        state=state,
        frame=frame,
        deterministic_family=deterministic_family,
    )
    if not candidates:
        metadata['family_classifier_status'] = 'no_candidates'
        return deterministic_family, metadata
    result = maybe_classify_dialogue_family(LLMFamilyClassificationRequest(
        question=question,
        dialogue_act=dialogue_act,
        dialogue_state=dict(state or {}),
        dialogue_frame=frame.as_dict(),
        deterministic_guess=dict(deterministic_family or {}),
        candidates=tuple(candidates),
    ))
    metadata.update(result.metadata())
    allowed_topics = {
        str(candidate.get('topic_candidate', '') or '')
        for candidate in candidates
        if candidate.get('topic_candidate')
    }
    if not result.used:
        return deterministic_family, metadata
    if result.status == 'exception':
        metadata['family_classifier_rejection_reason'] = 'exception'
        return deterministic_family, metadata
    candidate_topic = result.topic_candidate
    if not candidate_topic or candidate_topic == 'deterministic_fallback':
        metadata['family_classifier_status'] = 'deterministic_fallback'
        return deterministic_family, metadata
    if candidate_topic not in allowed_topics:
        metadata['family_classifier_status'] = 'rejected'
        metadata['family_classifier_rejection_reason'] = 'invalid_topic'
        return deterministic_family, metadata
    spec = get_dialogue_family_spec(candidate_topic)
    if spec is None:
        metadata['family_classifier_status'] = 'rejected'
        metadata['family_classifier_rejection_reason'] = 'invalid_topic'
        return deterministic_family, metadata
    if float(result.confidence or 0.0) < 0.9:
        metadata['family_classifier_status'] = 'rejected'
        metadata['family_classifier_rejection_reason'] = 'low_confidence'
        return deterministic_family, metadata
    if result.goal_candidate and result.goal_candidate != spec.goal:
        metadata['family_classifier_status'] = 'rejected'
        metadata['family_classifier_rejection_reason'] = 'invalid_goal'
        return deterministic_family, metadata
    opening = resolve_dialogue_transition(candidate_topic, 'opening')
    if not opening:
        metadata['family_classifier_status'] = 'rejected'
        metadata['family_classifier_rejection_reason'] = 'transition_conflict'
        return deterministic_family, metadata
    metadata['family_classifier_status'] = 'accepted'
    metadata['family_classifier_fallback_used'] = False
    metadata['family_classifier_result_topic'] = spec.topic
    metadata['family_classifier_result_goal'] = spec.goal
    return {
        'topic_candidate': spec.topic,
        'route_candidate': spec.route,
        'stance_shift': spec.stance,
        'goal_candidate': spec.goal,
        'confidence': result.confidence,
        'reason': result.reason,
    }, metadata


def _infer_special_topic(question: str, dialogue_act: str, *, state: dict, frame: DialogueFrame) -> tuple[str, str, dict]:
    marginal_route, marginal_metadata = _resolve_marginal_route(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=False,
    )
    if marginal_route:
        return (
            marginal_route.get('topic_candidate', '') or '',
            marginal_route.get('route_candidate', '') or '',
            marginal_metadata,
        )
    semantic_family, metadata = _resolve_semantic_family(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=False,
    )
    if semantic_family:
        return (
            semantic_family.get('topic_candidate', '') or '',
            semantic_family.get('route_candidate', '') or '',
            metadata,
        )
    return '', '', metadata


def _build_update_payload(*,
                          relation_to_previous: str,
                          is_new_topic: bool,
                          topic_candidate: str,
                          route_candidate: str,
                          stance_shift: str,
                          goal_candidate: str,
                          transition_kind: str,
                          pending_slot: str,
                          confidence: float,
                          update_source: str,
                          classifier_metadata: dict | None = None,
                          axis: str = '',
                          detail: str = '') -> dict:
    return {
        'relation_to_previous': relation_to_previous,
        'is_new_topic': is_new_topic,
        'topic_candidate': topic_candidate,
        'route_candidate': route_candidate,
        'stance_shift': stance_shift,
        'goal_candidate': goal_candidate,
        'transition_kind': transition_kind,
        'slot_fill': {'axis': axis, 'detail': detail, 'pending_slot': pending_slot},
        'classifier_metadata': dict(classifier_metadata or {}),
        'confidence': confidence,
        'update_source': update_source,
    }


def _infer_update_from_question(question: str, *,
                                dialogue_act: str,
                                state: dict,
                                frame: DialogueFrame,
                                selected_axis: str = '',
                                selected_detail: str = '') -> dict:
    q = _normalize(question)
    if not q:
        return {}

    active_topic = frame.topic or state.get('active_topic', '')
    previous_pending_slot = state.get('pending_slot', '') or frame.pending_slot

    if _contains_any(q, _TOPIC_SHIFT_MARKERS):
        special_topic, special_route, classifier_metadata = _infer_special_topic(
            question,
            'topic_shift',
            state=state,
            frame=frame,
        )
        topic_candidate = special_topic or infer_active_topic(question, route_name='') or active_topic
        stance_shift, goal_candidate = _family_stance_goal(topic_candidate)
        return _build_update_payload(
            relation_to_previous='shift',
            is_new_topic=True,
            topic_candidate=topic_candidate,
            route_candidate=special_route or frame.route or state.get('active_route', ''),
            stance_shift=stance_shift or ('general' if topic_candidate in {'scope-topics', 'relationship-foundations', 'greeting'} else 'personal'),
            goal_candidate=goal_candidate or 'clarify',
            transition_kind='opening',
            pending_slot=_family_opening_pending_slot(topic_candidate),
            confidence=0.93,
            update_source='intent_registry',
            classifier_metadata=classifier_metadata,
        )

    slotish_followup = bool(active_topic) and _looks_like_slot_followup_candidate(q) and not _looks_like_fresh_topic_opening(q)
    control_command, control_metadata = _resolve_control_command(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
    )
    if control_command:
        command_name = control_command.get('command_name', '')
        classifier_metadata = {
            **control_metadata,
            **_fallback_marginal_metadata(status='not_applicable'),
            **_fallback_family_metadata(status='not_applicable'),
        }
        if command_name in {'request_kb_grounding', 'continue_current_flow', 'no_command'}:
            return _build_update_payload(
                relation_to_previous=control_command.get('relation_to_previous', relation_from_act(dialogue_act)),
                is_new_topic=False,
                topic_candidate=frame.topic or state.get('active_topic', ''),
                route_candidate=frame.route or state.get('active_route', ''),
                stance_shift='general' if control_command.get('abstraction_shift') == 'more_general' else (
                    'personal' if control_command.get('abstraction_shift') == 'more_personal' else ''
                ),
                goal_candidate='overview' if control_command.get('abstraction_shift') == 'more_general' else '',
                transition_kind='',
                pending_slot=state.get('pending_slot', '') or frame.pending_slot,
                confidence=float(control_command.get('confidence', 0.0) or 0.0),
                update_source='control_command',
                classifier_metadata=classifier_metadata,
            )
        return _build_update_payload(
            relation_to_previous=control_command.get('relation_to_previous', 'reframe'),
            is_new_topic=bool(control_command.get('topic_candidate')),
            topic_candidate=control_command.get('topic_candidate', ''),
            route_candidate=control_command.get('route_candidate', ''),
            stance_shift=control_command.get('stance_shift', ''),
            goal_candidate=control_command.get('goal_candidate', ''),
            transition_kind='opening',
            pending_slot=control_command.get('pending_slot', ''),
            confidence=float(control_command.get('confidence', 0.84) or 0.84),
            update_source='control_command',
            classifier_metadata=classifier_metadata,
        )

    marginal_route, marginal_metadata = _resolve_marginal_route(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
    )
    if marginal_route:
        return _build_update_payload(
            relation_to_previous=marginal_route.get('relation_to_previous', 'reframe'),
            is_new_topic=True,
            topic_candidate=marginal_route.get('topic_candidate', ''),
            route_candidate=marginal_route.get('route_candidate', ''),
            stance_shift=marginal_route.get('stance_shift', ''),
            goal_candidate=marginal_route.get('goal_candidate', ''),
            transition_kind='opening',
            pending_slot=marginal_route.get('pending_slot', ''),
            confidence=float(marginal_route.get('confidence', 0.84) or 0.84),
            update_source='marginal_router',
            classifier_metadata={**control_metadata, **marginal_metadata, **_fallback_family_metadata(status='not_applicable')},
        )
    semantic_family, classifier_metadata = _resolve_semantic_family(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        slotish_followup=slotish_followup,
    )
    classifier_metadata = {**control_metadata, **marginal_metadata, **classifier_metadata}

    if semantic_family:
        return _build_update_payload(
            relation_to_previous='new',
            is_new_topic=True,
            topic_candidate=semantic_family.get('topic_candidate', ''),
            route_candidate=semantic_family.get('route_candidate', ''),
            stance_shift=semantic_family.get('stance_shift', ''),
            goal_candidate=semantic_family.get('goal_candidate', ''),
            transition_kind='opening',
            pending_slot=_family_opening_pending_slot(semantic_family.get('topic_candidate', '')),
            confidence=float(semantic_family.get('confidence', 0.78) or 0.78),
            update_source='family_classifier' if classifier_metadata.get('family_classifier_status') == 'accepted' else 'family_registry',
            classifier_metadata=classifier_metadata,
        )

    if active_topic and _looks_like_fresh_topic_opening(q):
        route_guess = infer_route(question)
        topic_guess = infer_active_topic(question, route_name=route_guess) or route_guess
        if topic_guess and topic_guess not in {'', active_topic, 'general'}:
            stance_guess, goal_guess = _family_stance_goal(topic_guess)
            return _build_update_payload(
                relation_to_previous='shift',
                is_new_topic=True,
                topic_candidate=topic_guess,
                route_candidate=route_guess if route_guess != 'general' or topic_guess == 'scope-topics' else frame.route or state.get('active_route', ''),
                stance_shift=stance_guess or ('general' if topic_guess in {'scope-topics', 'relationship-foundations', 'greeting'} else 'personal'),
                goal_candidate=goal_guess or 'clarify',
                transition_kind='opening',
                pending_slot=_family_opening_pending_slot(topic_guess),
                confidence=0.89,
                update_source='fresh_topic_guard',
                classifier_metadata=classifier_metadata,
            )

    inferred_axis = selected_axis or extract_dialogue_axis(question, state)
    if active_topic and inferred_axis and is_dialogue_transition_allowed(
        active_topic,
        'axis_answer',
        goal=frame.goal,
        dialogue_mode=state.get('dialogue_mode', ''),
        pending_slot=previous_pending_slot,
        abstraction_level=state.get('abstraction_level', ''),
    ):
        return _build_update_payload(
            relation_to_previous='answer_slot',
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift='',
            goal_candidate='clarify',
            transition_kind='axis_answer',
            pending_slot=previous_pending_slot,
            confidence=0.9,
            update_source='slot_answer',
            axis=inferred_axis,
        )

    inferred_detail = selected_detail or extract_dialogue_detail(question, state)
    if active_topic and inferred_detail and is_dialogue_transition_allowed(
        active_topic,
        'detail_answer',
        goal=frame.goal,
        dialogue_mode=state.get('dialogue_mode', ''),
        pending_slot=previous_pending_slot,
        abstraction_level=state.get('abstraction_level', ''),
    ):
        return _build_update_payload(
            relation_to_previous='answer_slot',
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift='',
            goal_candidate='clarify',
            transition_kind='detail_answer',
            pending_slot=previous_pending_slot,
            confidence=0.9,
            update_source='slot_answer',
            axis=state.get('active_axis', ''),
            detail=inferred_detail,
        )

    intent_spec = infer_dialogue_intent(question, active_topic=active_topic)
    if active_topic and intent_spec and intent_spec.name != 'topic_shift':
        return _build_update_payload(
            relation_to_previous=intent_spec.relation,
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift=intent_spec.stance_shift,
            goal_candidate=intent_spec.goal,
            transition_kind=_transition_kind_for_act(intent_spec.name),
            pending_slot=previous_pending_slot,
            confidence=intent_spec.confidence,
            update_source='intent_registry',
        )

    return {}


def _default_stance_for_act(dialogue_act: str, topic_candidate: str = '') -> str:
    if dialogue_act in {'request_menu', 'greeting_opening'}:
        return 'general'
    if dialogue_act == 'request_conversation_feedback':
        return 'personal'
    if dialogue_act in {
        'open_topic',
        'topic_shift',
        'request_psychological_portrait',
        'self_diagnosis_soft',
    }:
        return 'personal'
    if topic_candidate in {'psychological-portrait', 'self-diagnosis', 'relationship-loss-of-feeling'}:
        return 'personal'
    return ''


def _default_goal_for_act(dialogue_act: str, topic_candidate: str = '') -> str:
    if dialogue_act == 'greeting_opening':
        return 'opening'
    if dialogue_act == 'request_menu':
        return 'menu'
    if dialogue_act == 'request_conversation_feedback':
        return 'menu'
    if dialogue_act in {'request_psychological_portrait', 'self_diagnosis_soft'}:
        return 'clarify'
    if dialogue_act == 'topic_shift':
        if topic_candidate in {'psychological-portrait', 'self-diagnosis'}:
            return 'clarify'
        if topic_candidate in {'scope-topics', 'greeting'}:
            return 'menu' if topic_candidate == 'scope-topics' else 'opening'
        return 'opening'
    if dialogue_act == 'open_topic':
        return 'opening'
    return ''


def infer_dialogue_update(question: str, *,
                          dialogue_act: str,
                          dialogue_state: dict | None = None,
                          dialogue_frame: dict | DialogueFrame | None = None,
                          selected_axis: str = '',
                          selected_detail: str = '') -> DialogueUpdate:
    if isinstance(dialogue_state, DialogueState):
        state = dialogue_state.as_dict()
    else:
        state = dict(dialogue_state or {})
    frame = coerce_frame(dialogue_frame)
    relation = relation_from_act(dialogue_act)
    topic_candidate = frame.topic
    route_candidate = frame.route
    stance_shift = ''
    goal_candidate = ''
    transition_kind = _transition_kind_for_act(dialogue_act)
    is_new_topic = False
    confidence = 0.55
    update_source = 'dialogue_act_fallback'

    direct_update = _infer_update_from_question(
        question,
        dialogue_act=dialogue_act,
        state=state,
        frame=frame,
        selected_axis=selected_axis,
        selected_detail=selected_detail,
    )
    if direct_update:
        return DialogueUpdate(
            relation_to_previous=direct_update.get('relation_to_previous', relation),
            is_new_topic=bool(direct_update.get('is_new_topic', False)),
            topic_candidate=direct_update.get('topic_candidate', topic_candidate),
            route_candidate=direct_update.get('route_candidate', route_candidate),
            frame_type_candidate='',
            stance_shift=direct_update.get('stance_shift', ''),
            goal_candidate=direct_update.get('goal_candidate', ''),
            transition_kind=direct_update.get('transition_kind', ''),
            slot_fill=dict(direct_update.get('slot_fill') or {}),
            classifier_metadata=dict(direct_update.get('classifier_metadata') or {}),
            confidence=float(direct_update.get('confidence', 0.0) or 0.0),
            update_source=direct_update.get('update_source', ''),
        )

    if dialogue_act in {'open_topic', 'greeting_opening', 'request_menu', 'request_conversation_feedback', 'request_psychological_portrait', 'self_diagnosis_soft'}:
        semantic_family, classifier_metadata = _resolve_semantic_family(
            question,
            dialogue_act=dialogue_act,
            state=state,
            frame=frame,
            slotish_followup=False,
        )
        if semantic_family:
            topic_candidate = semantic_family.get('topic_candidate', '') or topic_candidate
            route_candidate = semantic_family.get('route_candidate', '') or route_candidate
            stance_shift = semantic_family.get('stance_shift', '') or stance_shift
            goal_candidate = semantic_family.get('goal_candidate', '') or goal_candidate
        else:
            topic_candidate = infer_active_topic(question, route_name=state.get('active_route', '') or frame.route)
            route_candidate = state.get('active_route', '') or frame.route
        is_new_topic = True
        confidence = 0.82
    elif dialogue_act == 'topic_shift':
        semantic_family, classifier_metadata = _resolve_semantic_family(
            question,
            dialogue_act=dialogue_act,
            state=state,
            frame=frame,
            slotish_followup=False,
        )
        if semantic_family:
            topic_candidate = semantic_family.get('topic_candidate', '') or topic_candidate
            route_candidate = semantic_family.get('route_candidate', '') or route_candidate
            stance_shift = semantic_family.get('stance_shift', '') or stance_shift
            goal_candidate = semantic_family.get('goal_candidate', '') or goal_candidate
        else:
            topic_candidate = infer_active_topic(question, route_name='') or topic_candidate
            route_candidate = frame.route
        is_new_topic = True
        confidence = 0.9
    else:
        classifier_metadata = {}
    if is_new_topic:
        family_stance, family_goal = _family_stance_goal(topic_candidate)
        stance_shift = family_stance or _default_stance_for_act(dialogue_act, topic_candidate) or stance_shift
        goal_candidate = family_goal or _default_goal_for_act(dialogue_act, topic_candidate) or goal_candidate
        if (classifier_metadata or {}).get('family_classifier_status') == 'accepted':
            update_source = 'family_classifier'
    if dialogue_act in {'abstractify_previous_question', 'confirm_scope', 'request_generalization'}:
        stance_shift = 'general'
        goal_candidate = 'overview'
        confidence = 0.9
    elif dialogue_act in {'personalize_previous_question', 'reject_scope'}:
        stance_shift = 'personal'
        goal_candidate = 'clarify'
        confidence = 0.9
    elif dialogue_act == 'request_cause_list':
        goal_candidate = 'cause_list'
        confidence = 0.9
    elif dialogue_act == 'request_example':
        goal_candidate = 'example'
        confidence = 0.9
    elif dialogue_act == 'request_next_step':
        goal_candidate = 'next_step'
        confidence = 0.9
    elif dialogue_act == 'request_mini_analysis':
        goal_candidate = 'mini_analysis'
        confidence = 0.9
    elif dialogue_act in {'supply_narrowing_axis', 'supply_concrete_manifestation'}:
        goal_candidate = 'clarify'
        confidence = 0.88

    return DialogueUpdate(
        relation_to_previous=relation,
        is_new_topic=is_new_topic,
        topic_candidate=topic_candidate,
        route_candidate=route_candidate,
        frame_type_candidate='',
        stance_shift=stance_shift,
        goal_candidate=goal_candidate,
        transition_kind=transition_kind,
        slot_fill={
            'axis': selected_axis,
            'detail': selected_detail,
            'pending_slot': state.get('pending_slot', '') or frame.pending_slot,
        },
        classifier_metadata=classifier_metadata,
        confidence=confidence,
        update_source=update_source,
    )


def apply_dialogue_update(current_frame: dict | DialogueFrame | None,
                          update: dict | DialogueUpdate | None,
                          *,
                          fallback_state: dict | None = None) -> DialogueFrame:
    frame = coerce_frame(current_frame)
    if isinstance(update, DialogueUpdate):
        payload = update.as_dict()
    else:
        payload = dict(update or {})
    if isinstance(fallback_state, DialogueState):
        state = fallback_state.as_dict()
    else:
        state = dict(fallback_state or {})

    if payload.get('is_new_topic'):
        frame.topic = payload.get('topic_candidate', '') or frame.topic
        frame.route = payload.get('route_candidate', '') or state.get('active_route', '') or frame.route
        frame.frame_type = ''
        frame.axis = ''
        frame.detail = ''
        frame.pending_slot = ''
        opening = resolve_dialogue_transition(frame.topic, 'opening')
        if opening:
            frame.goal = opening.get('goal', '') or payload.get('goal_candidate', '') or frame.goal
            frame.stance = opening.get('stance', '') or payload.get('stance_shift', '') or frame.stance
            frame.pending_slot = opening.get('pending_slot', '') or frame.pending_slot
    if payload.get('stance_shift'):
        frame.stance = payload.get('stance_shift') or frame.stance
    elif payload.get('is_new_topic'):
        frame.stance = 'personal'
    if payload.get('goal_candidate'):
        frame.goal = payload.get('goal_candidate') or frame.goal
    elif payload.get('is_new_topic'):
        frame.goal = 'opening'
    frame.relation_to_previous = payload.get('relation_to_previous', '') or frame.relation_to_previous
    frame.transition_kind = payload.get('transition_kind', '') or frame.transition_kind
    slot_fill = dict(payload.get('slot_fill') or {})
    frame.axis = slot_fill.get('axis', '') or frame.axis
    frame.detail = slot_fill.get('detail', '') or frame.detail
    frame.pending_slot = slot_fill.get('pending_slot', '') or state.get('pending_slot', '') or frame.pending_slot
    frame.confidence = str(payload.get('confidence', frame.confidence) or frame.confidence)
    frame.update_source = payload.get('update_source', '') or frame.update_source

    transition_kind = payload.get('transition_kind', '') or frame.transition_kind
    if frame.topic and transition_kind and transition_kind != 'opening':
        transition = resolve_dialogue_transition(
            frame.topic,
            transition_kind,
            goal=state.get('dialogue_goal', '') or frame.goal,
            dialogue_mode=state.get('dialogue_mode', ''),
            pending_slot=state.get('pending_slot', '') or frame.pending_slot,
            abstraction_level=state.get('abstraction_level', '') or frame.stance,
        )
        if transition:
            frame.goal = transition.get('goal', '') or frame.goal
            frame.stance = transition.get('stance', '') or frame.stance
            frame.pending_slot = transition.get('pending_slot', '') or frame.pending_slot
            if transition.get('clear_axis'):
                frame.axis = ''
            if transition.get('clear_detail'):
                frame.detail = ''
            if slot_fill.get('axis', ''):
                frame.axis = slot_fill.get('axis', '')
            if slot_fill.get('detail', ''):
                frame.detail = slot_fill.get('detail', '')

    if not frame.topic:
        frame.topic = state.get('active_topic', '') or ''
    if not frame.route:
        frame.route = state.get('active_route', '') or ''
    if not frame.frame_type:
        frame.frame_type = infer_frame_type(frame.topic, frame.stance)
    return frame
