---
phase: 04-plant-genomics-tools
plan: 01
subsystem: genomics-tools
tags: [genomics, ensembl-plants, uniprot, gene-annotation, gwas-qtl, caching, species-validation, gffutils]
dependency_graph:
  requires: []
  provides: [genomics.gene_annotation, genomics.gwas_qtl_lookup, gffutils-dependency]
  affects: [src/ct/tools/genomics.py, pyproject.toml, tests/test_genomics_plant.py]
tech_stack:
  added: [gffutils>=0.13]
  patterns: [lazy-imports, source-module-mocking, disk-ttl-cache, force-escape-hatch, species-validation]
key_files:
  created: [tests/test_genomics_plant.py]
  modified: [src/ct/tools/genomics.py, pyproject.toml]
decisions:
  - Import functions directly from genomics module in tests (not via registry.get_tool().fn) — Tool object uses .function attribute not .fn; direct import is cleaner and consistent with Phase 3 pattern of calling tool.run()
  - Lazy imports inside function body for _species, _api_cache, http_client — matches existing pattern; allows source-module-level mocking in tests
metrics:
  duration_minutes: 6
  tasks_completed: 2
  files_created: 1
  files_modified: 2
  tests_added: 13
  completed_date: "2026-02-28"
---

# Phase 4 Plan 01: Gene Annotation + GWAS/QTL Lookup Summary

**One-liner:** Gene annotation (GO terms, UniProt function, PubMed IDs via Ensembl Plants+UniProt) and GWAS/QTL phenotype lookup (Ensembl Plants phenotype endpoint with trait filtering) added to genomics module, plus gffutils>=0.13 core dependency for Phase 4 GFF3 parsing.

## What Was Built

### Tool 1: `genomics.gene_annotation`

Added to `src/ct/tools/genomics.py` (appended after existing `variant_classify` function):

- **Step 1:** Ensembl Plants REST API gene symbol lookup (`/lookup/symbol/{species}/{gene}`) — extracts Ensembl ID, biotype, location, description
- **Step 2:** Ensembl cross-reference lookup for GO terms (`/xrefs/id/{ensembl_id}?external_db=GO`) — deduplicates by GO ID
- **Step 3:** UniProt REST API search for protein-level GO terms, PubMed IDs, and function description
- Species validation via `resolve_species_taxon` / `resolve_species_binomial` from `_species.py`; `force=True` escape hatch allows bypassing registry for novel species
- 24h disk cache via `_api_cache.get_cached` / `set_cached` under namespace `"ensembl_gene"`
- Returns: `ensembl_id`, `display_name`, `species`, `go_terms`, `function_description`, `pubmed_ids`, `pubmed_count`, `location`, `biotype`

### Tool 2: `genomics.gwas_qtl_lookup`

Added to `src/ct/tools/genomics.py`:

- **Step 1:** Best-effort gene symbol to Ensembl ID resolution (non-fatal — phenotype endpoint accepts gene symbols)
- **Step 2:** Ensembl Plants phenotype endpoint (`/phenotype/gene/{species}/{gene}`)
- **Step 3:** Optional trait keyword filtering (case-insensitive substring match); sorts entries with PubMed evidence first
- Species-aware empty-result suggestions: non-Arabidopsis species get cross-species suggestion (try Arabidopsis ortholog); Arabidopsis gets general GWAS sparsity note
- 24h disk cache under namespace `"ensembl_phenotype"`
- Returns: `phenotype_count`, `phenotypes` list, `suggestion`, `trait_filter`

### Dependency: `gffutils>=0.13`

Added to `pyproject.toml` core `[project] dependencies` list (after `pyyaml>=6.0`) for GFF3 parsing in Phase 4 plan 03.

### Tests: `tests/test_genomics_plant.py`

13 tests in 3 classes:
- `TestGeneAnnotation` (6): arabidopsis success, unknown species, force override, pubmed IDs, cache hit, Ensembl lookup failure
- `TestGwasQtlLookup` (6): success, trait filter, empty non-Arabidopsis (cross-species suggestion), empty Arabidopsis (sparsity message), unknown species, cache hit
- `test_all_tools_registered` (1): both tools in registry with category "genomics"; "genomics" in PLANT_SCIENCE_CATEGORIES

All mocks at source module level per Phase 3 convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tool object attribute name corrected in tests**
- **Found during:** Task 2 — initial test run
- **Issue:** Tests called `registry.get_tool(...).fn` but the Tool dataclass uses `.function` attribute, not `.fn`
- **Fix:** Switched tests to import functions directly from `ct.tools.genomics` module (`_genomics_module.gene_annotation`, `_genomics_module.gwas_qtl_lookup`) — cleaner pattern consistent with Phase 3 approach of calling tool functions directly in tests
- **Files modified:** `tests/test_genomics_plant.py`
- **Commit:** 2bcb0cf

## Commits

| Hash    | Message |
|---------|---------|
| 9a29031 | feat(04-01): add gene_annotation and gwas_qtl_lookup tools; add gffutils dependency |
| 2bcb0cf | test(04-01): add unit tests for gene_annotation and gwas_qtl_lookup |

## Self-Check: PASSED

- `src/ct/tools/genomics.py` — modified, tools appended
- `pyproject.toml` — gffutils>=0.13 present
- `tests/test_genomics_plant.py` — created, 13 tests
- Commit 9a29031 — exists
- Commit 2bcb0cf — exists
- All 13 tests pass; no regressions in previously passing tests
