---
phase: 02-data-infrastructure
plan: 02
subsystem: organism-validation
tags: [species-validation, decorator, middleware, manifest, non-blocking, warn-proceed]
dependency_graph:
  requires:
    - species_registry_yaml
    - yaml_backed_species_resolution
    - dataset_manifest_loader
  provides:
    - validate_species_decorator
    - organism_validation_middleware
  affects:
    - 02-03-plant-data-tools
tech_stack:
  added:
    - functools.wraps (decorator metadata preservation)
    - sentinel pattern (reliable unknown-species detection without default collision)
  patterns:
    - Decorator factory (validate_species returns a decorator)
    - Sentinel default for distinguishing "not in registry" from "resolved to default"
    - Lazy imports inside wrapper body (matching project pattern)
    - Purely additive result mutation (never replaces, only prepends/adds keys)
key_files:
  created:
    - src/ct/tools/_validation.py
    - tests/test_validation.py
    - tests/fixtures/plantexp/manifest.yaml
  modified: []
decisions:
  - Sentinel default string used in resolve_species_binomial to reliably detect unknown species — avoids false negative when arabidopsis (the standard default) is present in the dataset's covered list
  - Config imported lazily inside _resolve_dataset_dir body — consistent with project lazy-import pattern and avoids circular imports
  - patch("ct.agent.config.Config") used in test 10 rather than patching within _validation module — because Config is imported lazily and does not exist at module level in _validation.py
metrics:
  duration: 2 min
  completed: 2026-02-25
  tasks_completed: 2
  files_created: 3
  files_modified: 0
  tests_added: 10
---

# Phase 02 Plan 02: Organism Validation Middleware Summary

Non-blocking `@validate_species` decorator that warns (never blocks) when a tool's requested species is not covered by the dataset manifest — using a sentinel-default pattern for reliable unknown-species detection.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | @validate_species decorator + plantexp test fixture | 3e98539 | _validation.py, tests/fixtures/plantexp/manifest.yaml |
| 2 | Comprehensive validation tests + sentinel bug fix | a4895a8 | test_validation.py, _validation.py (bug fix) |

## What Was Built

### src/ct/tools/_validation.py

The organism validation middleware decorator:

```python
@validate_species()
def my_tool(gene: str = "", species: str = "", dataset_dir: str = "", **kwargs) -> dict:
    ...

@validate_species(dataset_kwarg="dataset")
def my_tool(gene: str = "", species: str = "", dataset: str = "", **kwargs) -> dict:
    ...
```

Key behaviors:

- **Never blocks** — always calls the wrapped function and returns its result
- **Additive-only** — adds `species_warning` key and prepends warning to `summary` key
- **Two resolution modes**: explicit `dataset_dir` kwarg OR `dataset` name/path kwarg
- **Dataset kwarg mode**: absolute paths used directly; relative names resolved via `Config.data.base`
- **Species matching**: uses `resolve_species_binomial(species, default=_SENTINEL)` with a sentinel default to detect "not in registry" without any false negatives
- **Missing manifest**: proceeds silently (no warning, no error)
- **Empty species_covered**: proceeds silently (nothing to validate against)
- **Unknown species**: emits registry note ("not in registry; metadata could not be verified")
- **Known species, mismatch**: emits coverage warning with covered species listed
- **Known species, covered**: no warning

### tests/fixtures/plantexp/manifest.yaml

Synthetic fixture manifest covering Arabidopsis thaliana and Oryza sativa, used by the test suite without requiring any real dataset on disk.

### tests/test_validation.py

10 tests covering all specified behaviours:

| Test | Behaviour Verified |
|------|--------------------|
| 1 | Species match → no warning |
| 2 | Species mismatch → warning + data still returned |
| 3 | Unknown species → registry note + data returned |
| 4 | Multi-species dataset, requested species IS covered → no warning |
| 5 | No manifest in directory → silent proceed |
| 6 | No species kwarg → validation skipped entirely |
| 7 | No dataset_dir kwarg → validation skipped |
| 8 | Empty species_covered list → no warning |
| 9 | dataset_kwarg with absolute path → manifest loaded, warning present |
| 10 | dataset_kwarg with name → Config.data.base resolution → warning present |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sentinel pattern to fix false-negative unknown-species detection**
- **Found during:** Task 2 test run (test_unknown_species_proceeds_with_note failed)
- **Issue:** Initial implementation used `_DEFAULT_BINOMIAL = "Arabidopsis thaliana"` as the default in `resolve_species_binomial()`. When an unknown species resolved to the arabidopsis default AND arabidopsis was also in the covered list, the coverage check passed (canonical in covered_lower = True) and no warning was generated — a false negative.
- **Fix:** Use a sentinel string (`"__SENTINEL_NOT_IN_REGISTRY__"`) as the default value. If `resolve_species_binomial` returns the sentinel, the species is definitively not in the registry regardless of what the covered list contains.
- **Files modified:** `src/ct/tools/_validation.py`
- **Commit:** a4895a8

**2. [Rule 1 - Bug] patch path corrected for lazy-imported Config in test 10**
- **Found during:** Task 2 test run (test_dataset_kwarg_resolves_name_via_config failed)
- **Issue:** `patch("ct.tools._validation.Config")` fails because Config is only imported lazily inside `_resolve_dataset_dir()` — it is not a module-level attribute of `_validation`.
- **Fix:** Changed to `patch("ct.agent.config.Config")` — patching at the actual source of truth, which is the correct mock strategy for lazily-imported dependencies.
- **Files modified:** `tests/test_validation.py`
- **Commit:** a4895a8

## Verification

```
$ python -c "from ct.tools._validation import validate_species; print('OK')"
OK

$ python -m pytest tests/test_validation.py -x -v
==================== 10 passed in 0.07s ====================
```

All 10 tests pass. Species mismatch returns data + warning. Unknown species gets a registry note. Missing manifest proceeds silently.

## Self-Check: PASSED

Files confirmed:
- src/ct/tools/_validation.py: EXISTS
- tests/test_validation.py: EXISTS
- tests/fixtures/plantexp/manifest.yaml: EXISTS

Commits confirmed:
- 3e98539: feat(02-02): validate_species decorator and plantexp test fixture
- a4895a8: feat(02-02): comprehensive validate_species tests and bug fix
