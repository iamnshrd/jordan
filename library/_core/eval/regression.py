from library._core.runtime.frame import select_frame
from library._core.runtime.respond import respond
from library.config import (RUNTIME_REGRESSION_CASES, RUNTIME_REGRESSION_REPORT,
                             VOICE_REGRESSION_CASES, VOICE_REGRESSION_REPORT)
from library.utils import load_json, save_json

def runtime_regression():
    """Run runtime regression. Returns report dict."""
    cases = load_json(RUNTIME_REGRESSION_CASES, [])
    rows = []
    passes = 0
    for case in cases:
        data = select_frame(case['question'])
        preferred = (data.get('preferred_sources') or [None])[0]
        ok = preferred == case['expect_preferred_source']
        passes += int(ok)
        rows.append({
            'question': case['question'],
            'expect_preferred_source': case['expect_preferred_source'],
            'got_preferred_source': preferred,
            'ok': ok,
            'confidence': data.get('confidence'),
        })
    report = {'total': len(rows), 'pass': passes, 'results': rows}
    save_json(RUNTIME_REGRESSION_REPORT, report)
    return report

def voice_regression():
    """Run voice regression. Returns report dict."""
    cases = load_json(VOICE_REGRESSION_CASES, [])
    rows = []
    passes = 0
    for case in cases:
        output = respond(case['question'], mode='deep', voice=case['voice'])
        ok = all(token in output for token in case['must_include'])
        passes += int(ok)
        rows.append({
            'voice': case['voice'],
            'question': case['question'],
            'must_include': case['must_include'],
            'ok': ok,
        })
    report = {'total': len(rows), 'pass': passes, 'results': rows}
    save_json(VOICE_REGRESSION_REPORT, report)
    return report
