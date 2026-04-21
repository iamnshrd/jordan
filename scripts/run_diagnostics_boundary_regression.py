#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._adapters.default_components import (
    DefaultFrameSelector, DefaultSynthesizer,
)
from library._core.runtime.orchestrator import orchestrate_diagnostics


def main() -> None:
    with temp_store() as store:
        question = 'Я потерял смысл, дисциплину и направление'
        diag = orchestrate_diagnostics(
            question, user_id='telegram:65001', store=store, purpose='prompt',
        )
        selector = DefaultFrameSelector(store=store)
        synthesizer = DefaultSynthesizer(store=store)
        selection = selector.select(question, user_id='telegram:65002')
        synthesis = synthesizer.synthesize(question, user_id='telegram:65003')

        results = [
            {
                'name': 'diagnostics_exposes_boundary_ids',
                'pass': diag.get('assistant_id') == 'jordan'
                and diag.get('knowledge_set_id') == 'jordan-kb',
            },
            {
                'name': 'diagnostics_exposes_selection_and_bundle',
                'pass': isinstance(diag.get('selection'), dict)
                and isinstance(diag.get('bundle'), dict),
            },
            {
                'name': 'compat_wrappers_delegate_through_diagnostics_path',
                'pass': isinstance(selection, dict)
                and isinstance(synthesis, dict),
            },
        ]

        emit_report(
            results,
            samples={
                'diagnostics': {
                    'assistant_id': diag.get('assistant_id'),
                    'knowledge_set_id': diag.get('knowledge_set_id'),
                    'decision_action': (diag.get('decision') or {}).get('action'),
                },
                'selection_route': selection.get('route_name'),
                'has_synthesis': bool(synthesis),
            },
        )


if __name__ == '__main__':
    main()
