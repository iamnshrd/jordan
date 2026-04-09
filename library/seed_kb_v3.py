#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

SOURCE_ROUTE_ROWS = [
    ('12-rules', 'shame-self-contempt', 9, 'best first-order shame repair'),
    ('12-rules', 'basic-discipline', 10, 'best first stabilization source'),
    ('beyond-order', 'career-vocation', 10, 'best mature vocation source'),
    ('beyond-order', 'relationship-maintenance', 10, 'best romance maintenance source'),
    ('maps-of-meaning', 'mythic-meaning-collapse', 10, 'best deep collapse source'),
    ('maps-of-meaning', 'chaos-unknown', 9, 'best symbolic chaos source'),
]

BRIDGES = [
    ('career-bridge', 'meaning', 'aimlessness', 'Проблема не только в тумане, а в отсутствии выбранного бремени.', 'Ты избегаешь ответственности за выбор направления.', 'Выбери одно серьёзное обязательство на ближайший цикл.', 'Дальше нужно строить идентичность вокруг добровольно принятой ответственности.', 'hard', 'manual v3 seed'),
    ('shame-bridge', 'suffering', 'avoidance-loop', 'Здесь есть не просто боль, а саморазрушительное отождествление себя с провалом.', 'Ты избегаешь точного признания поступка, заменяя его тотальным осуждением себя.', 'Назови один конкретный проступок и один конкретный ремонтный шаг.', 'Долгосрочно нужно отделить вину от самоаннигиляции.', 'reflective', 'manual v3 seed'),
    ('relationship-bridge', 'responsibility', 'resentment-loop', 'Здесь копится не только конфликт, но и невысказанная обида.', 'Ты избегаешь прямого разговора и ясной границы.', 'Сформулируй один упрёк и одну границу без театрализованной вражды.', 'Дальше отношения держатся только на правде, переговорах и дисциплине.', 'default', 'manual v3 seed')
]

NEXT_STEPS = [
    ('one-duty', 'meaning', 'aimlessness', 'career-vocation', 'Назови одну обязанность, которую ты перестал нести, и верни её себе добровольно.', 'medium', 'today', '', 'manual v3 seed'),
    ('one-repair-act', 'suffering', 'avoidance-loop', 'shame-self-contempt', 'Сделай один конкретный восстановительный шаг вместо общего самоунижения.', 'low', 'today', '', 'manual v3 seed'),
    ('one-hard-conversation', 'responsibility', 'resentment-loop', 'relationship-maintenance', 'Проведи один трудный прямой разговор без молчаливой обиды и без истерики.', 'high', 'this-week', '', 'manual v3 seed')
]

QUOTE_PACKS = [
    ('career-pack', 'career-vocation', 'beyond-order,12-rules', 'discipline-quote,principle-quote', 'manual v3 seed'),
    ('shame-pack', 'shame-self-contempt', '12-rules,maps-of-meaning', 'shame-quote,principle-quote', 'manual v3 seed'),
    ('relationship-pack', 'relationship-maintenance', 'beyond-order,12-rules', 'relationship-quote,resentment-quote', 'manual v3 seed')
]

ARCHETYPE_INTERVENTIONS = [
    ('career-vocation', 'narrow-burden', 'manual v3 seed'),
    ('shame-self-contempt', 'separate-guilt-from-identity', 'manual v3 seed'),
    ('relationship-maintenance', 'truthful-negotiation', 'manual v3 seed')
]

THEME_STEP_LINKS = [
    ('meaning', 'one-duty'),
    ('suffering', 'one-repair-act'),
    ('responsibility', 'one-hard-conversation')
]

PATTERN_STEP_LINKS = [
    ('aimlessness', 'one-duty'),
    ('avoidance-loop', 'one-repair-act'),
    ('resentment-loop', 'one-hard-conversation')
]

ARCHETYPE_PACKS = [
    ('career-vocation', 'career-pack'),
    ('shame-self-contempt', 'shame-pack'),
    ('relationship-maintenance', 'relationship-pack')
]


def get_id(cur, table, name_col, value):
    row = cur.execute(f'SELECT id FROM {table} WHERE {name_col}=?', (value,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executemany('INSERT OR REPLACE INTO source_route_strength (source_name, route_name, strength, note) VALUES (?, ?, ?, ?)', SOURCE_ROUTE_ROWS)
    cur.executemany('INSERT OR REPLACE INTO bridge_to_action_templates (template_name, used_for_theme, used_for_pattern, diagnosis_stub, responsibility_stub, next_step_stub, long_term_stub, tone_profile, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', BRIDGES)
    cur.executemany('INSERT OR REPLACE INTO next_step_library (step_name, used_for_theme, used_for_pattern, used_for_archetype, step_text, difficulty, time_horizon, contraindications, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', NEXT_STEPS)
    cur.executemany('INSERT OR REPLACE INTO route_quote_packs (pack_name, route_name, preferred_sources, preferred_quote_types, note) VALUES (?, ?, ?, ?, ?)', QUOTE_PACKS)
    cur.executemany('INSERT OR REPLACE INTO archetype_interventions (archetype_name, intervention_pattern_name, note) VALUES (?, ?, ?)', ARCHETYPE_INTERVENTIONS)

    for theme_name, step_name in THEME_STEP_LINKS:
        step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
        cur.execute('INSERT OR REPLACE INTO theme_next_steps (theme_name, step_id, note) VALUES (?, ?, ?)', (theme_name, step_id, 'manual v3 seed'))

    for pattern_name, step_name in PATTERN_STEP_LINKS:
        step_id = get_id(cur, 'next_step_library', 'step_name', step_name)
        cur.execute('INSERT OR REPLACE INTO pattern_next_steps (pattern_name, step_id, note) VALUES (?, ?, ?)', (pattern_name, step_id, 'manual v3 seed'))

    for archetype_name, pack_name in ARCHETYPE_PACKS:
        pack_id = get_id(cur, 'route_quote_packs', 'pack_name', pack_name)
        cur.execute('INSERT OR REPLACE INTO archetype_quote_packs (archetype_name, pack_id, note) VALUES (?, ?, ?)', (archetype_name, pack_id, 'manual v3 seed'))

    conn.commit()
    print('seeded_v3')
    conn.close()


if __name__ == '__main__':
    main()
