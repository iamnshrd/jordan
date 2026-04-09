#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')

PACKS = {
    'career-pack': [
        'Imagine who you could be, and then aim single-mindedly at that.',
        'Do not do what you hate.',
        'The worst decision of all is no decision.',
        'Make yourself invaluable.'
    ],
    'shame-pack': [
        'Стыд за поступок можно исправлять. Но если ты превращаешь свою ошибку в доказательство собственной никчемности, ты разрушаешь возможность исправления.',
        'Shame can become the beginning of reformation if it is faced instead of denied.',
        'Shame and anxiety often signal the collapse of a former mode of adaptation.'
    ],
    'relationship-pack': [
        'Plan and work diligently to maintain the romance in your relationship.',
        'Do not allow yourself to become resentful, deceitful, or arrogant.',
        'If you have something difficult to say, silence may feel easier in the moment, but it is deadly in the long run.'
    ]
}


def get_pack_id(cur, name):
    row = cur.execute('SELECT id FROM route_quote_packs WHERE pack_name=?', (name,)).fetchone()
    return row[0] if row else None


def get_quote_id(cur, text):
    row = cur.execute('SELECT id FROM quotes WHERE quote_text=?', (text,)).fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for pack_name, quotes in PACKS.items():
        pack_id = get_pack_id(cur, pack_name)
        if not pack_id:
            continue
        for qt in quotes:
            qid = get_quote_id(cur, qt)
            if qid:
                cur.execute('INSERT OR REPLACE INTO quote_pack_items (pack_id, quote_id, note) VALUES (?, ?, ?)', (pack_id, qid, 'manual pack seed'))
    conn.commit()
    print('seeded_quote_pack_items')
    conn.close()


if __name__ == '__main__':
    main()
