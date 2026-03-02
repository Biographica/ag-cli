# Deferred Items — Phase 02.2

## Pre-existing test failures (out of scope for 02.2-01)

All failures below existed before this plan's changes (confirmed via `git stash`):

### ct.agent.trace module missing
- `test_trace_diagnose_command_outputs_summary` — `NameError: TraceLogger not defined`
- `test_trace_diagnose_strict_exits_on_unclosed_query` — `NameError: TraceLogger not defined`
- `test_trace_export_creates_bundle` — `NameError: TraceLogger not defined`
- `test_release_check_passes_with_no_tests_no_trace` — `ModuleNotFoundError: No module named 'ct.agent.trace'`
- `test_release_check_fails_when_pytest_step_fails` — same
- `test_release_check_fails_on_trace_integrity_issues` — same
- `test_release_check_pharma_policy_fails_without_profile` — same
- `test_release_check_pharma_policy_passes` — same

These require `ct.agent.trace` module and `TraceLogger` class to be implemented.
