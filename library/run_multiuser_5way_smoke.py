#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._adapters.fs_store import FileSystemStore
from library._core.mentor.checkins import save_state, record_reply, evaluate
from library._core.mentor.commitments import record_commitment, load_commitments
from library._core.state_store import KEY_CONTINUITY, KEY_MENTOR_STATE
from library.config import canonical_user_id


USERS = [
    {
        'raw': '10001',
        'loop': 'Ты не выбрал карьерное направление',
        'reply': 'Яснее вижу, куда иду',
        'commitment': 'Я завтра точно напишу ему',
    },
    {
        'raw': '10002',
        'loop': 'Ты избегаешь важного разговора',
        'reply': 'Отстань уже',
        'commitment': 'Я сегодня точно поговорю с ней и закрою этот разговор',
    },
    {
        'raw': '10003',
        'loop': 'Ты снова откладываешь и не можешь начать',
        'reply': 'После встречи вечером сделаю первый шаг',
        'commitment': 'Сегодня вечером начну и закрою первый кусок',
    },
    {
        'raw': '10004',
        'loop': 'Ты врешь себе о том, что двигаешься',
        'reply': 'Это было просто оправдание, я прикрывался объяснением',
        'commitment': 'Завтра честно разберу это письмо',
    },
    {
        'raw': '10005',
        'loop': 'Ты застрял в обиде и кормишь resentment',
        'reply': 'Я опять делаю вид, что двигаюсь, это был только красивый ответ',
        'commitment': 'На этой неделе разберу этот конфликт по-настоящему',
    },
]


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        summaries = []
        for spec in USERS:
            user_id = canonical_user_id(spec['raw'])
            store.put_json(user_id, KEY_CONTINUITY, {
                'open_loops': [{'summary': spec['loop'], 'salience': 5}],
                'top_themes': [{'name': 'theme-' + spec['raw']}],
                'top_patterns': [{'name': 'pattern-' + spec['raw']}],
            })
            save_state({'mode': 'standard'}, user_id=user_id, store=store)
            record_commitment(spec['commitment'], user_id=user_id, store=store)
            reply_state = record_reply(spec['reply'], user_id=user_id, store=store)
            eval_result = evaluate(user_id=user_id, store=store)
            commitments = load_commitments(user_id=user_id, store=store).get('items', [])
            mentor_state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
            summaries.append({
                'user_id': user_id,
                'question': eval_result.get('question'),
                'route': eval_result.get('route'),
                'last_rich_outcome': mentor_state.get('last_rich_outcome'),
                'commitments': [x.get('summary') for x in commitments],
                'selected_event_type': (eval_result.get('selected_event') or {}).get('type'),
                'skip': eval_result.get('skip'),
            })

        user_ids = [x['user_id'] for x in summaries]
        commitment_sets = [tuple(x['commitments']) for x in summaries]
        questions = [x['question'] for x in summaries]
        results = [
            {
                'name': 'five_unique_user_buckets',
                'pass': len(set(user_ids)) == 5,
            },
            {
                'name': 'five_distinct_commitment_sets',
                'pass': len(set(commitment_sets)) == 5,
            },
            {
                'name': 'five_distinct_background_questions',
                'pass': len(set(questions)) == 5,
            },
            {
                'name': 'all_users_have_mentor_state',
                'pass': all(x['last_rich_outcome'] for x in summaries),
            },
        ]
        total = len(results)
        passed = sum(1 for x in results if x.get('pass'))
        print(json.dumps({'total': total, 'pass': passed, 'results': results, 'summaries': summaries}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
