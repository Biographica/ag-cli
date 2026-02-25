---
phase: 02-data-infrastructure
verified: 2026-02-25T12:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run 'ag species list' in a terminal"
    expected: "A rich table with Binomial Name, Taxon ID, Common Names, Genome Build columns renders correctly with 24 species rows"
    why_human: "Table rendering is visual; typer.testing CLI runner verifies exit code and output text but cannot confirm rich table layout"
---

# Phase 02: Data Infrastructure Verification Report

**Phase Goal:** Create the data infrastructure layer — species registry, manifest system, organism validation middleware, and plant data tools (data.list_datasets, data.load_expression) that let the agent discover and query local curated datasets.
**Verified:** 2026-02-25
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ag species list` displays a table with binomial name, taxon ID, common names, and genome build for all registered species | VERIFIED | `species_app` at cli.py:296-318; `list_all_species()` called at line 303; rich.Table with 4 columns at lines 305-309; test_species_list_command passes |
| 2 | `resolve_species_binomial('barley')` returns `'Hordeum vulgare'` | VERIFIED | `_species.py` builds lookup from YAML; `species_registry.yaml` has Hordeum vulgare with common_names=['barley']; confirmed via live Python check |
| 3 | `resolve_species_genome_build('arabidopsis')` returns `'TAIR10'` | VERIFIED | `_species.py` lines 171-202; YAML entry for Arabidopsis thaliana has genome_build: "TAIR10"; confirmed via live Python check |
| 4 | `load_manifest()` on a directory with manifest.yaml returns parsed dict | VERIFIED | `manifest.py` lines 22-56; tries yaml first then json fallback; 13 tests pass including test_load_manifest_yaml and test_load_manifest_json_fallback |
| 5 | `load_manifest()` on a missing directory returns None, never raises | VERIFIED | `manifest.py` line 56 returns None; confirmed live: `load_manifest('/nonexistent') is None` = True |
| 6 | `manifest_summary()` returns formatted string with dataset name, species, and file list | VERIFIED | `manifest.py` lines 72-108; 3-line format with dataset: desc / Species: ... / Files: ... ; test_manifest_summary_format passes |
| 7 | @validate_species mismatch returns data plus species_warning (warn, never block) | VERIFIED | `_validation.py` lines 107-117; result is mutated additively; test_species_mismatch_warns_not_blocks passes; data always returned |
| 8 | @validate_species with unknown species proceeds with registry note, not block | VERIFIED | `_validation.py` lines 206-211 sentinel pattern; test_unknown_species_proceeds_with_note passes |
| 9 | `data.list_datasets` and `data.load_expression` are callable by the agent via the 'data' category | VERIFIED | 'data' in PLANT_SCIENCE_CATEGORIES (`__init__.py` line 42); 'plant_data' in _TOOL_MODULES (line 83); confirmed live: `registry.list_tools('data')` returns both tools |
| 10 | `data.load_expression` with species mismatch returns data plus species_warning via @validate_species | VERIFIED | `plant_data.py` line 116 decorates with `@validate_species(dataset_kwarg="dataset")`; test_load_expression_species_mismatch_warns passes |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ct/data/species_registry.yaml` | YAML registry with 24+ species, genome_build per entry | VERIFIED | 24 species entries; 14 with genome builds, 10 with empty build (correct per plan); binomial Arabidopsis thaliana present at line 19 |
| `src/ct/tools/_species.py` | YAML-backed species resolution; exports resolve_*, list_all_species | VERIFIED | _REGISTRY_PATH wired; _load_registry() cached; all 5 public functions present and substantive; 11 tests pass |
| `src/ct/data/manifest.py` | load_manifest, manifest_species, manifest_summary | VERIFIED | All 3 functions exist with full implementation; never-raise contract confirmed; 13 tests pass |
| `src/ct/cli.py` | species_app Typer subcommand with ag species list | VERIFIED | species_app at line 296; add_typer at line 297; species_list command at line 300-318; test_species_list_command exit code 0 |
| `src/ct/tools/_validation.py` | @validate_species decorator; imports from manifest.py and _species.py | VERIFIED | Full implementation; sentinel pattern for unknown species; functools.wraps used; 10 tests pass |
| `tests/fixtures/plantexp/manifest.yaml` | Synthetic manifest for testing | VERIFIED | Exists; covers Arabidopsis thaliana and Oryza sativa; used by validation and plant_data tests |
| `src/ct/tools/plant_data.py` | data.list_datasets and data.load_expression registered tools | VERIFIED | Both tools decorated with @registry.register; category="data"; @validate_species on load_expression; substantive implementation with parquet loading, tissue filtering, gene ID matching |
| `src/ct/tools/__init__.py` | 'data' in PLANT_SCIENCE_CATEGORIES; 'plant_data' in _TOOL_MODULES | VERIFIED | 'data' at line 42; 'plant_data' at line 83 |
| `src/ct/data/downloader.py` | 'plantexp' entry in DATASETS dict | VERIFIED | Entry at line 84; auto_download=False; None URLs per STATE.md blocker |
| `tests/test_species.py` | Species registry unit tests | VERIFIED | 11 tests (plan required 10, 1 extra for empty genome_build); all pass |
| `tests/test_manifest.py` | Manifest loading unit tests | VERIFIED | 13 tests; all pass including CLI test_species_list_command |
| `tests/test_validation.py` | Validation middleware unit tests | VERIFIED | 10 tests covering all specified behaviours; all pass |
| `tests/test_plant_data.py` | Plant data tool tests | VERIFIED | 12 tests (plan required 10, 2 extras); all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/_species.py` | `src/ct/data/species_registry.yaml` | `_load_registry()` uses `yaml.safe_load` | WIRED | Line 43: `data = yaml.safe_load(fh)` reads from `_REGISTRY_PATH` which points to the YAML file |
| `src/ct/cli.py` | `src/ct/tools/_species.py` | species list command calls `list_all_species()` | WIRED | Line 303: lazy import; line 311: `for entry in list_all_species()` |
| `src/ct/tools/_validation.py` | `src/ct/data/manifest.py` | imports `load_manifest, manifest_species` | WIRED | Line 185: `from ct.data.manifest import load_manifest, manifest_species` |
| `src/ct/tools/_validation.py` | `src/ct/tools/_species.py` | imports `resolve_species_binomial` | WIRED | Line 186: `from ct.tools._species import resolve_species_binomial` |
| `src/ct/tools/plant_data.py` | `src/ct/tools/__init__.py` | `@registry.register` with `category="data"` | WIRED | Lines 22 and 104: `category="data"` on both tools |
| `src/ct/tools/plant_data.py` | `src/ct/tools/_validation.py` | `@validate_species(dataset_kwarg="dataset")` on load_expression | WIRED | Line 116: decorator applied before function definition |
| `src/ct/tools/plant_data.py` | `src/ct/data/manifest.py` | `load_manifest` used for dataset discovery | WIRED | Line 47: `from ct.data.manifest import load_manifest, manifest_summary` |
| `src/ct/tools/__init__.py` | `src/ct/tools/plant_data.py` | `'plant_data'` in `_TOOL_MODULES` tuple | WIRED | Line 83: `"plant_data"` present in _TOOL_MODULES; `_load_tools()` imports it |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-01 | 02-03 | Agent can explore and analyse data from a local project folder | SATISFIED | `data.list_datasets` discovers manifests from any data_root; `data.load_expression` reads parquet files, filters by gene/tissue, returns tissue-level TPM values; both tools visible to agent via 'data' category in PLANT_SCIENCE_CATEGORIES |
| DATA-02 | 02-01 | Data manifest pattern — each data folder has a manifest describing datasets, species, schema | SATISFIED | `manifest.py` provides load_manifest (yaml+json), manifest_species, manifest_summary; test fixture plantexp/manifest.yaml demonstrates the convention; plan specifies the manifest schema |
| DATA-03 | 02-02 | Organism validation middleware — tools validate species consistency | SATISFIED | `@validate_species` decorator in `_validation.py`; warn-and-proceed on mismatch; additive species_warning injected into result dict; sentinel pattern for unknown species; applied to data.load_expression |
| DATA-04 | 02-01 | Species registry — central registry with metadata | SATISFIED | `species_registry.yaml` is single source of truth; 24 species; taxon_id, common_names, genome_build per entry; YAML-backed `_species.py`; `ag species list` CLI command renders registry table |

**Notes:**
- REQUIREMENTS.md traceability table maps all four DATA-0x requirements to Phase 2 with status "Complete"
- No orphaned requirements found — all Phase 2 requirements (DATA-01 through DATA-04) are claimed by at least one plan and verified present

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ct/data/downloader.py` | 88-98 | `plantexp` files have `None` URLs | INFO | Expected — per STATE.md blocker (PlantExp S3 paths unconfirmed). Not a gap; the entry exists to enable `ag data status` and provides informative error messages. Real URLs will be wired when confirmed. |

No blocker or warning anti-patterns found. The None URLs in the downloader entry are documented as an intentional placeholder (STATE.md blocker — not a code quality issue).

### Human Verification Required

#### 1. ag species list Table Rendering

**Test:** Run `ag species list` in a terminal with Rich support enabled
**Expected:** A formatted table with title "Supported Species Registry", four columns (Binomial Name, Taxon ID, Common Names, Genome Build), and 24 rows — one per species in the registry
**Why human:** The typer.testing CliRunner confirms exit code 0 and text content ("Arabidopsis thaliana", "Taxon ID"), but cannot confirm the rich table renders correctly in a real terminal environment

### Gaps Summary

No gaps. All phase truths are verified, all artifacts exist and are substantive, and all key links are wired. The full Phase 2 test suite passes with 46/46 tests green. All four requirement IDs (DATA-01 through DATA-04) are satisfied.

---

_Verified: 2026-02-25_
_Verifier: Claude (gsd-verifier)_
