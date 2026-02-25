---
status: complete
phase: 02-data-infrastructure
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-02-25T12:00:00Z
updated: 2026-02-25T12:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. ag species list CLI command
expected: Run `ag species list` (or `python -m ct.cli species list`). A formatted table appears with columns: Binomial Name, Taxon ID, Common Names, Genome Build. Arabidopsis thaliana, Oryza sativa, Zea mays, and other species should be visible.
result: pass

### 2. Species resolution by common name
expected: Run `python -c "from ct.tools._species import resolve_species_binomial; print(resolve_species_binomial('rice'))"`. Should print "Oryza sativa". Run with 'barley' — should print "Hordeum vulgare".
result: pass

### 3. Genome build resolution
expected: Run `python -c "from ct.tools._species import resolve_species_genome_build; print(resolve_species_genome_build('arabidopsis'))"`. Should print "TAIR10". Run with 'rice' — should print "IRGSP-1.0".
result: issue
reported: "genome_build assumes a single fixed build per species — poor assumption for a field with multiple genome builds per species, pan-genomes, and custom assemblies. Should clarify use cases and note pangenome support as desirable"
severity: minor

### 4. Unknown species returns default (never errors)
expected: Run `python -c "from ct.tools._species import resolve_species_taxon; print(resolve_species_taxon('unknown_plant'))"`. Should print "3702" (the default Arabidopsis taxon). No error, no traceback.
result: issue
reported: "default taxon should not be arabidopsis — an unknown species should return unknown, not silently assume arabidopsis. otherwise the agent could assume a random plant is arabidopsis"
severity: major

### 5. data.list_datasets tool visible to agent
expected: Run `python -c "from ct.tools import ensure_loaded, registry; ensure_loaded(); print([t.name for t in registry.list_tools('data')])"`. Should show `['data.list_datasets', 'data.load_expression']` — both tools registered in the 'data' category.
result: pass

### 6. data.list_datasets on empty/missing directory
expected: Run `python -c "from ct.tools.plant_data import list_datasets; r = list_datasets(data_root='/tmp/nonexistent'); print(r['summary'])"`. Should print a message about no data directory found, suggesting `ag data pull`. No crash, no traceback.
result: pass

### 7. Full test suite passes
expected: Run `python -m pytest tests/test_species.py tests/test_manifest.py tests/test_validation.py tests/test_plant_data.py -v`. All 46 tests should pass with no failures or errors.
result: pass

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Genome build resolution returns a single build per species"
  status: failed
  reason: "User reported: genome_build assumes a single fixed build per species — poor assumption for a field with multiple genome builds per species, pan-genomes, and custom assemblies. Should clarify use cases and note pangenome support as desirable"
  severity: minor
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Unknown species resolution returns a meaningful unknown indicator rather than defaulting to Arabidopsis"
  status: failed
  reason: "User reported: default taxon should not be arabidopsis — an unknown species should return unknown, not silently assume arabidopsis. otherwise the agent could assume a random plant is arabidopsis"
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
