#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/beyond_order_concepts.json')


def fetch_id(cur, table, name_col, name):
    row = cur.execute(f'SELECT id FROM {table} WHERE {name_col} = ?', (name,)).fetchone()
    return row[0] if row else None


def ensure_case(cur, title, summary):
    row = cur.execute('SELECT id FROM cases WHERE case_name = ?', (title,)).fetchone()
    if row:
        return row[0]
    cur.execute('INSERT INTO cases (case_name, description, intervention_style, risk_note) VALUES (?, ?, ?, ?)', (title, summary, 'manual-beyond-order', 'manual concept harvest'))
    return cur.lastrowid


def ensure_intervention_example(cur, title, summary):
    row = cur.execute('SELECT id FROM intervention_examples WHERE example_name = ?', (title,)).fetchone()
    if row:
        return row[0]
    cur.execute('INSERT INTO intervention_examples (example_name, description) VALUES (?, ?)', (title, summary))
    return cur.lastrowid


def main():
    data = json.loads(SRC.read_text())
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    imported = {'cases': 0, 'intervention_examples': 0}
    for item in data:
        title = item['name']
        summary = item['summary']
        if item['type'] == 'frame':
            _id = ensure_case(cur, title, summary)
            imported['cases'] += 1
        else:
            _id = ensure_intervention_example(cur, title, summary)
            imported['intervention_examples'] += 1
    conn.commit()
    print(json.dumps(imported, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
