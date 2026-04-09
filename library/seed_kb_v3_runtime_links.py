#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

SOURCE_ROUTE_UPSERT = [
    ('12-rules', 'career-vocation', 6, 'secondary support for vocation'),
    ('12-rules', 'relationship-maintenance', 7, 'truth/boundary backup source'),
    ('12-rules', 'mythic-meaning-collapse', 3, 'weak symbolic source'),
    ('beyond-order', 'shame-self-contempt', 5, 'secondary shame integration source'),
    ('beyond-order', 'mythic-meaning-collapse', 6, 'secondary symbolic source'),
    ('maps-of-meaning', 'career-vocation', 5, 'deep but secondary vocation source'),
    ('maps-of-meaning', 'shame-self-contempt', 7, 'deep shame/source of reorganization'),
]

ARCHETYPE_PACK_LINKS = [
    ('career-vocation', 'career-pack'),
    ('shame-self-contempt', 'shame-pack'),
    ('relationship-maintenance', 'relationship-pack'),
]

ARCHETYPE_STEP_LINKS = [
    ('career-vocation', 'one-duty'),
    ('shame-self-contempt', 'one-repair-act'),
    ('relationship-maintenance', 'one-hard-conversation'),
]


def get_pack_id(cur, name):
    row = cur.execute('SELECT id FROM route_quote_packs WHERE pack_name=?', (name,)).fetchone()
    return row[0] if row else None


def get_step_id(cur, name):
    row = cur.execute('SELECT id FROM next_step_library WHERE step_name=?', (name,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executemany('INSERT OR REPLACE INTO source_route_strength (source_name, route_name, strength, note) VALUES (?, ?, ?, ?)', SOURCE_ROUTE_UPSERT)

    for archetype_name, pack_name in ARCHETYPE_PACK_LINKS:
        pack_id = get_pack_id(cur, pack_name)
        if pack_id:
            cur.execute('INSERT OR REPLACE INTO archetype_quote_packs (archetype_name, pack_id, note) VALUES (?, ?, ?)', (archetype_name, pack_id, 'manual runtime seed'))

    # Archetype -> next-step links are currently represented indirectly via route/archetype naming
    # and existing next_step_library rows; deeper dedicated link table can be added later if needed.

    conn.commit()
    print('seeded_v3_runtime_links')
    conn.close()


if __name__ == '__main__':
    main()
