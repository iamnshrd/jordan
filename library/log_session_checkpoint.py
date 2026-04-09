#!/usr/bin/env python3
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.checkpoint import log

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--principle', default='')
    ap.add_argument('--source-blend', default='')
    ap.add_argument('--voice', default='default')
    ap.add_argument('--confidence', default='medium')
    ap.add_argument('--action-step', default='')
    ap.add_argument('--movement-estimate', default='unknown')
    ap.add_argument('--user-reaction-estimate', default='unknown')
    ap.add_argument('--resolved-loop-if-any', default='')
    ap.add_argument('--session-goal', default='')
    ap.add_argument('--recommended-next-mode', default='')
    args = ap.parse_args()
    result = log({
        'question': args.question,
        'theme': args.theme,
        'pattern': args.pattern,
        'principle': args.principle,
        'source_blend': getattr(args, 'source_blend', ''),
        'voice': args.voice,
        'confidence': args.confidence,
        'action_step': getattr(args, 'action_step', ''),
        'movement_estimate': getattr(args, 'movement_estimate', 'unknown'),
        'user_reaction_estimate': getattr(args, 'user_reaction_estimate', 'unknown'),
        'resolved_loop_if_any': getattr(args, 'resolved_loop_if_any', ''),
        'session_goal': getattr(args, 'session_goal', ''),
        'recommended_next_mode': getattr(args, 'recommended_next_mode', ''),
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))
