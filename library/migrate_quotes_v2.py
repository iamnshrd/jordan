#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')


def add_col(cur, table, col, spec):
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info({table})').fetchall()]
    if col not in cols:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {spec}')


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    add_col(cur, 'quotes', 'quote_type', 'TEXT')
    add_col(cur, 'quotes', 'theme_name', 'TEXT')
    add_col(cur, 'quotes', 'principle_name', 'TEXT')
    add_col(cur, 'quotes', 'pattern_name', 'TEXT')
    conn.commit()
    conn.close()
    print('ok')


if __name__ == '__main__':
    main()
