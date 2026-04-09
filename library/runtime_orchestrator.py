#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')
RESPOND = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/respond_with_kb.py')
READ_CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/read_continuity.py')
USER_STATE = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/user_state_profile.py')
UPDATE_SESSION = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/update_session_state.py')
UPDATE_EFFECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/update_effectiveness_memory.py')
LOG_CHECKPOINT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/log_session_checkpoint.py')
CHOOSE_VOICE = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/choose_voice_mode.py')
CONTEXT_GRAPH = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/assemble_context_graph.py')
PROGRESS = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/estimate_progress_state.py')
REACTION = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/estimate_user_reaction.py')


def run_json(cmd):
    return json.loads(subprocess.check_output(cmd, text=True))


def detect_mode(question):
    q = question.lower()
    practical_triggers = ['что мне делать', 'что делать', 'next step', 'практически', 'как мне', 'что дальше']
    deep_triggers = ['почему', 'разбери', 'объясни', 'помоги понять', 'что со мной происходит', 'в чём корень']
    if any(x in q for x in deep_triggers):
        return 'deep'
    if any(x in q for x in practical_triggers):
        return 'practical'
    if len(q) < 80:
        return 'practical'
    return 'deep'


def should_use_kb(question):
    q = question.lower()
    triggers = ['смысл', 'дисциплин', 'обид', 'стыд', 'отношен', 'конфликт', 'карьер', 'призвание', 'хаос', 'вру', 'самообман']
    return any(t in q for t in triggers)


def orchestrate(question):
    mode = detect_mode(question)
    if not should_use_kb(question):
        return {
            'question': question,
            'mode': mode,
            'use_kb': False,
            'confidence': 'low',
            'action': 'answer-directly',
            'reason': 'Question does not strongly match psychological/philosophical KB routes.',
            'continuity': run_json(['python3', str(READ_CONT)]),
        }
    subprocess.check_output(['python3', str(USER_STATE)], text=True)
    selected = run_json(['python3', str(SELECT), question])
    confidence = selected.get('confidence', 'low')
    continuity = run_json(['python3', str(READ_CONT)])
    progress = run_json(['python3', str(PROGRESS), question])
    reaction = run_json(['python3', str(REACTION), question])
    if confidence == 'low':
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': confidence,
            'action': 'ask-clarifying-question',
            'reason': 'KB route is weak; clarification preferred before forcing a frame.',
            'selection': selected,
            'continuity': continuity,
        }
    voice = subprocess.check_output([
        'python3', str(CHOOSE_VOICE), question,
        '--theme', ((selected.get('selected_theme') or {}).get('name') or '')
    ], text=True).strip() or 'default'
    if progress.get('recommended_voice_override'):
        voice = progress['recommended_voice_override']
    subprocess.check_output([
        'python3', str(UPDATE_SESSION), question,
        '--theme', ((selected.get('selected_theme') or {}).get('name') or ''),
        '--pattern', ((selected.get('selected_pattern') or {}).get('name') or ''),
        '--principle', ((selected.get('selected_principle') or {}).get('name') or ''),
        '--source-blend', f"{(selected.get('source_blend') or {}).get('primary','')}->{(selected.get('source_blend') or {}).get('secondary','')}",
        '--voice', voice,
        '--goal', ((selected.get('selected_theme') or {}).get('name') or '')
    ], text=True)
    action_step = 'narrow-burden' if progress.get('recommended_response_mode') == 'narrow' else 'normal-step'
    subprocess.check_output([
        'python3', str(LOG_CHECKPOINT), question,
        '--theme', ((selected.get('selected_theme') or {}).get('name') or ''),
        '--pattern', ((selected.get('selected_pattern') or {}).get('name') or ''),
        '--principle', ((selected.get('selected_principle') or {}).get('name') or ''),
        '--source-blend', f"{(selected.get('source_blend') or {}).get('primary','')}->{(selected.get('source_blend') or {}).get('secondary','')}",
        '--voice', voice,
        '--confidence', confidence,
        '--action-step', action_step,
        '--movement-estimate', progress.get('progress_state', 'unknown'),
        '--user-reaction-estimate', reaction.get('user_reaction_estimate', 'unknown'),
        '--resolved-loop-if-any', continuity.get('resolved_loops', [{}])[0].get('summary', '') if continuity.get('resolved_loops') else '',
        '--session-goal', ((selected.get('selected_theme') or {}).get('name') or ''),
        '--recommended-next-mode', progress.get('recommended_response_mode', 'normal'),
    ], text=True)
    primary = (selected.get('source_blend') or {}).get('primary', '')
    outcome = 'helpful' if progress.get('progress_state') == 'moving' and reaction.get('user_reaction_estimate') == 'accepting' else 'neutral' if progress.get('progress_state') == 'fragile' or reaction.get('user_reaction_estimate') == 'ambiguous' else 'resisted'
    if primary:
        subprocess.check_output(['python3', str(UPDATE_EFFECT), '--source', primary, '--outcome', outcome, '--route', ((selected.get('selected_theme') or {}).get('name') or '')], text=True)
    subprocess.check_output(['python3', str(CONTEXT_GRAPH)], text=True)
    response = subprocess.check_output(['python3', str(RESPOND), question, '--mode', mode if mode in {'quick','practical','deep'} else 'deep', '--voice', voice], text=True)
    return {
        'question': question,
        'mode': mode,
        'use_kb': True,
        'confidence': confidence,
        'action': 'respond-with-kb',
        'selection': selected,
        'continuity': continuity,
        'progress': progress,
        'reaction': reaction,
        'response': response,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(orchestrate(args.question), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
