#!/usr/bin/env python3
import json
import re
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/quotes_candidates.json')

QUOTE_PATTERNS = [
    r'говори(?:те)? правд[^.]{0,220}',
    r'tell the truth[^.]{0,220}',
    r'сравнивай(?:те)? себя[^.]{0,220}',
    r'compare yourself[^.]{0,220}',
    r'обращайтесь с собой[^.]{0,220}',
    r'treat yourself like[^.]{0,220}',
    r'убер(?:и|ите) свою комнат[^.]{0,220}',
    r'clean your room[^.]{0,220}',
    r'наведите идеальный порядок у себя дома[^.]{0,220}',
    r'perfect order in your house[^.]{0,220}',
    r'не позволяйте детям[^.]{0,220}',
    r'do not let your children[^.]{0,220}',
    r'предполага(?:й|йте), что человек[^.]{0,220}',
    r'assume that the person[^.]{0,220}',
    r'стыд[^.]{0,220}',
    r'позор[^.]{0,220}',
    r'shame[^.]{0,220}',
    r'resentment[^.]{0,220}',
    r'обида[^.]{0,220}',
]


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute('SELECT id, document_id, content FROM document_chunks').fetchall()
    out = []
    for chunk_id, document_id, content in rows:
        text = re.sub(r'\s+', ' ', content).strip()
        lowered = text.lower()
        for pat in QUOTE_PATTERNS:
            m = re.search(pat, lowered)
            if m:
                start = max(0, m.start() - 80)
                end = min(len(text), m.end() + 220)
                snippet = text[start:end].strip()
                out.append({
                    'document_id': document_id,
                    'chunk_id': chunk_id,
                    'quote_text': snippet,
                    'note': f'matched pattern: {pat}'
                })
                break
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({'quote_candidates': len(out)}, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
