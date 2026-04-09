#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

ANTI_PATTERN_ROWS = [
    ('career-vocation', 'abstract-inflation', 'manual v3 seed'),
    ('shame-self-contempt', 'identity-annihilation', 'manual v3 seed'),
    ('relationship-maintenance', 'silent-resentment-spiral', 'manual v3 seed'),
]

MOTIF_LINKS = [
    ('dragon', 'The heroic stance is voluntary confrontation with the unknown', 'narrow-burden'),
    ('dragon', 'The dragon of chaos guards the next stage of growth', 'narrow-burden'),
    ('dragon', 'The unknown is both threat and possibility', 'narrow-burden'),
    ('burden', 'Responsibility and meaning are linked', 'narrow-burden'),
    ('burden', 'Opportunity appears in abandoned responsibility', 'narrow-burden'),
    ('burden', 'No decision is itself a decision', 'narrow-burden'),
    ('burden', 'Parenting requires boundaries before resentment builds', 'truthful-negotiation'),
    ('burden', 'Relationship maintenance is active work', 'truthful-negotiation'),
]


def get_case_id(cur, name):
    row = cur.execute('SELECT id FROM cases WHERE case_name=?', (name,)).fetchone()
    return row[0] if row else None


def get_motif_id(cur, name):
    row = cur.execute('SELECT id FROM symbolic_motifs WHERE motif_name=?', (name,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for archetype_name, anti_pattern_name, note in ANTI_PATTERN_ROWS:
        cur.execute('INSERT OR REPLACE INTO archetype_anti_patterns (archetype_name, anti_pattern_name, note) VALUES (?, ?, ?)', (archetype_name, anti_pattern_name, note))

    for motif_name, case_name, intervention_name in MOTIF_LINKS:
        motif_id = get_motif_id(cur, motif_name)
        case_id = get_case_id(cur, case_name)
        if motif_id and case_id:
            cur.execute('INSERT OR REPLACE INTO motif_cases (motif_id, case_id, note) VALUES (?, ?, ?)', (motif_id, case_id, 'manual v3 seed'))
        if motif_id:
            cur.execute('INSERT OR REPLACE INTO motif_interventions (motif_id, intervention_pattern_name, note) VALUES (?, ?, ?)', (motif_id, intervention_name, 'manual v3 seed'))

    conn.commit()
    print('seeded_v3_motifs')
    conn.close()


if __name__ == '__main__':
    main()
