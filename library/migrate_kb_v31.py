#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

SQL = '''
CREATE TABLE IF NOT EXISTS quote_pack_items (
  pack_id INTEGER NOT NULL,
  quote_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(pack_id, quote_id)
);
'''


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executescript(SQL)
    conn.commit()
    print('migrated_v31')
    conn.close()


if __name__ == '__main__':
    main()
