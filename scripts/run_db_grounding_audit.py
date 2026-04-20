#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from library._core.runtime.orchestrator import orchestrate_for_llm
from library._adapters.fs_store import FileSystemStore


def build_questions() -> list[dict]:
    clusters: dict[str, list[str]] = {
        'success-structure': [
            'какие качества чаще всего есть у по-настоящему успешных людей?',
            'что сильнее всего отличает успешных людей от неуспешных?',
            'какие внутренние черты чаще всего приводят человека к успеху?',
            'какие привычки делают человека устойчиво успешным?',
            'какие качества у людей, которые долго выигрывают в жизни?',
            'что обычно общего у дисциплинированных и успешных людей?',
            'какие паттерны мышления чаще всего есть у сильных и успешных людей?',
            'что чаще всего мешает человеку стать по-настоящему успешным?',
            'какие качества важнее таланта, если человек хочет преуспеть?',
            'на что смотреть, если хочешь понять, будет ли человек успешным?',
        ],
        'vision-career': [
            'как понять, в каком направлении мне строить жизнь?',
            'как собрать внятное видение будущего, если внутри туман?',
            'как выбрать цель, если мне интересно слишком многое?',
            'что делать, если я умный, но без направления?',
            'как превратить смутное желание в работающий жизненный план?',
            'как перестать дрейфовать и начать двигаться осмысленно?',
            'как понять, какой путь действительно мой?',
            'как построить образ будущего, который выдержит реальность?',
            'что делать, если я всё понимаю, но не могу выбрать курс?',
            'как отличить настоящее призвание от фантазии о себе?',
        ],
        'discipline-routine': [
            'как стать дисциплинированнее, если я быстро сдуваюсь?',
            'почему я всё время откладываю даже важные вещи?',
            'как выстроить режим, если я живу рывками?',
            'что делать, если мне нужен порядок, но я постоянно распадаюсь?',
            'как перестать ждать мотивацию перед действием?',
            'как научиться выдерживать скучную регулярность?',
            'как сделать так, чтобы полезное действие стало вероятнее?',
            'что ломает дисциплину сильнее всего?',
            'как перестать разрушать собственный ритм?',
            'как выстраивать структуру, если меня тянет в хаос?',
        ],
        'truth-conflict': [
            'как говорить правду в трудном разговоре без лишней жестокости?',
            'что делать, если я коплю жалобу и не могу сказать её точно?',
            'почему люди уходят в общие обвинения вместо точной правды?',
            'как назвать проблему ясно, а не размыто?',
            'что делать, если правда вызывает страх конфликта?',
            'как перестать лгать себе о том, что меня реально мучает?',
            'как точнее говорить в отношениях, когда всё уже накалено?',
            'почему неясная жалоба так разрушает связь?',
            'как научиться не прятать проблему в тумане?',
            'что важнее в сложном разговоре: мягкость или точность?',
        ],
        'resentment': [
            'как понять, что я уже живу из обиды?',
            'что делать, если внутри накапливается горечь?',
            'почему обида так легко превращается в образ жизни?',
            'как отличить реальную несправедливость от культивируемой горечи?',
            'что делать, если я всё больше смотрю на мир с раздражением?',
            'как выйти из resentment, если кажется, что у меня есть причины злиться?',
            'почему бессилие так часто превращается в скрытую злобу?',
            'как перестать питаться grievance?',
            'что делать, если я становлюсь всё более циничным и злым?',
            'как не дать обиде организовать мою личность?',
        ],
        'shame-self-contempt': [
            'что делать, если мне стыдно за себя целиком?',
            'как не перепутать вину за поступок с отвращением к себе?',
            'почему стыд так быстро становится тотальным приговором личности?',
            'как восстанавливаться после унизительного провала?',
            'что делать, если мне кажется, что я ничтожный человек?',
            'как не превратить честность в самоуничтожение?',
            'что помогает выбраться из self-contempt?',
            'как работать со стыдом так, чтобы он вел к реорганизации, а не к распаду?',
            'почему некоторые люди тонут в shame вместо того, чтобы исправляться?',
            'что делать, если даже маленький шаг кажется унизительным?',
        ],
        'relationships': [
            'как не разрушать отношения накопленным молчанием?',
            'что удерживает романтические отношения живыми в долгую?',
            'почему пары начинают жить в скрытом раздражении?',
            'как поддерживать уважение в отношениях, когда оба устали?',
            'что важнее для отношений: чувство или дисциплина?',
            'как не допустить распада близости в быту?',
            'почему партнёры перестают делать друг другу достойное предложение?',
            'что разрушает романтику сильнее всего?',
            'как возвращать правду и игру в отношения, если всё стало механическим?',
            'как не скатиться в взаимную претензию?',
        ],
        'parenting': [
            'как воспитывать ребёнка без избыточной мягкости?',
            'что делает родителя по-настоящему полезным для ребёнка?',
            'почему детям вредна бесструктурная свобода?',
            'как ставить границы ребёнку без злобы?',
            'что значит любить ребёнка так, чтобы не испортить его?',
            'как не вырастить маленького тирана?',
            'почему родители боятся дисциплины больше, чем хаоса?',
            'как понять, что моя доброта к ребёнку стала слабостью?',
            'какая ошибка родителей чаще всего разрушает уважение ребёнка?',
            'как соединить заботу и требовательность в воспитании?',
        ],
        'fear-value': [
            'как понять, что страх показывает мне не только опасность, но и ценность?',
            'почему человек боится именно того, что для него может быть важным?',
            'как отличить трусость от разумной осторожности?',
            'что делать, если страх появляется именно там, где есть рост?',
            'как использовать страх как ориентир, а не только как стоп-сигнал?',
            'почему значимые решения почти всегда включают цену?',
            'как увидеть, за что я готов платить, а за что нет?',
            'что делать, если страх расплывчатый, но сильный?',
            'как понять, что я избегаю ценного именно из-за цены?',
            'почему courage связан не с отсутствием страха, а с его правильным чтением?',
        ],
        'tragedy-suffering': [
            'как не озлобиться перед лицом трагедии?',
            'что значит правильно отвечать на страдание?',
            'почему suffering может либо углубить человека, либо отравить его?',
            'как не сделать из боли мировоззрение?',
            'что держит человека от bitterness, когда жизнь реально тяжёлая?',
            'как смотреть на трагедию без цинизма и без иллюзий?',
            'почему некоторые люди становятся мудрее через боль, а другие только злее?',
            'как сохранять смысл, когда жизнь предъявляет страдание?',
            'что делать, если трагедия сломала мой прежний порядок?',
            'как не дать grievance вырасти из реальной боли?',
        ],
    }
    questions: list[dict] = []
    for theme, rows in clusters.items():
        for idx, question in enumerate(rows, 1):
            questions.append({
                'id': f'{theme}-{idx:02d}',
                'theme': theme,
                'question': question,
            })
    return questions


def is_broad_question(question: str) -> bool:
    q = (question or '').lower()
    markers = [
        'какие качества', 'что отличает', 'что общего', 'что чаще всего',
        'почему некоторые люди', 'что делает', 'what traits', 'what makes',
    ]
    return any(marker in q for marker in markers)


def summarize_case(case: dict, result: dict) -> dict:
    decision = result.get('decision_meta') or {}
    synthesis = result.get('synthesis') or {}
    grounding = synthesis.get('grounding_report') or {}
    fields = grounding.get('fields') or {}
    raw = synthesis.get('raw_selection') or {}
    bundle = (raw.get('bundle') or {})

    heuristic_fields = sorted(
        name for name, meta in fields.items()
        if meta.get('source') == 'heuristic'
    )
    fallback_reasons = sorted(
        reason_key for reason_key in (
            raw.get('selected_theme_reason'),
            raw.get('selected_principle_reason'),
            raw.get('selected_pattern_reason'),
        )
        if reason_key and 'fallback' in reason_key
    )

    failure_flags: list[str] = []
    if decision.get('action') == 'respond-with-kb' and raw.get('route_name') == 'general':
        failure_flags.append('answered_on_general_route')
    if decision.get('action') == 'respond-with-kb' and fallback_reasons:
        failure_flags.append('answered_with_fallback_frame')
    if decision.get('action') == 'respond-with-kb' and heuristic_fields:
        failure_flags.append('answered_with_heuristic_fields')
    if decision.get('action') == 'respond-with-kb' and (decision.get('avg_relevance') or 0) < 0.75:
        failure_flags.append('answered_with_weak_relevance')
    if decision.get('action') == 'respond-with-kb' and is_broad_question(case['question']):
        failure_flags.append('broad_question_answered')
    if decision.get('action') == 'respond-with-kb' and not bundle.get('relevant_claims'):
        failure_flags.append('answered_without_claims')
    if decision.get('action') == 'respond-with-kb' and not bundle.get('relevant_practices'):
        failure_flags.append('answered_without_practices')

    return {
        'id': case['id'],
        'theme': case['theme'],
        'question': case['question'],
        'action': decision.get('action'),
        'mode': result.get('mode'),
        'route_name': decision.get('route_name'),
        'confidence': decision.get('confidence'),
        'avg_relevance': decision.get('avg_relevance'),
        'evidence_count': decision.get('evidence_count'),
        'quote_count': decision.get('quote_count'),
        'backed_fields': grounding.get('backed_fields') or [],
        'missing_fields': grounding.get('missing_fields') or [],
        'heuristic_fields': heuristic_fields,
        'fallback_reasons': fallback_reasons,
        'preferred_sources': bundle.get('preferred_sources') or [],
        'top_theme': ((raw.get('selected_theme') or {}).get('name')),
        'top_principle': ((raw.get('selected_principle') or {}).get('name')),
        'top_pattern': ((raw.get('selected_pattern') or {}).get('name')),
        'claims_count': len(bundle.get('relevant_claims') or []),
        'practices_count': len(bundle.get('relevant_practices') or []),
        'definitions_count': len(bundle.get('relevant_definitions') or []),
        'chapter_summaries_count': len(bundle.get('relevant_chapter_summaries') or []),
        'failure_flags': failure_flags,
    }


def main() -> int:
    store = FileSystemStore(REPO_ROOT / 'workspace')
    questions = build_questions()
    results = []
    for case in questions:
        prompt = orchestrate_for_llm(case['question'], user_id='audit:db-grounding', store=store)
        results.append(summarize_case(case, prompt))

    flag_counter = Counter()
    route_counter = Counter()
    theme_counter = Counter()
    flagged_by_theme: dict[str, list[str]] = defaultdict(list)
    for row in results:
        route_counter[row['route_name'] or ''] += 1
        theme_counter[row['theme']] += 1
        for flag in row['failure_flags']:
            flag_counter[flag] += 1
            if len(flagged_by_theme[row['theme']]) < 6:
                flagged_by_theme[row['theme']].append(flag)

    problematic = [
        row for row in results
        if row['failure_flags']
    ]
    problematic.sort(
        key=lambda row: (
            -len(row['failure_flags']),
            row['avg_relevance'] if row['avg_relevance'] is not None else 1.0,
            row['question'],
        )
    )

    top_patterns = [
        {'pattern': name, 'count': count}
        for name, count in flag_counter.most_common()
    ]
    examples = problematic[:20]
    payload = {
        'total_questions': len(results),
        'answered': sum(1 for row in results if row['action'] == 'respond-with-kb'),
        'clarified': sum(1 for row in results if row['action'] == 'ask-clarifying-question'),
        'routes': dict(route_counter),
        'themes': dict(theme_counter),
        'top_failure_patterns': top_patterns,
        'problematic_examples': examples,
        'results': results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
