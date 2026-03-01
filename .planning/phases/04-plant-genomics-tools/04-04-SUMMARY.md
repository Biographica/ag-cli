---
phase: 04-plant-genomics-tools
plan: "04"
subsystem: genomics-tools
tags:
  - string-alignment
  - messaging
  - neutral-tone
  - atomic-tools
  - equal-species
dependency_graph:
  requires:
    - "04-03"
  provides:
    - aligned Phase 4 tool messaging strings
  affects:
    - src/ct/tools/genomics.py
    - tests/test_genomics_plant.py
tech_stack:
  added: []
  patterns:
    - neutral usage_guide tone (describes what tool returns, not how to use it)
    - generic sparse-result messaging ("data coverage is limited for this species")
    - atomic tool outputs (no prescribed next steps)
    - equal species treatment (no tiering language)
key_files:
  modified:
    - src/ct/tools/genomics.py
    - tests/test_genomics_plant.py
decisions:
  - Usage guides describe what a tool returns, not directives on when/how to chain tools
  - Sparse-result messages use "data coverage is limited" generic phrasing across all tools
  - Tool outputs must not prescribe next tool calls — agent decides independently
  - All species treated as equals in tool descriptions; existence of data stated factually
metrics:
  duration: "8 min"
  completed_date: "2026-03-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 04 Plan 04: Messaging Alignment Summary

Aligned all 5 Phase 4 tool strings with neutral tone, generic sparse-result messaging, atomic outputs, and equal species treatment per locked CONTEXT.md decisions.

## What Was Built

10 targeted string replacements across `src/ct/tools/genomics.py` and matching test assertion updates in `tests/test_genomics_plant.py`. No logic, data structures, imports, or return value shapes were changed.

## Tasks Completed

### Task 1: Update all tool registration strings and runtime messaging in genomics.py

Applied 10 string replacements:

1. **gene_annotation usage_guide** — neutral description of what tool returns (GO terms, genomic location, PubMed IDs); removed "Start here for target characterisation" and "Cross-reference PubMed IDs with..." directives
2. **gwas_qtl_lookup usage_guide** — neutral description of Ensembl Plants phenotype endpoint; removed "Arabidopsis has the richest coverage" and chaining suggestion
3. **gwas_qtl_lookup non-Arabidopsis empty suggestion** — "Phenotype data coverage is limited for this species in Ensembl Plants" replacing Arabidopsis-first messaging with specific tool suggestion
4. **gwas_qtl_lookup Arabidopsis empty suggestion** — "Phenotype data coverage is limited for this gene" replacing human-disease comparison
5. **ortholog_map usage_guide** — neutral description of Ensembl Compara return values; removed "Use to transfer functional knowledge" directive
6. **ortholog_map empty-result** — removed "Try without target_species filter..." chaining hint; agent decides independently
7. **gff_parse usage_guide** — neutral description of GFF3 parsing; removed "Needed for CRISPR guide design" prescription
8. **coexpression_network species parameter** — removed "rice best-effort" tiering language
9. **coexpression_network usage_guide** — neutral description of ATTED-II return values; removed "Arabidopsis has the best coverage" and locus code instruction
10. **coexpression_network unsupported species message** — "data coverage is limited for {binomial}" pattern; states what data exists factually without "best-effort" tiering

Commit: `6953720`

### Task 2: Update test assertions to match new messaging strings

Updated 4 assertion/comment strings in `tests/test_genomics_plant.py`:

- `test_empty_with_suggestion`: `assert "data coverage is limited" in result["suggestion"]` (was "Arabidopsis")
- `test_empty_arabidopsis`: `assert "data coverage is limited" in result["suggestion"]` (was "sparser than for human diseases")
- Updated inline comments for both test cases from specific-tool suggestions to "generic sparse-result message"

Commit: `88c836f`

## Verification Results

- All 34 tests in `tests/test_genomics_plant.py` pass
- All 5 Phase 4 tools register with aligned usage guides (registry verification passed)
- `grep -c 'Start here|Cross-reference|best coverage|best-effort|Needed for CRISPR|richest coverage|Try looking up|sparser than for human' src/ct/tools/genomics.py` = 1 (only inline code comment `# Step 1 — Resolve gene to Ensembl ID (best-effort; failure is non-fatal)`, which is out of scope per plan constraints)
- `grep -c 'data coverage is limited' src/ct/tools/genomics.py` = 3 (new generic messaging present in all 3 empty-result paths)

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- The one remaining "best-effort" occurrence (line 1607) is an inline implementation comment inside the function body, not a user-facing string — correctly left unchanged per the plan's explicit scope constraint ("Only string literals in `usage_guide`, `description` parameter entries, `suggestion` variables, and `summary` messages are modified.")

## Self-Check: PASSED

Files verified:
- FOUND: src/ct/tools/genomics.py
- FOUND: tests/test_genomics_plant.py
- FOUND: .planning/phases/04-plant-genomics-tools/04-04-SUMMARY.md

Commits verified:
- FOUND: 6953720 (feat: align Phase 4 tool strings)
- FOUND: 88c836f (test: update assertions)
