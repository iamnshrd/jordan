#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

NEW_STEPS = [
    ('write-the-memory', 'suffering', 'avoidance-loop', 'shame-self-contempt', 'Опиши болезненное воспоминание полностью и без театрализации, пока оно не перестанет быть туманным хозяином поведения.', 'medium', 'this-week', '', 'manual v3 step seed'),
    ('state-the-resentment-directly', 'resentment', 'resentment-loop', 'relationship-maintenance', 'Назови один невысказанный упрёк прямо и без накопленной ядовитой риторики.', 'high', 'today', '', 'manual v3 step seed'),
    ('restore-local-order', 'order-and-chaos', 'avoidance-loop', 'basic-discipline', 'Наведи локальный порядок в одной зоне, чтобы вернуть себе ощущение агентности через действие.', 'low', 'today', '', 'manual v3 step seed'),
    ('name-the-lie', 'truth', 'avoidance-loop', 'shame-self-contempt', 'Сформулируй одну ложь или полуправду, на которой сейчас держится твоя проблема.', 'medium', 'today', '', 'manual v3 step seed')
]

THEME_LINKS = [
    ('suffering', 'write-the-memory'),
    ('resentment', 'state-the-resentment-directly'),
    ('order-and-chaos', 'restore-local-order'),
    ('truth', 'name-the-lie')
]

PATTERN_LINKS = [
    ('avoidance-loop', 'write-the-memory'),
    ('resentment-loop', 'state-the-resentment-directly'),
    ('avoidance-loop', 'restore-local-order'),
    ('avoidance-loop', 'name-the-lie')
]


def get_step_id(cur, name):
    row = cur.execute('SELECT id FROM next_step_library WHERE step_name=?', (name,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executemany('INSERT OR REPLACE INTO next_step_library (step_name, used_for_theme, used_for_pattern, used_for_archetype, step_text, difficulty, time_horizon, contraindications, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', NEW_STEPS)

    for theme_name, step_name in THEME_LINKS:
        step_id = get_step_id(cur, step_name)
        if step_id:
            cur.execute('INSERT OR REPLACE INTO theme_next_steps (theme_name, step_id, note) VALUES (?, ?, ?)', (theme_name, step_id, 'manual v3 step seed'))

    for pattern_name, step_name in PATTERN_LINKS:
        step_id = get_step_id(cur, step_name)
        if step_id:
            cur.execute('INSERT OR REPLACE INTO pattern_next_steps (pattern_name, step_id, note) VALUES (?, ?, ?)', (pattern_name, step_id, 'manual v3 step seed'))

    conn.commit()
    print('seeded_v3_steps')
    conn.close()


if __name__ == '__main__':
    main()
