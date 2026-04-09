#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

ANTI_PATTERN_ROWS = [
    ('career-vocation', 'self-dramatizing-aimlessness', 'manual v3 quality seed'),
    ('career-vocation', 'abstract-inflation', 'manual v3 quality seed'),
    ('shame-self-contempt', 'identity-annihilation', 'manual v3 quality seed'),
    ('shame-self-contempt', 'moral-grandiosity-through-self-hatred', 'manual v3 quality seed'),
    ('relationship-maintenance', 'silent-resentment-spiral', 'manual v3 quality seed'),
    ('relationship-maintenance', 'indirect-hostility', 'manual v3 quality seed'),
]

CONFIDENCE_CASE_NAMES = [
    'No decision is itself a decision',
    'Meaning is a lived map, not an abstract slogan',
    'The heroic stance is voluntary confrontation with the unknown',
    'Relationship maintenance is active work',
    'Parenting requires boundaries before resentment builds',
    'Truth repairs structure',
    'Self-contempt destroys correction capacity',
]

CONFIDENCE_PACKS = ['career-pack', 'shame-pack', 'relationship-pack']
CONFIDENCE_STEPS = ['one-duty', 'one-repair-act', 'one-hard-conversation']


def get_id(cur, table, col, name):
    row = cur.execute(f'SELECT id FROM {table} WHERE {col}=?', (name,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for archetype_name, anti_pattern_name, note in ANTI_PATTERN_ROWS:
        cur.execute('INSERT OR REPLACE INTO archetype_anti_patterns (archetype_name, anti_pattern_name, note) VALUES (?, ?, ?)', (archetype_name, anti_pattern_name, note))

    for case_name in CONFIDENCE_CASE_NAMES:
        case_id = get_id(cur, 'cases', 'case_name', case_name)
        if case_id:
            cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('case', case_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

    for pack_name in CONFIDENCE_PACKS:
        pack_id = get_id(cur, 'route_quote_packs', 'pack_name', pack_name)
        if pack_id:
            cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('quote_pack', pack_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

    for step_name in CONFIDENCE_STEPS:
        step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
        if step_id:
            cur.execute('INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)', ('next_step', step_id, 'high', 'manual-curated', 2, 1, 'manual v3 quality seed'))

    conn.commit()
    print('seeded_v3_quality')
    conn.close()


if __name__ == '__main__':
    main()
