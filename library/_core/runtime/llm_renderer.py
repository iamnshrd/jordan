"""Controlled LLM renderer for frame-driven final_text answers."""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import os
import re
from typing import Any, Callable

from library.utils import log_event


_llm_renderer: Callable[..., Any] | None = None
_autoload_attempted = False
_llm_renderer_backend = 'none'
_llm_renderer_backend_detail = ''

_DEFAULT_FORBIDDEN_OPENERS = (
    'хорошо',
    'хорошо,',
    'хорошо.',
)

_DEFAULT_HARD_BANS = (
    'цитат',
    'цитата',
    'книга',
    'книг',
    'источник',
    'источники',
    'подкаст',
    'лекци',
    'lecture',
    'book',
    'quote',
    'source',
    'resentment',
)


@dataclass(frozen=True)
class LLMRenderRequest:
    frame_topic: str
    frame_goal: str
    frame_relation_to_previous: str
    transition_kind: str
    route_name: str
    profile: str
    stance: str
    axis: str
    detail: str
    question_kind: str
    render_kind: str
    fallback_text: str
    needs_ack: bool = False
    ends_with_question: bool = False
    max_sentences: int = 4
    allow_list: bool = False
    tone_variant: str = 'jordan_concise'
    forbidden_openers: tuple[str, ...] = ()
    hard_bans: tuple[str, ...] = ()
    prompt_notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'frame_topic': self.frame_topic,
            'frame_goal': self.frame_goal,
            'frame_relation_to_previous': self.frame_relation_to_previous,
            'transition_kind': self.transition_kind,
            'route_name': self.route_name,
            'profile': self.profile,
            'stance': self.stance,
            'axis': self.axis,
            'detail': self.detail,
            'question_kind': self.question_kind,
            'render_kind': self.render_kind,
            'fallback_text': self.fallback_text,
            'needs_ack': self.needs_ack,
            'ends_with_question': self.ends_with_question,
            'max_sentences': self.max_sentences,
            'allow_list': self.allow_list,
            'tone_variant': self.tone_variant,
            'forbidden_openers': list(self.forbidden_openers),
            'hard_bans': list(self.hard_bans),
            'prompt_notes': list(self.prompt_notes),
        }


@dataclass
class LLMRenderResult:
    rendered_text: str
    renderer_status: str
    attempt_count: int
    validation_flags: list[str] = field(default_factory=list)
    exception_detail: str = ''
    renderer_used: bool = False
    fallback_used: bool = False
    renderer_backend: str = 'none'
    renderer_backend_detail: str = ''

    def metadata(self) -> dict[str, Any]:
        return {
            'renderer_used': self.renderer_used,
            'renderer_mode': 'frame_final_text',
            'renderer_status': self.renderer_status,
            'renderer_backend': self.renderer_backend,
            'renderer_backend_detail': self.renderer_backend_detail,
            'renderer_attempt_count': self.attempt_count,
            'renderer_fallback_used': self.fallback_used,
            'renderer_validation_failures': list(self.validation_flags),
            'renderer_exception_detail': self.exception_detail,
        }


def _format_renderer_exception(exc: Exception) -> str:
    detail = f'{type(exc).__name__}: {exc}'.strip()
    return detail[:500]


def _renderer_detail_for(fn: Callable[..., Any] | None) -> str:
    if fn is None:
        return ''
    detail = getattr(fn, '__jordan_renderer_backend_detail__', '')
    if callable(detail):
        try:
            resolved = detail()
        except Exception:
            resolved = ''
        if isinstance(resolved, str):
            return resolved
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    module = getattr(fn, '__module__', '')
    name = getattr(fn, '__name__', '')
    if module and name:
        return f'{module}:{name}'
    return ''


def _set_renderer(fn: Callable[..., Any] | None, *, backend: str) -> None:
    global _llm_renderer, _llm_renderer_backend, _llm_renderer_backend_detail
    _llm_renderer = fn
    _llm_renderer_backend = backend if fn is not None else 'none'
    _llm_renderer_backend_detail = _renderer_detail_for(fn) if fn is not None else ''


def set_llm_renderer(fn: Callable[..., Any] | None) -> None:
    global _autoload_attempted
    _llm_renderer = fn
    _autoload_attempted = fn is not None
    _set_renderer(fn, backend='custom_hook')


def reset_llm_renderer() -> None:
    global _autoload_attempted
    _set_renderer(None, backend='none')
    _autoload_attempted = False


def _autoload_renderer_from_env() -> None:
    global _autoload_attempted
    if _autoload_attempted:
        return
    _autoload_attempted = True
    hook_ref = (
        os.environ.get('JORDAN_LLM_RENDERER_HOOK')
        or os.environ.get('JORDAN_LLM_RENDERER')
        or ''
    ).strip()
    if not hook_ref or ':' not in hook_ref:
        if str(os.environ.get('JORDAN_DISABLE_ANTHROPIC_API_RENDERER') or '').strip().lower() not in {
            '1', 'true', 'yes',
        }:
            try:
                from library._core.runtime.anthropic_api_renderer import (
                    is_available as anthropic_renderer_available,
                    render_via_anthropic_api,
                )
            except Exception:
                pass
            else:
                if anthropic_renderer_available():
                    _set_renderer(render_via_anthropic_api, backend='anthropic_api')
                    return
        if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_API_RENDERER') or '').strip().lower() not in {
            '1', 'true', 'yes',
        }:
            try:
                from library._core.runtime.openclaw_api_renderer import (
                    is_available as api_renderer_available,
                    render_via_openclaw_api,
                )
            except Exception:
                pass
            else:
                if api_renderer_available():
                    _set_renderer(render_via_openclaw_api, backend='openclaw_api')
                    return
        if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_CLI_RENDERER') or '').strip().lower() not in {
            '1', 'true', 'yes',
        }:
            try:
                from library._core.runtime.openclaw_cli_renderer import (
                    is_available as cli_renderer_available,
                    render_via_openclaw_cli,
                )
            except Exception:
                pass
            else:
                if cli_renderer_available():
                    _set_renderer(render_via_openclaw_cli, backend='openclaw_cli')
                    return
        if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER') or '').strip().lower() in {
            '1', 'true', 'yes',
        }:
            return
        try:
            from library._core.runtime.openclaw_gateway_renderer import (
                is_available as gateway_renderer_available,
                render_via_openclaw_gateway,
            )
        except Exception:
            return
        if gateway_renderer_available():
            _set_renderer(render_via_openclaw_gateway, backend='openclaw_gateway')
        return
    module_name, attr_name = hook_ref.split(':', 1)
    module_name = module_name.strip()
    attr_name = attr_name.strip()
    if not module_name or not attr_name:
        return
    try:
        module = importlib.import_module(module_name)
        candidate = getattr(module, attr_name, None)
    except Exception:
        return
    if callable(candidate):
        _set_renderer(candidate, backend='custom_hook')


def build_render_prompt(request: LLMRenderRequest, *, violations: list[str] | None = None) -> dict[str, str]:
    prompt_lines = [
        'Сформулируй естественный русский ответ в стиле Jordan-like mentor voice без пародии.',
        'Не меняй смысл и не добавляй новых утверждений.',
        'Не упоминай базу, книги, источники, цитаты, лекции или подкасты.',
        'Не ставь диагнозы и не звучай бюрократично.',
        'Не начинай ответ однотипно со слова "Хорошо".',
        f'Тема: {request.frame_topic}. Цель ответа: {request.frame_goal}.',
        f'Тип рендера: {request.render_kind}. Позиция: {request.stance}.',
    ]
    if request.needs_ack:
        prompt_lines.append('Ответ должен естественно продолжать предыдущий ход разговора.')
    if request.ends_with_question:
        prompt_lines.append('Ответ должен заканчиваться одним естественным вопросом.')
    else:
        prompt_lines.append('Ответ не должен заканчиваться вопросом и не должен содержать лишних вопросов.')
    prompt_lines.append(f'Максимум предложений: {request.max_sentences}.')
    if request.allow_list:
        prompt_lines.append('Короткий список допустим, если он звучит естественно.')
    if request.axis:
        prompt_lines.append(f'Текущая ось: {request.axis}.')
    if request.detail:
        prompt_lines.append(f'Текущая деталь: {request.detail}.')
    for note in request.prompt_notes:
        prompt_lines.append(note)
    if violations:
        prompt_lines.append('Исправь предыдущий невалидный рендер с учётом нарушений:')
        prompt_lines.extend(f'- {item}' for item in violations)
    prompt_lines.append('Опирайся на этот approved fallback как на смысловой контракт:')
    prompt_lines.append(request.fallback_text)
    return {
        'system': 'Ты переписываешь уже одобренный deterministic ответ в более живой и естественный русский ответ, не меняя его смысл и ограничения.',
        'user': '\n'.join(prompt_lines).strip(),
    }


def _extract_text(candidate: Any) -> str:
    if isinstance(candidate, str):
        return candidate.strip()
    if isinstance(candidate, dict):
        for key in ('text', 'rendered_text', 'message', 'output'):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ''


def _sentence_count(text: str) -> int:
    parts = [chunk.strip() for chunk in re.split(r'[.!?]+', text) if chunk.strip()]
    return len(parts)


def _cyrillic_ratio(text: str) -> float:
    cyr = len(re.findall(r'[А-Яа-яЁё]', text))
    lat = len(re.findall(r'[A-Za-z]', text))
    total = cyr + lat
    if total == 0:
        return 1.0
    return cyr / total


def validate_rendered_text(text: str, request: LLMRenderRequest) -> list[str]:
    flags: list[str] = []
    cleaned = (text or '').strip()
    if not cleaned:
        return ['empty']
    if _cyrillic_ratio(cleaned) < 0.6:
        flags.append('non_russian_dominant')
    lowered = cleaned.lower()
    forbidden_openers = tuple(request.forbidden_openers or _DEFAULT_FORBIDDEN_OPENERS)
    if any(lowered.startswith(item) for item in forbidden_openers):
        flags.append('forbidden_opener')
    hard_bans = tuple(request.hard_bans or _DEFAULT_HARD_BANS)
    if any(item in lowered for item in hard_bans):
        flags.append('hard_ban')
    if request.ends_with_question:
        if not cleaned.endswith('?'):
            flags.append('missing_final_question')
        if cleaned.count('?') > 1:
            flags.append('too_many_questions')
    elif '?' in cleaned:
        flags.append('unexpected_question')
    if _sentence_count(cleaned) > max(1, int(request.max_sentences or 4)):
        flags.append('too_many_sentences')
    if len(cleaned) > 900:
        flags.append('too_long')
    return flags


def maybe_render_with_llm(request: LLMRenderRequest) -> LLMRenderResult:
    _autoload_renderer_from_env()
    log_event(
        'renderer.invoked',
        stage='llm_renderer',
        frame_topic=request.frame_topic,
        frame_goal=request.frame_goal,
        render_kind=request.render_kind,
        transition_kind=request.transition_kind,
        renderer_backend=_llm_renderer_backend,
        renderer_backend_detail=_llm_renderer_backend_detail,
    )
    if _llm_renderer is None:
        result = LLMRenderResult(
            rendered_text=request.fallback_text,
            renderer_status='not_configured',
            attempt_count=0,
            validation_flags=[],
            renderer_used=False,
            fallback_used=False,
            renderer_backend='none',
            renderer_backend_detail='',
        )
        log_event(
            'renderer.completed',
            stage='llm_renderer',
            frame_topic=request.frame_topic,
            frame_goal=request.frame_goal,
            render_kind=request.render_kind,
            renderer_status=result.renderer_status,
            renderer_used=result.renderer_used,
            renderer_backend=result.renderer_backend,
            renderer_backend_detail=result.renderer_backend_detail,
            renderer_attempt_count=result.attempt_count,
            renderer_fallback_used=result.fallback_used,
            renderer_validation_failures=list(result.validation_flags),
            renderer_exception_detail=result.exception_detail,
        )
        return result

    violations: list[str] = []
    last_flags: list[str] = []
    for attempt in (1, 2):
        log_event(
            'renderer.attempt_started',
            stage='llm_renderer',
            frame_topic=request.frame_topic,
            frame_goal=request.frame_goal,
            render_kind=request.render_kind,
            renderer_backend=_llm_renderer_backend,
            renderer_backend_detail=_llm_renderer_backend_detail,
            attempt=attempt,
            prior_violations=list(violations),
        )
        try:
            prompt = build_render_prompt(request, violations=violations if attempt > 1 else None)
            candidate = _llm_renderer(request=request, prompt=prompt, attempt=attempt, violations=list(violations))
        except Exception as exc:
            exception_detail = _format_renderer_exception(exc)
            log_event(
                'renderer.attempt_failed',
                stage='llm_renderer',
                frame_topic=request.frame_topic,
                frame_goal=request.frame_goal,
                render_kind=request.render_kind,
                renderer_backend=_llm_renderer_backend,
                renderer_backend_detail=_llm_renderer_backend_detail,
                attempt=attempt,
                failure='renderer_exception',
                exception_detail=exception_detail,
                prior_violations=list(violations),
            )
            if attempt == 2:
                result = LLMRenderResult(
                    rendered_text=request.fallback_text,
                    renderer_status='exception_fallback',
                    attempt_count=attempt,
                    validation_flags=violations or ['renderer_exception'],
                    exception_detail=exception_detail,
                    renderer_used=True,
                    fallback_used=True,
                    renderer_backend=_llm_renderer_backend,
                    renderer_backend_detail=_llm_renderer_backend_detail,
                )
                log_event(
                    'renderer.completed',
                    stage='llm_renderer',
                    frame_topic=request.frame_topic,
                    frame_goal=request.frame_goal,
                    render_kind=request.render_kind,
                    renderer_status=result.renderer_status,
                    renderer_used=result.renderer_used,
                    renderer_backend=result.renderer_backend,
                    renderer_backend_detail=result.renderer_backend_detail,
                    renderer_attempt_count=result.attempt_count,
                    renderer_fallback_used=result.fallback_used,
                    renderer_validation_failures=list(result.validation_flags),
                    renderer_exception_detail=result.exception_detail,
                )
                return result
            violations = ['renderer_exception']
            continue
        rendered_text = _extract_text(candidate)
        last_flags = validate_rendered_text(rendered_text, request)
        if not last_flags:
            result = LLMRenderResult(
                rendered_text=rendered_text,
                renderer_status='ok',
                attempt_count=attempt,
                validation_flags=[],
                renderer_used=True,
                fallback_used=False,
                renderer_backend=_llm_renderer_backend,
                renderer_backend_detail=_llm_renderer_backend_detail,
            )
            log_event(
                'renderer.completed',
                stage='llm_renderer',
                frame_topic=request.frame_topic,
                frame_goal=request.frame_goal,
                render_kind=request.render_kind,
                renderer_status=result.renderer_status,
                renderer_used=result.renderer_used,
                renderer_backend=result.renderer_backend,
                renderer_backend_detail=result.renderer_backend_detail,
                renderer_attempt_count=result.attempt_count,
                renderer_fallback_used=result.fallback_used,
                renderer_validation_failures=list(result.validation_flags),
                renderer_exception_detail=result.exception_detail,
            )
            return result
        log_event(
            'renderer.attempt_failed',
            stage='llm_renderer',
            frame_topic=request.frame_topic,
            frame_goal=request.frame_goal,
            render_kind=request.render_kind,
            renderer_backend=_llm_renderer_backend,
            renderer_backend_detail=_llm_renderer_backend_detail,
            attempt=attempt,
            failure='validation_failed',
            validation_failures=list(last_flags),
            renderer_exception_detail='',
        )
        violations = list(last_flags)

    result = LLMRenderResult(
        rendered_text=request.fallback_text,
        renderer_status='validation_failed_fallback',
        attempt_count=2,
        validation_flags=last_flags,
        renderer_used=True,
        fallback_used=True,
        renderer_backend=_llm_renderer_backend,
        renderer_backend_detail=_llm_renderer_backend_detail,
    )
    log_event(
        'renderer.completed',
        stage='llm_renderer',
        frame_topic=request.frame_topic,
        frame_goal=request.frame_goal,
        render_kind=request.render_kind,
        renderer_status=result.renderer_status,
        renderer_used=result.renderer_used,
        renderer_backend=result.renderer_backend,
        renderer_backend_detail=result.renderer_backend_detail,
        renderer_attempt_count=result.attempt_count,
        renderer_fallback_used=result.fallback_used,
        renderer_validation_failures=list(result.validation_flags),
        renderer_exception_detail=result.exception_detail,
    )
    return result
