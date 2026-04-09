from library._core.runtime.frame import select_frame
from library._core.runtime.respond import respond
from library.config import EVAL_CASES, EVAL_REPORT
from library.utils import load_json, save_json

def run_case(case):
    """Run a single eval case. Returns result dict."""
    data = select_frame(case['question'])
    resp_out = respond(case['question'])
    got_theme = (data.get('selected_theme') or {}).get('name')
    got_principle = (data.get('selected_principle') or {}).get('name')
    got_pattern = (data.get('selected_pattern') or {}).get('name')
    acceptable_themes = case.get('acceptable_themes', [case['expect_theme']])
    acceptable_principles = case.get('acceptable_principles', [case['expect_principle']])
    acceptable_patterns = case.get('acceptable_patterns', [case['expect_pattern']])
    quote_type = None
    if 'Цитата:' in resp_out:
        quote_line = [line for line in resp_out.splitlines() if line.startswith('Цитата:')]
        if quote_line:
            quote_text = quote_line[0]
            if 'порядок у себя дома' in quote_text.lower() or 'наполнено смыслом' in quote_text.lower():
                quote_type = 'discipline-quote'
            elif 'молчание' in quote_text.lower() or 'трудное' in quote_text.lower() or 'не давайте детям' in quote_text.lower() or 'невзлюбить' in quote_text.lower():
                quote_type = 'relationship-quote'
            elif 'стыд' in quote_text.lower() or 'никчемности' in quote_text.lower():
                quote_type = 'shame-quote'
            elif 'правду' in quote_text.lower() or 'не лги' in quote_text.lower():
                quote_type = 'principle-quote'
    quote_ok = True
    if case.get('expect_quote_type'):
        quote_ok = quote_type == case['expect_quote_type']
    return {
        'id': case['id'],
        'question': case['question'],
        'expect_theme': case['expect_theme'],
        'acceptable_themes': acceptable_themes,
        'got_theme': got_theme,
        'theme_ok': got_theme in acceptable_themes,
        'expect_principle': case['expect_principle'],
        'acceptable_principles': acceptable_principles,
        'got_principle': got_principle,
        'principle_ok': got_principle in acceptable_principles,
        'expect_pattern': case['expect_pattern'],
        'acceptable_patterns': acceptable_patterns,
        'got_pattern': got_pattern,
        'pattern_ok': got_pattern in acceptable_patterns,
        'expect_quote_type': case.get('expect_quote_type'),
        'got_quote_type': quote_type,
        'quote_ok': quote_ok,
        'confidence': data.get('confidence'),
        'theme_reason': data.get('selected_theme_reason'),
        'principle_reason': data.get('selected_principle_reason'),
        'pattern_reason': data.get('selected_pattern_reason'),
    }

def evaluate():
    """Run full eval suite. Returns summary dict."""
    cases = load_json(EVAL_CASES, [])
    results = [run_case(c) for c in cases]
    summary = {
        'total': len(results),
        'theme_pass': sum(r['theme_ok'] for r in results),
        'principle_pass': sum(r['principle_ok'] for r in results),
        'pattern_pass': sum(r['pattern_ok'] for r in results),
        'quote_pass': sum(r['quote_ok'] for r in results),
        'all_pass': sum(r['theme_ok'] and r['principle_ok'] and r['pattern_ok'] and r['quote_ok'] for r in results),
        'results': results,
    }
    save_json(EVAL_REPORT, summary)
    return summary
