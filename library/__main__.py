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
        }, ensure_ascii=False, indent=2))


def cmd_frame(args):
    from library._core.runtime.frame import select_frame
    print(json.dumps(select_frame(args.question), ensure_ascii=False, indent=2))


def cmd_respond(args):
    from library._core.runtime.respond import respond
    print(respond(args.question, mode=args.mode, voice=args.voice,
                  user_id=args.user_id))


def cmd_retrieve(args):
    from library._core.runtime.retrieve import build_response_bundle
    print(json.dumps(build_response_bundle(args.question), ensure_ascii=False, indent=2))


def cmd_kb(args):
    action = args.kb_action
    if action == 'build':
        from library._core.kb.build import build
        print(json.dumps(build(), ensure_ascii=False, indent=2))
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
        from library._core.kb.concepts import import_beyond_order, import_maps_of_meaning, import_twelve_rules
        for fn in [import_beyond_order, import_maps_of_meaning, import_twelve_rules]:
            print(json.dumps(fn(), ensure_ascii=False, indent=2))
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


def build_parser():
    parser = argparse.ArgumentParser(prog='python -m library', description='Jordan Peterson Agent CLI')
    parser.add_argument('--user-id', dest='user_id', default='default',
                        help='User ID for multi-tenant state isolation')
    sub = parser.add_subparsers(dest='command')

    p_run = sub.add_parser('run', help='Orchestrate a full response')
    p_run.add_argument('question')
    p_run.set_defaults(func=cmd_run)

    p_frame = sub.add_parser('frame', help='Select psychological frame')
    p_frame.add_argument('question')
    p_frame.set_defaults(func=cmd_frame)

    p_respond = sub.add_parser('respond', help='Generate KB-backed response')
    p_respond.add_argument('question')
    p_respond.add_argument('--mode', choices=['quick', 'practical', 'deep'], default='deep')
    p_respond.add_argument('--voice', choices=['default', 'concise', 'hard', 'reflective'], default='default')
    p_respond.set_defaults(func=cmd_respond)

    p_retrieve = sub.add_parser('retrieve', help='Build response bundle')
    p_retrieve.add_argument('question')
    p_retrieve.set_defaults(func=cmd_retrieve)

    p_prompt = sub.add_parser('prompt', help='Build LLM prompt for OpenClaw')
    p_prompt.add_argument('question')
    p_prompt.add_argument('--system-only', dest='system_only', action='store_true',
                          help='Print only the system prompt text')
    p_prompt.set_defaults(func=cmd_prompt)

    p_kb = sub.add_parser('kb', help='Knowledge base operations')
    p_kb.add_argument('kb_action', choices=[
        'build', 'query', 'query-v3', 'extract', 'normalize', 'evidence',
        'extract-quotes', 'normalize-quotes', 'load-quotes',
        'migrate-v3', 'migrate-v31', 'migrate-quotes-v2',
        'seed-v3', 'seed-all', 'import-concepts',
    ])
    p_kb.add_argument('--query', default='')
    p_kb.add_argument('--table', default='')
    p_kb.add_argument('--limit', type=int, default=8)
    p_kb.add_argument('--theme', default='')
    p_kb.add_argument('--pattern', default='')
    p_kb.add_argument('--archetype', default='')
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

    p_mentor = sub.add_parser('mentor', help='Mentor follow-up triggers')
    p_mentor.add_argument('mentor_action', choices=['check', 'tick', 'sent', 'reply', 'set-mode'])
    p_mentor.add_argument('--question', default='')
    p_mentor.add_argument('--render', action='store_true', help='Render only the selected follow-up message')
    p_mentor.add_argument('--send', action='store_true', help='Record the selected mentor event as sent')
    p_mentor.add_argument('--event-type', default='manual-checkin')
    p_mentor.add_argument('--route', default='general')
    p_mentor.add_argument('--summary', default='')
    p_mentor.add_argument('--prompt', default='')
    p_mentor.add_argument('--mode', choices=['gentle', 'standard', 'hard', 'silent'], default='standard')
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
