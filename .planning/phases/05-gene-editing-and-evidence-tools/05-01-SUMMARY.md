---
phase: 05-gene-editing-and-evidence-tools
plan: "01"
subsystem: crispr-editing-tools
tags: [crispr, guide-design, editing, local-tools, subprocess]
dependency_graph:
  requires: []
  provides:
    - src/ct/tools/_local_tools.py
    - src/ct/tools/editing.py
  affects:
    - src/ct/tools/__init__.py
tech_stack:
  added: []
  patterns:
    - subprocess executor with (stdout, error) tuple pattern
    - regex lookahead for overlapping PAM site matching
    - heuristic on-target scoring (GC%, polyT, homopolymer)
    - data resolution chain: local file > Ensembl REST
key_files:
  created:
    - src/ct/tools/_local_tools.py
    - src/ct/tools/editing.py
    - tests/test_local_tools.py
    - tests/test_editing.py
    - tests/fixtures/FLC_mini_region.fasta
  modified:
    - src/ct/tools/__init__.py
decisions:
  - "_local_tools.py uses stdlib only (subprocess, shutil) at module level — no third-party imports, mirrors http_client.py (result, error) tuple contract"
  - "SpCas9 PAM scanning uses re lookahead pattern (?=(...)) to capture overlapping NGG matches — standard regex would miss adjacent PAMs sharing a nucleotide"
  - "Off-target counting uses regex mismatch scan for M1 even when aligner is present — full alignment pipeline requires genome indexing which is a future enhancement"
  - "editability_score regulatory_complexity_score returns None for M1 — stub documented explicitly"
  - "Guide tiers: high_confidence >= 0.65, acceptable >= 0.40, poor < 0.40 — based on Doench 2016 distilled heuristics"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-02"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 1
requirements-completed: [TOOL-06, TOOL-07]
---

# Phase 05 Plan 01: Shell Executor and CRISPR Guide Design Tools Summary

**One-liner:** Subprocess shell executor utility with (stdout, error) tuple pattern plus SpCas9/Cas12a CRISPR guide design with heuristic on-target scoring and regex off-target fallback, all behind a plant-science allowlisted "editing" category.

## What Was Built

### `src/ct/tools/_local_tools.py` — Shell Executor Utility

A subprocess wrapper that mirrors the `http_client.py` (result, error) tuple pattern for running external bioinformatics CLI tools (Bowtie2, minimap2, BLAST+, OrthoFinder). Uses stdlib only at module level.

Key functions:
- `run_local_tool(cmd, *, timeout, tool_name)` — returns `(stdout, None)` or `(None, error)`, never raises
- `check_tool_available(tool_name)` — checks registry check command first, falls back to `shutil.which`
- `_BIO_TOOL_REGISTRY` — covers bowtie2, minimap2, blastn, orthofinder with `check_cmd` and `install_hint`

### `src/ct/tools/editing.py` — CRISPR Editing Tools

Two registered tools in the `"editing"` category:

**`editing.crispr_guide_design`**
- Scans PAM sites for SpCas9 (NGG) and Cas12a (TTTV) using regex lookahead for overlapping matches
- Heuristic on-target scoring: baseline 0.5 + GC content reward/penalty (0.40-0.70 optimal) + polyT penalty (TTTT) + homopolymer penalty (5+ repeat)
- Guide fields: `guide_sequence`, `pam`, `strand`, `position`, `on_target_score`, `gc_content`, `tier`, `off_target_count`
- Tier labels: `high_confidence` (>=0.65), `acceptable` (>=0.40), `poor` (<0.40)
- Guides capped at `max_guides` (default 20, hard cap 50) after sorting by score descending
- Off-target counting: regex mismatch scan (graceful fallback, external aligner integration deferred)
- FASTA data chain: user-provided file > Ensembl Plants REST sequence/region endpoint
- Species validation via `resolve_species_taxon` with `force=True` escape hatch
- Results cached via `_api_cache`

**`editing.editability_score`**
- Aggregates sub-scores without composite weighting
- Sub-score 1: guide quality (fraction of high_confidence guides)
- Sub-score 2: structure complexity (exon count, intron count, gene span bp) via `gff_parse`
- Sub-score 3: regulatory complexity — `None` (M1 stub)

### `src/ct/tools/__init__.py` — Category Allowlist Update

Added `"editing"` to both `PLANT_SCIENCE_CATEGORIES` frozenset and `_TOOL_MODULES` tuple.

### Test Fixtures and Tests

- `tests/fixtures/FLC_mini_region.fasta` — 195 bp synthetic FASTA with known NGG (AGG at ~pos 39, 79) and TTTV (TTTA at ~pos 121) PAM sites
- `tests/test_local_tools.py` — 13 tests: success/fail/timeout/truncation, FileNotFoundError with/without hint, tool availability, registry structure
- `tests/test_editing.py` — 27 tests: helpers, PAM scanning (SpCas9/Cas12a/both strands/overlapping/field validation), guide design (local FASTA, tier labels, max cap, off-target fallback, species errors, force override, cache hit), editability score (sub-scores, regulatory stub, error cases), registration checks

## Decisions Made

1. `_local_tools.py` uses stdlib only (`subprocess`, `shutil`) at module level — mirrors `http_client.py` (result, error) tuple contract, no third-party imports needed for subprocess management.

2. SpCas9 PAM scanning uses re lookahead pattern `(?=(...))` to capture overlapping NGG matches — standard `re.finditer` with a consuming pattern would miss adjacent PAMs sharing a nucleotide (e.g., `AGGG` yields both `AGG` and `GGG` sites).

3. Off-target counting uses regex mismatch scan for M1 even when an aligner is present — full Bowtie2 alignment requires genome indexing (index files), which requires a separate workflow step. Logged as future enhancement.

4. `editability_score` regulatory complexity returns `None` for M1 — explicitly documented as a stub; downstream callers should treat `None` as "data not available" not "zero complexity".

5. Guide tiers based on Doench 2016 heuristics: `high_confidence` >= 0.65, `acceptable` >= 0.40, `poor` < 0.40 — thresholds chosen to be conservative (fewer high-confidence guides) for plant science context.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 461cac0 | feat(05-01): create _local_tools.py shell executor utility and tests |
| Task 2 | 540a809 | feat(05-01): create editing.py CRISPR tools and update category allowlist |
| Task 3 | 9f3bf06 | test(05-01): add comprehensive unit tests for editing.py |

## Self-Check: PASSED

Files verified:
- FOUND: src/ct/tools/_local_tools.py
- FOUND: src/ct/tools/editing.py
- FOUND: tests/test_local_tools.py
- FOUND: tests/test_editing.py
- FOUND: tests/fixtures/FLC_mini_region.fasta

Commits verified:
- FOUND: 461cac0
- FOUND: 540a809
- FOUND: 9f3bf06

Tests: 40 passed (13 local_tools + 27 editing), 0 failed
