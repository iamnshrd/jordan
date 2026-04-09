#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

CASE_LINKS = [
    ('No decision is itself a decision', 'career-vocation', 'narrow-burden'),
    ('Resentment-deceit-arrogance triad', 'relationship-maintenance', 'truthful-negotiation'),
    ('Shame marks exposed insufficiency before reorganization', 'shame-self-contempt', 'separate-guilt-from-identity'),
    ('Parenting requires boundaries before resentment builds', 'relationship-maintenance', 'truthful-negotiation'),
    ('Meaning is a lived map, not an abstract slogan', 'career-vocation', 'narrow-burden'),
]

CONFIDENCE_ROWS = [
    ('case', 'No decision is itself a decision', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('case', 'Resentment-deceit-arrogance triad', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('case', 'Shame marks exposed insufficiency before reorganization', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'career-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'shame-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
    ('bridge', 'relationship-bridge', 'high', 'manual-curated', 2, 1, 'manual v3 confidence'),
]


def get_case_id(cur, name):
    row = cur.execute('SELECT id FROM cases WHERE case_name=?', (name,)).fetchone()
    return row[0] if row else None


def get_bridge_id(cur, name):
    row = cur.execute('SELECT id FROM bridge_to_action_templates WHERE template_name=?', (name,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for case_name, archetype_name, intervention_name in CASE_LINKS:
        case_id = get_case_id(cur, case_name)
        if case_id:
            cur.execute('INSERT OR REPLACE INTO case_archetypes (case_id, archetype_name, note) VALUES (?, ?, ?)', (case_id, archetype_name, 'manual v3 seed'))
            cur.execute('INSERT OR REPLACE INTO case_interventions (case_id, intervention_pattern_name, note) VALUES (?, ?, ?)', (case_id, intervention_name, 'manual v3 seed'))

    for entity_type, entity_name, confidence, curation, source_count, manual_override, note in CONFIDENCE_ROWS:
        if entity_type == 'case':
            entity_id = get_case_id(cur, entity_name)
        elif entity_type == 'bridge':
            entity_id = get_bridge_id(cur, entity_name)
        else:
            entity_id = None
        if entity_id is not None:
            cur.execute(
                'INSERT OR REPLACE INTO confidence_tags (entity_type, entity_id, confidence_level, curation_level, source_count, manual_override, note) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (entity_type, entity_id, confidence, curation, source_count, manual_override, note)
            )

    conn.commit()
    print('seeded_v3_links')
    conn.close()


if __name__ == '__main__':
    main()
