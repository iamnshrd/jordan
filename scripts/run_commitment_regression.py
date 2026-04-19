#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.mentor.commitments import infer_commitment, record_commitment, maybe_resolve_from_reply, load_commitments, best_open_commitment, commitment_summary, commitment_prompt_style
from library._core.mentor.render import render_event


def main() -> None:
    results = []
    passed = 0

    parsed = infer_commitment('Я завтра точно напишу ему и закрою этот разговор, но сначала соберусь с мыслями')
    ok = parsed == 'завтра точно напишу ему и закрою этот разговор'
    results.append({'name': 'parse_commitment', 'pass': ok, 'value': parsed})
    passed += int(ok)

    with temp_store() as store:
        item = record_commitment('Я завтра точно напишу ему и закрою этот разговор', user_id='default', store=store)
        ok = bool(item and item.get('route') == 'relationship-maintenance')
        results.append({'name': 'route_inference', 'pass': ok, 'route': item.get('route') if item else None})
        passed += int(ok)

        ok = bool(item and item.get('action_core') == 'точно напишу ему и закрою этот разговор' and item.get('due_hint') == 'завтра' and item.get('due_at'))
        results.append({'name': 'due_and_action_core', 'pass': ok, 'action_core': item.get('action_core') if item else None, 'due_hint': item.get('due_hint') if item else None})
        passed += int(ok)

        ok = bool(item and item.get('strength') == 'hard' and commitment_prompt_style(item) == 'hard')
        results.append({'name': 'strength_and_prompt_style', 'pass': ok, 'strength': item.get('strength') if item else None})
        passed += int(ok)

        record_commitment('Я, может быть, на этой неделе разберу этот вопрос', user_id='default', store=store)
        best = best_open_commitment(user_id='default', store=store)
        ok = bool(best and best.get('summary') == 'завтра точно напишу ему и закрою этот разговор')
        results.append({'name': 'due_priority', 'pass': ok, 'best': best.get('summary') if best else None})
        passed += int(ok)

        summary = commitment_summary(user_id='default', store=store)
        ok = bool(summary.get('hard_open') == 1 and summary.get('soft_open') == 1)
        results.append({'name': 'summary_counts', 'pass': ok, 'summary': summary})
        passed += int(ok)

        resolved = maybe_resolve_from_reply('Да, я написал ему и закрыл этот разговор', user_id='default', store=store)
        items = load_commitments(user_id='default', store=store).get('items', [])
        resolved_item = next((x for x in items if x.get('summary') == 'завтра точно напишу ему и закрою этот разговор'), None)
        status = resolved_item.get('status') if resolved_item else None
        ok = bool(resolved and status == 'resolved')
        results.append({'name': 'resolve_from_reply', 'pass': ok, 'status': status})
        passed += int(ok)

        summary = commitment_summary(user_id='default', store=store)
        rendered = render_event({'type': 'mentor-summary', 'commitment_summary': summary})
        ok = bool('Недавно закрыто:' in rendered and 'Главный фокус сейчас:' in rendered)
        results.append({'name': 'movement_digest_render', 'pass': ok, 'rendered': rendered})
        passed += int(ok)

    emit_report(results)


if __name__ == '__main__':
    main()
