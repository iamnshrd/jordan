"""Human-problem clarification profiles for in-domain but weakly grounded asks."""
from __future__ import annotations

from dataclasses import dataclass, field

from library._core.kb.voice_patterns import load_profile_voice_bundle
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


def build_clarification(question: str, *,
                        selected: dict | None = None,
                        fallback_text: str = '') -> ClarificationResult:
    selected = selected or {}
    route_name = selected.get('route_name') or infer_route(question)
    q = _normalize(question)

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
            question_kind = (_PROFILE_SPECS.get(profile) or {}).get('question_kind', 'narrowing')
            return ClarificationResult(
                text=text,
                metadata=_metadata(
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
                ),
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
