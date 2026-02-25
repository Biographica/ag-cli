---
phase: 02-data-infrastructure
plan: 03
subsystem: plant-data-tools
tags: [tools, data, expression, manifest, validation, registry]
dependency_graph:
  requires:
    - 02-01  # manifest.py, _species.py, species_registry.yaml
    - 02-02  # _validation.py @validate_species decorator
  provides:
    - data.list_datasets tool
    - data.load_expression tool
    - "data" category in PLANT_SCIENCE_CATEGORIES allowlist
    - plantexp entry in DATASETS downloader dict
  affects:
    - src/ct/tools/__init__.py  # PLANT_SCIENCE_CATEGORIES, _TOOL_MODULES
    - src/ct/data/downloader.py # DATASETS dict
tech_stack:
  added: []
  patterns:
    - "@registry.register tool pattern with lazy imports"
    - "@validate_species(dataset_kwarg='dataset') for species mismatch warnings"
    - "tmp_path dynamic fixture generation (no committed binary files)"
key_files:
  created:
    - src/ct/tools/plant_data.py
    - tests/test_plant_data.py
  modified:
    - src/ct/tools/__init__.py
    - src/ct/data/downloader.py
decisions:
  - "tmp_path dynamic fixture generation preferred over committing binary parquet files"
  - "12 tests written (2 extra beyond plan's 10) covering case-insensitive gene matching and bare directories without manifests"
  - "plantexp DATASETS entry uses None file URLs (pending S3 confirmation per STATE.md blocker)"
metrics:
  duration: "~10 min"
  completed: "2026-02-25"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
  tests_added: 12
  tests_passing: 46
---

# Phase 2 Plan 03: Plant Data Tools Summary

**One-liner:** Plant data tools (data.list_datasets + data.load_expression) wired together with manifest discovery, parquet loading, tissue filtering, and @validate_species species mismatch warnings.

## What Was Built

### Task 1: plant_data.py tools + registry + downloader

Created `src/ct/tools/plant_data.py` with two agent-callable tools following the exact `@registry.register` pattern from CLAUDE.md:

**`data.list_datasets`**
- Iterates subdirectories under a data root (defaults to `Config.data.base`)
- Calls `load_manifest()` on each subdir and builds a summary via `manifest_summary()`
- Directories without a manifest are still listed with "No manifest — explore files directly"
- Returns `{"summary": ..., "datasets": [manifest_dict | dir_name_str, ...]}`

**`data.load_expression`**
- Resolves dataset path from absolute path or name (via `Config.data.base`)
- Loads `expression_matrix.parquet` (or `.csv` fallback) using pandas
- Filters by gene ID (case-insensitive) and optional tissue
- Groups by tissue, computes mean TPM per tissue
- Decorated with `@validate_species(dataset_kwarg="dataset")` — species mismatch injects `species_warning` into result dict and prepends to `summary` key
- Returns `{"summary": ..., "gene": ..., "n_samples": ..., "expression": [...]}`

**Registry updates:**
- Added `"data"` to `PLANT_SCIENCE_CATEGORIES` frozenset — tools are now visible to the agent at the MCP layer
- Added `"plant_data"` to `_TOOL_MODULES` tuple — auto-registration on import

**Downloader:**
- Added `"plantexp"` entry to `DATASETS` dict with `auto_download=False` and `None` file URLs (S3 paths unconfirmed per STATE.md blocker)
- Enables `ag data status` to show plantexp and provides helpful error message

### Task 2: Tests (12 tests, all passing)

Created `tests/test_plant_data.py` using `tmp_path` dynamic fixture generation — no binary files committed.

Helper `_create_test_dataset(path)` generates a 20-row synthetic DataFrame with 4 genes (AT1G65480, Os01g0100100, AT5G10140, Zm00001d012345) across 5 tissues, saved as parquet, plus a manifest.yaml covering Arabidopsis thaliana and Oryza sativa.

| Test | What It Covers |
|---|---|
| test_list_datasets_with_manifest | Discovers manifest, returns non-empty datasets list |
| test_list_datasets_empty_dir | Empty root returns empty datasets list without error |
| test_list_datasets_no_dir | Non-existent root returns "No data directory found" message |
| test_list_datasets_dir_without_manifest | Bare directories listed as strings with note |
| test_load_expression_finds_gene | Parquet loaded, n_samples > 0, expression list non-empty |
| test_load_expression_gene_not_found | Unknown gene returns n_samples=0 |
| test_load_expression_tissue_filter | tissue param restricts results to matching tissue only |
| test_load_expression_species_mismatch_warns | @validate_species injects species_warning for Zea mays vs Arabidopsis/Oryza manifest |
| test_load_expression_data_not_found | Missing parquet returns error message with ag data pull hint |
| test_load_expression_case_insensitive_gene | AT1G65480 == at1g65480 |
| test_data_category_in_allowlist | 'data' in PLANT_SCIENCE_CATEGORIES |
| test_plant_data_module_in_tool_modules | 'plant_data' in _TOOL_MODULES |

## Phase 2 Full Test Suite Results

```
tests/test_species.py       — 14 passed
tests/test_manifest.py      — 10 passed
tests/test_validation.py    — 10 passed
tests/test_plant_data.py    — 12 passed
Total:                        46 passed, 0 failed
```

## Verification Checks

- `python -c "from ct.tools import ensure_loaded, registry, PLANT_SCIENCE_CATEGORIES; ensure_loaded(); print([t.name for t in registry.list_tools('data')])"` → `['data.list_datasets', 'data.load_expression']`
- `python -c "from ct.data.downloader import DATASETS; print('plantexp' in DATASETS)"` → `True`

## Phase 2 Success Criteria

| Criterion | Status |
|---|---|
| SC1: data.load_expression returns tissue-level values (DATA-01) | PASSED |
| SC2: Manifest exists; manifest_summary returns species/schema (DATA-02) | PASSED (verified in 02-01) |
| SC3: data.load_expression with mismatch returns species_warning (DATA-03) | PASSED |
| SC4: ag species list returns registry table (DATA-04) | PASSED (verified in 02-01) |

## Commits

| Hash | Task | Description |
|---|---|---|
| 16d03f2 | Task 1 | feat(02-03): add data.list_datasets and data.load_expression tools |
| 28b4113 | Task 2 | test(02-03): add 12 plant data tool tests |

## Deviations from Plan

### Auto-added

**Extra tests beyond plan's 10:**
- `test_list_datasets_dir_without_manifest` — covers the no-manifest directory listing path documented in the tool implementation
- `test_load_expression_case_insensitive_gene` — verifies the case-insensitive gene matching implemented in load_expression

Both follow naturally from the implementation and increase confidence. No plan content was skipped.

## Self-Check: PASSED

All files exist on disk:
- FOUND: src/ct/tools/plant_data.py
- FOUND: src/ct/tools/__init__.py (modified)
- FOUND: src/ct/data/downloader.py (modified)
- FOUND: tests/test_plant_data.py

All commits exist in git history:
- 16d03f2 feat(02-03): add data.list_datasets and data.load_expression tools
- 28b4113 test(02-03): add 12 plant data tool tests
