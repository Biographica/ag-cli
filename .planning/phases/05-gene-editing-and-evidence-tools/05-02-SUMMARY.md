---
phase: 05-gene-editing-and-evidence-tools
plan: "02"
subsystem: genomics-tools
tags: [paralogy, gene-redundancy, orthofinder, ensembl-compara, functional-annotation]
dependency_graph:
  requires:
    - "05-01"  # genomics module and tool registry already established
    - "04-04"  # genomics.gene_annotation and genomics.coexpression_network (sub-calls)
  provides:
    - genomics.paralogy_score  # TOOL-08
  affects:
    - src/ct/tools/genomics.py
tech_stack:
  added: []
  patterns:
    - OrthoFinder Orthogroups.tsv CSV parsing via stdlib csv.DictReader
    - Local-first data resolution with Ensembl Compara API fallback
    - Sub-tool calling: gene_annotation and coexpression_network called as direct functions
    - Ensembl Compara paralogues endpoint (British spelling, compara=plants hardcoded)
key_files:
  created:
    - tests/test_paralogy.py
  modified:
    - src/ct/tools/genomics.py  # appended _parse_orthofinder_paralogs + paralogy_score
decisions:
  - "OrthoFinder Orthogroups.tsv parsed via stdlib csv.DictReader — no pandas dependency; reads incrementally, stops at first match"
  - "orthofinder_dir parameter explicit override checked first, then _CACHE_BASE/orthofinder, then ~/.ct/orthofinder — priority order matches user expectation"
  - "species_col_candidates tries binomial, underscore-form, and lowercase — OrthoFinder column naming conventions vary between runs"
  - "Sub-calls to gene_annotation and coexpression_network use direct function calls (not registry) — same module, no lookup overhead, easier to mock"
  - "max_paralogs_detail capped at 10 internally — avoids unbounded API fanout for genes with many paralogs"
  - "test_local_orthofinder_priority uses orthofinder_dir parameter (not _CACHE_BASE patch) — simpler, also validates the parameter path explicitly"
metrics:
  duration: "7 min (434 seconds)"
  completed: "2026-03-02"
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 02: Paralogy Score Tool Summary

**One-liner:** genomics.paralogy_score with OrthoFinder-local-first data resolution, Ensembl Compara paralogues fallback, and GO/co-expression overlap detail for top N paralogs.

## What Was Built

Added `genomics.paralogy_score` (TOOL-08) to the genomics module. This tool enables the agent to assess functional redundancy risk for gene editing target selection. If a gene has many paralogs with overlapping function, knocking it out may have minimal phenotypic effect.

### Tool: `genomics.paralogy_score`

**Location:** `src/ct/tools/genomics.py` (appended after `coexpression_network`)

**Returns:**
- `paralog_count` — total paralogs found
- `paralogs` — list of paralog gene IDs
- `data_source` — where paralogs came from (OrthoFinder path or "Ensembl Compara")
- `paralog_details` — per-paralog GO overlap and co-expression overlap for top N paralogs

**Data resolution chain:**
1. User-provided `orthofinder_dir` (if given)
2. `~/.ct/cache/orthofinder/` (managed by gsd cache)
3. `~/.ct/orthofinder/` (user-placed data)
4. Ensembl Compara paralogues endpoint (fallback)

**Helper function:** `_parse_orthofinder_paralogs(gene, species_col, orthogroups_tsv)` — parses Orthogroups.tsv to find genes in the same row + same species column.

### Tests: `tests/test_paralogy.py`

12 tests, all passing:

| Class | Tests |
|-------|-------|
| TestParseOrthofinderParalogs | 4 (finds paralogs, gene not found, single gene, file not found) |
| TestParalogyScore | 7 (Ensembl success+detail, OrthoFinder priority, params verification, empty response, unknown species, cache hit, missing gene) |
| module-level | 1 (registration check) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_local_orthofinder_priority needed gene_annotation and coexpression_network mocked**

- **Found during:** Task 2 test execution
- **Issue:** Test used `orthofinder_dir` to supply local data, causing paralogy_score to find paralogs and proceed to step 3 (detailed overlap). Step 3 calls `gene_annotation` and `coexpression_network`, which weren't mocked — causing `ValueError: not enough values to unpack` from the unmocked `request_json` tuple.
- **Fix:** Added `@patch("ct.tools.genomics.gene_annotation")` and `@patch("ct.tools.genomics.coexpression_network")` decorators with `return_value = {"go_terms": [], "coexpressed_genes": []}` to the test. This is consistent with how `test_ensembl_compara_success` already mocked these.
- **Files modified:** `tests/test_paralogy.py`
- **Commit:** 94e98bc

## Self-Check: PASSED

- FOUND: src/ct/tools/genomics.py
- FOUND: tests/test_paralogy.py
- FOUND: .planning/phases/05-gene-editing-and-evidence-tools/05-02-SUMMARY.md
- FOUND commit: 01306cf (feat: add genomics.paralogy_score tool)
- FOUND commit: 94e98bc (test: add unit tests for genomics.paralogy_score)
