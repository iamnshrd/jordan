#!/usr/bin/env python3
import json
import re
from pathlib import Path

SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/quotes_candidates.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/quotes_normalized.json')

BAD_SNIPPETS = [
    'правило 9',
    'правило 10',
    'оглавление',
    'table of contents',
    'copyright',
    'isbn',
    'random house',
    'toronto:',
    'london:',
    'footnote',
    'see also',
    'удк',
    'ббк',
]


def clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\.{2,}', '.', text)
    return text


def classify_quote(text):
    lower = text.lower()
    if 'говорите правду' in lower or 'не лгите' in lower or 'tell the truth' in lower or "don't lie" in lower:
        return ('principle-quote', 'truth', 'tell-the-truth-or-at-least-dont-lie', 'avoidance-loop')
    if 'сравнивайте себя' in lower or 'compare yourself' in lower:
        return ('principle-quote', 'meaning', None, 'aimlessness')
    if 'обращайтесь с собой' in lower or 'treat yourself like someone' in lower:
        return ('principle-quote', 'responsibility', 'take-responsibility-before-blame', None)
    if 'не позволяйте детям' in lower or 'do not let your children' in lower:
        return ('relationship-quote', 'responsibility', None, None)
    if 'убери' in lower or 'комнат' in lower or 'порядок у себя дома' in lower or 'наведите идеальный порядок у себя дома' in lower or 'clean your room' in lower or 'perfect order in your house' in lower:
        return ('discipline-quote', 'order-and-chaos', 'clean-up-what-is-in-front-of-you', 'avoidance-loop')
    if 'стыд' in lower or 'позор' in lower or 'отвращение к себе' in lower or 'shame' in lower:
        return ('shame-quote', 'suffering', None, 'avoidance-loop')
    if 'обида' in lower or 'горечь' in lower or 'resentment' in lower:
        return ('resentment-quote', 'resentment', None, 'resentment-loop')
    return ('general-quote', None, None, None)


def keep(item):
    text = clean(item.get('quote_text', ''))
    lowered = text.lower()
    if len(text) < 60:
        return False
    if any(b in lowered for b in BAD_SNIPPETS):
        return False
    if 'не позволяйте детям' in lowered and 'наведите идеальный порядок у себя дома' in lowered:
        return False
    if sum(ch.isdigit() for ch in text) > 18:
        return False
    if sum(1 for ch in text if ch.isupper()) > max(25, len(text) * 0.35):
        return False
    if text.count(':') >= 3:
        return False
    if text.count('.') <= 0 and len(text) > 180:
        return False
    if any(x in lowered for x in ['rule i', 'rule ii', 'rule iii', 'rule iv', 'rule v', 'rule vi', 'rule vii', 'rule viii', 'rule ix', 'rule x', 'rule xi', 'rule xii']):
        return False
    if re.search(r'\b\d{2,4}\b(?:\s+\b\d{2,4}\b){3,}', lowered):
        return False
    if re.search(r'\b[A-ZА-ЯЁ]{4,}\b(?:\s+\b[A-ZА-ЯЁ]{4,}\b){3,}', text):
        return False
    if not any(x in lowered for x in ['правд', 'tell the truth', 'сравнива', 'compare yourself', 'обращайтесь', 'treat yourself like', 'убери', 'clean your room', 'предполаг', 'assume that the person', 'не позволяйте', 'do not let your children', 'порядок у себя дома', 'perfect order in your house', 'стыд', 'позор', 'shame', 'обида', 'горечь', 'resentment']):
        return False
    return True


def main():
    data = json.loads(SRC.read_text())
    out = []
    seen = set()
    for item in data:
        if not keep(item):
            continue
        quote = clean(item['quote_text'])
        key = quote[:160].lower()
        if key in seen:
            continue
        seen.add(key)
        qtype, theme, principle, pattern = classify_quote(quote)
        item['quote_text'] = quote
        item['quote_type'] = qtype
        item['theme_name'] = theme
        item['principle_name'] = principle
        item['pattern_name'] = pattern
        out.append(item)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({'quotes_normalized': len(out)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
