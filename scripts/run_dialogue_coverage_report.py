#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter

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

    for row in rows:
        event = row.get('event', '')
        if event not in {'conversation.adapter_result', 'telegram.jordan_adapter_result'}:
            continue

        metadata = row.get('metadata') or {}
        reason_code = (
            row.get('reason_code')
            or row.get('reasonCode')
            or metadata.get('reason_code')
            or metadata.get('clarify_reason_code')
            or ''
        )
        decision_type = (
            row.get('decision_type')
            or row.get('decisionType')
            or metadata.get('decision_type')
            or ''
        )
        clarify_type = (
            row.get('clarify_type')
            or row.get('clarifyType')
            or metadata.get('clarify_type')
            or ''
        )
        text = (row.get('question') or row.get('text') or '').strip()
        frame_topic = metadata.get('frame_topic') or ''
        renderer_status = str(metadata.get('renderer_status') or '')
        renderer_exception_detail = str(metadata.get('renderer_exception_detail') or '')
        family_status = str(metadata.get('family_classifier_status') or '')
        family_topic = str(metadata.get('family_classifier_result_topic') or '')
        deterministic_topic = str(metadata.get('family_classifier_deterministic_topic') or '')
        family_rejection_reason = str(metadata.get('family_classifier_rejection_reason') or '')

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
            metadata.get('renderer_fallback_used')
            and renderer_status != 'not_configured'
            and text
        ):
            renderer_fallbacks[text] += 1
        for failure in metadata.get('renderer_validation_failures') or []:
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
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
