"""Human-problem clarification profiles for in-domain but weakly grounded asks."""
from __future__ import annotations

from dataclasses import dataclass, field

from library._core.kb.voice_patterns import load_profile_voice_bundle
from library._core.runtime.dialogue_family_registry import get_dialogue_acknowledgement_hint
from library._core.runtime.dialogue_frame_renderer import plan_act_fallback_render, plan_frame_render
from library._core.runtime.routes import infer_route


@dataclass
class ClarificationResult:
    text: str
    metadata: dict = field(default_factory=dict)


_ROUTE_THEMES = {
    'relationship-maintenance': 'relationship/intimacy',
    'career-vocation': 'meaning/direction',
    'shame-self-contempt': 'shame/self-contempt',
    'resentment': 'resentment/conflict',
    'avoidance-paralysis': 'avoidance/paralysis',
    'tragedy-suffering': 'tragedy/suffering',
    'self-deception': 'truth/self-deception',
    'fear-value': 'fear/value',
    'parenting-overprotection': 'parenting/boundaries',
}

_HUMAN_PROBLEM_ROUTES = set(_ROUTE_THEMES)

_SOURCE_LOOKUP_MARKERS = [
    'цитат', 'книг', 'книга', 'лекц', 'подкаст', 'где он говорит',
    'в каком месте', 'в какой главе', 'в какой книге', 'какая цитата',
    'какой тезис', 'which quote', 'which book', 'where did he say',
]

_SCOPE_PROBE_MARKERS = [
    'о чем можно поговорить', 'о чём можно поговорить',
    'на что в базе есть опора', 'что можно разобрать',
    'какие темы', 'на какие темы', 'с чем к тебе можно',
]

_PORTRAIT_REQUEST_MARKERS = [
    'психологический портрет',
    'мой портрет',
    'разбери мой характер',
]

_SELF_DIAGNOSIS_REQUEST_MARKERS = [
    'у меня ангедония',
    'подозреваю, что у меня',
    'кажется, что у меня',
    'похоже, что у меня',
]

_ABSTRACT_FOLLOWUP_MARKERS = [
    'абстрактно', 'абстрактный', 'в общем', 'в целом',
    'не конкретно у меня', 'не про меня', 'вообще, не про меня',
]

_RELATIONSHIP_SCOPE_MARKERS = [
    'сексуальные проблемы', 'sexual problems', 'sexual issue',
    'разбираешь сексуальные', 'про секс', 'про сексуальность',
]

_SEXUAL_REJECTION_MARKERS = [
    'не занимается со мной сексом', 'не занимается сексом',
    'не хочет секса', 'не хочет меня', 'не даёт', 'не дает',
    'нет близости', 'не тянет ко мне', 'меня не хотят',
    'меня больше не выбирают', 'отвергает', 'sexual rejection',
]

_DESIRE_MISMATCH_MARKERS = [
    'я хочу секса', 'хочу секса, а', 'разный уровень желания',
    'разное желание', 'разный темперамент', 'не совпадает желание',
    'желание не совпадает', 'работает круглосуточно',
]

_RESENTMENT_AND_SILENCE_MARKERS = [
    'не разговаривает', 'молчит', 'холодн', 'отдалился', 'отдалилась',
    'постоянно ссоримся', 'мы ссоримся', 'обид', 'накопилась злость',
    'невысказан', 'замалчиваем', 'silent resentment',
]

_LOST_AND_AIMLESS_MARKERS = [
    'потерялся', 'потерялась', 'потерял смысл', 'нет направления',
    'не понимаю, что делать', 'не понимаю что делать', 'нет цели',
    'нет структуры', 'не знаю куда идти', 'запутался',
]

_SHAME_MARKERS = [
    'стыд', 'позор', 'ненавижу себя', 'отвращение к себе', 'мерзок себе',
    'не могу простить себя',
]

_RESENTMENT_MARKERS = [
    'обид', 'горечь', 'несправедливо', 'злюсь', 'злость',
]

_AVOIDANCE_MARKERS = [
    'не могу начать', 'откладываю', 'прокраст', 'паралич', 'избегаю',
]

_SELF_DECEPTION_MARKERS = [
    'вру себе', 'самообман', 'лгу себе', 'честно с собой',
]

_FEAR_MARKERS = [
    'боюсь', 'страшно', 'страх', 'цена', 'готов платить',
]

_PARENTING_MARKERS = [
    'ребенок', 'ребёнок', 'дети', 'воспитание', 'родитель',
]

_TRAGEDY_MARKERS = [
    'утрата', 'потеря', 'страдание', 'горе', 'трагедия',
]


_PROFILE_SPECS = {
    'scope-sexual-problems': {
        'opening': 'Да, если вопрос не о технике и не о потребительских советах.',
        'moves': ('selection-sees-investment',),
        'framing_moves': ('sexual-domain-is-about-investment-risk-and-choice',),
        'narrowing_moves': ('narrow-sexual-scope-to-one-knot',),
        'fallback_voice': (
            'В такой области важнее не ярлык и не теория, а реальный паттерн выбора, вложения, отказа, стыда и близости.',
        ),
        'question_lead': 'Не пытайся решить всё сразу.',
        'question': 'Назови один узел, который у тебя сейчас действительно разрушает порядок.',
        'question_kind': 'topic_selection',
    },
    'sexual-rejection': {
        'opening': 'Если такая боль возвращается снова и снова, не стоит делать вид, будто речь только о сексе как таковом.',
        'moves': ('beneath-trigger', 'state-your-limit-plainly'),
        'framing_moves': ('rejection-threatens-dignity-and-bond',),
        'narrowing_moves': ('narrow-rejection-to-core-pain',),
        'fallback_profiles': ('relationship-knot', 'desire-mismatch', 'resentment-and-silence'),
        'fallback_voice': (
            'Когда в паре исчезает близость, под этим обычно уже лежат обида, отвержение или правда, которую никто не хочет произнести.',
        ),
        'question_lead': 'Скажи без украшений:',
        'question': 'что здесь больнее всего — отвержение, унижение, злость или страх, что связь уже начала распадаться?',
        'question_kind': 'narrowing',
    },
    'desire-mismatch': {
        'opening': 'Разный уровень желания редко бывает просто технической нестыковкой.',
        'moves': ('difference-becomes-chronic-conflict', 'state-your-limit-plainly'),
        'framing_moves': ('mismatch-is-structural-not-technical',),
        'narrowing_moves': ('narrow-mismatch-to-primary-loss',),
        'fallback_profiles': ('relationship-knot',),
        'fallback_voice': (
            'Обычно это значит, что порядок между близостью, усталостью, обязанностью и правдой уже нарушен.',
        ),
        'question_lead': 'Назови одну вещь прямо:',
        'question': 'ты больше страдаешь от телесного голода, эмоционального отдаления или от того, что тебя всё время ставят после всего остального?',
        'question_kind': 'narrowing',
    },
    'resentment-and-silence': {
        'opening': 'Если вы всё время срываетесь из-за поверхностного повода, значит под ним уже лежит более старый узел.',
        'moves': ('not-about-winning', 'humility-before-pride'),
        'fallback_profiles': ('relationship-knot',),
        'fallback_voice': (
            'Чаще всего это накопленная обида, старая рана или правда, которую никто не хочет сформулировать прямо.',
        ),
        'question_lead': 'И цель здесь не в том, чтобы доказать свою правоту.',
        'question': 'Скажи без украшений: там сейчас больше обиды, недоверия, утраты уважения или страха перед прямым разговором?',
        'question_kind': 'narrowing',
    },
    'relationship-knot': {
        'opening': 'Одного симптома в отношениях почти никогда не достаточно.',
        'moves': ('beneath-trigger', 'marriage-is-constructive-wrestling'),
        'fallback_voice': (
            'Если узел живёт долго, дело уже не в последнем эпизоде, а в повторяющемся паттерне, который никто не назвал как следует.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'здесь главнее обида, холод, утрата желания, ревность или ощущение, что тебя больше не слышат?',
        'question_kind': 'narrowing',
    },
    'lost-and-aimless': {
        'opening': 'Когда человек говорит, что потерялся, речь редко идёт просто о тумане.',
        'moves': ('drift-without-structure', 'bring-your-story-up-to-date'),
        'framing_moves': ('aimlessness-is-drift-not-fog',),
        'narrowing_moves': ('narrow-aimlessness-to-what-is-collapsing',),
        'fallback_voice': (
            'Чаще это значит, что он больше не знает, какое бремя готов нести добровольно, и потому порядок начинает расползаться.',
        ),
        'question_lead': 'Скажи прямо:',
        'question': 'что у тебя разваливается первым — дисциплина, цель, отношения или уважение к себе?',
        'question_kind': 'narrowing',
    },
    'shame-spiral': {
        'opening': 'Со стыдом почти бесполезно бороться общими словами.',
        'fallback_voice': (
            'Если он остаётся горячим, значит ты ещё не вынес из этого опыта ту правду, которая могла бы тебя перестроить.',
        ),
        'question_lead': 'Скажи честно:',
        'question': 'здесь главнее ошибка, которую ты не можешь простить, страх разоблачения или привычка смотреть на себя с презрением?',
        'question_kind': 'narrowing',
    },
    'resentment-buildup': {
        'opening': 'Там, где долго копится resentment, почти всегда лежит правда, которую человек боится произнести, и цена, которую он не хочет платить.',
        'moves': ('not-about-winning',),
        'fallback_voice': (
            'Если этого не назвать, обида начинает управлять характером из-под пола.',
        ),
        'question_lead': 'Назови одну вещь прямо:',
        'question': 'ты сейчас больше зол на другого, на себя или на собственную трусость перед необходимым разговором?',
        'question_kind': 'narrowing',
    },
    'avoidance-paralysis': {
        'opening': 'Паралич почти никогда не означает, что ты ничего не знаешь.',
        'fallback_voice': (
            'Гораздо чаще это значит, что ты уже видишь нужный шаг, но не хочешь встретиться с его ценой.',
        ),
        'question_lead': 'Скажи прямо:',
        'question': 'что именно ты откладываешь — разговор, дисциплину, решение или добровольное ограничение?',
        'question_kind': 'narrowing',
    },
    'self-deception': {
        'opening': 'Если вопрос упирается в самообман, значит где-то уже есть правда, которую ты знаешь, но не строишь вокруг неё порядок.',
        'framing_moves': ('self-deception-is-truth-without-order',),
        'narrowing_moves': ('narrow-self-deception-to-one-lie',),
        'fallback_voice': (
            'Пока это не названо, система будет снова и снова возвращать тебя в тот же узел.',
        ),
        'question_lead': 'Назови одну вещь прямо:',
        'question': 'в чём именно ты себе врёшь?',
        'question_kind': 'narrowing',
    },
    'fear-and-price': {
        'opening': 'Там, где человеком правит страх, почти всегда рядом стоит нечто достаточно ценное, чтобы за него пришлось платить.',
        'framing_moves': ('fear-points-to-the-price-of-value',),
        'narrowing_moves': ('narrow-fear-to-what-might-be-lost',),
        'fallback_voice': (
            'Проблема обычно не в том, что страшно, а в том, что цена ясна, а решение всё ещё отложено.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'чего ты боишься лишиться — одобрения, безопасности, власти или привычной идентичности?',
        'question_kind': 'narrowing',
    },
    'loneliness-rejection': {
        'opening': 'Одиночество особенно разрушительно там, где человек уже начинает переживать себя как того, кого перестали выбирать.',
        'fallback_voice': (
            'Тогда боль идёт не только от отсутствия людей рядом, а от ощущения невидимости, ненужности или скрытого отвержения.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'что здесь больнее всего — оставленность, невидимость, унижение или чувство, что тебя снова не выбрали?',
        'question_kind': 'narrowing',
    },
    'parenting-boundaries': {
        'opening': 'Воспитание почти никогда не сводится к технике.',
        'moves': ('don-t-solve-a-problem-you-don-t-have',),
        'framing_moves': ('love-needs-standards-not-indulgence',),
        'narrowing_moves': ('narrow-parenting-to-child-or-parent-fear',),
        'fallback_voice': (
            'Речь идёт о том, какую слабость ты закрепляешь и какой характер помогаешь построить.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'тебя больше тревожит поведение ребёнка, твоя собственная вина или страх дать ему столкнуться с реальностью?',
        'question_kind': 'narrowing',
    },
    'tragedy-and-bitterness': {
        'opening': 'Когда человек сталкивается со страданием, ему мало общей философии.',
        'fallback_voice': (
            'Нужно назвать, где именно боль начинает превращаться в горечь и ожесточение.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'ты сейчас борешься больше с утратой, со страхом, с несправедливостью или с искушением озлобиться?',
        'question_kind': 'narrowing',
    },
    'scope-topics': {
        'opening': 'Я могу быть полезен там, где человек начинает себе лгать и распадаться.',
        'fallback_voice': (
            'Это смысл и направление, дисциплина и самообман, resentment и обида, отношения и близость, страх, стыд и добровольно принятое бремя.',
        ),
        'question_lead': 'Не тащи сюда всю жизнь сразу.',
        'question': 'Выбери один узел и назови его прямо.',
        'question_kind': 'topic_selection',
    },
    'greeting-opening': {
        'opening': 'Добрый вечер.',
        'fallback_voice': (
            'Если хочешь, не будем тратить ход на вежливость и сразу возьмём один настоящий вопрос там, где у тебя есть конфликт, страх, обида, потеря направления или распад близости.',
        ),
        'question_lead': 'Назови прямо:',
        'question': 'что именно ты хочешь разобрать.',
        'question_kind': 'topic_selection',
    },
    'psychological-portrait-request': {
        'opening': 'Я не хочу лепить тебе психологический портрет из воздуха.',
        'fallback_voice': (
            'Если делать это честно, нужно смотреть не на ярлык, а на повторяющийся паттерн, который портит твою жизнь и характер.',
        ),
        'question_lead': 'Начни не с типа личности, а с правды.',
        'question': 'Где ты себе вредишь устойчивее всего — в дисциплине, в близости, в обиде, в избегании или в самообмане?',
        'question_kind': 'pattern_selection',
    },
    'self-evaluation-request': {
        'opening': 'Если ты спрашиваешь, что с тобой не так, я не хочу отвечать тебе ярлыком.',
        'fallback_voice': (
            'Полезнее искать не дефект личности, а повторяющийся паттерн, через который ты сам себе вредишь и разрушаешь порядок жизни.',
        ),
        'question_lead': 'Начни не с самоприговоров, а с правды.',
        'question': 'Где ты себе вредишь устойчивее всего — в дисциплине, в близости, в обиде, в избегании или в самообмане?',
        'question_kind': 'pattern_selection',
    },
    'shame-self-contempt-request': {
        'opening': 'Если стыд уже стал приговором личности, спорить с ним общими словами почти бесполезно.',
        'fallback_voice': (
            'Нужно понять, из чего именно он питается: из унижения, разоблачения, провала, внутренней ненависти к себе или из горечи, обращённой внутрь.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'здесь главнее унижение, разоблачение перед людьми, чувство провала, самоненависть или обида, обращённая на себя?',
        'question_kind': 'narrowing',
    },
    'self-diagnosis-soft': {
        'opening': 'Я не хочу приклеивать к тебе диагноз раньше, чем мы назвали сам опыт.',
        'fallback_voice': (
            'Сначала нужно различить, что именно рушится: удовольствие, энергия, смысл, связь с людьми или способность хотеть чего-то вообще.',
        ),
        'question_lead': 'Скажи точнее:',
        'question': 'здесь главнее эмоциональная пустота, утрата интереса, бессилие, отрыв от людей или ощущение, что ничто не зовёт вперёд?',
        'question_kind': 'symptom_narrowing',
    },
    'source-lookup': {
        'opening': 'Если тебе нужен ответ по базе, мне нужна не общая тема, а точка опоры.',
        'fallback_voice': (
            'Без этого я начну достраивать там, где надо сначала смотреть на текст.',
        ),
        'question_lead': 'Назови прямо:',
        'question': 'книгу, цитату, лекцию или один конкретный конфликт, который нужно разобрать.',
        'question_kind': 'source_anchor',
    },
    'abstract-followup': {
        'opening': 'Если ты хочешь говорить не о себе, а в общем виде, всё равно нужно назвать сам предмет разговора.',
        'fallback_voice': (
            'Иначе разговор теряет тему и начинает скользить по пустой мета-рамке вместо разбора.',
        ),
        'question_lead': 'Скажи прямо:',
        'question': 'ты хочешь разбирать в общем виде потерю чувств, обиду, угасание желания, предательство или что-то ещё?',
        'question_kind': 'topic_restate',
    },
    'abstractify-relationship-loss-of-feeling': {
        'opening': 'Если говорить в общем виде, чувство в серьёзных отношениях редко умирает по одной причине.',
        'fallback_voice': (
            'Обычно его подтачивают накопленная обида, невысказанный конфликт, утрата уважения, расхождение в желании или привычка жить рядом без настоящей встречи.',
        ),
        'question_lead': 'Если хочешь идти дальше по существу,',
        'question': 'выбери один паттерн: обида, холод, потеря желания, исчезновение уважения или ложь о том, что всё в порядке.',
        'question_kind': 'topic_variant',
    },
    'relationship-foundations-overview': {
        'opening': 'Если говорить о крепких отношениях по существу, их смысл не в том, чтобы устранить всякое напряжение.',
        'fallback_voice': (
            'Их смысл в том, чтобы два человека могли выдерживать правду, различие и совместное бремя без взаимного распада.',
            'Такая связь держится не на одном чувстве, а на правдивости, уважении, добровольной ответственности, сохранённом желании видеть другого как живого человека и способности чинить разрыв, не превращая его в войну.',
        ),
        'question_lead': 'Если хочешь идти дальше по делу,',
        'question': 'выбери, что для тебя здесь важнее разобрать: правду, уважение, совместное бремя, желание или восстановление связи после конфликта.',
        'question_kind': 'topic_variant',
    },
    'empty-input': {
        'opening': 'Сначала нужно сформулировать один честный вопрос.',
        'fallback_voice': (
            'Не обо всём сразу, а об одном узле, который действительно требует правды.',
        ),
        'question_lead': 'Назови прямо:',
        'question': 'цитату, конфликт, страх, обиду или выбор, который ты сейчас избегаешь.',
        'question_kind': 'restatement',
    },
    'fallback': {
        'opening': 'Я не хочу достраивать ответ на слабой опоре.',
        'fallback_voice': (
            'Если ты хочешь честный разбор, нужно сузить рамку до того места, где действительно есть что назвать.',
        ),
        'question_lead': 'Назови прямо:',
        'question': 'одну цитату, одну книгу, один конфликт или один паттерн, который нужно разобрать.',
        'question_kind': 'restatement',
    },
}


def _normalize(text: str) -> str:
    return ' '.join((text or '').lower().split())


def _contains_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _theme_for_route(route_name: str) -> str:
    return _ROUTE_THEMES.get(route_name, 'general')


def _metadata(*, clarify_type: str, route_name: str, profile: str,
              template_id: str, question_kind: str,
              reason_code: str | None = None,
              voice_moves: list[str] | None = None,
              framing_moves: list[str] | None = None,
              narrowing_moves: list[str] | None = None,
              source_refs: list[str] | None = None,
              voice_layer: str | None = None) -> dict:
    payload = {
        'clarify_type': clarify_type,
        'clarify_theme': _theme_for_route(route_name),
        'clarify_profile': profile,
        'clarify_template_id': template_id,
        'clarify_question_kind': question_kind,
        'clarify_reason_code': reason_code or profile,
    }
    if voice_moves:
        payload['clarify_voice_moves'] = list(voice_moves)
    if framing_moves:
        payload['clarify_framing_moves'] = list(framing_moves)
    if narrowing_moves:
        payload['clarify_narrowing_moves'] = list(narrowing_moves)
    if source_refs:
        payload['clarify_source_refs'] = list(source_refs)
    if voice_layer:
        payload['clarify_voice_layer'] = voice_layer
    return payload


def _best_typed_rows(bundle: dict, pattern_type: str, move_names: tuple[str, ...] | list[str]) -> list[dict]:
    typed = (bundle.get('typed_moves') or {}).get(pattern_type, {})
    rows: list[dict] = []
    for move_name in move_names or ():
        row = typed.get(move_name)
        if row and row not in rows:
            rows.append(row)
    return rows


def _select_profile(question: str, route_name: str) -> str | None:
    q = _normalize(question)
    if route_name == 'relationship-maintenance':
        if _contains_any(q, _RELATIONSHIP_SCOPE_MARKERS):
            return 'scope-sexual-problems'
        if _contains_any(q, _DESIRE_MISMATCH_MARKERS):
            return 'desire-mismatch'
        if _contains_any(q, _SEXUAL_REJECTION_MARKERS):
            return 'sexual-rejection'
        if _contains_any(q, _RESENTMENT_AND_SILENCE_MARKERS):
            return 'resentment-and-silence'
        return 'relationship-knot'
    if route_name == 'career-vocation' and _contains_any(q, _LOST_AND_AIMLESS_MARKERS):
        return 'lost-and-aimless'
    if route_name == 'shame-self-contempt' and _contains_any(q, _SHAME_MARKERS):
        return 'shame-spiral'
    if route_name == 'resentment' and _contains_any(q, _RESENTMENT_MARKERS):
        return 'resentment-buildup'
    if route_name == 'avoidance-paralysis' and _contains_any(q, _AVOIDANCE_MARKERS):
        return 'avoidance-paralysis'
    if route_name == 'self-deception' and _contains_any(q, _SELF_DECEPTION_MARKERS):
        return 'self-deception'
    if route_name == 'fear-value' and _contains_any(q, _FEAR_MARKERS):
        return 'fear-and-price'
    if route_name == 'parenting-overprotection' and _contains_any(q, _PARENTING_MARKERS):
        return 'parenting-boundaries'
    if route_name == 'tragedy-suffering' and _contains_any(q, _TRAGEDY_MARKERS):
        return 'tragedy-and-bitterness'
    return None


def _render_profile(profile: str) -> tuple[str, dict]:
    spec = _PROFILE_SPECS.get(profile) or _PROFILE_SPECS['fallback']
    bundle = load_profile_voice_bundle(
        profile,
        tuple(spec.get('fallback_profiles') or ()),
    )

    chosen_moves: list[str] = []
    chosen_framing_moves: list[str] = []
    chosen_narrowing_moves: list[str] = []
    chosen_sources: list[str] = []
    voice_lines: list[str] = []
    for move_name in spec.get('moves') or ():
        row = (bundle.get('moves') or {}).get(move_name)
        if not row:
            continue
        line = (row.get('pattern_text') or '').strip()
        if not line or line in voice_lines:
            continue
        voice_lines.append(line)
        chosen_moves.append(move_name)
        source_name = row.get('source_name', '')
        if source_name and source_name not in chosen_sources:
            chosen_sources.append(source_name)

    if not voice_lines:
        voice_lines = [line.strip() for line in (spec.get('fallback_voice') or ()) if line.strip()]

    framing_rows = _best_typed_rows(bundle, 'framing_move', tuple(spec.get('framing_moves') or ()))
    framing_lines: list[str] = []
    for row in framing_rows:
        line = (row.get('pattern_text') or '').strip()
        if not line or line in framing_lines:
            continue
        framing_lines.append(line)
        chosen_framing_moves.append(row.get('move_name', ''))
        source_name = row.get('source_name', '')
        if source_name and source_name not in chosen_sources:
            chosen_sources.append(source_name)

    narrowing_rows = _best_typed_rows(bundle, 'narrowing_question', tuple(spec.get('narrowing_moves') or ()))
    narrowing_lines: list[str] = []
    for row in narrowing_rows:
        line = (row.get('pattern_text') or '').strip()
        if not line or line in narrowing_lines:
            continue
        narrowing_lines.append(line)
        chosen_narrowing_moves.append(row.get('move_name', ''))
        source_name = row.get('source_name', '')
        if source_name and source_name not in chosen_sources:
            chosen_sources.append(source_name)

    question_lead = spec.get('question_lead', '').strip()
    question = spec.get('question', '').strip()
    question_block = ' '.join(part for part in [question_lead, question] if part).strip()
    opening = (framing_lines[0] if framing_lines else spec.get('opening', '').strip())
    question_text = (narrowing_lines[0] if narrowing_lines else question_block)
    parts = [
        opening,
        *voice_lines,
    ]
    if question_text:
        parts.append(question_text)
    text = ' '.join(part for part in parts if part).strip()
    metadata = {
        'voice_moves': chosen_moves,
        'framing_moves': [move for move in chosen_framing_moves if move],
        'narrowing_moves': [move for move in chosen_narrowing_moves if move],
        'source_refs': chosen_sources,
        'voice_layer': (
            'db.voice_patterns'
            if (chosen_moves or chosen_framing_moves or chosen_narrowing_moves)
            else ''
        ),
    }
    return text, metadata


def _render_axis_followup(active_topic: str, selected_axis: str) -> tuple[str, dict]:
    relationship_axis_map = {
        'resentment': (
            'Если главный разрушитель здесь обида, то чувство обычно гаснет не в один день, а когда человек слишком долго ведёт внутренний счёт и перестаёт говорить правду вовремя.',
            'Скажи точнее: эта обида родилась из унижения, хронического невнимания, невысказанного конфликта или из того, что уважение уже начало исчезать?',
        ),
        'coldness': (
            'Если главнее холод, значит между людьми уже исчезла живая встреча и всё начало держаться на функции, а не на добровольной связи.',
            'Скажи точнее: этот холод возник после обиды, после усталости, после потери уважения или после долгого ухода от правды?',
        ),
        'loss_of_desire': (
            'Если пропадает желание, это редко бывает только телесной историей; тело часто первым показывает, что уважение, доверие или правда уже нарушены.',
            'Скажи точнее: здесь важнее скука, скрытая обида, утрата уважения или страх близости?',
        ),
        'loss_of_respect': (
            'Если исчезает уважение, любовь начинает рушиться уже на уровне характера, а не только на уровне чувства.',
            'Скажи точнее: уважение размыли слабость, ложь, хроническое избегание или накопленная взаимная обида?',
        ),
        'unspoken_conflict': (
            'Если дело в невысказанном конфликте, чувство часто умирает в тишине раньше, чем в открытой ссоре.',
            'Скажи точнее: что именно не было сказано прямо — претензия, граница, потребность или страх потерять связь?',
        ),
    }
    self_diagnosis_axis_map = {
        'emotional_flatness': (
            'Если главнее пустота, не спеши делать из неё ярлык. Важно понять, это омертвение чувств, защитное онемение или жизнь, из которой ушла цель.',
            'Скажи точнее: эта пустота больше похожа на усталое онемение, на отчуждение от людей или на ощущение, что ничто больше не имеет веса?',
        ),
        'loss_of_interest': (
            'Если прежде всего ушёл интерес, вопрос уже не в настроении как таковом, а в том, что мир перестал звать тебя вперёд.',
            'Скажи точнее: интерес пропал ко всему, только к людям, только к работе или даже к тому, что раньше оживляло тебя изнутри?',
        ),
        'exhaustion': (
            'Если в центре бессилие, сначала нужно отличить истощение от пустоты и от капитуляции.',
            'Скажи точнее: это больше похоже на телесную выжатость, на эмоциональный износ или на ощущение, что ты давно живёшь без смысла?',
        ),
        'social_disconnection': (
            'Если главнее отрыв от людей, тогда проблема может быть не только в настроении, а в том, что ты уже выпал из взаимной связи и коррекции.',
            'Скажи точнее: ты больше чувствуешь изоляцию, недоверие, стыд перед людьми или просто отсутствие живого контакта?',
        ),
        'loss_of_aim': (
            'Если ничто не зовёт вперёд, возможно, рушится не просто чувство, а сама ось направления.',
            'Скажи точнее: ты больше потерял цель, внутреннее желание, дисциплину или ощущение, что твои усилия вообще чего-то стоят?',
        ),
    }
    portrait_axis_map = {
        'discipline': (
            'Если узел в дисциплине, характер разрушается не в одном срыве, а в том, что человек слишком долго позволяет хаосу управлять повседневностью.',
            'Скажи точнее: ты чаще срываешься из-за лени, страха, отсутствия структуры или скрытого бунта против нужного порядка?',
        ),
        'closeness': (
            'Если слабое место в близости, вопрос не в типологии, а в том, как ты строишь или ломаешь доверие.',
            'Скажи точнее: ты чаще уходишь в холод, в страх уязвимости, в обиду или в ожидание, что другой сам всё поймёт?',
        ),
        'resentment': (
            'Если в центре обида, характер постепенно начинает вращаться вокруг невысказанного обвинения.',
            'Скажи точнее: ты чаще копишь счёт, взрываешься, молча отдаляешься или используешь правоту как щит?',
        ),
        'avoidance': (
            'Если ты вредишь себе через избегание, проблема уже не в незнании, а в цене того шага, который ты слишком долго откладываешь.',
            'Скажи точнее: ты чаще избегаешь разговора, решения, ответственности или встречи с собственной слабостью?',
        ),
        'self_deception': (
            'Если главный узел — самообман, значит ты где-то уже знаешь правду, но ещё не построил вокруг неё жизнь.',
            'Скажи точнее: в чём именно ложь — в мотивах, в отношениях, в целях или в том, что ты называешь своими ценностями?',
        ),
    }
    shame_axis_map = {
        'humiliation': (
            'Если в центре унижение, тогда стыд держится не просто на ошибке, а на переживании собственного уменьшения в чьих-то глазах.',
            'Скажи точнее: это унижение родилось из презрения другого человека, из публичного эпизода, из собственной слабости или из того, что ты позволил с собой обращаться недопустимо?',
        ),
        'exposure': (
            'Если мучает прежде всего разоблачение, тогда ты живёшь не только с фактом, а с невыносимым взглядом воображаемого свидетеля.',
            'Скажи точнее: страшнее всего здесь чужое мнение, потеря лица, страх быть увиденным насквозь или чувство, что после этого тебя уже нельзя уважать?',
        ),
        'failure': (
            'Если ядро стыда — провал, тогда важно понять, это боль от реальной несостоятельности или тотальный приговор, который ты вынес себе из одного поражения.',
            'Скажи точнее: здесь больнее ошибка, слабость, потеря статуса или мысль, что один провал уже доказывает твою никчёмность?',
        ),
        'self_condemnation': (
            'Если всё уже перешло в самоненависть, тогда проблема не просто в поступке, а в том, что внутренний судья занял всё пространство и не оставил места для правды, кроме приговора.',
            'Скажи точнее: ты сейчас больше переживаешь отвращение к себе, желание исчезнуть, ощущение моральной испорченности или страх, что внутри тебя нет ничего достойного уважения?',
        ),
        'resentment': (
            'Если стыд спутан с горечью, тогда часть удара может быть обращена не только против себя, но и против того, кто унизил, отверг или заставил жить в скрытом счёте.',
            'Скажи точнее: здесь сильнее злость на другого, злость на себя за слабость, чувство несправедливости или мучительная смесь всех трёх?',
        ),
    }
    source_map = {
        'relationship-loss-of-feeling': relationship_axis_map,
        'shame-self-contempt': shame_axis_map,
        'self-diagnosis': self_diagnosis_axis_map,
        'psychological-portrait': portrait_axis_map,
        'self-evaluation': portrait_axis_map,
    }
    axis_map = source_map.get(active_topic, {})
    opening, question = axis_map.get(
        selected_axis,
        (
            'Тогда не повторяй всю тему заново, а назови, как именно этот узел портит порядок жизни.',
            'Скажи точнее: где это проявляется острее всего и какой правды ты здесь всё ещё избегаешь?',
        ),
    )
    return f'{opening} {question}'.strip(), {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _render_detail_followup(active_topic: str, active_axis: str, selected_detail: str) -> tuple[str, dict]:
    relationship_detail_map = {
        ('resentment', 'humiliation'): (
            'Если обида растёт из унижения, то здесь уже ранен не просто комфорт, а достоинство. После этого люди часто начинают наказывать друг друга холодом, счётом и молчаливым презрением.',
            'Тогда главный вопрос уже не в том, кто прав, а в том, что именно допустило такое унижение и почему это до сих пор не названо без уклонения.',
        ),
        ('resentment', 'chronic_neglect'): (
            'Если ядро обиды — хроническое невнимание, то чувство умирает от повторяющегося сигнала: ты не важен настолько, чтобы тебя видеть всерьёз.',
            'Здесь стоит разбирать уже не последний эпизод, а паттерн: где именно тебя перестали замечать и почему это стало нормой.',
        ),
        ('resentment', 'unspoken_conflict'): (
            'Если всё держится на невысказанном конфликте, обида начинает жить как подпольное обвинение. Тогда люди спорят уже не о предмете, а из-за непроговорённой правды под ним.',
            'Дальше стоит спрашивать не о симптоме, а о том, что именно нельзя было сказать прямо и какую цену каждый пытался не платить.',
        ),
        ('resentment', 'loss_of_respect'): (
            'Если в основе обиды уже лежит утрата уважения, это опаснее простой ссоры: отношения начинают разрушаться на уровне характера.',
            'Здесь следующий честный вопрос такой: чем именно уважение было подорвано — слабостью, ложью, трусостью или накопленной горечью?',
        ),
    }
    self_diagnosis_detail_map = {
        ('emotional_flatness', 'numbness'): (
            'Если это больше похоже на онемение, важно не путать это с ясностью. Иногда человек уже так долго гасил боль, что вместе с ней притупил и всё остальное.',
            'Тогда разбирать нужно не ярлык, а то, что именно пришлось слишком долго не чувствовать, чтобы вообще держаться.',
        ),
        ('emotional_flatness', 'social_disconnection'): (
            'Если пустота сильнее всего связана с отчуждением от людей, проблема может быть не только внутренней. Иногда человек выпадает из той связи, которая держит его восприятие живым и правдивым.',
            'Тогда следующий вопрос такой: это произошло из-за боли, недоверия, стыда или медленного ухода из участия в жизни других?',
        ),
        ('emotional_flatness', 'meaninglessness'): (
            'Если пустота уже связана с бессмысленностью, возможно, рушится не просто настроение, а сама структура ценности. Мир перестаёт отвечать, когда больше нечему отвечать внутри тебя.',
            'Здесь стоит смотреть на то, что именно утратило вес: цель, ответственность, связь, жертва или правда, вокруг которой можно строить жизнь.',
        ),
    }
    portrait_detail_map = {
        ('avoidance', 'conversation'): (
            'Если ты прежде всего избегаешь разговора, значит ты уже знаешь, где правда требует голоса, но всё ещё платишь за молчание меньшей ценой, чем за прямоту.',
            'Тогда следующий вопрос такой: что именно ты боишься запустить этим разговором — конфликт, потерю одобрения, разоблачение или необходимость меняться самому?',
        ),
        ('avoidance', 'decision'): (
            'Если узел именно в решении, то избегание начинает выглядеть как попытка не убить ни одну возможность, даже если за это приходится платить хаосом.',
            'Здесь нужно уже смотреть, какую цену ты пытаешься отсрочить и какую идентичность не хочешь потерять, выбрав что-то одно.',
        ),
        ('avoidance', 'responsibility'): (
            'Если ты уходишь именно от ответственности, тогда проблема не в недостатке понимания, а в сопротивлении добровольно принятому бремени.',
            'Следующий честный вопрос такой: какое бремя ты уже видишь, но всё ещё надеешься обойти стороной?',
        ),
        ('avoidance', 'weakness'): (
            'Если избегание завязано на встрече с собственной слабостью, то человек часто прячется не от задачи, а от правды о себе, которую она может открыть.',
            'Тогда стоит спрашивать: чего ты боишься увидеть — некомпетентность, зависимость, трусость или собственную неустроенность?',
        ),
    }
    source_map = {
        'relationship-loss-of-feeling': relationship_detail_map,
        'self-diagnosis': self_diagnosis_detail_map,
        'psychological-portrait': portrait_detail_map,
        'self-evaluation': portrait_detail_map,
    }
    opening, question = source_map.get(active_topic, {}).get(
        (active_axis, selected_detail),
        (
            'Теперь тема уже достаточно сузилась, чтобы не бегать по кругу вокруг общего симптома.',
            'Следующий шаг — удержать именно этот узел и посмотреть, какой скрытый паттерн его питает и какую правду он всё ещё прячет.',
        ),
    )
    return f'{opening} {question}'.strip(), {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _render_mini_analysis(active_topic: str, active_axis: str, active_detail: str) -> tuple[str, dict]:
    relationship_analysis_map = {
        ('resentment', 'humiliation'): (
            'Это значит, что в основе узла лежит не просто недовольство, а удар по достоинству. Когда человек чувствует унижение, он редко сразу идёт к правде; чаще он начинает вести скрытый счёт, холодеть и наказывать молчанием.',
            'Такой паттерн разрушает чувство потому, что связь перестаёт быть местом взаимной встречи и превращается в арену защиты и скрытого возмездия.',
        ),
        ('resentment', 'chronic_neglect'): (
            'Это значит, что связь подтачивает не один конфликт, а повторяющийся сигнал собственной незначимости. От такого невнимания чувство умирает медленно, но очень последовательно.',
            'Здесь любовь ослабевает не из-за одной ссоры, а из-за накопившегося опыта: тебя слишком долго не видят как человека, которого надо встречать всерьёз.',
        ),
        ('resentment', 'unspoken_conflict'): (
            'Это значит, что отношения уже живут под давлением невысказанной правды. Пока конфликт не назван, энергия уходит не в восстановление связи, а в её скрытое разрушение.',
            'Такой узел обычно держится на том, что оба человека платят за молчание меньше, чем боятся заплатить за прямоту.',
        ),
        ('resentment', 'loss_of_respect'): (
            'Это значит, что проблема уже вышла за пределы одной эмоции и ударила по самой основе притяжения: уважению. Когда уважение размывается, чувство теряет каркас.',
            'Тогда разговор нужно вести уже не о настроении, а о характере, слабости, правде и о том, что именно сделало другого внутренне маленьким в твоих глазах.',
        ),
    }
    self_diagnosis_analysis_map = {
        ('emotional_flatness', 'numbness'): (
            'Это значит, что пустота может быть не только отсутствием радости, а защитным онемением. Иногда человек так долго гасит боль, что вместе с ней гасит и способность чувствовать вообще.',
            'Тогда задача уже не в том, чтобы быстрее назвать диагноз, а в том, чтобы понять, от чего именно эта система пыталась тебя защитить.',
        ),
        ('emotional_flatness', 'social_disconnection'): (
            'Это значит, что пустота может поддерживаться разрывом связи, а не только внутренним химическим спадом. Человек начинает глохнуть изнутри, когда выпадает из живой взаимности и коррекции.',
            'Тогда вопрос уже не только в симптоме, а в том, как долго ты жил без настоящего участия, доверия и правдивого контакта.',
        ),
        ('emotional_flatness', 'meaninglessness'): (
            'Это значит, что проблема, возможно, уже касается не эмоции как таковой, а распада ценности. Когда ничто не имеет веса, мир перестаёт отвечать на усилие.',
            'Тогда разбирать нужно не просто настроение, а то, какая цель, жертва или ответственность исчезла из центра жизни.',
        ),
    }
    portrait_analysis_map = {
        ('avoidance', 'conversation'): (
            'Это значит, что ты избегаешь не просто разговора, а той правды, которая может изменить расстановку сил, самооценку или саму структуру отношений. Молчание здесь становится способом отложить реальность.',
            'Такой паттерн обычно делает человека слабее, потому что он платит временным облегчением за долгосрочное накопление хаоса и скрытого resentment.',
        ),
        ('avoidance', 'decision'): (
            'Это значит, что избегание кормится надеждой сохранить все двери открытыми. Но в реальности цена за это — утечка воли и распад структуры.',
            'Тогда характер портится не потому, что решение невозможно, а потому, что человек слишком долго не соглашается потерять хоть что-то ради одного выбранного пути.',
        ),
        ('avoidance', 'responsibility'): (
            'Это значит, что сопротивление идёт против бремени, которое уже выглядит необходимым. Человек знает, что нужно нести, но всё ещё надеется остаться свободным от цены взросления.',
            'Такой узел почти всегда ведёт к ухудшению самоуважения, потому что реальность видна, а добровольный отклик на неё всё ещё не дан.',
        ),
        ('avoidance', 'weakness'): (
            'Это значит, что ты уклоняешься не от задачи, а от возможной встречи с собственной несостоятельностью. Здесь страх направлен не наружу, а на образ себя.',
            'Тогда работу надо вести вокруг стыда и правды, а не вокруг иллюзии, будто ты просто ещё недостаточно всё продумал.',
        ),
    }
    source_map = {
        'relationship-loss-of-feeling': relationship_analysis_map,
        'self-diagnosis': self_diagnosis_analysis_map,
        'psychological-portrait': portrait_analysis_map,
        'self-evaluation': portrait_analysis_map,
    }
    paragraph_one, paragraph_two = source_map.get(active_topic, {}).get(
        (active_axis, active_detail),
        (
            'Это значит, что разговор уже дошёл до узла, который действительно что-то объясняет, а не просто повторяет симптом другими словами.',
            'Дальше стоит держать именно этот слой и смотреть, какой скрытый паттерн он создаёт в характере, связи или восприятии мира.',
        ),
    )
    return f'{paragraph_one} {paragraph_two}'.strip(), {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _render_next_step(active_topic: str, active_axis: str, active_detail: str) -> tuple[str, dict]:
    if active_topic == 'relationship-foundations' and not active_axis and not active_detail:
        return ' '.join((
            'Тогда не пытайся вывести окончательную формулу любви. Полезнее выбрать одну опору из уже названных и посмотреть, как она реально строится: правда, уважение, совместное бремя, желание или восстановление связи.',
            'Практический следующий шаг здесь обычно такой: возьми одну пару, одну свою связь или одну недавнюю историю и спроси не “есть ли там чувство”, а “держится ли связь на правде, уважении и добровольной ответственности, когда возникает напряжение”.',
        )), {
            'voice_moves': [],
            'framing_moves': [],
            'narrowing_moves': [],
            'source_refs': [],
            'voice_layer': '',
        }
    if active_topic == 'relationship-loss-of-feeling' and not active_axis and not active_detail:
        return (
            'Тогда не пытайся чинить всё сразу и не жди, что чувство само оживёт от одного инсайта. Первый практический шаг — выбрать одну причину из уже названных и проверить, где именно она проявляется у вас повторяющимся паттерном, а не единичным эпизодом.',
            'После этого нужен один честный разговор или одно честное наблюдение по этой линии: обида, невысказанный конфликт, утрата уважения, расхождение в желании или привычка жить рядом без настоящей встречи.',
        ), {
            'voice_moves': [],
            'framing_moves': [],
            'narrowing_moves': [],
            'source_refs': [],
            'voice_layer': '',
        }
    relationship_next_step_map = {
        ('resentment', 'humiliation'): (
            'Тогда первый шаг не в том, чтобы немедленно восстановить чувство, а в том, чтобы перестать прятать унижение под холодом и скрытым счётом. Назови себе без украшений, где именно было растоптано достоинство и какой факт ты до сих пор не произнёс вслух.',
            'Потом нужен один прямой разговор без накопительной бухгалтерии: не обо всём сразу, а о той форме обращения, которую ты больше не собираешься считать нормой.',
        ),
        ('resentment', 'chronic_neglect'): (
            'Тогда начни не с обвинительного списка, а с одного повторяющегося паттерна невнимания, который ты больше не хочешь делать нормой. Пока это не названо просто и конкретно, обида будет только накапливать яд.',
            'Следующий шаг — один честный разговор о том, где тебя перестали встречать всерьёз и что должно измениться в поведении, а не только в настроении.',
        ),
        ('resentment', 'unspoken_conflict'): (
            'Тогда практический шаг в том, чтобы вытащить подпольный конфликт на поверхность в самой короткой и правдивой форме. Не оправдывайся и не читай лекцию: назови то, что было скрыто, и цену, которую молчание уже взяло.',
            'После этого держись одной темы и не позволяй разговору расползаться в десяток старых эпизодов.',
        ),
        ('resentment', 'loss_of_respect'): (
            'Тогда сначала нужно назвать, чем именно было подорвано уважение. Пока это размыто, ты будешь бороться с атмосферой, а не с причиной.',
            'Следующий шаг — спросить себя и другого не “что мы чувствуем”, а “какой поступок, слабость или ложь сделали уважение почти невозможным”.',
        ),
    }
    self_diagnosis_next_step_map = {
        ('emotional_flatness', 'numbness'): (
            'Тогда первый шаг не в том, чтобы спешить с ярлыком, а в том, чтобы вернуть карте опыта различия. Заметь в течение нескольких дней, где ты действительно ничего не чувствуешь, а где чувство есть, но оно глухое, болезненное или слишком опасное, чтобы к нему подходить.',
            'После этого ищи не универсальное объяснение, а тот вид боли или перегруза, от которого психика могла начать защищаться онемением.',
        ),
        ('emotional_flatness', 'social_disconnection'): (
            'Тогда практический шаг — не ждать, пока связь сама оживёт, а вернуть себе хотя бы одну форму живого участия. Нужен не шум общения, а один настоящий контакт, в котором ты не прячешься за вежливой пустотой.',
            'Параллельно смотри, где ты сам поддерживаешь отчуждение: избеганием, недоверием, стыдом или привычкой жить без взаимности.',
        ),
        ('emotional_flatness', 'meaninglessness'): (
            'Тогда начинать нужно не с чувства, а с веса. Выбери одно обязательство, цель или службу, которая объективно требует тебя, и посмотри, способен ли ты снова строить вокруг неё день.',
            'Если ничто не зовёт, иногда нужно сначала добровольно встать под дисциплину, а не ждать, что смысл сам заговорит первым.',
        ),
    }
    portrait_next_step_map = {
        ('avoidance', 'conversation'): (
            'Тогда практический шаг — подготовить один разговор, который ты слишком долго откладывал, и войти в него с одной правдой, а не с туманной жалобой. Не пытайся сразу решить всю жизнь; назови один факт, одну границу или одну цену молчания.',
            'Если ты не дашь правде голос, характер и дальше будет платить за временное облегчение нарастающим хаосом.',
        ),
        ('avoidance', 'decision'): (
            'Тогда следующий шаг — сузить выбор до реального решения и согласиться потерять альтернативы. Пока ты хочешь сохранить все двери открытыми, никакая воля не соберётся.',
            'Выбери один срок, один критерий и одну цену, которую готов заплатить за движение вместо затяжного распада.',
        ),
        ('avoidance', 'responsibility'): (
            'Тогда начни с самого малого добровольного бремени, от которого ты всё ещё уклоняешься, и возьми его без драматизации. Не обещай новую личность; подними один вес, который уже лежит у твоих ног.',
            'Самоуважение часто возвращается не после озарения, а после честного подчинения очевидной необходимости.',
        ),
        ('avoidance', 'weakness'): (
            'Тогда практический шаг — выбрать одно место, где ты позволишь себе увидеть слабость без побега и самооправдания. Не чтобы растоптать себя, а чтобы заменить туман конкретной правдой.',
            'После этого нужен не самоанализ без конца, а маленькое действие, которое докажет, что ты способен встретиться с этой правдой и не рухнуть.',
        ),
    }
    source_map = {
        'relationship-loss-of-feeling': relationship_next_step_map,
        'self-diagnosis': self_diagnosis_next_step_map,
        'psychological-portrait': portrait_next_step_map,
        'self-evaluation': portrait_next_step_map,
    }
    paragraph_one, paragraph_two = source_map.get(active_topic, {}).get(
        (active_axis, active_detail),
        (
            'Тогда следующий шаг не в том, чтобы снова расширять тему, а в том, чтобы сделать одно честное действие, соответствующее уже названному узлу.',
            'Держись этого слоя и спроси себя: какой маленький, но реальный шаг перестанет подкармливать тот же паттерн завтра?',
        ),
    )
    return f'{paragraph_one} {paragraph_two}'.strip(), {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _render_example(active_topic: str, active_axis: str, active_detail: str) -> tuple[str, dict]:
    relationship_example_map = {
        ('resentment', 'humiliation'): (
            'Например, это может выглядеть так: один человек снова и снова шутит или говорит с пренебрежением, а другой внешне “не устраивает сцен”, но внутри начинает холодеть и вести скрытый счёт.',
            'Потом каждый новый бытовой эпизод уже переживается не сам по себе, а как ещё одно подтверждение: со мной можно обращаться унизительно и это даже не будет названо.',
        ),
        ('resentment', 'chronic_neglect'): (
            'Например, один человек месяцами просит о простом внимании, а второй формально не делает ничего ужасного, но всё время даёт понять делами: ты получишь остаток моего присутствия после всего остального.',
            'Тогда чувство умирает не из-за драмы, а из-за повторяющегося урока собственной незначимости.',
        ),
    }
    self_diagnosis_example_map = {
        ('emotional_flatness', 'social_disconnection'): (
            'Например, человек встречается с друзьями, отвечает вежливо, делает всё как надо, но внутри не включается в контакт и выходит из таких встреч ещё более пустым, чем вошёл.',
            'Снаружи это может выглядеть как обычная усталость, а внутри переживается как жизнь без взаимности и без настоящего присутствия.',
        ),
        ('emotional_flatness', 'meaninglessness'): (
            'Например, человек просыпается, делает нужные дела, но ни одно из них не переживается как нечто стоящее усилия; всё как будто теряет вес раньше, чем к нему успевает прикоснуться внимание.',
            'Тогда проблема ощущается не как резкая боль, а как тянущая пустота, в которой мир перестаёт отвечать.',
        ),
    }
    portrait_example_map = {
        ('avoidance', 'conversation'): (
            'Например, человек неделями знает, что должен сказать о границе, обиде или несогласии, но каждый раз откладывает разговор до “более подходящего момента”, а взамен становится всё более раздражительным и холодным.',
            'Снаружи это выглядит как спокойствие, а по сути является способом заплатить молчанием за страх прямоты.',
        ),
        ('avoidance', 'decision'): (
            'Например, человек бесконечно сравнивает варианты, читает, думает, обсуждает, но так и не выбирает ничего, потому что реальный выбор убил бы часть возможностей и заставил бы отвечать за курс.',
            'Тогда хаос растёт не из-за нехватки информации, а из-за нежелания потерять открытые двери.',
        ),
    }
    source_map = {
        'relationship-loss-of-feeling': relationship_example_map,
        'self-diagnosis': self_diagnosis_example_map,
        'psychological-portrait': portrait_example_map,
        'self-evaluation': portrait_example_map,
    }
    if active_topic == 'relationship-foundations' and not active_axis and not active_detail:
        return ' '.join((
            'Например, внешне крепкая пара не обязана всё время быть нежной или бесконфликтной. Но когда между ними возникает напряжение, они не прячут правду под вежливость, не размывают уважение мелким презрением и не используют близость как валюту давления.',
            'Они могут спорить жёстко, но всё равно возвращаются к вопросу: что здесь правда, за что каждый из нас отвечает и как восстановить связь так, чтобы после конфликта осталось больше порядка, а не больше тайной вражды.',
        )), {
            'voice_moves': [],
            'framing_moves': [],
            'narrowing_moves': [],
            'source_refs': [],
            'voice_layer': '',
        }
    if active_topic == 'relationship-loss-of-feeling' and not active_axis and not active_detail:
        return (
            'Например, пара может не переживать ни одной большой драмы, но месяцами жить так, что любой разговор о боли, желании или разочаровании откладывается “до более спокойного момента”. '
            'Снаружи всё выглядит терпимо, а внутри накапливаются обида, холод и утрата уважения, пока чувство не начинает умирать без формального разрыва.'
        ), {
            'voice_moves': [],
            'framing_moves': [],
            'narrowing_moves': [],
            'source_refs': [],
            'voice_layer': '',
        }
    paragraph_one, paragraph_two = source_map.get(active_topic, {}).get(
        (active_axis, active_detail),
        (
            'Например, это выглядит как ситуация, в которой симптом уже виден на поверхности, но настоящая проблема живёт глубже и управляет поведением из-под пола.',
            'То есть человек думает, что реагирует на текущий эпизод, а на деле снова и снова воспроизводит один и тот же неназванный паттерн.',
        ),
    )
    return f'{paragraph_one} {paragraph_two}'.strip(), {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _contextual_acknowledgement(dialogue_act: str, dialogue_state: dict | None = None) -> str:
    state = dialogue_state or {}
    topic = state.get('active_topic', '')
    abstraction_level = state.get('abstraction_level', 'personal') or 'personal'
    relation = {
        'abstractify_previous_question': 'reframe',
        'confirm_scope': 'continue',
        'personalize_previous_question': 'reframe',
        'supply_narrowing_axis': 'answer_slot',
        'supply_concrete_manifestation': 'answer_slot',
        'request_mini_analysis': 'continue',
        'request_next_step': 'continue',
        'request_example': 'continue',
        'request_cause_list': 'continue',
        'reject_scope': 'reframe',
        'topic_shift': 'shift',
    }.get(dialogue_act, '')
    goal = {
        'abstractify_previous_question': 'overview',
        'confirm_scope': 'overview',
        'personalize_previous_question': 'clarify',
        'supply_narrowing_axis': 'clarify',
        'supply_concrete_manifestation': 'clarify',
        'request_mini_analysis': 'mini_analysis',
        'request_next_step': 'next_step',
        'request_example': 'example',
        'request_cause_list': 'cause_list',
        'reject_scope': 'clarify',
        'topic_shift': 'opening',
    }.get(dialogue_act, '')
    return get_dialogue_acknowledgement_hint(
        topic=topic,
        relation=relation,
        goal=goal,
        stance=abstraction_level,
        has_detail=bool(state.get('active_detail')),
        dialogue_act=dialogue_act,
    )


def _render_cause_list(active_topic: str, abstraction_level: str = 'personal') -> tuple[str, dict]:
    relationship_text_general = (
        'Если говорить в общем виде, чувство в серьёзных отношениях чаще всего подтачивают пять вещей: '
        'накопленная обида, невысказанный конфликт, утрата уважения, расхождение в желании и привычка жить рядом без настоящей встречи. '
        'Обычно проблема не в одном пункте, а в том, какой из них слишком долго оставался неназванным.'
    )
    relationship_foundations_text = (
        'Если разложить крепкие отношения по главным опорам, я бы начал с пяти вещей: правдивость, уважение, добровольно принятое совместное бремя, сохранённое желание видеть другого как живого человека и способность восстанавливать связь после разрыва. '
        'Это не украшения вокруг любви, а структура, без которой чувство быстро становится либо сентиментом, либо скрытой войной.'
    )
    relationship_text_personal = (
        'Если возвращать это к личной истории, то обычно стоит смотреть на те же пять причин: накопленная обида, невысказанный конфликт, '
        'утрата уважения, расхождение в желании и привычка жить рядом без настоящей встречи. '
        'Но тебе не нужно хвататься за всё сразу: выбери ту причину, которая уже заметнее всего разрушает именно твою связь.'
    )
    self_diagnosis_text = (
        'Если держаться этой темы без поспешного диагноза, то чаще всего приходится различать пять основных причин: эмоциональную пустоту, '
        'утрату интереса, бессилие, отрыв от людей и распад направления. '
        'Главный вопрос не в ярлыке, а в том, какая из этих линий сильнее всего описывает твой опыт сейчас.'
    )
    portrait_text = (
        'Если говорить о характере честно, то слабое место обычно лежит в одном из пяти узлов: дисциплина, близость, resentment, избегание или самообман. '
        'Дальше важно не каталогизировать себя, а назвать, какой из этих паттернов повторяется у тебя чаще всего и дороже всего обходится.'
    )
    self_evaluation_text = (
        'Если задавать вопрос честно и без самоприговоров, то обычно приходится смотреть на те же пять узлов: дисциплина, близость, resentment, избегание и самообман. '
        'Полезный ход здесь не в том, чтобы решить, что с тобой “не так” вообще, а в том, чтобы назвать, какой из этих паттернов повторяется у тебя чаще всего и дороже всего обходится.'
    )
    topic_map = {
        'relationship-loss-of-feeling': relationship_text_general if abstraction_level == 'general' else relationship_text_personal,
        'relationship-foundations': relationship_foundations_text,
        'self-diagnosis': self_diagnosis_text,
        'psychological-portrait': portrait_text,
        'self-evaluation': self_evaluation_text,
    }
    text = topic_map.get(
        active_topic,
        'Лучше всего двигаться не от хаотического списка, а от нескольких главных причин, которые уже собирают проблему в один узел. '
        'Выбери ту линию, которая сильнее всего объясняет происходящее сейчас.',
    )
    return text, {
        'voice_moves': [],
        'framing_moves': [],
        'narrowing_moves': [],
        'source_refs': [],
        'voice_layer': '',
    }


def _compose_contextual_response(base_text: str, *, dialogue_act: str = '',
                                 dialogue_state: dict | None = None) -> tuple[str, str]:
    acknowledgement = _contextual_acknowledgement(dialogue_act, dialogue_state)
    if not acknowledgement:
        return base_text.strip(), ''
    return f'{acknowledgement} {base_text}'.strip(), 'acknowledge_and_continue'


def _contextual_acknowledgement_from_frame(dialogue_frame: dict | None = None,
                                           dialogue_state: dict | None = None) -> str:
    frame = dialogue_frame or {}
    state = dialogue_state or {}
    topic = frame.get('topic') or state.get('active_topic', '')
    goal = frame.get('goal', '')
    stance = frame.get('stance') or state.get('abstraction_level', 'personal')
    relation = frame.get('relation_to_previous', '')
    return get_dialogue_acknowledgement_hint(
        topic=topic,
        relation=relation,
        goal=goal,
        stance=stance,
        has_detail=bool(state.get('active_detail')),
    )


def _compose_frame_contextual_response(base_text: str, *,
                                       dialogue_frame: dict | None = None,
                                       dialogue_state: dict | None = None) -> tuple[str, str]:
    acknowledgement = _contextual_acknowledgement_from_frame(dialogue_frame, dialogue_state)
    if not acknowledgement:
        return base_text.strip(), ''
    return f'{acknowledgement} {base_text}'.strip(), 'acknowledge_and_continue'


def _render_from_frame_plan(plan, *,
                            route_name: str,
                            dialogue_state: dict | None = None,
                            dialogue_frame: dict | None = None) -> ClarificationResult:
    if plan.render_kind == 'profile':
        text, voice_meta = _render_profile(plan.profile)
    elif plan.render_kind == 'cause_list':
        text, voice_meta = _render_cause_list(plan.topic, plan.stance)
    elif plan.render_kind == 'mini_analysis':
        text, voice_meta = _render_mini_analysis(plan.topic, plan.axis, plan.detail)
    elif plan.render_kind == 'next_step':
        text, voice_meta = _render_next_step(plan.topic, plan.axis, plan.detail)
    elif plan.render_kind == 'example':
        text, voice_meta = _render_example(plan.topic, plan.axis, plan.detail)
    elif plan.render_kind == 'axis_followup':
        text, voice_meta = _render_axis_followup(plan.topic, plan.axis)
    elif plan.render_kind == 'detail_followup':
        text, voice_meta = _render_detail_followup(plan.topic, plan.axis, plan.detail)
    else:
        raise ValueError(f'Unsupported frame render kind: {plan.render_kind}')

    if plan.response_mode == 'act':
        text, response_move = _compose_contextual_response(
            text,
            dialogue_act=plan.source_act or 'reject_scope',
            dialogue_state=dialogue_state,
        )
    else:
        text, response_move = _compose_frame_contextual_response(
            text,
            dialogue_frame=dialogue_frame,
            dialogue_state=dialogue_state,
        )

    meta = _metadata(
        clarify_type=plan.clarify_type,
        route_name=plan.route_name or route_name,
        profile=plan.profile,
        template_id=plan.template_id,
        question_kind=plan.question_kind,
        reason_code=plan.reason_code,
        voice_moves=voice_meta.get('voice_moves'),
        framing_moves=voice_meta.get('framing_moves'),
        narrowing_moves=voice_meta.get('narrowing_moves'),
        source_refs=voice_meta.get('source_refs'),
        voice_layer=voice_meta.get('voice_layer'),
    )
    if response_move:
        meta['response_move'] = response_move
    return ClarificationResult(text=text, metadata=meta)


def build_clarification(question: str, *,
                        selected: dict | None = None,
                        fallback_text: str = '',
                        dialogue_state: dict | None = None,
                        dialogue_frame: dict | None = None,
                        dialogue_act: str = '',
                        selected_axis: str = '',
                        selected_detail: str = '') -> ClarificationResult:
    selected = selected or {}
    dialogue_state = dialogue_state or {}
    dialogue_frame = dialogue_frame or {}
    route_name = selected.get('route_name') or infer_route(question)
    q = _normalize(question)
    frame_topic = dialogue_frame.get('topic') or dialogue_state.get('active_topic', '')
    frame_goal = dialogue_frame.get('goal', '')
    frame_stance = dialogue_frame.get('stance') or dialogue_state.get('abstraction_level', 'personal')
    frame_relation = dialogue_frame.get('relation_to_previous', '')
    use_act_fallback = not frame_topic
    frame_plan = plan_frame_render(
        route_name=route_name,
        dialogue_state=dialogue_state,
        dialogue_frame=dialogue_frame,
        dialogue_act=dialogue_act,
        selected_axis=selected_axis,
        selected_detail=selected_detail,
    )
    if frame_plan is not None:
        return _render_from_frame_plan(
            frame_plan,
            route_name=route_name,
            dialogue_state=dialogue_state,
            dialogue_frame=dialogue_frame,
        )

    if use_act_fallback:
        act_fallback_plan = plan_act_fallback_render(
            question=question,
            route_name=route_name,
            dialogue_state=dialogue_state,
            dialogue_act=dialogue_act,
            selected_axis=selected_axis,
            selected_detail=selected_detail,
        )
        if act_fallback_plan is not None:
            return _render_from_frame_plan(
                act_fallback_plan,
                route_name=route_name,
                dialogue_state=dialogue_state,
                dialogue_frame=dialogue_frame,
            )

    if not q:
        text, voice_meta = _render_profile('empty-input')
        return ClarificationResult(
            text=text,
            metadata=_metadata(
                clarify_type='empty_or_media',
                route_name=route_name,
                profile='empty-input',
                template_id='empty-input.v1',
                question_kind='restatement',
                reason_code='empty-input',
                voice_moves=voice_meta.get('voice_moves'),
                framing_moves=voice_meta.get('framing_moves'),
                narrowing_moves=voice_meta.get('narrowing_moves'),
                source_refs=voice_meta.get('source_refs'),
                voice_layer=voice_meta.get('voice_layer'),
            ),
        )

    if route_name == 'relationship-maintenance':
        profile = _select_profile(question, route_name)
        if profile:
            text, voice_meta = _render_profile(profile)
            text, response_move = _compose_contextual_response(
                text,
                dialogue_act=dialogue_act,
                dialogue_state=dialogue_state,
            )
            question_kind = (_PROFILE_SPECS.get(profile) or {}).get('question_kind', 'narrowing')
            meta = _metadata(
                clarify_type='human_problem',
                route_name=route_name,
                profile=profile,
                template_id=f'{profile}.v1',
                question_kind=question_kind,
                voice_moves=voice_meta.get('voice_moves'),
                framing_moves=voice_meta.get('framing_moves'),
                narrowing_moves=voice_meta.get('narrowing_moves'),
                source_refs=voice_meta.get('source_refs'),
                voice_layer=voice_meta.get('voice_layer'),
            )
            if response_move:
                meta['response_move'] = response_move
            return ClarificationResult(
                text=text,
                metadata=meta,
            )

    if _contains_any(q, _SCOPE_PROBE_MARKERS):
        text, voice_meta = _render_profile('scope-topics')
        return ClarificationResult(
            text=text,
            metadata=_metadata(
                clarify_type='scope',
                route_name=route_name,
                profile='scope-topics',
                template_id='scope-topics.v1',
                question_kind='topic_selection',
                reason_code='scope-topics',
                voice_moves=voice_meta.get('voice_moves'),
                framing_moves=voice_meta.get('framing_moves'),
                narrowing_moves=voice_meta.get('narrowing_moves'),
                source_refs=voice_meta.get('source_refs'),
                voice_layer=voice_meta.get('voice_layer'),
            ),
        )

    if route_name == 'general' and _contains_any(q, _ABSTRACT_FOLLOWUP_MARKERS):
        text, voice_meta = _render_profile('abstract-followup')
        return ClarificationResult(
            text=text,
            metadata=_metadata(
                clarify_type='scope',
                route_name=route_name,
                profile='abstract-followup',
                template_id='abstract-followup.v1',
                question_kind='topic_restate',
                reason_code='abstract-followup',
                voice_moves=voice_meta.get('voice_moves'),
                framing_moves=voice_meta.get('framing_moves'),
                narrowing_moves=voice_meta.get('narrowing_moves'),
                source_refs=voice_meta.get('source_refs'),
                voice_layer=voice_meta.get('voice_layer'),
            ),
        )

    if _contains_any(q, _SOURCE_LOOKUP_MARKERS):
        text, voice_meta = _render_profile('source-lookup')
        return ClarificationResult(
            text=text,
            metadata=_metadata(
                clarify_type='source',
                route_name=route_name,
                profile='source-lookup',
                template_id='source-lookup.v1',
                question_kind='source_anchor',
                reason_code='source-lookup',
                voice_moves=voice_meta.get('voice_moves'),
                framing_moves=voice_meta.get('framing_moves'),
                narrowing_moves=voice_meta.get('narrowing_moves'),
                source_refs=voice_meta.get('source_refs'),
                voice_layer=voice_meta.get('voice_layer'),
            ),
        )

    if route_name in _HUMAN_PROBLEM_ROUTES:
        profile = _select_profile(question, route_name)
        if profile:
            text, voice_meta = _render_profile(profile)
            return ClarificationResult(
                text=text,
                metadata=_metadata(
                    clarify_type='human_problem',
                    route_name=route_name,
                    profile=profile,
                    template_id=f'{profile}.v1',
                    question_kind=(_PROFILE_SPECS.get(profile) or {}).get('question_kind', 'narrowing'),
                    voice_moves=voice_meta.get('voice_moves'),
                    framing_moves=voice_meta.get('framing_moves'),
                    narrowing_moves=voice_meta.get('narrowing_moves'),
                    source_refs=voice_meta.get('source_refs'),
                    voice_layer=voice_meta.get('voice_layer'),
                ),
            )

    profile = 'fallback'
    text, voice_meta = _render_profile(profile)
    clarify_type = 'generic'
    if route_name == 'general':
        clarify_type = 'source'
        profile = 'source-lookup'
        text, voice_meta = _render_profile(profile)
    if fallback_text:
        text = fallback_text

    return ClarificationResult(
        text=text,
        metadata=_metadata(
            clarify_type=clarify_type,
            route_name=route_name,
            profile=profile,
            template_id=f'{profile}.v1',
            question_kind=(
                'source_anchor'
                if clarify_type == 'source'
                else (_PROFILE_SPECS.get(profile) or {}).get('question_kind', 'restatement')
            ),
            reason_code='source-lookup' if clarify_type == 'source' else 'kb-grounding-gap',
            voice_moves=voice_meta.get('voice_moves'),
            framing_moves=voice_meta.get('framing_moves'),
            narrowing_moves=voice_meta.get('narrowing_moves'),
            source_refs=voice_meta.get('source_refs'),
            voice_layer=voice_meta.get('voice_layer'),
        ),
    )
