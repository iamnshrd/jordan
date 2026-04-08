#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/quotes_normalized.json')
MANUAL = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/manual_quotes.json')
MANUAL_BEYOND = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/manual_quotes_beyond_order.json')
MANUAL_MAPS = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/manual_quotes_maps_of_meaning.json')


def main():
    data = json.loads(SRC.read_text())
    if MANUAL.exists():
        data.extend(json.loads(MANUAL.read_text()))
    if MANUAL_BEYOND.exists():
        data.extend(json.loads(MANUAL_BEYOND.read_text()))
    if MANUAL_MAPS.exists():
        data.extend(json.loads(MANUAL_MAPS.read_text()))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('DELETE FROM quotes')
    for item in data:
        cur.execute(
            'INSERT INTO quotes (document_id, chunk_id, quote_text, note, quote_type, theme_name, principle_name, pattern_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                item['document_id'],
                item['chunk_id'],
                item['quote_text'],
                item['note'],
                item.get('quote_type'),
                item.get('theme_name'),
                item.get('principle_name'),
                item.get('pattern_name'),
            )
        )
    conn.commit()
    print(json.dumps({'quotes': cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]}, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
