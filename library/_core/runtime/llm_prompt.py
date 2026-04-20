"""Build LLM prompts from retrieved context for OpenClaw integration.

OpenClaw handles the actual LLM call; this module assembles the system
prompt and user context so the response is grounded in KB evidence.
"""
from __future__ import annotations

from pathlib import Path
from library.config import get_default_store
from library._core.state_store import StateStore
from library.utils import ensure_trace_context, log_event, traced_stage


_PERSONA_CACHE: str | None = None
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _load_persona() -> str:
    """Load IDENTITY.md + SOUL.md as the base persona."""
    global _PERSONA_CACHE
    if _PERSONA_CACHE is not None:
        return _PERSONA_CACHE

    parts: list[str] = []
    for fname in ('IDENTITY.md', 'SOUL.md'):
        path = _PROJECT_ROOT / fname
        if path.exists():
            parts.append(path.read_text(encoding='utf-8').strip())
    _PERSONA_CACHE = '\n\n'.join(parts) if parts else ''
    return _PERSONA_CACHE


def _format_evidence(chunks: list[dict], max_chunks: int = 5) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks[:max_chunks], 1):
        snippet = c.get('snippet', c.get('content', ''))
        lines.append(f'[{i}] {snippet}')
    return '\n'.join(lines)


def _format_quotes(quotes: list[dict], max_quotes: int = 3) -> str:
    lines: list[str] = []
    for q in quotes[:max_quotes]:
        text = q.get('quote_text', '')
        if text:
            lines.append(f'> {text}')
    return '\n'.join(lines)


def _format_structured_rows(rows: list[dict], title_key: str = 'title',
                            body_key: str = 'summary',
                            max_rows: int = 3) -> str:
    lines: list[str] = []
    for row in rows[:max_rows]:
        title = (row.get(title_key) or '').strip()
        body = (row.get(body_key) or '').strip()
        if title and body:
            lines.append(f'- {title}: {body}')
        elif title:
            lines.append(f'- {title}')
        elif body:
            lines.append(f'- {body}')
    return '\n'.join(lines)


def _prefer_source_linked_rows(rows: list[dict], max_rows: int = 2) -> list[dict]:
    preferred = [row for row in rows if row.get('_source_preference', 999) < 999]
    source = preferred or rows
    return source[:max_rows]


def _has_text(value: str | None) -> bool:
    return bool((value or '').strip())


def _append_db_backed_synthesis(system_parts: list[str], data: dict) -> None:
    """Only expose synthesis fields that are backed by DB-selected rows."""
    fields = ((data.get('grounding_report') or {}).get('fields') or {})

    if _has_text(data.get('core_problem')) and (fields.get('core_problem') or {}).get('backed'):
        system_parts.append(f'- Ядро проблемы: {data["core_problem"]}')
    if _has_text(data.get('relevant_pattern')) and (fields.get('relevant_pattern') or {}).get('backed'):
        system_parts.append(f'- Релевантный паттерн: {data["relevant_pattern"]}')
    if (_has_text(data.get('responsibility_avoided'))
            and (fields.get('responsibility_avoided') or {}).get('backed')):
        system_parts.append(
            f'- Избегаемая ответственность: {data["responsibility_avoided"]}'
        )
    if _has_text(data.get('guiding_principle')) and (fields.get('guiding_principle') or {}).get('backed'):
        system_parts.append(f'- Опорный принцип: {data["guiding_principle"]}')
    if (_has_text(data.get('practical_next_step'))
            and (fields.get('practical_next_step') or {}).get('backed')):
        system_parts.append(f'- Следующий шаг: {data["practical_next_step"]}')
    if (_has_text(data.get('longer_term_correction'))
            and (fields.get('longer_term_correction') or {}).get('backed')):
        system_parts.append(
            f'- Долгосрочная коррекция: {data["longer_term_correction"]}'
        )


def _append_grounding_report(system_parts: list[str], data: dict) -> None:
    report = data.get('grounding_report') or {}
    backed = report.get('backed_fields') or []
    missing = report.get('missing_fields') or []
    evidence_count = report.get('evidence_count', 0)
    quote_count = report.get('quote_count', 0)
    structured_count = report.get('structured_count', 0)
    system_parts.append('\n## Grounding Report')
    system_parts.append(f'- DB-backed fields: {", ".join(backed) if backed else "none"}')
    system_parts.append(f'- Missing DB backing: {", ".join(missing) if missing else "none"}')
    system_parts.append(f'- Evidence chunks: {evidence_count}')
    system_parts.append(f'- Quotes: {quote_count}')
    system_parts.append(f'- Structured knowledge rows: {structured_count}')


def build_prompt(question: str, user_id: str = 'default',
                 store: StateStore | None = None,
                 voice_mode: str = 'default',
                 plan=None,
                 frame: dict | None = None,
                 progress: dict | None = None,
                 precomputed_synthesis: dict | None = None) -> dict:
    """Assemble an LLM-ready prompt from the full reasoning pipeline.

    When *precomputed_synthesis* is provided, skip the expensive synthesize()
    call and use the provided data directly.

    Returns a dict with:
    - ``system``: system prompt (persona + retrieved context + instructions)
    - ``user``: user message (the question)
    - ``synthesis``: the full synthesis dict (for fallback rendering)
    - ``continuity``: user continuity state
    """
    store = store or get_default_store()
    with ensure_trace_context(user_id=user_id, store=store,
                              purpose='prompt', question=question):
        log_event('prompt.entry', store=store, user_id=user_id,
                  voice_mode=voice_mode)
        with traced_stage('runtime.prompt_build', store=store, user_id=user_id):
            if plan is None:
                from library._core.runtime.planner import build_answer_plan
                plan = build_answer_plan(question, user_id=user_id, store=store, purpose='prompt')
            if not plan.decision.allow_llm_prompt:
                result = plan.prompt_result()
                log_event(
                    'prompt.short_circuit',
                    store=store,
                    user_id=user_id,
                    action=result.get('action', ''),
                    reason=(result.get('decision_meta') or {}).get('reason', ''),
                )
                return result

            data = precomputed_synthesis or plan.synthesis or {}
            continuity = plan.continuity or {}

    bundle = data.get('raw_selection', {}).get('bundle', {})
    chunks = bundle.get('relevant_chunks', [])
    quotes = bundle.get('relevant_quotes', [])
    canonical_concepts = bundle.get('canonical_concepts', [])
    definitions = bundle.get('relevant_definitions', [])
    claims = bundle.get('relevant_claims', [])
    practices = bundle.get('relevant_practices', [])
    objections = bundle.get('relevant_objections', [])
    chapter_summaries = bundle.get('relevant_chapter_summaries', [])

    raw = data.get('raw_selection') or {}
    theme_sel = raw.get('selected_theme')
    theme_name = theme_sel.get('name', '') if isinstance(theme_sel, dict) else ''
    principle_sel = raw.get('selected_principle')
    principle_name = principle_sel.get('name', '') if isinstance(principle_sel, dict) else ''
    pattern_sel = raw.get('selected_pattern')
    pattern_name = pattern_sel.get('name', '') if isinstance(pattern_sel, dict) else ''

    persona = _load_persona()

    system_parts: list[str] = []

    if persona:
        system_parts.append(persona)

    system_parts.append('## Инструкция по генерации ответа')
    system_parts.append(
        'Ты отвечаешь на вопрос пользователя, опираясь на конкретный контекст из библиотеки. '
        'НЕ выдумывай цитаты. Используй только предоставленные фрагменты и цитаты. '
        'Если в предоставленном контексте нет опоры для утверждения, не компенсируй это знаниями модели: '
        'коротко обозначь ограничение и попроси уточнение. '
        'Каждый содержательный тезис в ответе должен опираться на явный claim, practice, objection или quote из контекста ниже. '
        'Не расширяй ответ до длинной таксономии качеств, если в контексте нет такого количества отдельных DB-backed утверждений. '
        'Отвечай на русском языке в стиле, описанном в persona выше.'
    )

    if voice_mode == 'hard':
        system_parts.append('Стиль: прямой, требовательный, без смягчений.')
    elif voice_mode == 'reflective':
        system_parts.append('Стиль: вдумчивый, рефлексивный, без нотаций.')
    else:
        system_parts.append('Стиль: серьёзный, структурированный, конкретный.')

    system_parts.append('\n## Выбранная рамка')
    system_parts.append(f'- Тема: {theme_name}')
    system_parts.append(f'- Принцип: {principle_name}')
    system_parts.append(f'- Паттерн: {pattern_name}')
    _append_db_backed_synthesis(system_parts, data)
    _append_grounding_report(system_parts, data)

    tone_hint = data.get('tone_hint')
    if tone_hint:
        system_parts.append(f'- Тональность intervention: {tone_hint}')

    blend = data.get('source_blend') or {}
    if blend.get('primary'):
        system_parts.append(f'- Основной источник: {blend["primary"]}')
    rationale = data.get('source_blend_rationale')
    if rationale:
        system_parts.append(f'- Почему этот источник: {rationale}')

    if chunks:
        system_parts.append('\n## Релевантные фрагменты из библиотеки')
        system_parts.append(_format_evidence(chunks, max_chunks=3))

    filtered_quotes = _prefer_source_linked_rows(quotes, max_rows=2)
    filtered_claims = _prefer_source_linked_rows(claims, max_rows=2)
    filtered_practices = _prefer_source_linked_rows(practices, max_rows=2)
    filtered_objections = _prefer_source_linked_rows(objections, max_rows=1)
    filtered_definitions = _prefer_source_linked_rows(definitions, max_rows=1)

    if filtered_quotes:
        system_parts.append('\n## Подходящие цитаты')
        system_parts.append(_format_quotes(filtered_quotes, max_quotes=2))

    if filtered_claims:
        system_parts.append('\n## Claims')
        system_parts.append(_format_structured_rows(
            filtered_claims, title_key='title', body_key='summary', max_rows=2,
        ))

    if filtered_practices:
        system_parts.append('\n## Practices')
        system_parts.append(_format_structured_rows(
            filtered_practices, title_key='title', body_key='summary', max_rows=2,
        ))

    if filtered_objections:
        system_parts.append('\n## Objections And Replies')
        system_parts.append(_format_structured_rows(
            filtered_objections, title_key='title', body_key='response', max_rows=1,
        ))

    if not filtered_claims and not filtered_practices and filtered_definitions:
        system_parts.append('\n## Definitions')
        system_parts.append(_format_structured_rows(
            filtered_definitions, title_key='title', body_key='summary', max_rows=1,
        ))

    if data.get('supporting_quote'):
        system_parts.append(f'\n## Рекомендованная цитата для ответа')
        system_parts.append(f'> {data["supporting_quote"]}')

    recurring_themes = continuity.get('recurring_themes', [])
    user_patterns = continuity.get('user_patterns', [])
    if recurring_themes or user_patterns:
        system_parts.append('\n## Контекст пользователя (continuity)')
        if recurring_themes:
            names = [t['name'] if isinstance(t, dict) else str(t)
                     for t in recurring_themes[:5]]
            system_parts.append(f'- Повторяющиеся темы: {", ".join(names)}')
        if user_patterns:
            names = [p['name'] if isinstance(p, dict) else str(p)
                     for p in user_patterns[:5]]
            system_parts.append(f'- Повторяющиеся паттерны: {", ".join(names)}')

    system_parts.append('\n## Формат ответа')
    system_parts.append(
        'Собери короткий ответ из 2-4 абзацев.\n'
        'Используй максимум 3 substantive points, и только если каждый из них явно поддержан claim/practice/quote выше.\n'
        'Если вопрос слишком широкий для такого ответа, не достраивай список из общих качеств — прямо сузь рамку и попроси уточнение.\n'
        'Не нумеруй пункты в финальном ответе.'
    )

    plan.system = '\n'.join(system_parts)
    plan.user = question
    plan.synthesis = data
    plan.continuity = continuity
    result = plan.prompt_result()
    log_event(
        'prompt.completed',
        store=store,
        user_id=user_id,
        action=result.get('action', ''),
        system_length=len(result.get('system', '')),
        backed_fields=(data.get('grounding_report') or {}).get('backed_fields', []),
    )
    return result


def build_fallback_response(prompt_result: dict, mode: str = 'deep',
                            voice_mode: str = 'default') -> str:
    """Render a template-based response from the synthesis data (no LLM needed).

    Use this when OpenClaw's LLM call fails or is unavailable.
    """
    from library._core.runtime.respond import render
    return render(
        prompt_result['synthesis'],
        prompt_result['continuity'],
        mode=mode,
        voice_mode=voice_mode,
    )
