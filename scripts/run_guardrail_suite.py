#!/usr/bin/env python3
from __future__ import annotations

from _helpers import run_suite


def main() -> None:
    run_suite([
        'run_adapter_cli_regression.py',
        'run_adaptive_guardrail_regression.py',
        'run_adapter_boundary_regression.py',
        'run_assistant_boundary_regression.py',
        'run_default_workspace_audit_regression.py',
        'run_default_workspace_migration_regression.py',
        'run_diagnostics_boundary_regression.py',
        'run_domain_guardrail_escalation_regression.py',
        'run_domain_guardrail_regression.py',
        'run_decision_contract_regression.py',
        'run_legacy_cleanup_regression.py',
        'run_planner_api_cleanup_regression.py',
        'run_policy_scope_regression.py',
        'run_guardrail_tone_regression.py',
        'run_unified_logging_regression.py',
    ], 'guardrail')


if __name__ == '__main__':
    main()
