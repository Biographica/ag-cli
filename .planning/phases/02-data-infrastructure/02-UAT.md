---
status: diagnosed
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
  root_cause: "genome_build field is a single string per species with no documentation that it represents the primary reference build, not an exhaustive inventory. No acknowledgment of pangenomes or multi-assembly reality."
  artifacts:
    - path: "src/ct/data/species_registry.yaml"
      issue: "Schema comment lacks clarification that genome_build is primary reference build only"
    - path: "src/ct/tools/_species.py"
      issue: "resolve_species_genome_build docstring does not clarify it returns primary reference build"
  missing:
    - "Update YAML schema comment to note genome_build is primary reference assembly for API calls"
    - "Add docstring clarification to resolve_species_genome_build"
    - "Add note about pangenome support as future extension"

- truth: "Unknown species resolution returns a meaningful unknown indicator rather than defaulting to Arabidopsis"
  status: failed
  reason: "User reported: default taxon should not be arabidopsis — an unknown species should return unknown, not silently assume arabidopsis. otherwise the agent could assume a random plant is arabidopsis"
  severity: major
  test: 4
  root_cause: "_DEFAULT_TAXON=3702 and _DEFAULT_BINOMIAL='Arabidopsis thaliana' cause all unknown species to silently resolve as Arabidopsis. Callers cannot distinguish 'user passed Arabidopsis' from 'species was unknown'. Defaults should be 0/empty string."
  artifacts:
    - path: "src/ct/tools/_species.py"
      issue: "_DEFAULT_TAXON=3702 and _DEFAULT_BINOMIAL='Arabidopsis thaliana' silently assume Arabidopsis for unknowns"
    - path: "tests/test_species.py"
      issue: "test_resolve_species_taxon_unknown_returns_default asserts 3702, needs to assert 0"
    - path: "src/ct/tools/parity.py"
      issue: "_normalize_mygene_species coerces None/empty to 'arabidopsis thaliana' — same anti-pattern"
  missing:
    - "Change _DEFAULT_TAXON to 0 and _DEFAULT_BINOMIAL to empty string"
    - "Change resolve_species_ensembl_name default from 'arabidopsis_thaliana' to empty string"
    - "Update tests to expect 0/empty for unknown species"
    - "Add guards in callers (network.py, protein.py, data_api.py) to handle 0 taxon gracefully"
    - "Fix parity.py _normalize_mygene_species to not coerce empty to Arabidopsis"
