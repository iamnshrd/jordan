#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/kb_candidates_normalized.json')


def get_id(cur, table, name_col, name):
    cur.execute(f'SELECT id FROM {table} WHERE {name_col} = ?', (name,))
    row = cur.fetchone()
    return row[0] if row else None


def insert_theme_evidence(cur, theme_name, chunk_id, note):
    theme_id = get_id(cur, 'themes', 'theme_name', theme_name)
    if theme_id:
        cur.execute('INSERT INTO theme_evidence (theme_id, chunk_id, note) VALUES (?, ?, ?)', (theme_id, chunk_id, note))


def insert_principle_evidence(cur, principle_name, chunk_id, note):
    pid = get_id(cur, 'principles', 'principle_name', principle_name)
    if pid:
        cur.execute('INSERT INTO principle_evidence (principle_id, chunk_id, note) VALUES (?, ?, ?)', (pid, chunk_id, note))


def insert_pattern_evidence(cur, pattern_name, chunk_id, note):
    pid = get_id(cur, 'patterns', 'pattern_name', pattern_name)
    if pid:
        cur.execute('INSERT INTO pattern_evidence (pattern_id, chunk_id, note) VALUES (?, ?, ?)', (pid, chunk_id, note))


def main():
    data = json.loads(SRC.read_text())
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('DELETE FROM theme_evidence')
    cur.execute('DELETE FROM principle_evidence')
    cur.execute('DELETE FROM pattern_evidence')
    for item in data.get('themes', []):
        insert_theme_evidence(cur, item['theme_name'], item['chunk_id'], ', '.join(item.get('matched_terms', [])))
    for item in data.get('principles', []):
        insert_principle_evidence(cur, item['principle_name'], item['chunk_id'], ', '.join(item.get('matched_terms', [])))
    for item in data.get('patterns', []):
        insert_pattern_evidence(cur, item['pattern_name'], item['chunk_id'], ', '.join(item.get('matched_terms', [])))
    conn.commit()
    counts = {
        'theme_evidence': cur.execute('SELECT COUNT(*) FROM theme_evidence').fetchone()[0],
        'principle_evidence': cur.execute('SELECT COUNT(*) FROM principle_evidence').fetchone()[0],
        'pattern_evidence': cur.execute('SELECT COUNT(*) FROM pattern_evidence').fetchone()[0],
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
