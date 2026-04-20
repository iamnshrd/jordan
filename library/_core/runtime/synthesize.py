"""Response synthesis -- structured assembly from DB-backed runtime inputs."""
from __future__ import annotations

from library._core.runtime.frame import select_frame
from library._core.kb.query_v3 import query_v3
from library._core.session.progress import estimate as estimate_progress
from library._core.state_store import StateStore
from library.config import INTERVENTION_PATTERNS, SOURCE_BLEND_EXAMPLES
from library.utils import load_json, timed


# ── intervention patterns & source blend data ─────────────────────────

_intervention_patterns_cache: list | None = None
_source_blend_cache: list | None = None


def _get_intervention_patterns() -> list:
    global _intervention_patterns_cache
    if _intervention_patterns_cache is None:
        _intervention_patterns_cache = load_json(INTERVENTION_PATTERNS, default=[])
    return _intervention_patterns_cache


def _get_source_blend_examples() -> list:
    global _source_blend_cache
    if _source_blend_cache is None:
        _source_blend_cache = load_json(SOURCE_BLEND_EXAMPLES, default=[])
    return _source_blend_cache


def match_intervention_pattern(route_name: str, pattern_name: str) -> dict | None:
    """Find the best matching intervention pattern for the given route/pattern."""
    for ip in _get_intervention_patterns():
        when = ip.get('when_to_use', [])
        if route_name in when or pattern_name in when:
            return ip
    return None


def match_source_blend(route_name: str) -> dict | None:
    """Find source blend guidance for the given route."""
    for blend in _get_source_blend_examples():
        if blend.get('route') == route_name:
            return blend
    return None

# ── db-driven text generators ─────────────────────────────────────────

def db_driven_theme_text(theme_name, selected):
    desc = ((selected.get('selected_theme') or {}).get('description') or '').strip()
    if desc:
        return desc, 'theme-description'
    return '', 'none'


def db_driven_principle_text(principle_name, selected):
    desc = ((selected.get('selected_principle') or {}).get('description') or '').strip()
    if desc:
        return desc, 'principle-description'
    return '', 'none'


def db_driven_pattern_text(pattern_name, selected):
    desc = ((selected.get('selected_pattern') or {}).get('description') or '').strip()
    if desc:
        return desc, 'pattern-description'
    return '', 'none'


def db_driven_responsibility_text(selected, bridge, question):
    stub = (bridge.get('responsibility_stub') or '').strip()
    if stub:
        return stub, 'bridge'
    return '', 'none'


def db_driven_longer_term_text(selected, bridge, question):
    stub = (bridge.get('long_term_stub') or '').strip()
    if stub:
        return stub, 'bridge'
    return '', 'none'


def db_driven_practical_text(selected, next_step_v3, question):
    step = (next_step_v3.get('step_text') or '').strip()
    if step:
        return step, 'next-step'
    return '', 'none'


# ── quote helpers ─────────────────────────────────────────────────────

def normalize_quote_text(q):
    q = q.strip()
    for sep in [' Почему', ' Представьте', ' Но ', ' Это значит',
                ' Религиозная проблема', ' Трудно представить']:
        idx = q.find(sep)
        if idx > 40:
            q = q[:idx].strip()
            break
    q = q.replace(').', '.').replace('  ', ' ')
    if len(q) > 180:
        q = q[:180].rstrip() + '...'
    return q


def select_supporting_quote(bundle, selected):
    rows = bundle.get('relevant_quotes', []) or []
    if not rows:
        return None
    theme = ((selected.get('selected_theme') or {}).get('name'))
    principle = ((selected.get('selected_principle') or {}).get('name'))
    q = (selected.get('question') or '').lower()

    preferred_types = []
    if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител', 'тирана']):
        preferred_types = ['relationship-quote', 'principle-quote',
                           'discipline-quote']
        for row in rows:
            if (row.get('quote_type') == 'relationship-quote'
                    and (row.get('note') or '').startswith('manual')
                    and row.get('quote_text')):
                return normalize_quote_text(row['quote_text'])
    elif any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес',
                               'путь']):
        for row in rows:
            if (row.get('quote_type') == 'discipline-quote'
                    and (row.get('note') or '').startswith('manual')
                    and row.get('quote_text')):
                return normalize_quote_text(row['quote_text'])
        preferred_types = ['discipline-quote', 'principle-quote']
    elif principle == 'clean-up-what-is-in-front-of-you':
        preferred_types = ['discipline-quote', 'principle-quote']
    elif (principle == 'tell-the-truth-or-at-least-dont-lie'
          and theme == 'suffering'):
        preferred_types = ['shame-quote', 'principle-quote']
    elif theme == 'resentment':
        preferred_types = ['resentment-quote', 'relationship-quote',
                           'principle-quote']
    elif theme == 'responsibility':
        preferred_types = ['relationship-quote', 'principle-quote']
    elif theme == 'meaning':
        preferred_types = ['discipline-quote', 'principle-quote']
    else:
        preferred_types = ['principle-quote', 'discipline-quote',
                           'relationship-quote', 'shame-quote',
                           'resentment-quote']

    for ptype in preferred_types:
        for row in rows:
            if row.get('quote_type') == ptype and row.get('quote_text'):
                return normalize_quote_text(row['quote_text'])
    first_text = rows[0].get('quote_text') or ''
    return normalize_quote_text(first_text) if first_text else ''


def select_structured_text(bundle, key, *fields):
    rows = bundle.get(key, []) or []
    if not rows:
        return ''
    for row in rows:
        for field in fields:
            value = (row.get(field) or '').strip()
            if value:
                return value
    return ''


# ── archetype inference ───────────────────────────────────────────────

def infer_archetype(question):
    """Delegate to the canonical route classifier in frame.py."""
    from library._core.runtime.frame import infer_route_name
    route = infer_route_name(question)
    return '' if route == 'general' else route


def append_sentence(base, addition):
    base = (base or '').strip()
    addition = (addition or '').strip()
    if not addition:
        return base
    if addition in base:
        return base
    if not base:
        return addition
    return base.rstrip() + ' ' + addition


def build_grounding_report(selected, bundle, v3, data) -> dict:
    """Expose which synthesis fields are DB-backed vs heuristic/runtime-derived."""
    chunks = bundle.get('relevant_chunks', []) or []
    quotes = bundle.get('relevant_quotes', []) or []
    definitions = bundle.get('relevant_definitions', []) or []
    claims = bundle.get('relevant_claims', []) or []
    practices = bundle.get('relevant_practices', []) or []
    objections = bundle.get('relevant_objections', []) or []
    chapter_summaries = bundle.get('relevant_chapter_summaries', []) or []
    field_sources = data.get('field_sources') or {}

    def _meta(field: str, default_source: str = 'heuristic') -> dict:
        source = field_sources.get(field, default_source)
        return {
            'backed': source not in {'heuristic', 'none', ''},
            'source': source or default_source,
        }

    fields = {
        'core_problem': _meta('core_problem'),
        'relevant_pattern': _meta('relevant_pattern'),
        'guiding_principle': _meta('guiding_principle'),
        'responsibility_avoided': _meta('responsibility_avoided'),
        'practical_next_step': _meta('practical_next_step'),
        'longer_term_correction': _meta('longer_term_correction'),
        'supporting_quote': {
            'backed': bool(data.get('supporting_quote')) and bool(quotes),
            'source': 'quotes' if quotes else 'none',
        },
    }
    backed_fields = [name for name, meta in fields.items() if meta['backed']]
    missing_fields = [name for name, meta in fields.items() if not meta['backed']]
    return {
        'fields': fields,
        'backed_fields': backed_fields,
        'missing_fields': missing_fields,
        'evidence_count': len(chunks),
        'quote_count': len(quotes),
        'structured_count': (
            len(definitions) + len(claims) + len(practices)
            + len(objections) + len(chapter_summaries)
        ),
    }


# ── main synthesis ────────────────────────────────────────────────────

def unify_selection_policy(selected, bridge, next_step_v3, question):
    route = selected.get('route_name') or 'general'
    policy = {
        'route': route,
        'prefer_bridge': bool(bridge),
        'prefer_next_step': bool(next_step_v3),
        'suppress_continuity': route in {'career-vocation', 'avoidance-paralysis'},
        'diagnosis_style': 'direct' if route in {'career-vocation', 'avoidance-paralysis'} else 'reflective',
    }
    return policy


@timed('synthesize')
def synthesize(question, user_id: str = 'default',
               store: StateStore | None = None,
               frame: dict | None = None,
               progress: dict | None = None):
    selected = frame or select_frame(question, user_id=user_id, store=store)
    bundle = selected.get('bundle', {})
    if progress is None:
        progress = estimate_progress(question, user_id=user_id, store=store)

    theme_name = (selected.get('selected_theme') or {}).get('name')
    principle_name = (selected.get('selected_principle') or {}).get('name')
    pattern_name = (selected.get('selected_pattern') or {}).get('name')
    archetype = infer_archetype(question)
    v3 = query_v3(theme_name or '', pattern_name or '', archetype)

    core_problem, core_problem_source = db_driven_theme_text(theme_name, selected)
    pattern_text, pattern_source = db_driven_pattern_text(pattern_name, selected)
    principle_text, principle_source = db_driven_principle_text(principle_name, selected)
    structured_definition = select_structured_text(
        bundle, 'relevant_definitions', 'summary',
    )
    structured_claim = select_structured_text(
        bundle, 'relevant_claims', 'summary', 'title',
    )
    structured_practice = select_structured_text(
        bundle, 'relevant_practices', 'summary', 'title',
    )
    structured_objection_response = select_structured_text(
        bundle, 'relevant_objections', 'response', 'summary',
    )
    chapter_summary = select_structured_text(
        bundle, 'relevant_chapter_summaries', 'summary',
    )

    bridge = v3.get('bridge') or {}
    next_step_v3 = v3.get('next_step') or {}
    policy = unify_selection_policy(selected, bridge, next_step_v3, question)

    route_name = selected.get('route_name') or 'general'
    intervention = match_intervention_pattern(route_name, pattern_name or '')
    blend_guidance = match_source_blend(route_name)

    if bridge.get('diagnosis_stub'):
        core_problem = bridge['diagnosis_stub']
        core_problem_source = 'bridge'
    elif structured_claim:
        core_problem = append_sentence(core_problem, structured_claim)
        core_problem_source = 'claims'
    elif structured_definition:
        core_problem = append_sentence(core_problem, structured_definition)
        core_problem_source = 'definitions'
    elif chapter_summary:
        core_problem = append_sentence(core_problem, chapter_summary)
        core_problem_source = 'chapter-summaries'

    responsibility_avoided, responsibility_source = db_driven_responsibility_text(
        selected, bridge, question,
    )

    longer_term, longer_term_source = db_driven_longer_term_text(selected, bridge, question)
    practical, practical_source = db_driven_practical_text(selected, next_step_v3, question)
    if structured_definition and structured_definition not in principle_text:
        principle_text = append_sentence(principle_text, structured_definition)
        principle_source = 'definitions'
    if not next_step_v3.get('step_text') and structured_practice:
        practical = append_sentence(practical, structured_practice)
        practical_source = 'practices'
    if not bridge.get('long_term_stub') and structured_objection_response:
        longer_term = append_sentence(longer_term, structured_objection_response)
        longer_term_source = 'objections'
    elif not bridge.get('long_term_stub') and chapter_summary:
        longer_term = append_sentence(longer_term, chapter_summary)
        longer_term_source = 'chapter-summaries'

    anti_patterns = v3.get('anti_patterns') or []
    case_links = v3.get('case_links') or []
    best_case = v3.get('best_case') or {}
    intervention_links = v3.get('intervention_links') or []
    motif_links = v3.get('motif_links') or []
    conf = v3.get('confidence_summary') or {}

    if not best_case.get('case_name') and case_links:
        best_case = {
            'case_name': case_links[0],
            'confidence_level': None,
        }

    source_blend = selected.get('source_blend') or {}
    if blend_guidance and not source_blend:
        source_blend = {
            'primary': blend_guidance.get('primary_source'),
            'secondary': blend_guidance.get('secondary_source'),
            'rationale': blend_guidance.get('why'),
        }

    tone_hint = None
    if intervention:
        tone_hint = intervention.get('tone_profile')

    result = {
        'question': question,
        'selection_policy': policy,
        'core_problem': core_problem,
        'relevant_pattern': pattern_text,
        'responsibility_avoided': responsibility_avoided,
        'guiding_principle': principle_text,
        'supporting_quote': select_supporting_quote(bundle, selected),
        'evidence_preview': bundle.get('relevant_chunks', [])[:3],
        'practical_next_step': practical,
        'longer_term_correction': longer_term,
        'selected_theme_reason': selected.get('selected_theme_reason'),
        'selected_principle_reason': selected.get('selected_principle_reason'),
        'selected_pattern_reason': selected.get('selected_pattern_reason'),
        'preferred_sources': selected.get('preferred_sources'),
        'source_blend': source_blend,
        'source_blend_rationale': (blend_guidance or {}).get('why'),
        'confidence': selected.get('confidence'),
        'tone_hint': tone_hint,
        'intervention_pattern': intervention.get('pattern_name') if intervention else None,
        'progress': progress,
        'v3_runtime': v3,
        'quote_pack': v3.get('quote_pack'),
        'anti_patterns': anti_patterns,
        'case_links': case_links,
        'best_case': best_case,
        'intervention_links': intervention_links,
        'motif_links': motif_links,
        'field_sources': {
            'core_problem': core_problem_source,
            'relevant_pattern': pattern_source,
            'responsibility_avoided': responsibility_source,
            'guiding_principle': principle_source,
            'practical_next_step': practical_source,
            'longer_term_correction': longer_term_source,
        },
        'structured_knowledge': {
            'definitions': bundle.get('relevant_definitions', [])[:3],
            'claims': bundle.get('relevant_claims', [])[:3],
            'practices': bundle.get('relevant_practices', [])[:3],
            'objections': bundle.get('relevant_objections', [])[:2],
            'chapter_summaries': bundle.get('relevant_chapter_summaries', [])[:2],
            'canonical_concepts': bundle.get('canonical_concepts', [])[:3],
        },
        'raw_selection': selected,
    }
    result['grounding_report'] = build_grounding_report(
        selected, bundle, v3, result,
    )
    return result
