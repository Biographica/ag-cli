---
phase: 02-data-infrastructure
plan: 01
subsystem: data-registry
tags: [species-registry, yaml, manifest, cli, data-infrastructure]
dependency_graph:
  requires: []
  provides:
    - species_registry_yaml
    - yaml_backed_species_resolution
    - genome_build_resolution
    - dataset_manifest_loader
    - ag_species_list_cli
  affects:
    - 02-02-organism-validation
    - 02-03-plant-data-tools
tech_stack:
  added:
    - PyYAML (safe_load for species registry and manifest loading)
    - functools.lru_cache (registry and lookup caching)
  patterns:
    - YAML as single source of truth for configuration data
    - lru_cache for module-level singleton registries
    - Lazy imports inside CLI command bodies (matching existing pattern)
    - tmp_path pytest fixture for filesystem tests
key_files:
  created:
    - src/ct/data/species_registry.yaml
    - src/ct/data/manifest.py
    - tests/test_species.py
    - tests/test_manifest.py
  modified:
    - src/ct/tools/_species.py
    - src/ct/cli.py
decisions:
  - YAML common_names entries used for rice subspecies aliases (japonica/indica
    resolve to species-level taxon 4530) rather than a separate subspecies_taxon_ids
    field — simpler, consistent with lookup architecture
  - load_manifest tries yaml first, json as fallback; never raises on missing
    files (locked CONTEXT.md decision: registry is a convenience, not a gatekeeper)
  - species_app added after data_app section in cli.py, before tool_app, following
    existing Typer subcommand pattern exactly
metrics:
  duration: 3 min
  completed: 2026-02-25
  tasks_completed: 2
  files_created: 4
  files_modified: 2
  tests_added: 24
---

# Phase 02 Plan 01: Species Registry and Data Manifest Infrastructure Summary

YAML-backed species registry replacing the in-memory dict, adding genome build metadata, plus a manifest loader convention and `ag species list` CLI command.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | YAML species registry + YAML-backed _species.py + tests | 01a1c23 | species_registry.yaml, _species.py, test_species.py |
| 2 | manifest.py + ag species list CLI command + tests | ffef5e5 | manifest.py, cli.py, test_manifest.py |

## What Was Built

### src/ct/data/species_registry.yaml

The single source of truth for all species resolution. Contains 24 species entries (all from the previous `_PLANT_TAXON_MAP` plus genome build metadata):

- 14 plant species with confirmed genome builds (TAIR10, IRGSP-1.0, etc.)
- 5 less common plants and 5 cross-species reference organisms with empty genome_build (to be populated later)
- Each entry: binomial, taxon_id, common_names (lookup keys), abbreviations (lookup keys), genome_build, optional notes

Rice subspecies (japonica/indica) handled as common_names aliases on the Oryza sativa entry, resolving to taxon 4530.

### src/ct/tools/_species.py (rewritten)

YAML-backed replacement for the in-memory `_PLANT_TAXON_MAP` dict. Key changes:

- `_load_registry()` — reads YAML once via `lru_cache(maxsize=1)`
- `_build_lookup()` — builds normalised lowercase dict, also cached
- All existing public functions (`resolve_species_taxon`, `resolve_species_binomial`, `resolve_species_ensembl_name`) have identical signatures and behaviour
- New: `resolve_species_genome_build(species, default="") -> str`
- New: `list_all_species() -> list[dict]`

### src/ct/data/manifest.py

Lightweight manifest convention for dataset directories:

- `load_manifest(dataset_dir)` — tries `manifest.yaml`, then `manifest.json`; returns `None` if neither exists; never raises
- `manifest_species(manifest)` — extracts `species_covered` list; returns `[]` if key absent
- `manifest_summary(manifest)` — returns 3-line human-readable string (dataset: description / Species: ... / Files: ...)

### src/ct/cli.py

Added `species_app` Typer subcommand following the exact pattern of `data_app` and `tool_app`:

```
ag species list   — displays rich.Table with Binomial Name, Taxon ID, Common Names, Genome Build
```

Lazy import of `list_all_species` inside the command function body (consistent with project pattern).

## Test Coverage

24 tests added across 2 files, all passing:

- `tests/test_species.py` (11 tests): taxon resolution by common name, abbreviation, binomial; numeric passthrough; unknown-species fallback; genome build resolution; `list_all_species` structure; rice subspecies alias
- `tests/test_manifest.py` (13 tests): YAML load, JSON fallback, YAML preferred over JSON, missing file returns None, nonexistent directory returns None, species extraction, empty/missing species key, summary formatting, string-file list, CLI `ag species list` exit code and output content

## Verification

```
$ python -c "from ct.tools._species import resolve_species_taxon, resolve_species_genome_build, list_all_species; print(resolve_species_taxon('rice'), resolve_species_genome_build('arabidopsis'), len(list_all_species()))"
4530 TAIR10 24

$ python -c "from ct.data.manifest import load_manifest; print(load_manifest('/nonexistent') is None)"
True
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed:
- src/ct/data/species_registry.yaml: EXISTS
- src/ct/tools/_species.py: EXISTS (rewritten)
- src/ct/data/manifest.py: EXISTS
- src/ct/cli.py: EXISTS (modified, species_app added)
- tests/test_species.py: EXISTS
- tests/test_manifest.py: EXISTS

Commits confirmed:
- 01a1c23 feat(02-01): YAML-backed species registry and rewritten _species.py
- ffef5e5 feat(02-01): manifest loader, ag species list CLI command, and tests
