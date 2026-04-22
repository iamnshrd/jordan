"""Bounded LLM classifiers for dialogue-family and planner control."""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import json
import os
from typing import Any, Callable

from library._core.runtime import anthropic_api_renderer
from library._core.runtime import openclaw_api_renderer


_family_classifier: Callable[..., Any] | None = None
_family_classifier_backend = 'none'
_family_classifier_backend_detail = ''
_family_autoload_attempted = False


def _runtime_classifier_enabled() -> bool:
    explicit = str(os.environ.get('JORDAN_ENABLE_LLM_CLASSIFIERS') or '').strip().lower()
    if explicit in {'1', 'true', 'yes'}:
        return True
    return bool(
        os.environ.get('OPENCLAW_CONFIG_PATH')
        or os.environ.get('OPENCLAW_STATE_DIR')
        or os.environ.get('OPENCLAW_JORDAN_BRIDGE_CWD')
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or '').strip()
    if not text:
        return {}
    if text.startswith('```'):
        parts = [part.strip() for part in text.split('```') if part.strip()]
        for part in parts:
            if part.startswith('{'):
                text = part
                break
            if '\n' in part:
                maybe = part.split('\n', 1)[1].strip()
                if maybe.startswith('{'):
                    text = maybe
                    break
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _classifier_detail_for(fn: Callable[..., Any] | None) -> str:
    if fn is None:
        return ''
    detail = getattr(fn, '__jordan_classifier_backend_detail__', '')
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


def _set_family_classifier(fn: Callable[..., Any] | None, *, backend: str) -> None:
    global _family_classifier, _family_classifier_backend, _family_classifier_backend_detail
    _family_classifier = fn
    _family_classifier_backend = backend if fn is not None else 'none'
    _family_classifier_backend_detail = _classifier_detail_for(fn) if fn is not None else ''


def set_family_classifier(fn: Callable[..., Any] | None) -> None:
    global _family_autoload_attempted
    _family_autoload_attempted = fn is not None
    _set_family_classifier(fn, backend='custom_hook')


def reset_family_classifier() -> None:
    global _family_autoload_attempted
    _family_autoload_attempted = False
    _set_family_classifier(None, backend='none')


def _autoload_family_classifier() -> None:
    global _family_autoload_attempted
    if _family_autoload_attempted:
        return
    _family_autoload_attempted = True
    if str(os.environ.get('JORDAN_DISABLE_LLM_FAMILY_CLASSIFIER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return
    hook_ref = (
        os.environ.get('JORDAN_LLM_FAMILY_CLASSIFIER_HOOK')
        or os.environ.get('JORDAN_LLM_CLASSIFIER_HOOK')
        or ''
    ).strip()
    if hook_ref and ':' in hook_ref:
        module_name, attr_name = hook_ref.split(':', 1)
        try:
            module = importlib.import_module(module_name.strip())
            candidate = getattr(module, attr_name.strip(), None)
        except Exception:
            candidate = None
        if callable(candidate):
            _set_family_classifier(candidate, backend='custom_hook')
            return
    if not _runtime_classifier_enabled():
        return
    if anthropic_api_renderer.is_available():
        _set_family_classifier(classify_dialogue_family_with_anthropic, backend='anthropic_api')
        return
    if openclaw_api_renderer.is_available():
        _set_family_classifier(classify_dialogue_family_with_llm, backend='openclaw_api')


@dataclass(frozen=True)
class LLMFamilyClassificationRequest:
    question: str
    dialogue_act: str
    dialogue_state: dict[str, Any]
    dialogue_frame: dict[str, Any]
    deterministic_guess: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]


@dataclass
class LLMFamilyClassificationResult:
    topic_candidate: str = ''
    route_candidate: str = ''
    stance_shift: str = ''
    goal_candidate: str = ''
    confidence: float = 0.0
    reason: str = ''
    source: str = 'deterministic_fallback'
    used: bool = False
    backend: str = 'none'
    backend_detail: str = ''
    status: str = 'not_configured'
    fallback_used: bool = True
    rejection_reason: str = ''
    deterministic_topic: str = ''
    deterministic_goal: str = ''

    def metadata(self) -> dict[str, Any]:
        return {
            'family_classifier_used': self.used,
            'family_classifier_backend': self.backend,
            'family_classifier_backend_detail': self.backend_detail,
            'family_classifier_status': self.status,
            'family_classifier_confidence': self.confidence,
            'family_classifier_fallback_used': self.fallback_used,
            'family_classifier_result_topic': self.topic_candidate,
            'family_classifier_result_goal': self.goal_candidate,
            'family_classifier_deterministic_topic': self.deterministic_topic,
            'family_classifier_deterministic_goal': self.deterministic_goal,
            'family_classifier_reason': self.reason,
            'family_classifier_rejection_reason': self.rejection_reason,
        }


def _build_family_prompt(request: LLMFamilyClassificationRequest) -> dict[str, str]:
    candidate_lines = []
    for candidate in request.candidates:
        candidate_lines.append(
            '- '
            + json.dumps(
                {
                    'topic_candidate': candidate.get('topic_candidate', ''),
                    'route_candidate': candidate.get('route_candidate', ''),
                    'stance_shift': candidate.get('stance_shift', ''),
                    'goal_candidate': candidate.get('goal_candidate', ''),
                    'description': candidate.get('description', ''),
                },
                ensure_ascii=False,
            )
        )
    deterministic_guess = json.dumps(request.deterministic_guess, ensure_ascii=False)
    system = (
        'Ты классифицируешь пользовательскую реплику только в пределах допустимого shortlist. '
        'Нельзя придумывать новые темы, советы, объяснения или текст ответа. '
        'Верни только JSON-объект без markdown. Если не уверен, верни deterministic_fallback. '
        'Схема: '
        '{"topic_candidate":"<topic|deterministic_fallback>",'
        '"route_candidate":"<route>",'
        '"stance_shift":"<general|personal>",'
        '"goal_candidate":"<opening|menu|clarify|overview|cause_list|mini_analysis|next_step|example>",'
        '"confidence":0.0,'
        '"reason":"<short_reason>"}'
    )
    user = '\n'.join([
        f'question={request.question}',
        f'dialogue_act={request.dialogue_act}',
        f'active_frame={json.dumps(request.dialogue_frame, ensure_ascii=False)}',
        f'active_state={json.dumps(request.dialogue_state, ensure_ascii=False)}',
        f'deterministic_guess={deterministic_guess}',
        'allowed_candidates:',
        *candidate_lines,
    ])
    return {'system': system, 'user': user}


def _call_openclaw_api_json(prompt: dict[str, str]) -> dict[str, Any]:
    store = openclaw_api_renderer._load_auth_profiles()
    credential = openclaw_api_renderer._select_openai_codex_profile(store)
    if credential is None:
        raise RuntimeError('LLM classifier could not find an openai-codex oauth profile.')
    access = str(credential.get('access') or '').strip()
    if not access:
        raise RuntimeError('LLM classifier found an openai-codex profile without access token.')
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access}',
    }
    account_id = str(credential.get('accountId') or '').strip()
    if account_id:
        headers['ChatGPT-Account-Id'] = account_id
    payload = {
        'model': openclaw_api_renderer._resolve_model_id(),
        'instructions': prompt.get('system', ''),
        'input': [
            {
                'role': 'user',
                'content': [{'type': 'input_text', 'text': str(prompt.get('user') or '').strip()}],
            }
        ],
        'stream': True,
        'store': False,
        'text': {'verbosity': 'low'},
    }
    timeout = float((os.environ.get('JORDAN_LLM_CLASSIFIER_TIMEOUT_SECONDS') or '2.5').strip() or '2.5')
    req = openclaw_api_renderer.request_module.Request(
        openclaw_api_renderer._resolve_endpoint(),
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with openclaw_api_renderer.request_module.urlopen(req, timeout=timeout) as resp:
            content_type = str(resp.headers.get('content-type') or '')
            raw = resp.read().decode('utf-8', errors='replace')
    except openclaw_api_renderer.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'LLM classifier HTTP {exc.code}: {detail[:500]}') from exc
    except openclaw_api_renderer.error.URLError as exc:
        raise RuntimeError(f'LLM classifier connection failed: {exc}') from exc

    stripped = raw.lstrip()
    if 'text/event-stream' in content_type or stripped.startswith('data:') or stripped.startswith('event:'):
        text = openclaw_api_renderer._extract_output_text_from_sse(raw)
    else:
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f'LLM classifier returned non-JSON payload: {raw[:500]}') from exc
        text = openclaw_api_renderer._extract_output_text(parsed)
    payload = _extract_json_object(text)
    if payload:
        return payload
    raise RuntimeError(f'LLM classifier returned invalid JSON text: {str(text)[:500]}')


def describe_api_classifier_backend() -> str:
    return openclaw_api_renderer.describe_api_backend()


def classify_dialogue_family_with_llm(*, request: LLMFamilyClassificationRequest) -> dict[str, Any]:
    return _call_openclaw_api_json(_build_family_prompt(request))


classify_dialogue_family_with_llm.__jordan_classifier_backend_detail__ = describe_api_classifier_backend


def describe_anthropic_classifier_backend() -> str:
    return anthropic_api_renderer.describe_anthropic_backend()


def classify_dialogue_family_with_anthropic(*, request: LLMFamilyClassificationRequest) -> dict[str, Any]:
    timeout = float((os.environ.get('JORDAN_LLM_CLASSIFIER_TIMEOUT_SECONDS') or '2.5').strip() or '2.5')
    return anthropic_api_renderer.call_anthropic_json(
        prompt=_build_family_prompt(request),
        timeout_seconds=timeout,
        max_tokens=220,
    )


classify_dialogue_family_with_anthropic.__jordan_classifier_backend_detail__ = (
    describe_anthropic_classifier_backend
)


def maybe_classify_dialogue_family(request: LLMFamilyClassificationRequest) -> LLMFamilyClassificationResult:
    _autoload_family_classifier()
    deterministic_topic = str(request.deterministic_guess.get('topic_candidate', '') or '')
    deterministic_goal = str(request.deterministic_guess.get('goal_candidate', '') or '')
    result = LLMFamilyClassificationResult(
        topic_candidate=deterministic_topic,
        route_candidate=str(request.deterministic_guess.get('route_candidate', '') or ''),
        stance_shift=str(request.deterministic_guess.get('stance_shift', '') or ''),
        goal_candidate=deterministic_goal,
        confidence=float(request.deterministic_guess.get('confidence', 0.0) or 0.0),
        reason='deterministic_fallback',
        source='deterministic_fallback',
        used=False,
        backend=_family_classifier_backend,
        backend_detail=_family_classifier_backend_detail,
        status='not_configured' if _family_classifier is None else 'not_used',
        fallback_used=True,
        deterministic_topic=deterministic_topic,
        deterministic_goal=deterministic_goal,
    )
    if _family_classifier is None:
        return result
    try:
        payload = _family_classifier(request=request)
    except Exception as exc:
        result.used = True
        result.status = 'exception'
        result.rejection_reason = 'exception'
        result.reason = f'{type(exc).__name__}: {exc}'
        return result

    if isinstance(payload, LLMFamilyClassificationResult):
        payload.backend = _family_classifier_backend
        payload.backend_detail = _family_classifier_backend_detail
        payload.used = True
        payload.deterministic_topic = deterministic_topic
        payload.deterministic_goal = deterministic_goal
        return payload

    if not isinstance(payload, dict):
        result.used = True
        result.status = 'invalid_payload'
        result.rejection_reason = 'invalid_payload'
        return result

    result.used = True
    result.backend = _family_classifier_backend
    result.backend_detail = _family_classifier_backend_detail
    result.topic_candidate = str(payload.get('topic_candidate', '') or deterministic_topic)
    result.route_candidate = str(payload.get('route_candidate', '') or result.route_candidate)
    result.stance_shift = str(payload.get('stance_shift', '') or result.stance_shift)
    result.goal_candidate = str(payload.get('goal_candidate', '') or result.goal_candidate)
    result.confidence = float(payload.get('confidence', 0.0) or 0.0)
    result.reason = str(payload.get('reason', '') or '')
    result.source = str(payload.get('source', 'llm_classifier') or 'llm_classifier')
    result.status = 'classified'
    result.fallback_used = False
    return result


@dataclass(frozen=True)
class LLMModeClassificationRequest:
    question: str


@dataclass(frozen=True)
class LLMModeClassificationResult:
    mode: str
    confidence: float = 0.0
    reason: str = ''


@dataclass(frozen=True)
class LLMKBClassificationRequest:
    question: str


@dataclass(frozen=True)
class LLMKBClassificationResult:
    use_kb: bool
    confidence: float = 0.0
    reason: str = ''


def _build_mode_prompt(question: str) -> dict[str, str]:
    return {
        'system': (
            'Классифицируй вопрос только как practical или deep. '
            'Верни только JSON {"mode":"practical|deep","confidence":0.0,"reason":"..."}'
        ),
        'user': f'question={question}',
    }


def _build_kb_prompt(question: str) -> dict[str, str]:
    return {
        'system': (
            'Реши, нужен ли вопросу KB retrieval. '
            'Верни только JSON {"use_kb":true|false,"confidence":0.0,"reason":"..."}'
        ),
        'user': f'question={question}',
    }


def classify_mode_with_llm(question: str) -> dict[str, Any]:
    payload = _call_openclaw_api_json(_build_mode_prompt(question))
    return {
        'mode': str(payload.get('mode', '') or ''),
        'confidence': float(payload.get('confidence', 0.0) or 0.0),
        'reason': str(payload.get('reason', '') or ''),
        'backend': 'openclaw_api',
        'backend_detail': describe_api_classifier_backend(),
        'status': 'classified',
    }


def classify_kb_with_llm(question: str) -> dict[str, Any]:
    payload = _call_openclaw_api_json(_build_kb_prompt(question))
    raw_use_kb = payload.get('use_kb')
    use_kb = bool(raw_use_kb) if isinstance(raw_use_kb, bool) else str(raw_use_kb).strip().lower() in {'1', 'true', 'yes'}
    return {
        'use_kb': use_kb,
        'confidence': float(payload.get('confidence', 0.0) or 0.0),
        'reason': str(payload.get('reason', '') or ''),
        'backend': 'openclaw_api',
        'backend_detail': describe_api_classifier_backend(),
        'status': 'classified',
    }


def planner_classifiers_available() -> bool:
    if str(os.environ.get('JORDAN_DISABLE_LLM_MODE_CLASSIFIER') or '').strip().lower() in {
        '1', 'true', 'yes',
    } and str(os.environ.get('JORDAN_DISABLE_LLM_KB_CLASSIFIER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return False
    return _runtime_classifier_enabled() and openclaw_api_renderer.is_available()
