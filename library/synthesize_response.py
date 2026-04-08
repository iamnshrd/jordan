#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')

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


def select(question):
    out = subprocess.check_output(['python3', str(SELECT), question], text=True)
    return json.loads(out)


def normalize_quote_text(q):
    q = q.strip()
    for sep in [' Почему', ' Представьте', ' Но ', ' Это значит', ' Религиозная проблема', ' Трудно представить']:
        idx = q.find(sep)
        if idx > 40:
            q = q[:idx].strip()
            break
    q = q.replace(').', '.').replace('  ', ' ')
    if len(q) > 180:
        q = q[:180].rstrip() + '...'
    return q


def first_quote(rows):
    if not rows:
        return None
    return normalize_quote_text(rows[0]['quote_text'])


def select_supporting_quote(bundle, selected):
    rows = bundle.get('relevant_quotes', []) or []
    if not rows:
        return None
    theme = ((selected.get('selected_theme') or {}).get('name'))
    principle = ((selected.get('selected_principle') or {}).get('name'))
    pattern = ((selected.get('selected_pattern') or {}).get('name'))
    q = (selected.get('question') or '').lower()
    preferred_types = []
    if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител', 'тирана']):
        preferred_types = ['relationship-quote', 'principle-quote', 'discipline-quote']
        for row in rows:
            if row.get('quote_type') == 'relationship-quote' and (row.get('note') or '').startswith('manual'):
                return normalize_quote_text(row['quote_text'])
    elif any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес', 'путь']):
        for row in rows:
            if row.get('quote_type') == 'discipline-quote' and (row.get('note') or '').startswith('manual'):
                return normalize_quote_text(row['quote_text'])
        preferred_types = ['discipline-quote', 'principle-quote']
    elif principle == 'clean-up-what-is-in-front-of-you':
        for row in rows:
            qt = (row.get('quote_text') or '').strip()
            if qt == 'Наведите идеальный порядок у себя дома.':
                return normalize_quote_text(qt)
        for row in rows:
            if row.get('principle_name') == 'clean-up-what-is-in-front-of-you' and row.get('theme_name') == 'meaning':
                return normalize_quote_text(row['quote_text'])
        preferred_types = ['discipline-quote', 'principle-quote']
    elif principle == 'tell-the-truth-or-at-least-dont-lie' and theme == 'suffering':
        preferred_types = ['shame-quote', 'principle-quote']
    elif theme == 'resentment':
        preferred_types = ['resentment-quote', 'relationship-quote', 'principle-quote']
    elif theme == 'responsibility':
        preferred_types = ['relationship-quote', 'principle-quote']
    elif theme == 'meaning':
        preferred_types = ['discipline-quote', 'principle-quote']
    else:
        preferred_types = ['principle-quote', 'discipline-quote', 'relationship-quote', 'shame-quote', 'resentment-quote']

    for ptype in preferred_types:
        for row in rows:
            if row.get('quote_type') == ptype:
                return normalize_quote_text(row['quote_text'])
    return normalize_quote_text(rows[0]['quote_text'])


def synthesize(question):
    selected = select(question)
    bundle = selected.get('bundle', {})
    theme_name = (selected.get('selected_theme') or {}).get('name')
    principle_name = (selected.get('selected_principle') or {}).get('name')
    pattern_name = (selected.get('selected_pattern') or {}).get('name')
    core_problem = THEME_MAP.get(theme_name, 'Нужно точнее определить, в чём ядро проблемы.')
    pattern_text = PATTERN_MAP.get(pattern_name, 'Здесь есть повторяющийся разрушительный паттерн, который стоит назвать точнее.')
    principle_text = PRINCIPLE_MAP.get(principle_name, 'Нужен принцип, который вернёт структуру и направление.')
    practical = 'Следующий шаг — сузить проблему до одной сферы, где ты реально можешь навести порядок уже сегодня.'
    if principle_name == 'clean-up-what-is-in-front-of-you':
        practical = 'Следующий шаг — выбрать одну зону локального беспорядка и привести её в порядок сегодня, а не когда-нибудь потом.'
    elif principle_name == 'tell-the-truth-or-at-least-dont-lie':
        practical = 'Следующий шаг — письменно сформулировать, что именно ты разрушил, чего избегаешь и что продолжаешь себе про это рассказывать.'
    elif principle_name == 'take-responsibility-before-blame':
        practical = 'Следующий шаг — назвать одну обязанность, которую ты перестал нести, и вернуть её себе добровольно.'

    if theme_name == 'resentment' and pattern_name == 'resentment-loop':
        practical = 'Следующий шаг — письменно отделить, где была реальная несправедливость, а где ты сам много раз промолчал, уступил или отступил.'
    if selected.get('selected_theme_reason') == 'relationship tie-break':
        practical = 'Следующий шаг — назвать один повторяющийся конфликт, один невысказанный упрёк и одну границу, которую ты не обозначаешь прямо.'
    if selected.get('selected_theme_reason') == 'resentment tie-break':
        practical = 'Следующий шаг — прекратить пересказывать себе историю о несправедливости и вместо этого назвать одну точку, где ты всё ещё можешь действовать.'
    if 'shame' in (selected.get('selected_theme_reason') or '') or any(x in question.lower() for x in ['стыд', 'позор', 'отвращение к себе']):
        practical = 'Следующий шаг — назвать один конкретный поступок или провал, за который тебе стыдно, не превращая его в тотальный приговор себе целиком.'

    responsibility_avoided = 'Есть ощущение, что часть ответственности была отложена, а вместе с ней распалась и опора.'
    if selected.get('selected_principle_reason') == 'discipline/order tie-break':
        responsibility_avoided = 'Скорее всего, ты перестал добровольно наводить локальный порядок и начал ждать мотивацию раньше структуры.'
    elif selected.get('selected_principle_reason') == 'meaning-direction tie-break':
        responsibility_avoided = 'Похоже, что ты уклоняешься от выбора направления и от ответственности, которая идёт вместе с ним.'
    longer_term = 'Долгосрочная коррекция требует более честной структуры жизни, а не только эмоционального облегчения.'
    if theme_name == 'meaning':
        longer_term = 'Тебе нужно не ждать возвращения смысла как чувства, а заново строить его через цель, дисциплину и повторяющееся действие.'
    elif theme_name == 'resentment':
        longer_term = 'Долгосрочно придётся отделить реальную несправедливость от горечи, которая выросла из избегания и бессилия.'
    elif any(x in question.lower() for x in ['стыд', 'позор', 'отвращение к себе']):
        longer_term = 'Долгосрочно нужно научиться различать вину за поступок и тотальное отвержение собственной личности.'
    elif selected.get('selected_theme_reason') == 'relationship tie-break':
        longer_term = 'Долгосрочно отношения улучшатся только если прекратится смесь молчаливой уступчивости, обиды и непрямой коммуникации.'

    return {
        'question': question,
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
        'source_blend': selected.get('source_blend'),
        'confidence': selected.get('confidence'),
        'raw_selection': selected,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(synthesize(args.question), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
