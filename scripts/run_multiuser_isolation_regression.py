#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.mentor.checkins import save_state, record_reply, evaluate
from library._core.mentor.commitments import record_commitment, load_commitments
from library._core.state_store import KEY_CONTINUITY
from library.config import canonical_user_id


def main() -> None:
    results = []
    with temp_store() as store:
        u1 = canonical_user_id('77571089')
        u2 = canonical_user_id('99999999')

        store.put_json(u1, KEY_CONTINUITY, {
            'open_loops': [{'summary': 'Ты не выбрал карьерное направление', 'salience': 5}],
            'top_themes': [{'name': 'meaning'}],
            'top_patterns': [{'name': 'avoidance-loop'}],
        })
        store.put_json(u2, KEY_CONTINUITY, {
            'open_loops': [{'summary': 'Ты избегаешь важного разговора', 'salience': 5}],
            'top_themes': [{'name': 'duty'}],
            'top_patterns': [{'name': 'avoidance-loop'}],
        })

        save_state({'mode': 'standard'}, user_id=u1, store=store)
        save_state({'mode': 'standard'}, user_id=u2, store=store)

        record_commitment('Я завтра точно напишу ему', user_id=u1, store=store)
        record_commitment('Я сегодня точно поговорю с ней и закрою этот разговор', user_id=u2, store=store)
        record_reply('Яснее вижу, куда иду', user_id=u1, store=store)
        record_reply('Отстань уже', user_id=u2, store=store)

        c1 = load_commitments(user_id=u1, store=store).get('items', [])
        c2 = load_commitments(user_id=u2, store=store).get('items', [])
        e1 = evaluate(user_id=u1, store=store)
        e2 = evaluate(user_id=u2, store=store)

        results.append({
            'name': 'canonical_user_id_numeric_to_telegram',
            'pass': canonical_user_id('77571089') == 'telegram:77571089',
        })
        results.append({
            'name': 'commitments_are_isolated',
            'pass': len(c1) == 1 and len(c2) == 1 and c1[0].get('summary') != c2[0].get('summary'),
            'user1_commitment': c1[0].get('summary') if c1 else '',
            'user2_commitment': c2[0].get('summary') if c2 else '',
        })
        results.append({
            'name': 'evaluations_are_isolated',
            'pass': e1.get('route') != e2.get('route') or (e1.get('question') != e2.get('question')),
            'user1_route': e1.get('route'),
            'user2_route': e2.get('route'),
            'user1_question': e1.get('question'),
            'user2_question': e2.get('question'),
        })

    emit_report(results)


if __name__ == '__main__':
    main()
