#!/usr/bin/env python3
"""Harvest voice-rich transcript excerpts for future Jordan phrasing work."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from library.config import TEXTS, VOICE_EXCERPT_CANDIDATES
from library.utils import save_json


TARGET_FILES = [
    'Master Relationships.txt',
    'romantic relationship.txt',
    'Would You Love the Same Man.txt',
    'Evolution, Sex & Desire  David Buss  EP 235.txt',
    'w_lex.txt',
]

TAG_KEYWORDS = {
    'relationship': [
        'relationship', 'wife', 'husband', 'marriage', 'married', 'partner',
        'romance', 'love', 'conflict', 'resentment', 'betray', 'boundary',
        'boundaries', 'intimacy', 'sexual', 'sex', 'desire', 'rejection',
        'mother', 'father',
    ],
    'meaning': [
        'meaning', 'purpose', 'responsibility', 'burden', 'truth', 'future',
        'past', 'sacrifice', 'order', 'chaos', 'discipline', 'conscience',
        'encouragement', 'direction', 'aim', 'goal',
    ],
    'voice_move': [
        "you don't", 'you have to', 'you want', "that's because",
        'the problem is', 'well', 'look', 'i think', 'you can',
        'you should', 'it means', 'what you do', 'if you',
    ],
}

STRONG_PATTERNS = [
    r"\byou don't\b",
    r'\byou have to\b',
    r'\byou should\b',
    r'\bthe problem is\b',
    r'\bthat means\b',
    r'\bif you\b',
    r'\byou can\b',
    r'\bthat\'s because\b',
]


def _clean_line(line: str) -> str:
    line = re.sub(r'^\s*\d+:\d{2}(?::\d{2})?\s*', '', line)
    line = re.sub(r'\s+', ' ', line)
    return line.strip(' "\'')


def _tags_for_excerpt(text: str) -> list[str]:
    lower = text.lower()
    tags = [
        tag for tag, keywords in TAG_KEYWORDS.items()
        if any(keyword in lower for keyword in keywords)
    ]
    return sorted(tags)


def _score_excerpt(text: str) -> int:
    lower = text.lower()
    score = 0
    length = len(text)
    if 80 <= length <= 320:
        score += 6
    elif 60 <= length <= 420:
        score += 3

    for keywords in TAG_KEYWORDS.values():
        for keyword in keywords:
            if keyword in lower:
                score += 2

    for pattern in STRONG_PATTERNS:
        if re.search(pattern, lower):
            score += 4

    if any(ch in text for ch in '?:'):
        score += 1
    if text[:1].isupper():
        score += 1
    return score


def _iter_candidate_lines(text: str):
    for raw in text.splitlines():
        cleaned = _clean_line(raw)
        if len(cleaned) < 60:
            continue
        if cleaned.lower().startswith(('hello every', 'hello everyone', 'today i\'m')):
            continue
        yield cleaned


def harvest() -> dict:
    files_out = []
    summary = Counter()
    for filename in TARGET_FILES:
        path = TEXTS / filename
        if not path.exists():
            files_out.append({
                'file': filename,
                'missing': True,
                'segments': [],
            })
            continue

        seen: set[str] = set()
        ranked = []
        text = path.read_text(encoding='utf-8', errors='ignore')
        for line in _iter_candidate_lines(text):
            key = re.sub(r'[^a-zа-я0-9]+', ' ', line.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            tags = _tags_for_excerpt(line)
            score = _score_excerpt(line)
            if score < 8 or not tags:
                continue
            ranked.append({
                'score': score,
                'excerpt': line,
                'tags': tags,
            })

        ranked.sort(key=lambda item: (-item['score'], item['excerpt']))
        top = ranked[:20]
        for item in top:
            for tag in item['tags']:
                summary[tag] += 1
        files_out.append({
            'file': filename,
            'missing': False,
            'segments': top,
        })

    result = {
        'generated_at': int(time.time()),
        'target_files': TARGET_FILES,
        'summary': dict(summary),
        'files': files_out,
    }
    save_json(VOICE_EXCERPT_CANDIDATES, result)
    return result


if __name__ == '__main__':
    data = harvest()
    total = sum(len(file['segments']) for file in data['files'])
    print({
        'voice_excerpt_candidates': total,
        'output': str(VOICE_EXCERPT_CANDIDATES),
        'summary': data['summary'],
    })
