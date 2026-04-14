"""Build LLM prompts from retrieved context for OpenClaw integration.

OpenClaw handles the actual LLM call; this module assembles the system
prompt and user context so the response is grounded in KB evidence.
"""
from __future__ import annotations

from pathlib import Path
from library.config import get_default_store
from library._core.runtime.synthesize import synthesize
from library._core.session.continuity import load as load_continuity
from library._core.state_store import StateStore


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


def build_prompt(question: str, user_id: str = 'default',
                 store: StateStore | None = None,
                 voice_mode: str = 'default',
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
    data = precomputed_synthesis or synthesize(
        question, user_id=user_id, store=store,
        frame=frame, progress=progress,
    )
    continuity = load_continuity(user_id=user_id, store=store)

    bundle = data.get('raw_selection', {}).get('bundle', {})
    chunks = bundle.get('relevant_chunks', [])
    quotes = bundle.get('relevant_quotes', [])

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

    if data.get('core_problem'):
        system_parts.append(f'- Ядро проблемы: {data["core_problem"]}')
    if data.get('responsibility_avoided'):
        system_parts.append(f'- Избегаемая ответственность: {data["responsibility_avoided"]}')
    if data.get('guiding_principle'):
        system_parts.append(f'- Опорный принцип: {data["guiding_principle"]}')
    if data.get('practical_next_step'):
        system_parts.append(f'- Следующий шаг: {data["practical_next_step"]}')
    if data.get('longer_term_correction'):
        system_parts.append(f'- Долгосрочная коррекция: {data["longer_term_correction"]}')

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
        system_parts.append(_format_evidence(chunks))

    if quotes:
        system_parts.append('\n## Подходящие цитаты')
        system_parts.append(_format_quotes(quotes))

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
        'Структурируй ответ:\n'
        '1. Назови ядро проблемы (1-2 предложения)\n'
        '2. Покажи паттерн, который поддерживает проблему\n'
        '3. Назови избегаемую ответственность\n'
        '4. Дай опорный принцип\n'
        '5. Включи цитату если она релевантна\n'
        '6. Дай конкретный следующий шаг\n'
        '7. Обозначь долгосрочное направление коррекции\n'
        'Не нумеруй пункты в финальном ответе — пиши связным текстом с абзацами.'
    )

    return {
        'system': '\n'.join(system_parts),
        'user': question,
        'synthesis': data,
        'continuity': continuity,
    }


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
