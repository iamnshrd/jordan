#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

RETRIEVE = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/retrieve_for_prompt.py')


def retrieve(question):
    out = subprocess.check_output(['python3', str(RETRIEVE), question], text=True)
    return json.loads(out)


def choose_theme(bundle, question):
    q = question.lower()
    rows = bundle.get('top_themes', [])
    if any(x in q for x in ['смысл', 'направление', 'цель', 'дисциплин']):
        for preferred in ['meaning', 'order-and-chaos', 'responsibility']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-loss tie-break'
    if any(x in q for x in ['обид', 'гореч', 'несправед', 'злость']):
        for preferred in ['resentment', 'responsibility']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'resentment tie-break'
    if any(x in q for x in ['отношен', 'партнер', 'конфликт', 'жена', 'муж', 'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        if any(x in q for x in ['обид', 'скрытая обида', 'невысказан']):
            for preferred in ['responsibility', 'resentment', 'truth']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'relationship tie-break'
        if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител', 'тирана']):
            for preferred in ['responsibility', 'order-and-chaos', 'truth']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'parenting tie-break'
        for preferred in ['responsibility', 'truth', 'resentment']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship tie-break'
    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе', 'никчем']):
        for preferred in ['suffering', 'truth', 'responsibility']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'shame tie-break'
    return (rows[0], 'top-score fallback') if rows else (None, 'no theme')


def choose_principle(bundle, question):
    q = question.lower()
    rows = bundle.get('top_principles', [])
    if any(x in q for x in ['дисциплин', 'хаос', 'беспоряд', 'не могу начать']):
        for preferred in ['clean-up-what-is-in-front-of-you', 'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'discipline/order tie-break'
    if any(x in q for x in ['смысл', 'направление', 'цель']):
        for preferred in ['take-responsibility-before-blame', 'clean-up-what-is-in-front-of-you']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-direction tie-break'
    if any(x in q for x in ['отношен', 'партнер', 'конфликт', 'жена', 'муж', 'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител', 'тирана']):
            for preferred in ['clean-up-what-is-in-front-of-you', 'tell-the-truth-or-at-least-dont-lie', 'take-responsibility-before-blame']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'parenting tie-break'
        for preferred in ['tell-the-truth-or-at-least-dont-lie', 'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship tie-break'
    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе', 'никчем']):
        for preferred in ['tell-the-truth-or-at-least-dont-lie', 'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'shame tie-break'
    if any(x in q for x in ['вру', 'самообман', 'лож', 'честн']):
        for preferred in ['tell-the-truth-or-at-least-dont-lie']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'truth tie-break'
    return (rows[0], 'top-score fallback') if rows else (None, 'no principle')


def choose_pattern(bundle, question):
    q = question.lower()
    rows = bundle.get('top_patterns', [])
    if any(x in q for x in ['смысл', 'направление', 'цель']):
        for preferred in ['aimlessness', 'avoidance-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-direction tie-break'
    if any(x in q for x in ['избег', 'прокраст', 'не могу начать', 'отклады']):
        for preferred in ['avoidance-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'avoidance tie-break'
    if any(x in q for x in ['обид', 'гореч', 'злость']):
        for preferred in ['resentment-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'resentment tie-break'
    return (rows[0], 'top-score fallback') if rows else (None, 'no pattern')


def select_frame(question):
    bundle = retrieve(question)
    theme, theme_reason = choose_theme(bundle, question)
    principle, principle_reason = choose_principle(bundle, question)
    pattern, pattern_reason = choose_pattern(bundle, question)
    confidence = 'medium'
    if theme_reason != 'top-score fallback' and principle_reason != 'top-score fallback' and pattern_reason != 'top-score fallback':
        confidence = 'high'
    preferred_sources = bundle.get('preferred_sources')
    source_blend = None
    if preferred_sources and len(preferred_sources) >= 2:
        source_blend = {
            'primary': preferred_sources[0],
            'secondary': preferred_sources[1],
        }
    return {
        'question': question,
        'selected_theme': theme,
        'selected_theme_reason': theme_reason,
        'selected_principle': principle,
        'selected_principle_reason': principle_reason,
        'selected_pattern': pattern,
        'selected_pattern_reason': pattern_reason,
        'confidence': confidence,
        'preferred_sources': preferred_sources,
        'source_blend': source_blend,
        'bundle': bundle,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(select_frame(args.question), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
