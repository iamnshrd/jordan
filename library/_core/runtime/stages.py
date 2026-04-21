"""Composable runtime stages used by the planner.

These helpers keep the planner focused on decision-making while the execution
details for policy, routing, retrieval, and synthesis live behind explicit
stage boundaries.
"""
from __future__ import annotations

from library._core.mentor.commitments import record_commitment
from library._core.runtime.frame import select_frame
from library._core.runtime.policy import detect_policy_block
from library._core.runtime.retrieval_validator import (
    get_relevance_judge, validate_chunks,
)
from library._core.runtime.synthesize import synthesize
from library._core.runtime.voice import choose as choose_voice
from library._core.session.checkpoint import log as log_checkpoint
from library._core.session.context import assemble as assemble_context
from library._core.session.continuity import load as load_continuity
from library._core.session.effectiveness import update as update_effectiveness
from library._core.session.progress import estimate as estimate_progress
from library._core.session.reaction import estimate as estimate_reaction
from library._core.session.state import build_user_profile, update_session
from library._core.state_store import StateStore
from library.utils import log_event, traced_stage


def run_policy_stage(question: str, *, user_id: str,
                     store: StateStore) -> dict | None:
    with traced_stage('policy.detect', store=store, user_id=user_id):
        return detect_policy_block(question, user_id=user_id, store=store)


def run_profile_context_stage(*, user_id: str, store: StateStore) -> None:
    with traced_stage('runtime.profile_context', store=store, user_id=user_id):
        build_user_profile(user_id=user_id, store=store)
        assemble_context(user_id=user_id, store=store)


def run_frame_stage(question: str, *, user_id: str, store: StateStore,
                    purpose: str) -> dict:
    with traced_stage('runtime.frame_selection', store=store, user_id=user_id):
        selected = select_frame(question, user_id=user_id, store=store)
        if purpose == 'response':
            record_commitment(
                question,
                route=selected.get('route_name') or '',
                user_id=user_id,
                store=store,
            )
    log_event(
        'planner.frame_selected',
        store=store,
        user_id=user_id,
        route_name=selected.get('route_name') or 'general',
        confidence=selected.get('confidence', 'low'),
        selected_theme=((selected.get('selected_theme') or {}).get('name') or ''),
        selected_principle=((selected.get('selected_principle') or {}).get('name') or ''),
        selected_pattern=((selected.get('selected_pattern') or {}).get('name') or ''),
    )
    return selected


def run_user_state_stage(question: str, *, user_id: str, store: StateStore,
                         purpose: str) -> tuple[dict, dict, dict]:
    with traced_stage('runtime.user_state', store=store, user_id=user_id):
        continuity = load_continuity(user_id=user_id, store=store)
        progress = estimate_progress(question, user_id=user_id, store=store)
        reaction = (
            estimate_reaction(question, user_id=user_id, store=store)
            if purpose == 'response' else {}
        )
    return continuity, progress, reaction


def run_retrieval_validation_stage(question: str, *, selected: dict,
                                   user_id: str,
                                   store: StateStore) -> dict:
    bundle = selected.get('bundle', {})
    retrieved_chunks = bundle.get('relevant_chunks', [])
    with traced_stage('runtime.retrieval_validation', store=store, user_id=user_id):
        validation = validate_chunks(
            question, retrieved_chunks, judge=get_relevance_judge(),
        )
    log_event(
        'planner.retrieval_validated',
        store=store,
        user_id=user_id,
        avg_relevance=validation.get('avg_relevance'),
        valid=validation.get('valid'),
        chunk_count=len(retrieved_chunks),
    )
    return validation


def run_voice_stage(question: str, *, selected: dict, progress: dict,
                    user_id: str, store: StateStore) -> str:
    theme_name = (selected.get('selected_theme') or {}).get('name', '')
    with traced_stage('runtime.voice_selection', store=store, user_id=user_id):
        voice_mode = choose_voice(
            question, theme=theme_name, user_id=user_id, store=store,
        ) or 'default'
        if progress.get('recommended_voice_override'):
            voice_mode = progress['recommended_voice_override']
    return voice_mode


def run_runtime_side_effects_stage(question: str, *, user_id: str,
                                   store: StateStore, selected: dict,
                                   progress: dict, reaction: dict,
                                   confidence: str,
                                   voice_mode: str) -> None:
    with traced_stage('runtime.side_effects', store=store, user_id=user_id):
        theme_name = (selected.get('selected_theme') or {}).get('name') or ''
        pattern_name = (selected.get('selected_pattern') or {}).get('name') or ''
        principle_name = (selected.get('selected_principle') or {}).get('name') or ''
        blend = selected.get('source_blend') or {}
        source_blend_str = (f"{blend.get('primary', '')}"
                            f"->{blend.get('secondary', '')}")

        update_session(
            question,
            theme=theme_name,
            pattern=pattern_name,
            principle=principle_name,
            source_blend=source_blend_str,
            voice=voice_mode,
            goal=theme_name,
            user_id=user_id,
            store=store,
        )

        action_step = ('narrow-burden'
                       if progress.get('recommended_response_mode') == 'narrow'
                       else 'normal-step')

        continuity = load_continuity(user_id=user_id, store=store)
        resolved_loop_summary = ''
        if continuity.get('resolved_loops'):
            first = continuity['resolved_loops'][0]
            resolved_loop_summary = (
                first.get('summary', '') if isinstance(first, dict) else str(first)
            )

        log_checkpoint({
            'question': question,
            'theme': theme_name,
            'pattern': pattern_name,
            'principle': principle_name,
            'source_blend': source_blend_str,
            'voice': voice_mode,
            'confidence': confidence,
            'action_step': action_step,
            'movement_estimate': progress.get('progress_state', 'unknown'),
            'user_reaction_estimate': reaction.get('user_reaction_estimate', 'unknown'),
            'resolved_loop_if_any': resolved_loop_summary,
            'session_goal': theme_name,
            'recommended_next_mode': progress.get('recommended_response_mode', 'normal'),
        }, user_id=user_id, store=store)

        primary = blend.get('primary', '')
        progress_state = progress.get('progress_state')
        reaction_est = reaction.get('user_reaction_estimate')

        if progress_state == 'moving' and reaction_est == 'accepting':
            outcome = 'helpful'
        elif progress_state == 'fragile' or reaction_est == 'ambiguous':
            outcome = 'neutral'
        else:
            outcome = 'resisted'

        if primary:
            route_name = selected.get('route_name') or 'general'
            update_effectiveness(
                source=primary,
                outcome=outcome,
                route=route_name,
                user_id=user_id,
                store=store,
            )


def run_synthesis_stage(question: str, *, user_id: str, store: StateStore,
                        selected: dict, progress: dict) -> dict:
    with traced_stage('runtime.synthesis', store=store, user_id=user_id):
        synthesis_data = synthesize(
            question, user_id=user_id, store=store,
            frame=selected, progress=progress,
        )
    log_event(
        'planner.synthesis_ready',
        store=store,
        user_id=user_id,
        backed_fields=(synthesis_data.get('grounding_report') or {}).get('backed_fields', []),
        missing_fields=(synthesis_data.get('grounding_report') or {}).get('missing_fields', []),
    )
    return synthesis_data
