---
phase: 02-data-infrastructure
verified: 2026-02-25T22:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 10/10
  note: "Previous verification predated plan 02-04 (gap-closure). This re-verification covers all four plans including gap-closure fixes."
  gaps_closed:
    - "Unknown species input now returns taxon 0 and empty binomial, not Arabidopsis defaults"
    - "resolve_species_genome_build docstring and YAML schema comment clarify single-build limitation"
    - "parity.py _normalize_mygene_species no longer coerces empty species to arabidopsis thaliana"
    - "network.py ppi_analysis returns clear error dict when taxon resolves to 0"
    - "protein.py function_predict and domain_annotate return clear error dicts when taxon resolves to 0"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run 'ag species list' in a terminal with Rich support enabled"
    expected: "A formatted table titled 'Supported Species Registry' with four columns (Binomial Name, Taxon ID, Common Names, Genome Build) and 24 rows — one per species in the registry"
    why_human: "typer.testing CliRunner confirms exit code 0 and text content but cannot confirm rich table renders correctly in a real terminal"
---

# Phase 02: Data Infrastructure Verification Report

**Phase Goal:** The agent can access and explore local curated plant datasets through a versioned manifest system with programmatic organism validation on every data access
**Verified:** 2026-02-25
**Status:** passed
**Re-verification:** Yes — after 02-04 gap closure (previous verification predated this plan)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ag species list` displays a table with binomial name, taxon ID, common names, and genome build for all registered species | VERIFIED | `species_app` in `cli.py`; `list_all_species()` called; rich.Table with 4 columns; `test_species_list_command` passes with exit code 0 |
| 2 | `resolve_species_binomial('barley')` returns `'Hordeum vulgare'` | VERIFIED | `_species.py` builds lookup from YAML; YAML has Hordeum vulgare with `common_names=['barley']`; live confirmed |
| 3 | `resolve_species_genome_build('arabidopsis')` returns `'TAIR10'` | VERIFIED | `_species.py` lines 174-209; YAML entry has `genome_build: "TAIR10"`; live confirmed |
| 4 | `load_manifest()` on a directory with manifest.yaml returns parsed dict | VERIFIED | `manifest.py` tries yaml first then json fallback; 13 tests pass including `test_load_manifest_yaml` |
| 5 | `load_manifest()` on a missing directory returns None, never raises | VERIFIED | `manifest.py` returns None on missing path; `test_load_manifest_nonexistent_dir_returns_none` passes |
| 6 | `manifest_summary()` returns formatted string with dataset name, species, and file list | VERIFIED | `manifest.py`; 3-line format; `test_manifest_summary_format` passes |
| 7 | `@validate_species` mismatch returns data plus `species_warning` (warn, never block) | VERIFIED | `_validation.py`; result is mutated additively; `test_species_mismatch_warns_not_blocks` passes |
| 8 | `@validate_species` with unknown species proceeds with registry note, not block | VERIFIED | `_validation.py` sentinel pattern; `test_unknown_species_proceeds_with_note` passes |
| 9 | `data.list_datasets` and `data.load_expression` are callable by the agent via the 'data' category | VERIFIED | `'data'` in `PLANT_SCIENCE_CATEGORIES`; `'plant_data'` in `_TOOL_MODULES`; `test_data_category_in_allowlist` and `test_plant_data_module_in_tool_modules` pass |
| 10 | `data.load_expression` with species mismatch returns data plus `species_warning` via `@validate_species` | VERIFIED | `plant_data.py` decorated with `@validate_species(dataset_kwarg="dataset")`; `test_load_expression_species_mismatch_warns` passes |
| 11 | Unknown species input returns taxon 0 and empty binomial, not Arabidopsis defaults | VERIFIED | `_DEFAULT_TAXON=0`, `_DEFAULT_BINOMIAL=''` in `_species.py:25-26`; live: `resolve_species_taxon('unknown_plant')` = 0; `test_resolve_species_taxon_unknown_returns_default` asserts 0 |
| 12 | `resolve_species_genome_build` docstring and YAML schema comment clarify the single-build limitation | VERIFIED | `_species.py:175-179` docstring states "primary reference assembly identifier"; `species_registry.yaml:12-16` schema comment documents single-entry limitation and notes pangenome as future extension |
| 13 | `parity.py _normalize_mygene_species` does not coerce empty species to arabidopsis thaliana | VERIFIED | `parity.py:95-97`: `s = (species or "").strip().lower()` then `return s` for empty; live: `_normalize_mygene_species('')` = `''`; `_normalize_mygene_species(None)` = `''` |
| 14 | `network.py ppi_analysis` returns a clear error dict when taxon resolves to 0 | VERIFIED | `network.py:69-73`: `if species_taxon == 0: return {error, summary}` guard; live: unknown species returns error dict without API call |
| 15 | `protein.py function_predict` and `domain_annotate` return error dicts when taxon resolves to 0 | VERIFIED | `protein.py:139-143` (function_predict) and `protein.py:364-368` (domain_annotate) both guard `if species_taxon == 0:`; live confirmed for both |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ct/data/species_registry.yaml` | YAML registry with 24+ species, genome_build per entry, schema comment for single-build limitation | VERIFIED | 24 species entries; schema comment at lines 12-16 documents single-assembly limitation and pangenome future; Arabidopsis thaliana at line 23 |
| `src/ct/tools/_species.py` | YAML-backed species resolution; `_DEFAULT_TAXON=0`, `_DEFAULT_BINOMIAL=''`; exports resolve_*, list_all_species; genome_build docstring clarified | VERIFIED | Sentinels at lines 25-26; all 5 public functions present and substantive; docstring updated; 11 tests pass |
| `src/ct/data/manifest.py` | `load_manifest`, `manifest_species`, `manifest_summary` | VERIFIED | All 3 functions exist with full implementation; never-raise contract confirmed; 13 tests pass |
| `src/ct/cli.py` | `species_app` Typer subcommand with `ag species list` | VERIFIED | `species_app` and `add_typer` present; `species list` command renders table; `test_species_list_command` exits 0 |
| `src/ct/tools/_validation.py` | `@validate_species` decorator; imports from `manifest.py` and `_species.py` | VERIFIED | Full implementation; sentinel pattern for unknown species; `functools.wraps` used; 10 tests pass |
| `tests/fixtures/plantexp/manifest.yaml` | Synthetic manifest for testing | VERIFIED | Exists; covers Arabidopsis thaliana and Oryza sativa; used by validation and plant_data tests |
| `src/ct/tools/plant_data.py` | `data.list_datasets` and `data.load_expression` registered tools | VERIFIED | Both tools decorated with `@registry.register`; `category="data"`; `@validate_species` on `load_expression`; substantive parquet loading implementation |
| `src/ct/tools/__init__.py` | `'data'` in `PLANT_SCIENCE_CATEGORIES`; `'plant_data'` in `_TOOL_MODULES` | VERIFIED | Both present; confirmed by passing tests |
| `src/ct/data/downloader.py` | `'plantexp'` entry in DATASETS dict | VERIFIED | Entry present; `auto_download=False`; None URLs per STATE.md blocker (intentional) |
| `src/ct/tools/parity.py` | `_normalize_mygene_species` returns `''` not `'3702'` for empty/None species | VERIFIED | Lines 95-97: `s = (species or "").strip().lower()`; `return s` for empty; live confirmed |
| `src/ct/tools/network.py` | `ppi_analysis` guards against `species_taxon == 0` | VERIFIED | Lines 69-73: guard present; live: unknown species returns error dict, no API call |
| `src/ct/tools/protein.py` | `function_predict` and `domain_annotate` guard against `species_taxon == 0` | VERIFIED | `function_predict` lines 139-143; `domain_annotate` lines 364-368; live confirmed for both |
| `tests/test_species.py` | Species registry unit tests; `test_resolve_species_taxon_unknown_returns_default` asserts 0 | VERIFIED | 11 tests; `assert result == 0` at line 158; all 11 pass |
| `tests/test_manifest.py` | Manifest loading unit tests | VERIFIED | 13 tests; all pass including `test_species_list_command` |
| `tests/test_validation.py` | Validation middleware unit tests | VERIFIED | 10 tests covering all specified behaviours; all pass |
| `tests/test_plant_data.py` | Plant data tool tests | VERIFIED | 12 tests; all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/_species.py` | `src/ct/data/species_registry.yaml` | `_load_registry()` reads YAML from `_REGISTRY_PATH` | WIRED | `_REGISTRY_PATH` at line 22; `yaml.safe_load(fh)` at line 43 |
| `src/ct/cli.py` | `src/ct/tools/_species.py` | species list command calls `list_all_species()` | WIRED | Lazy import; iterates `list_all_species()` to populate rich.Table |
| `src/ct/tools/_validation.py` | `src/ct/data/manifest.py` | imports `load_manifest, manifest_species` | WIRED | `from ct.data.manifest import load_manifest, manifest_species` |
| `src/ct/tools/_validation.py` | `src/ct/tools/_species.py` | imports `resolve_species_binomial` | WIRED | `from ct.tools._species import resolve_species_binomial` |
| `src/ct/tools/plant_data.py` | `src/ct/tools/__init__.py` | `@registry.register` with `category="data"` | WIRED | Both tools registered with `category="data"` |
| `src/ct/tools/plant_data.py` | `src/ct/tools/_validation.py` | `@validate_species(dataset_kwarg="dataset")` on `load_expression` | WIRED | Decorator applied to `load_expression` |
| `src/ct/tools/plant_data.py` | `src/ct/data/manifest.py` | `load_manifest` used for dataset discovery | WIRED | `from ct.data.manifest import load_manifest, manifest_summary` |
| `src/ct/tools/__init__.py` | `src/ct/tools/plant_data.py` | `'plant_data'` in `_TOOL_MODULES` tuple | WIRED | `"plant_data"` present in `_TOOL_MODULES`; `_load_tools()` imports it |
| `src/ct/tools/network.py` | `src/ct/tools/_species.py` | `resolve_species_taxon` + guard `if species_taxon == 0` | WIRED | Lines 64-73: lazy import and guard present; unknown species returns error dict |
| `src/ct/tools/protein.py` | `src/ct/tools/_species.py` | `resolve_species_taxon` + guard `if species_taxon == 0` (two functions) | WIRED | `function_predict` lines 137-143; `domain_annotate` lines 362-368; both guards confirmed live |
| `src/ct/tools/parity.py` | (no longer silently to arabidopsis) | `_normalize_mygene_species` returns `''` for empty species | WIRED | Lines 95-97: sentinel empty-string passthrough; live confirmed |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-01 | 02-03 | Agent can explore and analyse data from a local project folder | SATISFIED | `data.list_datasets` discovers manifests from any `data_root`; `data.load_expression` reads parquet files, filters by gene/tissue, returns tissue-level TPM values; both tools visible to agent via `'data'` category; 12 tests pass |
| DATA-02 | 02-01, 02-04 | Data manifest pattern — each data folder has a manifest describing datasets, species, schema | SATISFIED | `manifest.py` provides `load_manifest` (yaml+json fallback), `manifest_species`, `manifest_summary`; test fixture `plantexp/manifest.yaml` demonstrates the convention; schema comment in `species_registry.yaml` updated (02-04) |
| DATA-03 | 02-02 | Organism validation middleware — tools validate species consistency | SATISFIED | `@validate_species` decorator in `_validation.py`; warn-and-proceed on mismatch; additive `species_warning` injected into result dict; sentinel pattern for unknown species; applied to `data.load_expression`; callers (network, protein) now return explicit errors for taxon 0 |
| DATA-04 | 02-01 | Species registry — central registry with metadata | SATISFIED | `species_registry.yaml` is single source of truth; 24 species; taxon_id, common_names, genome_build per entry; YAML-backed `_species.py`; `ag species list` CLI command renders registry table; unknown-species sentinel (0/'') prevents silent Arabidopsis default |

**Notes:**
- REQUIREMENTS.md traceability table maps all four DATA-0x requirements to Phase 2 with status "Complete"
- No orphaned requirements — all Phase 2 requirements (DATA-01 through DATA-04) claimed by at least one plan and verified present in the codebase

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ct/data/downloader.py` | 88-98 | `plantexp` files have `None` URLs | INFO | Expected — per STATE.md blocker (PlantExp S3 paths unconfirmed). Entry exists to enable `ag data status` and provides informative error messages. Real URLs wired when confirmed. |

No blocker or warning anti-patterns found. The None URLs in the downloader entry are a documented intentional placeholder.

### Human Verification Required

#### 1. ag species list Table Rendering

**Test:** Run `ag species list` in a terminal with Rich support enabled
**Expected:** A formatted table titled "Supported Species Registry" with four columns (Binomial Name, Taxon ID, Common Names, Genome Build) and 24 rows — one per species in the registry
**Why human:** The typer.testing CliRunner confirms exit code 0 and text content ("Arabidopsis thaliana", "Taxon ID"), but cannot confirm the rich table renders correctly in a real terminal environment

### Gaps Summary

No gaps. All 15 phase truths verified, all artifacts exist and are substantive, and all key links are wired. The full Phase 2 test suite passes with 46/46 tests green. All four requirement IDs (DATA-01 through DATA-04) are satisfied.

The 02-04 gap-closure plan is fully executed and verified:
- `_DEFAULT_TAXON=0`, `_DEFAULT_BINOMIAL=''` — unknown species no longer silently masquerade as Arabidopsis
- `network.ppi_analysis`, `protein.function_predict`, and `protein.domain_annotate` return error dicts for unknown species
- `parity._normalize_mygene_species` passes empty species as `''`, not `'3702'`
- `species_registry.yaml` schema comment and `resolve_species_genome_build` docstring document the single-assembly limitation
- Commits `9a81b82` and `55cdd98` verified present in git log

---

_Verified: 2026-02-25_
_Verifier: Claude (gsd-verifier)_
