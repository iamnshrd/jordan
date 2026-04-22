#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from library.config import CONVERSATION_AUDIT_LOG


AUDIT_PATH = CONVERSATION_AUDIT_LOG


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return rows


def _top(counter: Counter[str], limit: int = 10) -> list[dict]:
    return [{'key': key, 'count': count} for key, count in counter.most_common(limit)]


def _field(row: dict, metadata: dict, *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in {None, ''}:
            return str(value)
        value = metadata.get(name)
        if value not in {None, ''}:
            return str(value)
    return ''


def main() -> None:
    rows = _load_rows(AUDIT_PATH)
    reason_codes: Counter[str] = Counter()
    source_lookup: Counter[str] = Counter()
    respond_kb: Counter[str] = Counter()
    generic_clarify: Counter[str] = Counter()
    unmatched_openings: Counter[str] = Counter()
    renderer_fallbacks: Counter[str] = Counter()
    renderer_banned_openers: Counter[str] = Counter()
    renderer_validation_failures: Counter[str] = Counter()
    renderer_exception_details: Counter[str] = Counter()
    family_overrides: Counter[str] = Counter()
    family_rejections: Counter[str] = Counter()
    family_accepted_source_lookup_avoidance: Counter[str] = Counter()
    marginal_routes: Counter[str] = Counter()
    marginal_rejections: Counter[str] = Counter()
    marginal_exceptions: Counter[str] = Counter()
    marginal_source_lookup_avoidance: Counter[str] = Counter()

    for row in rows:
        event = row.get('event', '')
        if event not in {'conversation.adapter_result', 'telegram.jordan_adapter_result'}:
            continue

        metadata = row.get('metadata') or {}
        reason_code = _field(row, metadata, 'reason_code', 'reasonCode', 'clarify_reason_code')
        decision_type = _field(row, metadata, 'decision_type', 'decisionType')
        clarify_type = _field(row, metadata, 'clarify_type', 'clarifyType')
        text = (row.get('question') or row.get('text') or '').strip()
        frame_topic = _field(row, metadata, 'frame_topic')
        renderer_status = _field(row, metadata, 'renderer_status')
        renderer_exception_detail = _field(row, metadata, 'renderer_exception_detail')
        family_status = _field(row, metadata, 'family_classifier_status')
        family_topic = _field(row, metadata, 'family_classifier_result_topic')
        deterministic_topic = _field(row, metadata, 'family_classifier_deterministic_topic')
        family_rejection_reason = _field(row, metadata, 'family_classifier_rejection_reason')
        marginal_status = _field(row, metadata, 'marginal_router_status')
        marginal_route = _field(row, metadata, 'marginal_router_result_route')
        marginal_rejection_reason = _field(row, metadata, 'marginal_router_rejection_reason')
        marginal_exception_detail = _field(row, metadata, 'marginal_router_exception_detail')

        if reason_code:
            reason_codes[reason_code] += 1
        if reason_code == 'source-lookup' and text:
            source_lookup[text] += 1
        if decision_type == 'respond_kb' and text:
            respond_kb[text] += 1
        if (
            decision_type == 'clarify'
            and text
            and (
                reason_code == 'ask-clarifying-question'
                or clarify_type == 'human_problem'
                or not frame_topic
                or frame_topic == 'general'
            )
        ):
            generic_clarify[text] += 1
        if text and (not frame_topic or frame_topic == 'general'):
            unmatched_openings[text] += 1
        if (
            (row.get('renderer_fallback_used') or metadata.get('renderer_fallback_used'))
            and renderer_status != 'not_configured'
            and text
        ):
            renderer_fallbacks[text] += 1
        for failure in (row.get('renderer_validation_failures') or metadata.get('renderer_validation_failures') or []):
            renderer_validation_failures[str(failure)] += 1
            if str(failure) == 'forbidden_opener' and text:
                renderer_banned_openers[text] += 1
        if renderer_exception_detail:
            renderer_exception_details[renderer_exception_detail] += 1
        if family_status == 'accepted' and family_topic and deterministic_topic and family_topic != deterministic_topic:
            family_overrides[f'{deterministic_topic} -> {family_topic}'] += 1
        if family_rejection_reason:
            family_rejections[family_rejection_reason] += 1
        if family_status == 'accepted' and family_topic and reason_code != 'source-lookup' and text:
            family_accepted_source_lookup_avoidance[text] += 1
        if marginal_status == 'accepted' and marginal_route:
            marginal_routes[marginal_route] += 1
        if marginal_rejection_reason:
            marginal_rejections[marginal_rejection_reason] += 1
        if marginal_exception_detail:
            marginal_exceptions[marginal_exception_detail] += 1
        if marginal_status == 'accepted' and text and reason_code != 'source-lookup':
            marginal_source_lookup_avoidance[text] += 1

    report = {
        'audit_path': str(AUDIT_PATH),
        'rows_scanned': len(rows),
        'top_reason_code': _top(reason_codes),
        'top_source_lookup': _top(source_lookup),
        'top_respond_kb': _top(respond_kb),
        'top_generic_ask_clarifying_question': _top(generic_clarify),
        'top_unmatched_open_topic_phrasings': _top(unmatched_openings),
        'top_renderer_fallbacks': _top(renderer_fallbacks),
        'top_renderer_banned_opener_violations': _top(renderer_banned_openers),
        'top_renderer_validation_failures': _top(renderer_validation_failures),
        'top_renderer_exception_details': _top(renderer_exception_details),
        'top_family_classifier_overrides': _top(family_overrides),
        'top_family_classifier_rejections': _top(family_rejections),
        'top_family_classifier_source_lookup_avoidance': _top(family_accepted_source_lookup_avoidance),
        'top_marginal_routes': _top(marginal_routes),
        'top_marginal_route_rejections': _top(marginal_rejections),
        'top_marginal_route_exceptions': _top(marginal_exceptions),
        'top_marginal_route_source_lookup_avoidance': _top(marginal_source_lookup_avoidance),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
