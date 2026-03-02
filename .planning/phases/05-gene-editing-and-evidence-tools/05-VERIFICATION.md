---
phase: 05-gene-editing-and-evidence-tools
verified: 2026-03-02T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 05: Gene Editing and Evidence Tools — Verification Report

**Phase Goal:** The agent can assess CRISPR guide design and editability for any gene, score paralogy and functional redundancy risk, and orchestrate multi-species evidence collection across the full M1 tool suite for a provided gene list
**Verified:** 2026-03-02
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Shell executor utility `_local_tools.py` wraps subprocess calls with timeout, error handling, and install-hint detection | VERIFIED | `run_local_tool` returns `(stdout, None)` or `(None, error)`, catches `FileNotFoundError`, `TimeoutExpired`, and generic exceptions — lines 61-81 of `_local_tools.py` |
| 2  | Bio tool registry covers bowtie2, minimap2, blastn, orthofinder with `check_cmd` and `install_hint` | VERIFIED | `_BIO_TOOL_REGISTRY` dict at lines 19-36 of `_local_tools.py` |
| 3  | `check_tool_available` detects installed tools via registry check command with `shutil.which` fallback | VERIFIED | Lines 84-100 of `_local_tools.py`; 13 tests all pass |
| 4  | `editing.crispr_guide_design` scans PAM sites for SpCas9 (NGG) and Cas12a (TTTV) using regex with overlapping match support | VERIFIED | `_scan_pam_sites` uses `(?=([ACGT]{20}[ACGT]GG))` lookahead at line 118 of `editing.py`; `test_overlapping_ngg_matches` passes |
| 5  | Guide scoring uses heuristic on-target score (GC%, polyT penalty, homopolymer penalty) returning 0-1 score | VERIFIED | `_score_guide_heuristic` at lines 54-82 of `editing.py`; all scoring tests pass |
| 6  | Each guide includes `guide_sequence`, `pam`, `strand`, `position`, `on_target_score`, `gc_content`, `tier` | VERIFIED | `_scan_pam_sites` appends all 7 fields; `test_guide_fields_present` passes |
| 7  | Guides are capped at `max_guides` (default 20, hard cap 50) after sorting by score descending | VERIFIED | Lines 432-435 of `editing.py`; `test_max_guides_cap` passes |
| 8  | `editing.editability_score` aggregates guide quality, structure complexity (via `gff_parse`), and regulatory complexity stub | VERIFIED | Lines 526-581 of `editing.py`; calls `crispr_guide_design` and `gff_parse`; `regulatory_complexity_score = None` explicitly documented; `test_regulatory_stub` passes |
| 9  | `genomics.paralogy_score` returns `paralog_count`, `paralogs` list, `paralog_details` with shared GO/co-expression overlap, and `data_source` | VERIFIED | Lines 2406-2600 of `genomics.py`; `test_ensembl_compara_success` validates all fields |
| 10 | OrthoFinder local data checked first (user-provided `orthofinder_dir` > `~/.ct/cache/orthofinder/` > `~/.ct/orthofinder/`), Ensembl Compara as fallback | VERIFIED | Lines 2461-2500 of `genomics.py`; `test_local_orthofinder_priority` passes |
| 11 | Ensembl Compara API uses `type=paralogues` (British spelling) and `compara=plants` | VERIFIED | Lines 2514-2515 of `genomics.py`; `test_compara_paralogues_param` asserts both parameters |
| 12 | End-to-end test validates multi-gene evidence collection across 6 tools for 5+ genes, gated behind `--run-e2e` | VERIFIED | `tests/test_e2e_evidence.py` with `@pytest.mark.e2e`; `TestMultiGeneEvidenceCollection` uses 6 genes (FLC, FT, CO, GI, SOC1, SVP) and 6 tool functions; 4 tests pass with `--run-e2e` flag |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ct/tools/_local_tools.py` | Shell executor utility (TOOL-06/07) | VERIFIED | 100 lines; substantive implementation; imported by `editing.py` at line 403 |
| `src/ct/tools/editing.py` | `editing.crispr_guide_design` and `editing.editability_score` tools (TOOL-06/07) | VERIFIED | 581 lines; both tools registered; `editing` in `PLANT_SCIENCE_CATEGORIES` |
| `src/ct/tools/__init__.py` | `"editing"` in category allowlist | VERIFIED | `PLANT_SCIENCE_CATEGORIES` includes `"editing"` at line 23; `_TOOL_MODULES` at line 87 |
| `tests/fixtures/FLC_mini_region.fasta` | Test fixture for CRISPR guide design tests | VERIFIED | File exists; used by `test_local_fasta_spcas9` and `test_cas12a_guides` |
| `tests/test_local_tools.py` | Unit tests for `_local_tools.py` | VERIFIED | 122 lines; 13 tests; all pass |
| `tests/test_editing.py` | Unit tests for `editing.py` | VERIFIED | 334 lines; 27 tests; all pass |
| `src/ct/tools/genomics.py` | `genomics.paralogy_score` appended (TOOL-08) | VERIFIED | `_parse_orthofinder_paralogs` helper at line 2367; `paralogy_score` at line 2426; both substantive |
| `tests/test_paralogy.py` | Unit tests for paralogy scoring (TOOL-08) | VERIFIED | 233 lines; `TestParseOrthofinderParalogs` (4 tests) + `TestParalogyScore` (7 tests) + registration (1 test); 12 tests all pass |
| `tests/test_e2e_evidence.py` | E2E evidence orchestration test (TOOL-09) | VERIFIED | 395 lines; `TestMultiGeneEvidenceCollection` class with `@pytest.mark.e2e`; `test_all_phase5_tools_registered` always runs |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `editing.py` | `_local_tools.py` | `from ct.tools._local_tools import check_tool_available` | WIRED | Line 403 of `editing.py`; called in off-target branch |
| `editing.py` | `_species.py` | `from ct.tools._species import resolve_species_taxon, resolve_species_binomial` | WIRED | Lines 296, 508 of `editing.py`; both functions called |
| `editing.py` | `_api_cache.py` | `from ct.tools._api_cache import get_cached, set_cached` | WIRED | Lines 297 of `editing.py`; cache check at line 325; set at line 468 |
| `editing.py` | `genomics.gff_parse` | `from ct.tools.genomics import gff_parse` | WIRED | Line 540 of `editing.py`; `gff_parse` called at line 541; result consumed for `exon_count`, `intron_count`, `gene_span_bp` |
| `editing.py` | `http_client.py` | `from ct.tools.http_client import request_json, request` | WIRED | Line 216 of `editing.py`; used in `_fetch_gene_region_fasta` |
| `genomics.py` | `_api_cache.py` | `from ct.tools._api_cache import get_cached, set_cached, _CACHE_BASE` | WIRED | Lines 2437, 2523-2530 of `genomics.py`; cache check + set implemented |
| `genomics.py` | `_species.py` | `resolve_species_taxon` + `resolve_species_binomial` | WIRED | Lines 2435-2436; both called with force escape hatch |
| `genomics.py` | `http_client.py` | `request_json` for Ensembl Compara paralogues API | WIRED | Line 2436; called for gene lookup and homology endpoint |
| `genomics.py (paralogy_score)` | `genomics.gene_annotation` | Direct function call for GO overlap | WIRED | Lines 2549, 2568; called for query gene and each paralog |
| `genomics.py (paralogy_score)` | `genomics.coexpression_network` | Direct function call for co-expression overlap | WIRED | Lines 2557, 2581; called for query gene and each paralog |
| `tests/test_e2e_evidence.py` | `ct.tools.genomics` | `from ct.tools.genomics import gene_annotation, ortholog_map, gwas_qtl_lookup, coexpression_network, paralogy_score` | WIRED | Lines 190, 301, 344; imported and called in all 3 test methods |
| `tests/test_e2e_evidence.py` | `ct.tools.editing` | `from ct.tools.editing import crispr_guide_design` | WIRED | Lines 197, 308, 351; imported and called in all 3 test methods |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| TOOL-06 | 05-01 | User can assess CRISPR guide design (PAM sites, guide scoring, off-target prediction) for a gene | SATISFIED | `editing.crispr_guide_design` registered; SpCas9 and Cas12a supported; 10 tests covering guide design pass |
| TOOL-07 | 05-01 | User can estimate editability of a gene based on gene structure, guide availability, and regulatory complexity | SATISFIED | `editing.editability_score` registered; aggregates guide quality, structure complexity via `gff_parse`, regulatory complexity stub (explicitly documented as M1 limitation) |
| TOOL-08 | 05-02 | User can score paralogy/functional redundancy for a gene (paralog count, co-expression overlap, shared annotations) | SATISFIED | `genomics.paralogy_score` registered; returns `paralog_count`, `paralogs`, `paralog_details` with `shared_go_count` and `coexpression_overlap_count`; 12 tests pass |
| TOOL-09 | 05-03 | User can gather evidence across species for a given gene list (multi-species evidence collection orchestrated by agent) | SATISFIED | Validated as compositional e2e test (not a new tool, per CONTEXT.md decision); `TestMultiGeneEvidenceCollection` exercises 6 tools for 6 genes; all 4 e2e tests pass with `--run-e2e` |

No orphaned requirements — REQUIREMENTS.md confirms all four IDs (TOOL-06, TOOL-07, TOOL-08, TOOL-09) are mapped to Phase 5 and marked Complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `editing.py` | 552-554 | `regulatory_complexity_score = None` (M1 stub) | INFO | Intentional and explicitly documented in code comment, summary output, and SUMMARY.md decisions. Downstream callers receive `None` not zero — correct signal. Not a blocker. |

No other anti-patterns found. No TODO/FIXME/HACK/PLACEHOLDER comments. No empty handlers. No static API returns.

---

### Human Verification Required

None. All phase 05 functionality is verifiable programmatically:

- Tool registration confirmed by registry inspection
- PAM scanning verified by test assertions on known FASTA fixture
- Guide scoring verified by unit tests with known input sequences
- Paralogy data resolution chain verified by mocked OrthoFinder priority test
- E2E composition verified by mocked multi-gene workflow test

The `regulatory_complexity_score = None` stub is intentional for M1 and explicitly documented — no human verification needed.

---

### Gaps Summary

No gaps. All 12 observable truths are verified. All 9 required artifacts exist with substantive implementations and verified wiring. All 4 requirements (TOOL-06 through TOOL-09) are satisfied.

**Full test suite status (phase 05 files only):**
- `tests/test_local_tools.py`: 13/13 passed
- `tests/test_editing.py`: 27/27 passed (includes 2 registration tests)
- `tests/test_paralogy.py`: 12/12 passed
- `tests/test_e2e_evidence.py` (always-run): 1/1 passed
- `tests/test_e2e_evidence.py` (--run-e2e): 4/4 passed

The 57 failures in the full test suite (`test_omics.py`, `test_sandbox.py`, `test_shell.py`, `test_terminal.py`) are pre-existing and unrelated to Phase 05. No regressions were introduced.

All 6 commits from the three plans are verified in git history:
- `461cac0` — feat(05-01): create `_local_tools.py` shell executor utility and tests
- `540a809` — feat(05-01): create `editing.py` CRISPR tools and update category allowlist
- `9f3bf06` — test(05-01): add comprehensive unit tests for `editing.py`
- `01306cf` — feat(05-02): add `genomics.paralogy_score` tool to `genomics.py`
- `94e98bc` — test(05-02): add unit tests for `genomics.paralogy_score`
- `f5aeb73` — feat(05-03): add e2e evidence orchestration test for TOOL-09

---

_Verified: 2026-03-02_
_Verifier: Claude (gsd-verifier)_
