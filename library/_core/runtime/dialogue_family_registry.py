"""Data-driven dialogue frame-family registry for semantic topic inference."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DialogueRenderSpec:
    goal: str
    clarify_type: str
    profile: str
    question_kind: str
    reason_code: str
    render_kind: str = 'profile'
    response_mode: str = 'frame'
    needs_ack: bool = True
    ends_with_question: bool = False
    max_sentences: int = 4
    allow_list: bool = False
    tone_variant: str = 'jordan_concise'
    forbidden_openers: tuple[str, ...] = ()
    hard_bans: tuple[str, ...] = ()
    prompt_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DialogueTransitionSpec:
    transition: str
    from_goals: tuple[str, ...] = ()
    from_modes: tuple[str, ...] = ()
    from_pending_slots: tuple[str, ...] = ()
    from_stances: tuple[str, ...] = ()
    to_goal: str = ''
    to_mode: str = ''
    to_pending_slot: str = ''
    to_stance: str = ''
    clear_axis: bool = False
    clear_detail: bool = False


def _progression_render_specs(topic: str) -> tuple[DialogueRenderSpec, ...]:
    return (
        DialogueRenderSpec(
            goal='cause_list',
            clarify_type='human_problem',
            profile='cause-list',
            question_kind='cause_list',
            reason_code=f'{topic}-cause-list',
            render_kind='cause_list',
            max_sentences=5,
            allow_list=True,
        ),
        DialogueRenderSpec(
            goal='mini_analysis',
            clarify_type='human_problem',
            profile='mini-analysis',
            question_kind='meaning_reframe',
            reason_code=f'{topic}-mini-analysis',
            render_kind='mini_analysis',
        ),
        DialogueRenderSpec(
            goal='next_step',
            clarify_type='human_problem',
            profile='next-step',
            question_kind='practical_next_step',
            reason_code=f'{topic}-next-step',
            render_kind='next_step',
            max_sentences=4,
        ),
        DialogueRenderSpec(
            goal='example',
            clarify_type='human_problem',
            profile='example',
            question_kind='illustrative_example',
            reason_code=f'{topic}-example',
            render_kind='example',
            max_sentences=4,
        ),
    )


@dataclass(frozen=True)
class DialogueFamilySpec:
    topic: str
    route: str
    stance: str
    goal: str
    transition_specs: tuple[DialogueTransitionSpec, ...] = ()
    render_specs: tuple[DialogueRenderSpec, ...] = ()
    reframe_general_ack: str = ''
    overview_continue_ack: str = ''
    reframe_personal_ack: str = ''
    reject_scope_ack: str = ''
    opening_mode: str = 'human_problem_clarify'
    opening_pending_slot: str = 'narrowing_axis'
    reframe_general_mode: str = 'followup_reframe'
    reframe_general_pending_slot: str = 'pattern_family'
    reframe_personal_mode: str = 'human_problem_clarify'
    reframe_personal_pending_slot: str = 'narrowing_axis'
    reject_scope_mode: str = 'human_problem_clarify'
    reject_scope_pending_slot: str = 'narrowing_axis'
    cause_list_mode: str = 'cause_list'
    cause_list_pending_slot: str = 'narrowing_axis'
    axis_mode: str = 'followup_narrowing'
    axis_pending_slot: str = 'concrete_manifestation'
    detail_mode: str = 'followup_deepen'
    detail_pending_slot: str = 'analysis_focus'
    mini_analysis_mode: str = 'mini_analysis'
    mini_analysis_pending_slot: str = 'next_step'
    next_step_mode: str = 'practical_next_step'
    next_step_pending_slot: str = 'example_or_shift'
    example_mode: str = 'example_illustration'
    example_pending_slot: str = ''
    allowed_transitions: tuple[str, ...] = (
        'reframe_general',
        'reframe_personal',
        'reject_scope',
        'cause_list',
        'axis_answer',
        'detail_answer',
        'mini_analysis',
        'next_step',
        'example',
    )
    candidate_axes: tuple[str, ...] = ()
    strong_markers: tuple[str, ...] = ()
    concept_markers: tuple[str, ...] = ()
    subject_markers: tuple[str, ...] = ()
    self_markers: tuple[str, ...] = ()
    threshold: int = 2


_GOAL_BY_MODE = {
    'topic_opening': 'opening',
    'scope_clarify': 'menu',
    'human_problem_clarify': 'clarify',
    'followup_reframe': 'overview',
    'followup_narrowing': 'clarify',
    'followup_deepen': 'clarify',
    'mini_analysis': 'mini_analysis',
    'practical_next_step': 'next_step',
    'example_illustration': 'example',
    'cause_list': 'cause_list',
    'kb_answer': 'analyze',
}


def _goal_from_mode(dialogue_mode: str) -> str:
    return _GOAL_BY_MODE.get(dialogue_mode or '', 'opening')


def _default_transition_specs_for(spec: DialogueFamilySpec) -> tuple[DialogueTransitionSpec, ...]:
    specs = [
        DialogueTransitionSpec(
            transition='opening',
            to_goal=spec.goal,
            to_mode=spec.opening_mode,
            to_pending_slot=spec.opening_pending_slot,
            to_stance=spec.stance,
            clear_axis=True,
            clear_detail=True,
        ),
    ]
    if 'reframe_general' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='reframe_general',
            from_stances=('personal',),
            to_goal='overview',
            to_mode=spec.reframe_general_mode,
            to_pending_slot=spec.reframe_general_pending_slot,
            to_stance='general',
        ))
    if 'reframe_personal' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='reframe_personal',
            from_stances=('general',),
            to_goal='clarify',
            to_mode=spec.reframe_personal_mode,
            to_pending_slot=spec.reframe_personal_pending_slot,
            to_stance='personal',
            clear_axis=True,
            clear_detail=True,
        ))
    if 'reject_scope' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='reject_scope',
            from_stances=('general',),
            to_goal='clarify',
            to_mode=spec.reject_scope_mode,
            to_pending_slot=spec.reject_scope_pending_slot,
            to_stance='personal',
            clear_axis=True,
            clear_detail=True,
        ))
    if 'cause_list' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='cause_list',
            from_goals=('clarify', 'overview'),
            from_modes=tuple(mode for mode in (spec.opening_mode, spec.reframe_general_mode) if mode),
            from_pending_slots=tuple(
                slot for slot in (spec.opening_pending_slot, spec.reframe_general_pending_slot) if slot
            ),
            to_goal='cause_list',
            to_mode=spec.cause_list_mode,
            to_pending_slot=spec.cause_list_pending_slot,
        ))
    if 'axis_answer' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='axis_answer',
            from_goals=('clarify', 'overview', 'cause_list', 'next_step', 'example'),
            from_modes=tuple(
                mode
                for mode in (
                    spec.opening_mode,
                    spec.reframe_general_mode,
                    spec.cause_list_mode,
                    spec.next_step_mode,
                    spec.example_mode,
                )
                if mode
            ),
            from_pending_slots=tuple(
                slot
                for slot in (
                    spec.opening_pending_slot,
                    spec.reframe_general_pending_slot,
                    spec.cause_list_pending_slot,
                    spec.next_step_pending_slot,
                    spec.example_pending_slot,
                )
                if slot
            ),
            to_goal='clarify',
            to_mode=spec.axis_mode,
            to_pending_slot=spec.axis_pending_slot,
            clear_detail=True,
        ))
    if 'detail_answer' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='detail_answer',
            from_goals=('clarify',),
            from_modes=(spec.axis_mode,),
            from_pending_slots=(spec.axis_pending_slot,),
            to_goal='clarify',
            to_mode=spec.detail_mode,
            to_pending_slot=spec.detail_pending_slot,
        ))
    if 'mini_analysis' in spec.allowed_transitions:
        specs.append(DialogueTransitionSpec(
            transition='mini_analysis',
            from_goals=('clarify',),
            from_modes=(spec.detail_mode,),
            from_pending_slots=(spec.detail_pending_slot,),
            to_goal='mini_analysis',
            to_mode=spec.mini_analysis_mode,
            to_pending_slot=spec.mini_analysis_pending_slot,
        ))
    if 'next_step' in spec.allowed_transitions:
        specs.extend((
            DialogueTransitionSpec(
                transition='next_step',
                from_goals=('mini_analysis',),
                from_modes=(spec.mini_analysis_mode,),
                from_pending_slots=(spec.mini_analysis_pending_slot,),
                to_goal='next_step',
                to_mode=spec.next_step_mode,
                to_pending_slot=spec.next_step_pending_slot,
            ),
            DialogueTransitionSpec(
                transition='next_step',
                from_goals=('cause_list',),
                from_modes=(spec.cause_list_mode,),
                to_goal='next_step',
                to_mode=spec.next_step_mode,
                to_pending_slot=spec.next_step_pending_slot,
            ),
            DialogueTransitionSpec(
                transition='next_step',
                from_goals=('clarify',),
                from_modes=tuple(mode for mode in (spec.axis_mode, spec.detail_mode) if mode),
                from_pending_slots=tuple(slot for slot in (spec.axis_pending_slot, spec.detail_pending_slot) if slot),
                to_goal='next_step',
                to_mode=spec.next_step_mode,
                to_pending_slot=spec.next_step_pending_slot,
            ),
        ))
    if 'example' in spec.allowed_transitions:
        specs.extend((
            DialogueTransitionSpec(
                transition='example',
                from_goals=('next_step',),
                from_modes=(spec.next_step_mode,),
                from_pending_slots=(spec.next_step_pending_slot,),
                to_goal='example',
                to_mode=spec.example_mode,
                to_pending_slot=spec.example_pending_slot,
            ),
            DialogueTransitionSpec(
                transition='example',
                from_goals=('cause_list',),
                from_modes=(spec.cause_list_mode,),
                to_goal='example',
                to_mode=spec.example_mode,
                to_pending_slot=spec.example_pending_slot,
            ),
        ))
    return tuple(specs)


def _iter_transition_specs(spec: DialogueFamilySpec) -> tuple[DialogueTransitionSpec, ...]:
    return spec.transition_specs or _default_transition_specs_for(spec)


DIALOGUE_FAMILY_REGISTRY: tuple[DialogueFamilySpec, ...] = (
    DialogueFamilySpec(
        topic='greeting',
        route='general',
        stance='general',
        goal='opening',
        render_specs=(
            DialogueRenderSpec(
                goal='opening',
                clarify_type='scope',
                profile='greeting-opening',
                question_kind='topic_selection',
                reason_code='greeting-opening',
            ),
        ),
        opening_mode='topic_opening',
        opening_pending_slot='',
        allowed_transitions=('opening',),
        strong_markers=('привет', 'здарова', 'здорова', 'салют', 'здравствуйте', 'добрый вечер', 'добрый день', 'доброе утро'),
        concept_markers=('здравств', 'добрый', 'доброе', 'здаров', 'салют'),
        subject_markers=('питерсон', 'доктор', 'джордан'),
        threshold=2,
    ),
    DialogueFamilySpec(
        topic='social-small-talk',
        route='general',
        stance='general',
        goal='opening',
        render_specs=(
            DialogueRenderSpec(
                goal='opening',
                clarify_type='scope',
                profile='social-small-talk',
                question_kind='topic_selection',
                reason_code='social-small-talk',
            ),
        ),
        opening_mode='topic_opening',
        opening_pending_slot='',
        allowed_transitions=('opening',),
        strong_markers=(
            'как ваши дела',
            'как у вас дела',
            'как дела',
            'шо ты как ты',
            'я тут',
            'я здесь',
            'я тебе пишу сообщение',
            'проверяем рендерер',
            'проверка связи',
            'рас два рас два',
            'джордан...',
            'на связи',
            'вечерочек',
            'добрейши вечерочек',
        ),
        concept_markers=('дела', 'на связи', 'тут', 'здесь', 'вечероч', 'вечерочек', 'рендерер', 'проверя', 'сообщение', 'связь'),
        subject_markers=('как', 'вы', 'ты', 'джордан', 'пишу'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='how-to-address',
        route='general',
        stance='general',
        goal='opening',
        render_specs=(
            DialogueRenderSpec(
                goal='opening',
                clarify_type='scope',
                profile='how-to-address',
                question_kind='topic_selection',
                reason_code='how-to-address',
            ),
        ),
        opening_mode='topic_opening',
        opening_pending_slot='',
        allowed_transitions=('opening',),
        strong_markers=('как к вам обращаться', 'как вас называть', 'как мне к вам обращаться', 'как к тебе обращаться', 'как тебя называть'),
        concept_markers=('обращаться', 'называть'),
        subject_markers=('к вам', 'к тебе', 'вас', 'тебя'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='problem-sharing-opening',
        route='general',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='problem-sharing-opening',
                question_kind='topic_selection',
                reason_code='problem-sharing-opening',
            ),
        ),
        opening_mode='human_problem_clarify',
        opening_pending_slot='topic_selection',
        allowed_transitions=('opening',),
        strong_markers=('я хочу поделиться', 'у меня есть некоторые проблемы', 'мне нужно выговориться', 'мне нужно поделиться'),
        concept_markers=('поделиться', 'выговориться', 'рассказать', 'поговорить'),
        subject_markers=('проблем', 'болит', 'есть', 'хочу'),
        self_markers=('у меня', 'мне', 'я '),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='life-direction-opening',
        route='career-vocation',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='life-direction-opening',
                question_kind='narrowing',
                reason_code='life-direction-opening',
            ),
        ) + _progression_render_specs('life-direction-opening'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('direction', 'discipline', 'relationships', 'self_respect', 'burden'),
        strong_markers=('как мне дальше жить', 'как изменить жизнь', 'как изменить свою жизнь', 'как жить дальше'),
        concept_markers=('как жить', 'жить дальше', 'изменить жизнь', 'изменить свою жизнь'),
        subject_markers=('жить', 'жизн', 'дальше', 'изменить'),
        self_markers=('мне', 'мою', 'свою', 'я '),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='appearance-self-presentation',
        route='general',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='appearance-self-presentation',
                question_kind='narrowing',
                reason_code='appearance-self-presentation',
            ),
        ) + _progression_render_specs('appearance-self-presentation'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('body', 'style', 'confidence', 'discipline', 'social_presence'),
        strong_markers=(
            'как стать красивым',
            'как стать красивой',
            'как стать привлекательным',
            'как стать привлекательной',
        ),
        concept_markers=('красив', 'привлекатель', 'внешн', 'выгляде', 'презентац'),
        subject_markers=('стать', 'быть', 'выглядеть'),
        self_markers=('мне', 'я ', 'себя'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='relationship-loss-of-feeling',
        route='relationship-maintenance',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='relationship-knot',
                question_kind='narrowing',
                reason_code='relationship-knot',
            ),
            DialogueRenderSpec(
                goal='overview',
                clarify_type='scope',
                profile='abstractify-relationship-loss-of-feeling',
                question_kind='topic_variant',
                reason_code='abstractify-relationship-loss-of-feeling',
            ),
        ) + _progression_render_specs('relationship-loss-of-feeling'),
        reframe_general_ack='Хорошо, значит речь теперь не о твоём частном случае, а о самой структуре этой проблемы.',
        overview_continue_ack='Хорошо, держим этот разговор в общем виде и не сваливаемся обратно в частную историю.',
        reframe_personal_ack='Хорошо, тогда вернём разговор от общей схемы к тебе лично и посмотрим, где этот узел бьёт по твоей жизни.',
        reject_scope_ack='Хорошо, тогда уберём общую рамку и вернёмся к одному живому узлу, который у тебя действительно болит.',
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('resentment', 'coldness', 'loss_of_desire', 'loss_of_respect', 'unspoken_conflict'),
        strong_markers=('потеря чувств', 'потери чувств', 'чувства прошли', 'прошли чувства'),
        concept_markers=('потеря', 'пропали', 'ушли', 'исчезли', 'остыл', 'остыла'),
        subject_markers=('чувств', 'любов', 'желани', 'близост'),
        self_markers=('отношен', 'браке', 'браку', 'в паре'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='relationship-foundations',
        route='relationship-maintenance',
        stance='general',
        goal='overview',
        render_specs=(
            DialogueRenderSpec(
                goal='overview',
                clarify_type='scope',
                profile='relationship-foundations-overview',
                question_kind='topic_variant',
                reason_code='relationship-foundations-overview',
            ),
        ) + _progression_render_specs('relationship-foundations'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='pattern_family',
        example_pending_slot='pattern_family',
        allowed_transitions=(
            'reframe_personal',
            'reject_scope',
            'cause_list',
            'axis_answer',
            'detail_answer',
            'mini_analysis',
            'next_step',
            'example',
        ),
        candidate_axes=('truth', 'respect', 'shared_burden', 'desire', 'repair'),
        strong_markers=('крепкий брак', 'крепкие отношения', 'здоровые отношения', 'что делает отношения крепкими'),
        concept_markers=('смысл', 'суть', 'основа', 'держится', 'строится', 'делает крепкими', 'удерживает', 'крепкими'),
        subject_markers=('отношен', 'брак', 'союз', 'пара', 'любов'),
        threshold=2,
    ),
    DialogueFamilySpec(
        topic='lost-and-aimless',
        route='career-vocation',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='lost-and-aimless',
                question_kind='narrowing',
                reason_code='lost-and-aimless',
            ),
        ) + _progression_render_specs('lost-and-aimless'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('meaninglessness', 'drift', 'burden_avoidance', 'fear_of_choice', 'structure_decay'),
        strong_markers=('потерял смысл и направление', 'потеряла смысл и направление', 'я потерялся', 'я потерялась'),
        concept_markers=('не понимаю', 'потерял', 'потеряла', 'застрял', 'застряла', 'куда', 'зачем', 'ради чего'),
        subject_markers=('смысл', 'направлен', 'идти', 'двигаться', 'жить', 'дальше'),
        self_markers=('я ', 'мне ', 'у меня'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='scope-topics',
        route='general',
        stance='general',
        goal='menu',
        render_specs=(
            DialogueRenderSpec(
                goal='menu',
                clarify_type='scope',
                profile='scope-topics',
                question_kind='topic_selection',
                reason_code='scope-topics',
            ),
        ),
        opening_mode='scope_clarify',
        opening_pending_slot='topic_selection',
        allowed_transitions=('opening',),
        strong_markers=('о чем с тобой можно поговорить', 'о чём с тобой можно поговорить', 'а что есть в базе?', 'что есть в базе'),
        concept_markers=('о чем', 'о чём', 'какие темы', 'какие вопросы', 'что мы можем', 'что можно', 'что есть'),
        subject_markers=('поговорить', 'обсудить', 'разобрать', 'говорить', 'база', 'в базе'),
        self_markers=('с тобой', 'ты', 'у тебя'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='conversation-feedback',
        route='general',
        stance='personal',
        goal='menu',
        render_specs=(
            DialogueRenderSpec(
                goal='menu',
                clarify_type='scope',
                profile='conversation-feedback',
                question_kind='topic_selection',
                reason_code='conversation-feedback',
            ),
        ),
        opening_mode='scope_clarify',
        opening_pending_slot='topic_selection',
        allowed_transitions=('opening',),
        strong_markers=('ты задаёшь слишком много вопросов', 'не задавай столько вопросов'),
        concept_markers=('слишком много', 'меньше вопросов', 'не задавай столько'),
        subject_markers=('вопрос', 'спрашиваешь', 'задаёшь'),
        self_markers=('ты ',),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='self-evaluation',
        route='general',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='self-evaluation-request',
                question_kind='pattern_selection',
                reason_code='self-evaluation-request',
            ),
        ) + _progression_render_specs('self-evaluation'),
        reframe_personal_ack='Хорошо, тогда отойдём от общей самокритики и посмотрим, где именно этот паттерн бьёт по твоей жизни на практике.',
        opening_mode='human_problem_clarify',
        opening_pending_slot='pattern_selection',
        candidate_axes=('discipline', 'closeness', 'resentment', 'avoidance', 'self_deception'),
        strong_markers=('что со мной не так', 'почему я всё порчу', 'почему я все порчу'),
        concept_markers=('что со мной', 'почему я', 'какой я', 'кто я', 'что я за'),
        subject_markers=('не так', 'порчу', 'ломаю', 'человек', 'такой', 'такая', 'всё ломаю', 'все ломаю'),
        self_markers=('я ', 'мной', 'мне', 'себе'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='shame-self-contempt',
        route='shame-self-contempt',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='shame-self-contempt-request',
                question_kind='narrowing',
                reason_code='shame-self-contempt-request',
            ),
        ) + _progression_render_specs('shame-self-contempt'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('humiliation', 'exposure', 'failure', 'self_condemnation', 'resentment'),
        strong_markers=('мне стыдно за себя', 'я себя ненавижу', 'ненавижу себя'),
        concept_markers=('стыд', 'позор', 'ненавижу', 'омерз', 'противно', 'отвращение', 'мерз'),
        subject_markers=('за себя', 'себя', 'себе'),
        self_markers=('я ', 'мне ', 'себя', 'себе'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='resentment-conflict',
        route='resentment',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='resentment-buildup',
                question_kind='narrowing',
                reason_code='resentment-buildup',
            ),
        ) + _progression_render_specs('resentment-conflict'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('toward_other', 'toward_self', 'cowardice_before_truth', 'chronic_scorekeeping'),
        strong_markers=('я коплю обиду', 'копится обида', 'я в обиде', 'я не могу отпустить обиду'),
        concept_markers=('обид', 'горечь', 'злюсь', 'злость', 'раздраж', 'счёт'),
        subject_markers=('на него', 'на нее', 'на неё', 'на себя', 'на них', 'внутри'),
        self_markers=('я ', 'мне ', 'у меня'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='self-deception',
        route='self-deception',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='self-deception',
                question_kind='narrowing',
                reason_code='self-deception',
            ),
        ) + _progression_render_specs('self-deception'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('motives', 'relationships', 'values', 'goals', 'self_image'),
        strong_markers=('я обманываю себя', 'я вру себе', 'я себе вру'),
        concept_markers=('самообман', 'лгу', 'вру', 'обманываю', 'не хочу признавать'),
        subject_markers=('себе', 'с собой', 'мотив', 'ценност', 'правд'),
        self_markers=('я ', 'мне ', 'себе'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='fear-and-price',
        route='fear-value',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='fear-and-price',
                question_kind='narrowing',
                reason_code='fear-and-price',
            ),
        ) + _progression_render_specs('fear-and-price'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('approval', 'safety', 'power', 'identity', 'loss'),
        strong_markers=('я боюсь сделать шаг', 'мне страшно сделать шаг', 'я боюсь потерять'),
        concept_markers=('боюсь', 'страшно', 'страх', 'тревож', 'цена'),
        subject_markers=('потерять', 'лишиться', 'одобрения', 'безопасности', 'идентичности'),
        self_markers=('я ', 'мне ', 'меня'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='loneliness-rejection',
        route='relationship-maintenance',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='loneliness-rejection',
                question_kind='narrowing',
                reason_code='loneliness-rejection',
            ),
        ) + _progression_render_specs('loneliness-rejection'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('abandonment', 'invisibility', 'humiliation', 'emotional_distance', 'not_chosen'),
        strong_markers=('я никому не нужен', 'я никому не нужна', 'меня не выбирают', 'я совсем один', 'я совсем одна'),
        concept_markers=('один', 'одна', 'одиноч', 'отверж', 'не выбирают', 'не нужен', 'не нужна'),
        subject_markers=('никому', 'меня', 'со мной', 'рядом'),
        self_markers=('я ', 'мне ', 'меня'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='parenting-boundaries',
        route='parenting-overprotection',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='parenting-boundaries',
                question_kind='narrowing',
                reason_code='parenting-boundaries',
            ),
        ) + _progression_render_specs('parenting-boundaries'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('child_behavior', 'parent_guilt', 'fear_of_reality', 'softness_without_structure'),
        strong_markers=('мой ребенок не слушается', 'мой ребёнок не слушается', 'я слишком мягок с ребенком', 'я слишком мягкая с ребенком'),
        concept_markers=('ребен', 'ребён', 'воспитан', 'границ', 'избал', 'мягк'),
        subject_markers=('сын', 'дочь', 'дет', 'ребёнок', 'ребенок'),
        self_markers=('мой', 'моя', 'я ', 'мне '),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='tragedy-bitterness',
        route='tragedy-suffering',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='tragedy-and-bitterness',
                question_kind='narrowing',
                reason_code='tragedy-and-bitterness',
            ),
        ) + _progression_render_specs('tragedy-bitterness'),
        opening_mode='human_problem_clarify',
        opening_pending_slot='narrowing_axis',
        candidate_axes=('loss', 'fear', 'injustice', 'bitterness', 'despair'),
        strong_markers=('я озлобился после потери', 'я озлобилась после потери', 'меня ломает утрата', 'я не могу пережить утрату'),
        concept_markers=('утрат', 'страдан', 'горе', 'озлоб', 'горечь', 'несправедлив'),
        subject_markers=('после', 'из-за', 'потери', 'боли'),
        self_markers=('я ', 'мне ', 'меня'),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='self-diagnosis',
        route='general',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='self-diagnosis-soft',
                question_kind='symptom_narrowing',
                reason_code='self-diagnosis-soft',
            ),
        ) + _progression_render_specs('self-diagnosis'),
        reframe_personal_ack='Хорошо, тогда вернёмся от общей картины к твоему личному опыту и посмотрим, что именно у тебя рушится изнутри.',
        opening_mode='human_problem_clarify',
        opening_pending_slot='symptom_narrowing',
        candidate_axes=('emotional_flatness', 'loss_of_interest', 'exhaustion', 'social_disconnection', 'loss_of_aim'),
        strong_markers=('я подозреваю, что у меня', 'кажется, что у меня', 'похоже, что у меня'),
        concept_markers=('подозреваю', 'кажется', 'похоже', 'думаю'),
        subject_markers=('ангедон', 'депресс', 'диагноз', 'расстройств', 'синдром'),
        self_markers=('у меня', 'мне', 'я '),
        threshold=3,
    ),
    DialogueFamilySpec(
        topic='psychological-portrait',
        route='general',
        stance='personal',
        goal='clarify',
        render_specs=(
            DialogueRenderSpec(
                goal='clarify',
                clarify_type='human_problem',
                profile='psychological-portrait-request',
                question_kind='pattern_selection',
                reason_code='psychological-portrait-request',
            ),
        ) + _progression_render_specs('psychological-portrait'),
        reframe_personal_ack='Хорошо, тогда вернёмся от общей схемы характера к тебе лично и посмотрим, где этот паттерн портит твою жизнь на практике.',
        opening_mode='human_problem_clarify',
        opening_pending_slot='pattern_selection',
        candidate_axes=('discipline', 'closeness', 'resentment', 'avoidance', 'self_deception'),
        strong_markers=('психологический портрет', 'разбери мой характер'),
        concept_markers=('портрет', 'характер', 'разбери'),
        subject_markers=('мой', 'меня', 'человека'),
        self_markers=('я ', 'мой', 'меня'),
        threshold=3,
    ),
)


def normalize_dialogue_text(text: str) -> str:
    return ' '.join((text or '').lower().split())


def dialogue_contains_any(text: str, markers: tuple[str, ...] | list[str]) -> bool:
    return any(marker in text for marker in markers)


def score_dialogue_family(text: str, spec: DialogueFamilySpec) -> int:
    score = 0
    if spec.strong_markers and dialogue_contains_any(text, spec.strong_markers):
        score += 3
    if spec.concept_markers and dialogue_contains_any(text, spec.concept_markers):
        score += 1
    if spec.subject_markers and dialogue_contains_any(text, spec.subject_markers):
        score += 1
    if spec.self_markers and dialogue_contains_any(text, spec.self_markers):
        score += 1
    return score


def build_dialogue_family_candidates(question: str,
                                     *,
                                     route_name: str = '',
                                     active_topic: str = '',
                                     limit: int = 5) -> list[dict]:
    q = normalize_dialogue_text(question)
    if not q:
        return []

    scored: list[tuple[int, DialogueFamilySpec]] = []
    for spec in DIALOGUE_FAMILY_REGISTRY:
        score = score_dialogue_family(q, spec)
        if score > 0:
            scored.append((score, spec))

    scored.sort(key=lambda item: item[0], reverse=True)
    candidates: list[dict] = []
    seen_topics: set[str] = set()
    if scored:
        best_score = scored[0][0]
        minimum_score = max(1, best_score - 1)
        for score, spec in scored:
            if score < minimum_score and score < spec.threshold:
                continue
            if spec.topic in seen_topics:
                continue
            candidates.append({
                'topic_candidate': spec.topic,
                'route_candidate': spec.route,
                'stance_shift': spec.stance,
                'goal_candidate': spec.goal,
                'score': score,
                'threshold': spec.threshold,
                'description': (
                    f'route={spec.route}; stance={spec.stance}; goal={spec.goal}; '
                    f'opening_mode={spec.opening_mode}'
                ),
            })
            seen_topics.add(spec.topic)
            if len(candidates) >= limit:
                return candidates

    fallback_routes = [route_name, active_topic]
    for fallback_route in fallback_routes:
        if not fallback_route:
            continue
        for spec in DIALOGUE_FAMILY_REGISTRY:
            if spec.topic in seen_topics:
                continue
            if spec.route != fallback_route and spec.topic != fallback_route:
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
            if len(candidates) >= limit:
                return candidates

    return candidates


def infer_dialogue_family(question: str) -> dict:
    candidates = build_dialogue_family_candidates(question)
    if not candidates:
        return {}

    qualified_candidates: list[dict] = []
    for candidate in candidates:
        topic = str(candidate.get('topic_candidate') or '')
        spec = get_dialogue_family_spec(topic)
        if spec is None:
            continue
        score = int(candidate.get('score', 0) or 0)
        if score < spec.threshold:
            continue
        qualified_candidates.append(candidate)

    if not qualified_candidates:
        return {}

    best = qualified_candidates[0]
    best_score = int(best.get('score', 0) or 0)
    second_score = int(qualified_candidates[1].get('score', 0) or 0) if len(qualified_candidates) > 1 else 0
    best_topic = str(best.get('topic_candidate') or '')
    best_spec = get_dialogue_family_spec(best_topic)
    if best_spec is None:
        return {}
    if best_score < best_spec.threshold:
        return {}
    if second_score and best_score - second_score < 1:
        return {}

    confidence = min(0.95, 0.72 + (0.05 * best_score))
    return {
        'topic_candidate': best_spec.topic,
        'route_candidate': best_spec.route,
        'stance_shift': best_spec.stance,
        'goal_candidate': best_spec.goal,
        'confidence': confidence,
    }


def get_dialogue_family_spec(topic: str) -> DialogueFamilySpec | None:
    for spec in DIALOGUE_FAMILY_REGISTRY:
        if spec.topic == topic:
            return spec
    return None


def get_dialogue_transition_hints(topic: str, transition: str) -> dict:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return {}
    for transition_spec in _iter_transition_specs(spec):
        if transition_spec.transition != transition:
            continue
        return {
            'goal': transition_spec.to_goal,
            'dialogue_mode': transition_spec.to_mode,
            'pending_slot': transition_spec.to_pending_slot,
            'stance': transition_spec.to_stance,
            'clear_axis': transition_spec.clear_axis,
            'clear_detail': transition_spec.clear_detail,
        }
    return {}


def resolve_dialogue_transition(topic: str,
                                transition: str,
                                *,
                                goal: str = '',
                                dialogue_mode: str = '',
                                pending_slot: str = '',
                                abstraction_level: str = '') -> dict:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return {}
    current_goal = goal or _goal_from_mode(dialogue_mode)
    for transition_spec in _iter_transition_specs(spec):
        if transition_spec.transition != transition:
            continue
        if transition_spec.from_goals and current_goal not in transition_spec.from_goals:
            continue
        if transition_spec.from_modes and dialogue_mode not in transition_spec.from_modes:
            continue
        if transition_spec.from_pending_slots and pending_slot not in transition_spec.from_pending_slots:
            continue
        if transition_spec.from_stances and abstraction_level not in transition_spec.from_stances:
            continue
        return {
            'transition': transition,
            'goal': transition_spec.to_goal or current_goal,
            'dialogue_mode': transition_spec.to_mode or dialogue_mode,
            'pending_slot': transition_spec.to_pending_slot,
            'stance': transition_spec.to_stance or abstraction_level,
            'clear_axis': transition_spec.clear_axis,
            'clear_detail': transition_spec.clear_detail,
        }
    return {}


def is_dialogue_transition_allowed(topic: str,
                                   transition: str,
                                   *,
                                   goal: str = '',
                                   dialogue_mode: str = '',
                                   pending_slot: str = '',
                                   abstraction_level: str = '') -> bool:
    return bool(resolve_dialogue_transition(
        topic,
        transition,
        goal=goal,
        dialogue_mode=dialogue_mode,
        pending_slot=pending_slot,
        abstraction_level=abstraction_level,
    ))


def get_dialogue_render_hints(topic: str, goal: str) -> dict:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return {}
    for render_spec in spec.render_specs:
        if render_spec.goal == goal:
            default_question = render_spec.render_kind in {'profile', 'axis_followup', 'detail_followup'}
            if render_spec.question_kind in {'topic_selection', 'narrowing', 'pattern_selection', 'symptom_narrowing', 'topic_variant', 'concrete_manifestation'}:
                default_question = True
            return {
                'render_kind': render_spec.render_kind,
                'clarify_type': render_spec.clarify_type,
                'profile': render_spec.profile,
                'template_id': f'{render_spec.profile}.v1',
                'question_kind': render_spec.question_kind,
                'reason_code': render_spec.reason_code,
                'response_mode': render_spec.response_mode,
                'renderer_hints': {
                    'needs_ack': render_spec.needs_ack,
                    'ends_with_question': render_spec.ends_with_question or default_question,
                    'max_sentences': render_spec.max_sentences,
                    'allow_list': render_spec.allow_list,
                    'tone_variant': render_spec.tone_variant,
                    'forbidden_openers': list(render_spec.forbidden_openers or ('хорошо', 'хорошо,', 'хорошо.')),
                    'hard_bans': list(render_spec.hard_bans or (
                        'цитат', 'цитата', 'книга', 'книг', 'источник',
                        'источники', 'подкаст', 'лекци', 'resentment',
                    )),
                    'prompt_notes': list(render_spec.prompt_notes),
                },
            }
    return {}


def get_dialogue_acknowledgement_hint(*,
                                      topic: str,
                                      relation: str,
                                      goal: str,
                                      stance: str,
                                      has_detail: bool = False,
                                      dialogue_act: str = '') -> str:
    def _sentence_case(text: str) -> str:
        if not text:
            return ''
        return text[:1].upper() + text[1:]

    def _vary_prefix(text: str) -> str:
        if not text:
            return ''
        normalized = text
        for prefix in ('Хорошо, ', 'Хорошо. ', 'Хорошо '):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        variants_map = {
            ('shift', ''): ('Оставим прежний узел и возьмём новый вопрос как отдельную тему.',),
            ('answer_slot', 'clarify'): (
                'Значит, держим именно этот слой проблемы.',
                'Тогда не разбрасываемся и остаёмся внутри этого слоя.',
            ),
            ('answer_slot_detail', 'clarify'): (
                'Теперь узел уже достаточно сузился, чтобы не ходить кругами вокруг общего симптома.',
                'Теперь тема уже сузилась настолько, что можно удерживать именно этот слой.',
            ),
            ('continue', 'cause_list'): (
                'Тогда разложим тему по главным причинам.',
                'Значит, полезнее разложить тему по главным линиям, чем держать её туманной.',
            ),
            ('continue', 'next_step'): (
                'Тогда переведём это в один честный следующий шаг.',
                'Значит, пора не расширять тему, а перевести её в действие.',
            ),
            ('continue', 'example'): (
                'Тогда посмотрим, как этот узел выглядит в живом примере.',
                'Значит, не останемся на уровне схемы и возьмём живой пример.',
            ),
            ('continue', 'mini_analysis'): (
                'Если держаться именно этого узла, уже можно понять, что он делает с человеком.',
                'Раз тема уже сузилась, можно не только уточнять, но и понять её внутреннюю механику.',
            ),
        }
        key = ('answer_slot_detail', goal) if relation == 'answer_slot' and has_detail else (relation, goal)
        variants = variants_map.get(key)
        if not variants:
            return _sentence_case(normalized)
        seed = sum(ord(ch) for ch in f'{topic}:{relation}:{goal}:{stance}')
        return _sentence_case(variants[seed % len(variants)])

    spec = get_dialogue_family_spec(topic)

    if relation == 'shift':
        return _vary_prefix('Хорошо, оставим прежний узел и возьмём новый вопрос как отдельную тему.')

    if dialogue_act == 'reject_scope':
        if spec and spec.reject_scope_ack:
            return _vary_prefix(spec.reject_scope_ack)
        return 'Тогда уберём общую рамку и вернёмся к одному живому узлу, который у тебя действительно болит.'

    if relation == 'reframe' and stance == 'general':
        if spec and spec.reframe_general_ack:
            return _vary_prefix(spec.reframe_general_ack)

    if relation == 'continue' and stance == 'general' and goal == 'overview':
        if spec and spec.overview_continue_ack:
            return _vary_prefix(spec.overview_continue_ack)

    if relation == 'reframe' and stance == 'personal':
        if spec and spec.reframe_personal_ack:
            return _vary_prefix(spec.reframe_personal_ack)

    if relation == 'answer_slot' and goal == 'clarify' and not has_detail:
        return _vary_prefix('Хорошо, значит не разбрасываемся и держим именно этот слой проблемы.')

    if relation == 'answer_slot' and goal == 'clarify' and has_detail:
        return _vary_prefix('Хорошо, теперь узел уже достаточно сузился, чтобы не ходить кругами вокруг общего симптома.')

    if goal == 'mini_analysis':
        return _vary_prefix('Хорошо, если держаться именно этого узла, уже можно не только сужать, но и понять, что он делает с человеком.')

    if goal == 'next_step':
        return _vary_prefix('Хорошо, тогда не будем снова расширять тему, а попробуем перевести её в один честный следующий шаг.')

    if goal == 'example':
        return _vary_prefix('Хорошо, тогда не останемся на уровне схемы, а посмотрим, как этот узел выглядит в живом примере.')

    if goal == 'cause_list':
        return _vary_prefix('Хорошо, тогда не будем блуждать вокруг темы, а разложим по главным причинам.')

    return ''
