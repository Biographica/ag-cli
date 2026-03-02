---
phase: 05-gene-editing-and-evidence-tools
plan: "03"
subsystem: testing
tags: [e2e-test, tool-composition, evidence-gathering, CRISPR, genomics, TOOL-09]
dependency_graph:
  requires: ["05-01", "05-02"]
  provides: ["e2e-evidence-test"]
  affects: ["tests/test_e2e_evidence.py"]
tech_stack:
  added: []
  patterns: ["pytest.mark.e2e gating via conftest.py", "mock side_effect factory functions for tool composition testing"]
key_files:
  created:
    - tests/test_e2e_evidence.py
  modified:
    - tests/conftest.py
decisions:
  - "TOOL-09 validated as e2e test not a new tool — agent tool suite composability is a test concern, not a runtime concern"
  - "conftest.py pytest_collection_modifyitems changed to marker-only gating (not nodeid filename) — filename-based check incorrectly skipped non-e2e registration tests in test_e2e_* files"
metrics:
  duration: "10 min"
  completed: "2026-03-02"
  tasks_completed: 1
  files_created: 1
  files_modified: 1
---

# Phase 05 Plan 03: E2E Evidence Orchestration Test Summary

**One-liner:** TOOL-09 validated as e2e test: 6 Arabidopsis flowering-time genes exercised across gene_annotation, ortholog_map, gwas_qtl_lookup, coexpression_network, paralogy_score, and crispr_guide_design with full mock coverage.

## What Was Built

Created `tests/test_e2e_evidence.py` — an end-to-end test validating that the Phase 3-5 tool suite composes into a multi-gene evidence-gathering workflow. The test confirms TOOL-09 is not a new tool but a compositional property of the existing tool suite.

### Test Structure

**Class `TestMultiGeneEvidenceCollection`** (gated behind `@pytest.mark.e2e`):

1. `test_multi_gene_evidence_collection` — Full workflow for all 6 genes (`FLC, FT, CO, GI, SOC1, SVP`). Calls 6 tools per gene, assembles a per-gene evidence summary dict, validates structure and call counts.

2. `test_evidence_summaries_are_structured` — Validates consistent `required_keys` structure across a 3-gene subset. Verifies each sub-result has a `"summary"` key (tool contract).

3. `test_tool_diversity` — Validates >= 5 distinct tools are exercised in a single-gene run.

**Function `test_all_phase5_tools_registered`** (always runs, no marker):
- Verifies `editing.crispr_guide_design`, `editing.editability_score`, `genomics.paralogy_score` are registered
- Verifies `"editing"` is in `PLANT_SCIENCE_CATEGORIES` allowlist

### Gene List

6 real Arabidopsis flowering-time genes (`FLC, FT, CO, GI, SOC1, SVP`) — biologically plausible, exceeds TOOL-09's 5+ gene requirement.

### Mock Strategy

All tool calls use `@patch("ct.tools.genomics.<fn>", side_effect=<factory>)` pattern. Factory functions return realistic dicts with all expected keys and correct structure. No network access, no real APIs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] conftest.py nodeid-based e2e gating was too broad**

- **Found during:** Task 1 — running `test_all_phase5_tools_registered` in `test_e2e_evidence.py` resulted in SKIPPED
- **Issue:** `conftest.py` `pytest_collection_modifyitems` checked `"test_e2e" in item.nodeid` which matched ALL tests in any file named `test_e2e_*`, including the non-e2e `test_all_phase5_tools_registered` function
- **Fix:** Changed condition to `"e2e" in item.keywords` only — relies exclusively on the `@pytest.mark.e2e` marker, which is the correct gating mechanism
- **Files modified:** `tests/conftest.py`
- **Commit:** f5aeb73

The plan's `test_e2e_evidence.py` template included `try/except ValueError` around `pytest_addoption` to handle the "already registered" case from conftest.py. Since conftest.py already handles both hooks correctly (after the fix), the duplicate hooks were omitted entirely from the test file.

## Verification Results

```
# Registration test (always runs)
python -m pytest tests/test_e2e_evidence.py::test_all_phase5_tools_registered -v
-> 1 passed

# Without --run-e2e (e2e tests skipped)
python -m pytest tests/test_e2e_evidence.py -v
-> 1 passed, 3 skipped

# With --run-e2e (all tests run)
python -m pytest tests/test_e2e_evidence.py --run-e2e -v
-> 4 passed

# Regression check (editing + paralogy + genomics + e2e)
python -m pytest tests/test_e2e_evidence.py tests/test_editing.py tests/test_paralogy.py tests/test_genomics_plant.py -q
-> 74 passed, 3 skipped
```

## Self-Check: PASSED

- FOUND: tests/test_e2e_evidence.py
- FOUND: commit f5aeb73
