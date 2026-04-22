#!/usr/bin/env python3
"""Unified CLI entry point for the Jordan Peterson agent library.

Usage examples:
    python -m library run "вопрос"
    python -m library frame "вопрос"
    python -m library respond "вопрос" --mode deep --voice hard
    python -m library kb build
    python -m library kb query --query "смысл"
    python -m library kb migrate-v3
    python -m library kb seed-v3
    python -m library ingest auto
    python -m library eval audit
    python -m library eval regression
    python -m library eval voice-regression
    python -m library eval full
"""
import argparse
import json
import sys

from library.logging_config import setup as setup_logging
from library.config import canonical_user_id


def _build_adapter_cli_result(payload: dict) -> dict:
    envelope = payload.get('decision_envelope') or {}
    adapter_contract = payload.get('adapter_contract') or {}
    decision_metadata = envelope.get('metadata') or {}
    delivery_mode = payload.get('delivery_mode') or adapter_contract.get('delivery_mode', '')
    final_user_text = payload.get('final_user_text') or payload.get('message', '') or ''
    result = {
        'trace_id': payload.get('trace_id', '') or envelope.get('trace_id', ''),
        'assistant_id': payload.get('assistant_id', '') or envelope.get('assistant_id', ''),
        'knowledge_set_id': (
            payload.get('knowledge_set_id', '')
            or envelope.get('knowledge_set_id', '')
        ),
        'decision_type': payload.get('decision_type', '') or envelope.get('decision_type', ''),
        'domain_status': payload.get('domain_status', '') or envelope.get('domain_status', ''),
        'reason_code': payload.get('reason_code', '') or envelope.get('reason_code', ''),
        'allow_model_call': bool(payload.get('delivery_mode') == 'model' or envelope.get('allow_model_call')),
        'delivery_mode': delivery_mode,
        'final_user_text': final_user_text,
        'decision_metadata': decision_metadata,
        'dialogue_frame': payload.get('dialogue_frame', {}),
    }
    if result['allow_model_call']:
        result['model_prompt'] = {
            'system': payload.get('system', ''),
            'user': payload.get('user', ''),
        }
    return result


def cmd_run(args):
    from library._core.runtime.orchestrator import orchestrate
    print(json.dumps(orchestrate(args.question, user_id=args.user_id),
                     ensure_ascii=False, indent=2))


def cmd_prompt(args):
    from library._core.runtime.orchestrator import orchestrate_for_llm
    result = orchestrate_for_llm(args.question, user_id=args.user_id)
    if args.system_only:
        print(result.get('system', ''))
    else:
        print(json.dumps({
            'system': result.get('system', ''),
            'user': result.get('user', ''),
            'action': result.get('action', ''),
            'mode': result.get('mode', ''),
            'voice_mode': result.get('voice_mode', ''),
            'decision_type': result.get('decision_type', ''),
            'assistant_id': result.get('assistant_id', ''),
            'knowledge_set_id': result.get('knowledge_set_id', ''),
            'domain_status': result.get('domain_status', ''),
            'reason_code': result.get('reason_code', ''),
            'allow_model_call': result.get('allow_model_call', False),
            'final_user_text': result.get('final_user_text', ''),
            'adapter_contract': result.get('adapter_contract', {}),
            'decision_envelope': result.get('decision_envelope', {}),
            'trace_id': result.get('trace_id', ''),
        }, ensure_ascii=False, indent=2))


def cmd_adapter(args):
    from library._core.runtime.orchestrator import orchestrate_for_adapter
    from library.utils import audit_event

    question = args.question or ''
    user_id = canonical_user_id(args.user_id)
    audit_event(
        'conversation.adapter_request',
        user_id=user_id,
        channel=args.adapter_channel,
        question=question,
        question_length=len(question),
        entrypoint='cli.adapter',
    )
    payload = orchestrate_for_adapter(question, user_id=user_id)
    result = _build_adapter_cli_result(payload)
    audit_event(
        'conversation.adapter_result',
        user_id=user_id,
        channel=args.adapter_channel,
        question=question,
        decision_type=result.get('decision_type', ''),
        domain_status=result.get('domain_status', ''),
        reason_code=result.get('reason_code', ''),
        allow_model_call=result.get('allow_model_call', False),
        delivery_mode=result.get('delivery_mode', ''),
        final_user_text=result.get('final_user_text', ''),
        trace_id=result.get('trace_id', ''),
        clarify_type=(result.get('decision_metadata') or {}).get('clarify_type', ''),
        clarify_theme=(result.get('decision_metadata') or {}).get('clarify_theme', ''),
        clarify_profile=(result.get('decision_metadata') or {}).get('clarify_profile', ''),
        dialogue_act=(result.get('decision_metadata') or {}).get('dialogue_act', ''),
        dialogue_mode=(result.get('decision_metadata') or {}).get('dialogue_mode', ''),
        active_topic=(result.get('decision_metadata') or {}).get('active_topic', ''),
        abstraction_level=(result.get('decision_metadata') or {}).get('abstraction_level', ''),
        pending_slot=(result.get('decision_metadata') or {}).get('pending_slot', ''),
        frame_topic=(result.get('decision_metadata') or {}).get('frame_topic', ''),
        frame_type=(result.get('decision_metadata') or {}).get('frame_type', ''),
        frame_goal=(result.get('decision_metadata') or {}).get('frame_goal', ''),
        frame_relation=(result.get('decision_metadata') or {}).get('frame_relation_to_previous', ''),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


def cmd_frame(args):
    from library._core.runtime.orchestrator import orchestrate_diagnostics
    result = orchestrate_diagnostics(args.question, user_id=args.user_id, purpose='prompt')
    print(json.dumps(result.get('selection', {}), ensure_ascii=False, indent=2))


def cmd_respond(args):
    from library._core.runtime.respond import respond
    print(respond(args.question, mode=args.mode, voice=args.voice,
                  user_id=args.user_id))


def cmd_retrieve(args):
    from library._core.runtime.orchestrator import orchestrate_diagnostics
    result = orchestrate_diagnostics(args.question, user_id=args.user_id, purpose='prompt')
    bundle = result.get('bundle', {})
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


def cmd_kb(args):
    action = args.kb_action
    if action == 'build':
        from library._core.kb.build import build
        print(json.dumps(
            build(
                force=args.force,
                allow_partial=args.allow_partial,
                enrich=not args.no_enrich,
            ),
            ensure_ascii=False, indent=2,
        ))
    elif action == 'doctor':
        from library._core.kb.doctor import doctor
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
    elif action == 'smoke':
        from library._core.kb.doctor import smoke
        print(json.dumps(smoke(args.query or 'смысл'), ensure_ascii=False, indent=2))
    elif action == 'query':
        from library._core.kb.query import query
        print(json.dumps(query(args.query, args.table, args.limit), ensure_ascii=False, indent=2))
    elif action == 'query-v3':
        from library._core.kb.query_v3 import query_v3
        print(json.dumps(query_v3(args.theme, args.pattern, args.archetype), ensure_ascii=False, indent=2))
    elif action == 'extract':
        from library._core.kb.extract import extract
        print(json.dumps(extract(), ensure_ascii=False, indent=2))
    elif action == 'normalize':
        from library._core.kb.normalize import normalize
        print(json.dumps(normalize(), ensure_ascii=False, indent=2))
    elif action == 'evidence':
        from library._core.kb.evidence import write_evidence
        print(json.dumps(write_evidence(), ensure_ascii=False, indent=2))
    elif action == 'extract-quotes':
        from library._core.kb.quotes import extract_quotes
        print(json.dumps(extract_quotes(), ensure_ascii=False, indent=2))
    elif action == 'normalize-quotes':
        from library._core.kb.quotes import normalize_quotes
        print(json.dumps(normalize_quotes(), ensure_ascii=False, indent=2))
    elif action == 'load-quotes':
        from library._core.kb.quotes import load_quotes
        print(json.dumps(load_quotes(), ensure_ascii=False, indent=2))
    elif action == 'migrate-v3':
        from library._core.kb.migrate import migrate_v3
        print(migrate_v3())
    elif action == 'migrate-v31':
        from library._core.kb.migrate import migrate_v31
        print(migrate_v31())
    elif action == 'migrate-quotes-v2':
        from library._core.kb.migrate import migrate_quotes_v2
        print(migrate_quotes_v2())
    elif action == 'seed-v3':
        from library._core.kb.seed import seed_v3
        print(seed_v3())
    elif action == 'seed-all':
        from library._core.kb.seed import (
            seed_v3, seed_v3_links, seed_v3_motifs,
            seed_v3_quality, seed_v3_runtime_links,
            seed_v3_steps, seed_quote_pack_items,
        )
        for fn in [seed_v3, seed_v3_links, seed_v3_motifs, seed_v3_quality,
                    seed_v3_runtime_links, seed_v3_steps, seed_quote_pack_items]:
            print(fn())
    elif action == 'import-concepts':
        from library._core.kb.concepts import (
            import_article_concepts, import_beyond_order,
            import_maps_of_meaning, import_twelve_rules,
        )
        for fn in [import_beyond_order, import_maps_of_meaning, import_twelve_rules, import_article_concepts]:
            print(json.dumps(fn(), ensure_ascii=False, indent=2))
    elif action == 'import-knowledge':
        from library._core.kb.knowledge import (
            build_chapter_summaries,
            import_canonical_concepts,
            import_structured_knowledge,
        )
        for fn in [import_canonical_concepts, import_structured_knowledge, build_chapter_summaries]:
            print(json.dumps(fn(), ensure_ascii=False, indent=2))
    elif action == 'prune-revisions':
        from library._core.kb.build import prune_superseded_revisions
        print(json.dumps(
            prune_superseded_revisions(
                keep_latest_per_document=args.keep_superseded,
            ),
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(f'Unknown kb action: {action}', file=sys.stderr)
        sys.exit(1)


def cmd_ingest(args):
    action = args.ingest_action
    if action == 'auto':
        from library._core.ingest.auto import ingest
        print(json.dumps(ingest(dry_run=args.dry_run), ensure_ascii=False, indent=2))
    elif action == 'book':
        from library._core.ingest.book import register
        print(json.dumps(register(args.pdf, args.text, args.status), ensure_ascii=False, indent=2))
    else:
        print(f'Unknown ingest action: {action}', file=sys.stderr)
        sys.exit(1)


def cmd_mentor(args):
    action = args.mentor_action
    if action == 'check':
        from library._core.mentor.checkins import evaluate
        from library._core.mentor.render import render_event
        result = evaluate(args.question or '', user_id=args.user_id)
        if args.render:
            rendered = render_event(result.get('selected_event') or {})
            print(rendered)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif action == 'tick':
        from library._core.mentor.tick import tick
        result = tick(args.question or '', user_id=args.user_id, send=args.send)
        if args.render:
            print(result.get('rendered_message', ''))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif action == 'sent':
        from library._core.mentor.checkins import record_sent
        event = {'type': args.event_type, 'route': args.route, 'summary': args.summary, 'prompt': args.prompt}
        print(json.dumps(record_sent(event, user_id=args.user_id), ensure_ascii=False, indent=2))
    elif action == 'reply':
        from library._core.mentor.checkins import record_reply
        print(json.dumps(record_reply(user_id=args.user_id), ensure_ascii=False, indent=2))
    elif action == 'set-mode':
        from library._core.mentor.checkins import load_state, save_state
        state = load_state(user_id=args.user_id)
        state['mode'] = args.mode
        print(json.dumps(save_state(state, user_id=args.user_id), ensure_ascii=False, indent=2))
    elif action == 'targets-list':
        from library.mentor_targets_admin import list_targets
        print(json.dumps(list_targets(), ensure_ascii=False, indent=2))
    elif action == 'targets-enable':
        from library.mentor_targets_admin import set_enabled
        print(json.dumps(set_enabled(args.target_user, True), ensure_ascii=False, indent=2))
    elif action == 'targets-disable':
        from library.mentor_targets_admin import set_enabled
        print(json.dumps(set_enabled(args.target_user, False), ensure_ascii=False, indent=2))
    elif action == 'targets-add':
        from library.mentor_targets_admin import upsert_target
        print(json.dumps(upsert_target(args.target_user, channel=args.target_channel, target=args.target or '', enabled=args.target_enabled), ensure_ascii=False, indent=2))
    elif action == 'targets-remove':
        from library.mentor_targets_admin import remove_target
        print(json.dumps(remove_target(args.target_user), ensure_ascii=False, indent=2))
    elif action == 'targets-report':
        from library.mentor_targets_admin import onboarding_report
        print(json.dumps(onboarding_report(), ensure_ascii=False, indent=2))
    else:
        print(f'Unknown mentor action: {action}', file=sys.stderr)
        sys.exit(1)


def cmd_eval(args):
    action = args.eval_action
    if action == 'audit':
        from library._core.eval.audit import audit
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
    elif action == 'regression':
        from library._core.eval.regression import runtime_regression
        print(json.dumps(runtime_regression(), ensure_ascii=False, indent=2))
    elif action == 'voice-regression':
        from library._core.eval.regression import voice_regression
        print(json.dumps(voice_regression(), ensure_ascii=False, indent=2))
    elif action == 'full':
        from library._core.eval.evaluate import evaluate
        print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
    else:
        print(f'Unknown eval action: {action}', file=sys.stderr)
        sys.exit(1)


def cmd_trace(args):
    from library.config import get_default_store
    from library._core.state_store import KEY_TRACE_EVENTS

    store = get_default_store()
    rows = store.read_jsonl(canonical_user_id(args.user_id), KEY_TRACE_EVENTS)
    if args.trace_id:
        rows = [row for row in rows if row.get('trace_id') == args.trace_id]
    if args.event:
        rows = [row for row in rows if row.get('event') == args.event]
    if args.reverse:
        rows = list(reversed(rows))
    if args.limit:
        rows = rows[-args.limit:] if not args.reverse else rows[:args.limit]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_state(args):
    from library.config import CONVERSATION_AUDIT_LOG, RUNTIME_LOG, get_default_store

    store = get_default_store()
    if args.state_action == 'audit-default-workspace':
        print(json.dumps(
            store.audit_default_workspace_migration(),
            ensure_ascii=False,
            indent=2,
        ))
    elif args.state_action == 'log-paths':
        print(json.dumps({
            'runtime_log': str(RUNTIME_LOG),
            'conversation_audit_log': str(CONVERSATION_AUDIT_LOG),
        }, ensure_ascii=False, indent=2))
    else:
        print(f'Unknown state action: {args.state_action}', file=sys.stderr)
        sys.exit(1)


def build_parser():
    parser = argparse.ArgumentParser(prog='python -m library', description='Jordan Peterson Agent CLI')
    parser.add_argument('--user-id', dest='user_id', default='default',
                        help='User ID for multi-tenant state isolation')
    sub = parser.add_subparsers(dest='command')

    p_run = sub.add_parser('run', help='Orchestrate a full response')
    p_run.add_argument('question')
    p_run.set_defaults(func=cmd_run)

    p_frame = sub.add_parser('frame', help=argparse.SUPPRESS)
    p_frame.add_argument('question')
    p_frame.set_defaults(func=cmd_frame)

    p_respond = sub.add_parser('respond', help='Generate KB-backed response')
    p_respond.add_argument('question')
    p_respond.add_argument('--mode', choices=['quick', 'practical', 'deep'], default='deep')
    p_respond.add_argument('--voice', choices=['default', 'concise', 'hard', 'reflective'], default='default')
    p_respond.set_defaults(func=cmd_respond)

    p_retrieve = sub.add_parser('retrieve', help=argparse.SUPPRESS)
    p_retrieve.add_argument('question')
    p_retrieve.set_defaults(func=cmd_retrieve)

    p_prompt = sub.add_parser('prompt', help='Build LLM prompt for OpenClaw')
    p_prompt.add_argument('question')
    p_prompt.add_argument('--system-only', dest='system_only', action='store_true',
                          help='Print only the system prompt text')
    p_prompt.set_defaults(func=cmd_prompt)

    p_adapter = sub.add_parser('adapter', help='Build adapter-safe JSON contract')
    p_adapter.add_argument('adapter_channel', choices=['telegram'])
    p_adapter.add_argument('question')
    p_adapter.add_argument('--pretty', action='store_true',
                           help='Pretty-print adapter JSON payload')
    p_adapter.set_defaults(func=cmd_adapter)

    p_kb = sub.add_parser('kb', help='Knowledge base operations')
    p_kb.add_argument('kb_action', choices=[
        'build', 'doctor', 'smoke', 'query', 'query-v3', 'extract', 'normalize', 'evidence',
        'extract-quotes', 'normalize-quotes', 'load-quotes',
        'migrate-v3', 'migrate-v31', 'migrate-quotes-v2',
        'seed-v3', 'seed-all', 'import-concepts', 'import-knowledge',
        'prune-revisions',
    ])
    p_kb.add_argument('--query', default='')
    p_kb.add_argument('--table', default='')
    p_kb.add_argument('--limit', type=int, default=8)
    p_kb.add_argument('--theme', default='')
    p_kb.add_argument('--pattern', default='')
    p_kb.add_argument('--archetype', default='')
    p_kb.add_argument('--force', action='store_true',
                      help='Rebuild all indexed corpus documents')
    p_kb.add_argument('--allow-partial', dest='allow_partial',
                      action='store_true',
                      help='Allow kb build to proceed when some corpus files are missing')
    p_kb.add_argument('--no-enrich', action='store_true',
                      help='Only build raw chunks and taxonomy without enrichment')
    p_kb.add_argument('--keep-superseded', dest='keep_superseded', type=int, default=0,
                      help='How many newest superseded revisions to keep per document when pruning')
    p_kb.set_defaults(func=cmd_kb)

    p_ingest = sub.add_parser('ingest', help='Ingest source material')
    p_ingest.add_argument('ingest_action', choices=['auto', 'book'])
    p_ingest.add_argument('--pdf', default='')
    p_ingest.add_argument('--text', default=None)
    p_ingest.add_argument('--status', default='pending_text_extraction')
    p_ingest.add_argument('--dry-run', dest='dry_run', action='store_true',
                          help='Scan files without processing')
    p_ingest.set_defaults(func=cmd_ingest)

    p_eval = sub.add_parser('eval', help='Run evaluations')
    p_eval.add_argument('eval_action', choices=['audit', 'regression', 'voice-regression', 'full'])
    p_eval.set_defaults(func=cmd_eval)

    p_trace = sub.add_parser('trace', help='Inspect persisted runtime trace events')
    p_trace.add_argument('--trace-id', dest='trace_id', default='')
    p_trace.add_argument('--event', default='')
    p_trace.add_argument('--limit', type=int, default=50)
    p_trace.add_argument('--reverse', action='store_true')
    p_trace.set_defaults(func=cmd_trace)

    p_state = sub.add_parser('state', help='Inspect workspace state layout')
    p_state.add_argument('state_action', choices=['audit-default-workspace', 'log-paths'])
    p_state.set_defaults(func=cmd_state)

    p_mentor = sub.add_parser('mentor', help='Mentor follow-up triggers')
    p_mentor.add_argument('mentor_action', choices=['check', 'tick', 'sent', 'reply', 'set-mode', 'targets-list', 'targets-enable', 'targets-disable', 'targets-add', 'targets-remove', 'targets-report'])
    p_mentor.add_argument('--question', default='')
    p_mentor.add_argument('--render', action='store_true', help='Render only the selected follow-up message')
    p_mentor.add_argument('--send', action='store_true', help='Record the selected mentor event as sent')
    p_mentor.add_argument('--event-type', default='manual-checkin')
    p_mentor.add_argument('--route', default='general')
    p_mentor.add_argument('--summary', default='')
    p_mentor.add_argument('--prompt', default='')
    p_mentor.add_argument('--mode', choices=['gentle', 'standard', 'hard', 'silent'], default='standard')
    p_mentor.add_argument('--target-user', dest='target_user', default='')
    p_mentor.add_argument('--target-channel', dest='target_channel', default='telegram')
    p_mentor.add_argument('--target', default='')
    p_mentor.add_argument('--target-enabled', dest='target_enabled', action='store_true')
    p_mentor.set_defaults(func=cmd_mentor)

    return parser


def main():
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == '__main__':
    main()
