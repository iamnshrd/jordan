"""Response synthesis -- combine frame, V3 query, and progress into a response bundle.

Restructured from: synthesize_response.py
Dead-code removal: first assignments to practical / longer_term that were
immediately overwritten by db_driven_* calls have been removed.
"""
from __future__ import annotations

from library._core.runtime.frame import select_frame
from library._core.kb.query_v3 import query_v3
from library._core.session.progress import estimate as estimate_progress
from library._core.state_store import StateStore
from library.config import INTERVENTION_PATTERNS, SOURCE_BLEND_EXAMPLES
from library.utils import load_json, timed


# ── intervention patterns & source blend data ─────────────────────────

_intervention_patterns_cache: list | None = None
_source_blend_cache: list | None = None


def _get_intervention_patterns() -> list:
    global _intervention_patterns_cache
    if _intervention_patterns_cache is None:
        _intervention_patterns_cache = load_json(INTERVENTION_PATTERNS, default=[])
    return _intervention_patterns_cache


def _get_source_blend_examples() -> list:
    global _source_blend_cache
    if _source_blend_cache is None:
        _source_blend_cache = load_json(SOURCE_BLEND_EXAMPLES, default=[])
    return _source_blend_cache


def match_intervention_pattern(route_name: str, pattern_name: str) -> dict | None:
    """Find the best matching intervention pattern for the given route/pattern."""
    for ip in _get_intervention_patterns():
        when = ip.get('when_to_use', [])
        if route_name in when or pattern_name in when:
            return ip
    return None


def match_source_blend(route_name: str) -> dict | None:
    """Find source blend guidance for the given route."""
    for blend in _get_source_blend_examples():
        if blend.get('route') == route_name:
            return blend
    return None


# ── text maps ─────────────────────────────────────────────────────────

THEME_MAP = {
    'meaning': 'Проблема упирается в утрату смысла и ориентации.',
    'responsibility': 'Здесь есть тема ответственности и добровольно принятого бремени.',
    'order-and-chaos': 'Похоже, что хаос перевешивает порядок и структура распалась.',
    'truth': 'Есть риск самообмана или неясности в том, что именно происходит.',
    'suffering': 'Слой страдания здесь не побочный — он структурный.',
    'resentment': 'Под проблемой может копиться обида или горечь.',
}

PRINCIPLE_MAP = {
    'take-responsibility-before-blame': 'Сначала нужно вернуть себе агентность, а не объяснять всё внешними силами.',
    'clean-up-what-is-in-front-of-you': 'Начинать стоит с локального порядка, а не с абстрактного спасения всей жизни целиком.',
    'tell-the-truth-or-at-least-dont-lie': 'Нужно назвать проблему точно и перестать лгать себе о её масштабе и природе.',
}

PATTERN_MAP = {
    'aimlessness': 'Основной паттерн похож на утрату цели и распад направления.',
    'avoidance-loop': 'Проблема может поддерживаться избеганием и откладыванием.',
    'resentment-loop': 'Есть риск, что бессилие уже превращается в горечь.',
}

THEME_DESC_MAP = {
    'meaning': 'Смысл здесь выступает как ориентация против хаоса и страдания.',
    'responsibility': 'Ответственность здесь выступает как стабилизирующая сила, а не как абстрактный моральный жест.',
    'order-and-chaos': 'Проблема выглядит как перекос между структурой и неопределённостью.',
    'truth': 'Здесь важно точное называние реальности как форма психологической дисциплины.',
    'resentment': 'Обида здесь выглядит не случайной эмоцией, а следствием слабости, уклонения или предательства.',
}

PRINCIPLE_DESC_MAP = {
    'clean-up-what-is-in-front-of-you': 'Начинать стоит с локального порядка, прежде чем пытаться починить всю жизнь целиком.',
    'tell-the-truth-or-at-least-dont-lie': 'Правдивость здесь нужна как основа внутренней целостности.',
    'take-responsibility-before-blame': 'Сначала нужно взять на себя ответственность, а уже потом обвинять мир.',
}

PATTERN_DESC_MAP = {
    'avoidance-loop': 'Избегание создаёт страх, слабость и ещё больше избегания.',
    'resentment-loop': 'Обида растёт там, где ответственность отвергается, а grievance культивируется.',
    'aimlessness': 'Отсутствие цели постепенно разъедает мотивацию и самоуважение.',
}


# ── db-driven text generators ─────────────────────────────────────────

def db_driven_theme_text(theme_name, selected):
    desc = ((selected.get('selected_theme') or {}).get('description') or '').strip()
    if desc:
        return desc
    return THEME_DESC_MAP.get(theme_name,
           THEME_MAP.get(theme_name,
                         'Нужно точнее определить, в чём ядро проблемы.'))


def db_driven_principle_text(principle_name, selected):
    desc = ((selected.get('selected_principle') or {}).get('description') or '').strip()
    if desc:
        return desc
    return PRINCIPLE_DESC_MAP.get(principle_name,
           PRINCIPLE_MAP.get(principle_name,
                             'Нужен принцип, который вернёт структуру и направление.'))


def db_driven_pattern_text(pattern_name, selected):
    desc = ((selected.get('selected_pattern') or {}).get('description') or '').strip()
    if desc:
        return desc
    return PATTERN_DESC_MAP.get(pattern_name,
           PATTERN_MAP.get(pattern_name,
                           'Здесь есть повторяющийся разрушительный паттерн, который стоит назвать точнее.'))


def db_driven_responsibility_text(selected, bridge, question):
    stub = (bridge.get('responsibility_stub') or '').strip()
    if stub:
        return stub
    q = (question or '').lower()
    theme_name = (selected.get('selected_theme') or {}).get('name')
    principle_reason = selected.get('selected_principle_reason') or ''
    if principle_reason == 'discipline/order tie-break':
        return 'Скорее всего, ты перестал добровольно наводить локальный порядок и начал ждать мотивацию раньше структуры.'
    if principle_reason == 'meaning-direction tie-break':
        return 'Похоже, что ты уклоняешься от выбора направления и от ответственности, которая идёт вместе с ним.'
    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        return 'Похоже, ты избегаешь точного признания поступка и заменяешь его тотальным осуждением себя.'
    if theme_name == 'resentment':
        return 'Похоже, ты долго терпишь, копишь обиду и не называешь прямо то, что должно быть вынесено в разговор.'
    return 'Есть ощущение, что часть ответственности была отложена, а вместе с ней распалась и опора.'


def db_driven_longer_term_text(selected, bridge, question):
    stub = (bridge.get('long_term_stub') or '').strip()
    if stub:
        return stub
    q = (question or '').lower()
    theme_name = (selected.get('selected_theme') or {}).get('name')
    if theme_name == 'meaning':
        return 'Тебе нужно не ждать возвращения смысла как чувства, а заново строить его через цель, дисциплину и повторяющееся действие.'
    if theme_name == 'resentment':
        return 'Долгосрочно придётся отделить реальную несправедливость от горечи, которая выросла из избегания и бессилия.'
    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        return 'Долгосрочно нужно научиться различать вину за поступок и тотальное отвержение собственной личности.'
    return 'Долгосрочная коррекция требует более честной структуры жизни, а не только эмоционального облегчения.'


def db_driven_practical_text(selected, next_step_v3, question):
    step = (next_step_v3.get('step_text') or '').strip()
    if step:
        return step
    q = (question or '').lower()
    principle_name = (selected.get('selected_principle') or {}).get('name')
    theme_name = (selected.get('selected_theme') or {}).get('name')
    theme_reason = selected.get('selected_theme_reason') or ''
    if principle_name == 'clean-up-what-is-in-front-of-you':
        return 'Следующий шаг — выбрать одну зону локального беспорядка и привести её в порядок сегодня, а не когда-нибудь потом.'
    if principle_name == 'tell-the-truth-or-at-least-dont-lie':
        return 'Следующий шаг — письменно сформулировать, что именно ты разрушил, чего избегаешь и что продолжаешь себе про это рассказывать.'
    if principle_name == 'take-responsibility-before-blame':
        return 'Следующий шаг — назвать одну обязанность, которую ты перестал нести, и вернуть её себе добровольно.'
    if theme_name == 'resentment' and theme_reason == 'relationship tie-break':
        return 'Следующий шаг — назвать один повторяющийся конфликт, один невысказанный упрёк и одну границу, которую ты не обозначаешь прямо.'
    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        return 'Следующий шаг — назвать один конкретный поступок или провал, за который тебе стыдно, не превращая его в тотальный приговор себе целиком.'
    return 'Следующий шаг — сузить проблему до одной сферы, где ты реально можешь навести порядок уже сегодня.'


# ── quote helpers ─────────────────────────────────────────────────────

def normalize_quote_text(q):
    q = q.strip()
    for sep in [' Почему', ' Представьте', ' Но ', ' Это значит',
                ' Религиозная проблема', ' Трудно представить']:
        idx = q.find(sep)
        if idx > 40:
            q = q[:idx].strip()
            break
    q = q.replace(').', '.').replace('  ', ' ')
    if len(q) > 180:
        q = q[:180].rstrip() + '...'
    return q


def select_supporting_quote(bundle, selected):
    rows = bundle.get('relevant_quotes', []) or []
    if not rows:
        return None
    theme = ((selected.get('selected_theme') or {}).get('name'))
    principle = ((selected.get('selected_principle') or {}).get('name'))
    q = (selected.get('question') or '').lower()

    preferred_types = []
    if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител', 'тирана']):
        preferred_types = ['relationship-quote', 'principle-quote',
                           'discipline-quote']
        for row in rows:
            if (row.get('quote_type') == 'relationship-quote'
                    and (row.get('note') or '').startswith('manual')
                    and row.get('quote_text')):
                return normalize_quote_text(row['quote_text'])
    elif any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес',
                               'путь']):
        for row in rows:
            if (row.get('quote_type') == 'discipline-quote'
                    and (row.get('note') or '').startswith('manual')
                    and row.get('quote_text')):
                return normalize_quote_text(row['quote_text'])
        preferred_types = ['discipline-quote', 'principle-quote']
    elif principle == 'clean-up-what-is-in-front-of-you':
        preferred_types = ['discipline-quote', 'principle-quote']
    elif (principle == 'tell-the-truth-or-at-least-dont-lie'
          and theme == 'suffering'):
        preferred_types = ['shame-quote', 'principle-quote']
    elif theme == 'resentment':
        preferred_types = ['resentment-quote', 'relationship-quote',
                           'principle-quote']
    elif theme == 'responsibility':
        preferred_types = ['relationship-quote', 'principle-quote']
    elif theme == 'meaning':
        preferred_types = ['discipline-quote', 'principle-quote']
    else:
        preferred_types = ['principle-quote', 'discipline-quote',
                           'relationship-quote', 'shame-quote',
                           'resentment-quote']

    for ptype in preferred_types:
        for row in rows:
            if row.get('quote_type') == ptype and row.get('quote_text'):
                return normalize_quote_text(row['quote_text'])
    first_text = rows[0].get('quote_text') or ''
    return normalize_quote_text(first_text) if first_text else ''


# ── archetype inference ───────────────────────────────────────────────

def infer_archetype(question):
    """Delegate to the canonical route classifier in frame.py."""
    from library._core.runtime.frame import infer_route_name
    route = infer_route_name(question)
    return '' if route == 'general' else route


# ── text assembly helpers ─────────────────────────────────────────────

def append_sentence(base, addition):
    base = (base or '').strip()
    addition = (addition or '').strip()
    if not addition:
        return base
    if addition in base:
        return base
    if not base:
        return addition
    return base.rstrip() + ' ' + addition


def should_suppress_progress_extra(question, practical, next_step_v3,
                                   anti_patterns, intervention_links):
    q = (question or '').lower()
    practical = (practical or '').lower()
    if (next_step_v3.get('confidence_level') == 'high'
            and len((next_step_v3.get('step_text') or '').split()) >= 8):
        return True
    if 'abstract-inflation' in (anti_patterns or []):
        return True
    if 'narrow-burden' in (intervention_links or []):
        return True
    if (any(x in q for x in ['жена', 'муж', 'отношен', 'конфликт'])
            and any(x in practical for x in ['разговор', 'скажи', 'обсуди'])):
        return True
    if (any(x in q for x in ['стыд', 'позор', 'отвращение к себе'])
            and any(x in practical for x in ['восстановительный шаг',
                                              'не превращай',
                                              'признания поступка'])):
        return True
    return False


def compress_longer_term(longer_term, best_case, anti_patterns, v3):
    parts = []
    seen = set()

    def add(text):
        text = (text or '').strip()
        if not text or text in seen:
            return
        seen.add(text)
        parts.append(text)

    base = (longer_term or '').strip()
    if ' Ближайший аналог:' in base:
        base = base.split(' Ближайший аналог:')[0].strip()
    add(base)

    shame_case = (best_case.get('case_name')
                  == 'Shame marks exposed insufficiency before reorganization')
    shame_guard = 'identity-annihilation' in (anti_patterns or [])

    if best_case.get('case_name'):
        if shame_case and shame_guard:
            add('Ближайший аналог: Shame marks exposed insufficiency before '
                'reorganization. Смысл здесь не в самоуничтожении, а в '
                'реорганизации после честного признания.')
        else:
            case_line = f"Ближайший аналог: {best_case['case_name']}."
            if best_case.get('confidence_level') == 'high':
                case_line += (' Это высоко-уверенный ориентир, а не случайная '
                              'аналогия.')
            else:
                case_line += (' Это полезная рабочая аналогия, но не '
                              'окончательный якорь.')
            add(case_line)

    if shame_guard and not shame_case:
        add('Не превращай исправление в театральное самоуничтожение.')

    if (v3.get('symbolic_permission')
            and 'dragon' in (v3.get('motif_links') or [])):
        add('Здесь есть мотив встречи с неизвестным, а не только мотив '
            'поломки.')

    return ' '.join(parts).strip()


def collect_practical_extras(question, practical, next_step_v3, anti_patterns,
                             intervention_links, motif_links, v3,
                             progress_extra):
    extras = []
    q = (question or '').lower()

    if ('abstract-inflation' in anti_patterns
            and any(x in q for x in ['карьер', 'призвание', 'путь'])):
        extras.append(('anti-pattern',
                       'Не раздувай это в метафизическую драму: выбери один '
                       'рабочий вектор.'))

    if intervention_links and 'narrow-burden' in intervention_links:
        extras.append(('intervention',
                       'Сузь задачу до одного добровольно принятого '
                       'бремени.'))

    if (v3.get('symbolic_permission')
            and motif_links and 'burden' in motif_links):
        extras.append(('symbolic',
                       'Смотри на это как на вопрос о том, какое бремя ты '
                       'готов нести.'))

    if (progress_extra
            and not should_suppress_progress_extra(
                question, practical, next_step_v3, anti_patterns,
                intervention_links)):
        extras.append(('progress', progress_extra))

    return extras


def collect_longer_extras(motif_links, v3):
    extras = []
    if (v3.get('symbolic_permission')
            and motif_links and 'dragon' in motif_links):
        extras.append(('symbolic',
                       'Здесь есть мотив встречи с неизвестным, а не только '
                       'мотив поломки.'))
    return extras


def apply_priority_pruning(practical, longer_term, practical_extras,
                           longer_extras):
    practical_priority = {
        'anti-pattern': 4, 'intervention': 3, 'progress': 2, 'symbolic': 1,
    }
    longer_priority = {'anti-pattern': 3, 'symbolic': 2}

    if practical_extras:
        practical_extras = sorted(
            practical_extras,
            key=lambda x: -practical_priority.get(x[0], 0),
        )
        practical = append_sentence(practical, practical_extras[0][1])
    if longer_extras:
        longer_extras = sorted(
            longer_extras,
            key=lambda x: -longer_priority.get(x[0], 0),
        )
        longer_term = append_sentence(longer_term, longer_extras[0][1])
    return practical, longer_term


def build_grounding_report(selected, bundle, v3, data) -> dict:
    """Expose which synthesis fields are DB-backed vs heuristic/runtime-derived."""
    theme_desc = ((selected.get('selected_theme') or {}).get('description') or '').strip()
    pattern_desc = ((selected.get('selected_pattern') or {}).get('description') or '').strip()
    principle_desc = ((selected.get('selected_principle') or {}).get('description') or '').strip()
    bridge = (v3 or {}).get('bridge') or {}
    next_step = (v3 or {}).get('next_step') or {}
    chunks = bundle.get('relevant_chunks', []) or []
    quotes = bundle.get('relevant_quotes', []) or []

    fields = {
        'core_problem': {
            'backed': bool((bridge.get('diagnosis_stub') or '').strip() or theme_desc),
            'source': 'bridge' if (bridge.get('diagnosis_stub') or '').strip() else ('theme-description' if theme_desc else 'heuristic'),
        },
        'relevant_pattern': {
            'backed': bool(pattern_desc),
            'source': 'pattern-description' if pattern_desc else 'heuristic',
        },
        'guiding_principle': {
            'backed': bool(principle_desc),
            'source': 'principle-description' if principle_desc else 'heuristic',
        },
        'responsibility_avoided': {
            'backed': bool((bridge.get('responsibility_stub') or '').strip()),
            'source': 'bridge' if (bridge.get('responsibility_stub') or '').strip() else 'heuristic',
        },
        'practical_next_step': {
            'backed': bool((next_step.get('step_text') or '').strip() or (bridge.get('next_step_stub') or '').strip()),
            'source': 'next-step' if (next_step.get('step_text') or '').strip() else ('bridge' if (bridge.get('next_step_stub') or '').strip() else 'heuristic'),
        },
        'longer_term_correction': {
            'backed': bool((bridge.get('long_term_stub') or '').strip()),
            'source': 'bridge' if (bridge.get('long_term_stub') or '').strip() else 'heuristic',
        },
        'supporting_quote': {
            'backed': bool(data.get('supporting_quote')) and bool(quotes),
            'source': 'quotes' if quotes else 'none',
        },
    }
    backed_fields = [name for name, meta in fields.items() if meta['backed']]
    missing_fields = [name for name, meta in fields.items() if not meta['backed']]
    return {
        'fields': fields,
        'backed_fields': backed_fields,
        'missing_fields': missing_fields,
        'evidence_count': len(chunks),
        'quote_count': len(quotes),
    }


# ── main synthesis ────────────────────────────────────────────────────

def unify_selection_policy(selected, bridge, next_step_v3, question):
    route = selected.get('route_name') or 'general'
    policy = {
        'route': route,
        'prefer_bridge': bool(bridge),
        'prefer_next_step': bool(next_step_v3),
        'suppress_continuity': route in {'career-vocation', 'avoidance-paralysis'},
        'diagnosis_style': 'direct' if route in {'career-vocation', 'avoidance-paralysis'} else 'reflective',
    }
    return policy


@timed('synthesize')
def synthesize(question, user_id: str = 'default',
               store: StateStore | None = None,
               frame: dict | None = None,
               progress: dict | None = None):
    selected = frame or select_frame(question, user_id=user_id, store=store)
    bundle = selected.get('bundle', {})
    if progress is None:
        progress = estimate_progress(question, user_id=user_id, store=store)

    theme_name = (selected.get('selected_theme') or {}).get('name')
    principle_name = (selected.get('selected_principle') or {}).get('name')
    pattern_name = (selected.get('selected_pattern') or {}).get('name')
    archetype = infer_archetype(question)
    v3 = query_v3(theme_name or '', pattern_name or '', archetype)

    core_problem = db_driven_theme_text(theme_name, selected)
    pattern_text = db_driven_pattern_text(pattern_name, selected)
    principle_text = db_driven_principle_text(principle_name, selected)

    bridge = v3.get('bridge') or {}
    next_step_v3 = v3.get('next_step') or {}
    policy = unify_selection_policy(selected, bridge, next_step_v3, question)

    route_name = selected.get('route_name') or 'general'
    intervention = match_intervention_pattern(route_name, pattern_name or '')
    blend_guidance = match_source_blend(route_name)

    if bridge.get('diagnosis_stub'):
        core_problem = bridge['diagnosis_stub']
    elif intervention and intervention.get('opening_move'):
        core_problem = append_sentence(core_problem, intervention['opening_move'])

    responsibility_avoided = db_driven_responsibility_text(
        selected, bridge, question,
    )
    if intervention and intervention.get('core_move') and not bridge.get('responsibility_stub'):
        responsibility_avoided = append_sentence(
            responsibility_avoided, intervention['core_move'],
        )

    longer_term = db_driven_longer_term_text(selected, bridge, question)
    practical = db_driven_practical_text(selected, next_step_v3, question)
    if intervention and intervention.get('followup_move') and not next_step_v3.get('step_text'):
        practical = append_sentence(practical, intervention['followup_move'])

    progress_extra = None
    progress_state = progress.get('progress_state')
    if progress_state == 'stuck':
        practical = ('Следующий шаг — перестать расширять проблему и выбрать '
                     'одну конкретную обязанность или один разговор, который '
                     'ты откладываешь, и сделать только его.')
        longer_term = ('Сейчас тебе меньше всего нужен новый красивый '
                       'анализ. Тебе нужна повторяемая дисциплина в одной '
                       'точке, пока не появится реальное движение.')
    elif progress_state == 'moving':
        progress_extra = 'Не меняй рамку снова: дожми уже выбранное действие.'
    elif progress_state == 'fragile':
        practical = ('Следующий шаг — не ломать себя об глобальные выводы, '
                     'а сделать один маленький, но честный шаг без '
                     'самоунижения.')
        longer_term = ('Долгосрочно тебе нужна не жестокость к себе, а более '
                       'устойчивая форма честности, в которой правда не '
                       'превращается в самоуничтожение.')

    anti_patterns = v3.get('anti_patterns') or []
    case_links = v3.get('case_links') or []
    best_case = v3.get('best_case') or {}
    intervention_links = v3.get('intervention_links') or []
    motif_links = v3.get('motif_links') or []
    conf = v3.get('confidence_summary') or {}

    if not best_case.get('case_name') and case_links:
        best_case = {
            'case_name': case_links[0],
            'confidence_level': None,
        }

    practical_extras = collect_practical_extras(
        question, practical, next_step_v3, anti_patterns,
        intervention_links, motif_links, v3, progress_extra,
    )
    longer_extras = collect_longer_extras(motif_links, v3)

    bridge_conf = bridge if bridge else (conf.get('bridge_confidence') or {})
    if (bridge_conf.get('confidence_level') not in {'high'}
            and bridge.get('diagnosis_stub')):
        core_problem = ('Нужно ещё точнее проверить рамку, но текущая '
                        'рабочая формулировка такая: ' + core_problem)
    if (next_step_v3.get('confidence_level') not in {'high'}
            and next_step_v3.get('step_text')):
        practical = ('Рабочий, но ещё не окончательно проверенный следующий '
                     'шаг: ' + practical)

    practical, longer_term = apply_priority_pruning(
        practical, longer_term, practical_extras, longer_extras,
    )
    longer_term = compress_longer_term(
        longer_term, best_case, anti_patterns, v3,
    )

    source_blend = selected.get('source_blend') or {}
    if blend_guidance and not source_blend:
        source_blend = {
            'primary': blend_guidance.get('primary_source'),
            'secondary': blend_guidance.get('secondary_source'),
            'rationale': blend_guidance.get('why'),
        }

    tone_hint = None
    if intervention:
        tone_hint = intervention.get('tone_profile')

    result = {
        'question': question,
        'selection_policy': policy,
        'core_problem': core_problem,
        'relevant_pattern': pattern_text,
        'responsibility_avoided': responsibility_avoided,
        'guiding_principle': principle_text,
        'supporting_quote': select_supporting_quote(bundle, selected),
        'evidence_preview': bundle.get('relevant_chunks', [])[:3],
        'practical_next_step': practical,
        'longer_term_correction': longer_term,
        'selected_theme_reason': selected.get('selected_theme_reason'),
        'selected_principle_reason': selected.get('selected_principle_reason'),
        'selected_pattern_reason': selected.get('selected_pattern_reason'),
        'preferred_sources': selected.get('preferred_sources'),
        'source_blend': source_blend,
        'source_blend_rationale': (blend_guidance or {}).get('why'),
        'confidence': selected.get('confidence'),
        'tone_hint': tone_hint,
        'intervention_pattern': intervention.get('pattern_name') if intervention else None,
        'progress': progress,
        'v3_runtime': v3,
        'quote_pack': v3.get('quote_pack'),
        'anti_patterns': anti_patterns,
        'case_links': case_links,
        'best_case': best_case,
        'intervention_links': intervention_links,
        'motif_links': motif_links,
        'raw_selection': selected,
    }
    result['grounding_report'] = build_grounding_report(
        selected, bundle, v3, result,
    )
    return result
