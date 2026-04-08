#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/maps_of_meaning_concepts.json')


def ensure_case(cur, title, summary):
    row = cur.execute('SELECT id FROM cases WHERE case_name = ?', (title,)).fetchone()
    if row:
        return row[0]
    cur.execute('INSERT INTO cases (case_name, description, intervention_style, risk_note) VALUES (?, ?, ?, ?)', (title, summary, 'manual-maps-of-meaning', 'manual concept harvest'))
    return cur.lastrowid


def main():
    data = json.loads(SRC.read_text())
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    imported = 0
    for item in data:
        ensure_case(cur, item['name'], item['summary'])
        imported += 1
    conn.commit()
    print(json.dumps({'maps_of_meaning_cases_imported': imported}, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
