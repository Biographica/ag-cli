---
phase: 04-plant-genomics-tools
plan: "02"
subsystem: genomics
tags: [ensembl-compara, ortholog-mapping, phylogenetic-distance, plant-genomics, python]

# Dependency graph
requires:
  - phase: 04-01
    provides: gene_annotation and gwas_qtl_lookup tools, _api_cache, _species, http_client interfaces
provides:
  - genomics.ortholog_map tool with Ensembl Compara (compara=plants) integration
  - _PHYLO_DISTANCES_MYA distance matrix covering all 19 registry plant species
  - _phylo_weight() function returning 0-1 evolutionary closeness score
  - Unit tests: TestOrthologMap (6 tests) + 3 standalone weight/registration tests
affects:
  - 04-03 (GFF3 parsing — uses same genomics module; may add further tools)
  - agent workflow (ortholog_map enables cross-species gene function transfer)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy imports inside tool function body for all external dependencies"
    - "compara=plants parameter mandatory for all Ensembl Compara API calls (never vertebrates default)"
    - "Module-level constant dict (frozenset keys) for O(1) phylogenetic distance lookup"
    - "Weight formula: 1/(1+dist_mya/100), 200 Mya default for unknown pairs"

key-files:
  created: []
  modified:
    - src/ct/tools/genomics.py
    - tests/test_genomics_plant.py

key-decisions:
  - "frozenset keys in _PHYLO_DISTANCES_MYA — symmetric pairs stored once, O(1) lookup"
  - "200 Mya default for unknown taxon pairs — conservative (distant) estimate avoids false high weights"
  - "compara=plants hardcoded in params dict not as argument default — prevents caller from accidentally omitting it"
  - "Sort orthologs by phylo_weight desc then percent_identity desc — prioritises evolutionary closeness, breaks ties by sequence similarity"

patterns-established:
  - "Phylogenetic weight encoding: _phylo_weight(taxon_a, taxon_b) with frozenset key lookup"
  - "Test mock pattern for multi-call resolve_species_taxon: use side_effect=[source_taxon, target_taxon]"

requirements-completed: [TOOL-02]

# Metrics
duration: 5min
completed: 2026-02-28
---

# Phase 04 Plan 02: Ortholog Map Summary

**genomics.ortholog_map tool using Ensembl Compara (compara=plants) with curated 19-species phylogenetic distance matrix and 0-1 weight scoring**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-28T13:53:09Z
- **Completed:** 2026-02-28T13:58:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `_PHYLO_DISTANCES_MYA` — 60-entry frozenset-keyed dict covering all key pairs among 19 registry plant species, with 200 Mya default for unknown pairs
- Added `_phylo_weight()` — returns 0-1 closeness score using `1/(1+dist/100)` formula; same-species returns 1.0
- Added `genomics.ortholog_map` — full Ensembl Compara workflow: species validation, gene symbol lookup, ortholog query with `compara=plants`, phylo weight application, disk caching
- Added 9 tests covering all paths: success, compara param assertion, empty response, target_species filter, unknown species guard, cache hit, weight correctness, unknown pair default, tool registration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add phylogenetic distance matrix and ortholog_map tool** - `7d2ec27` (feat)
2. **Task 2: Write unit tests for ortholog_map** - `4811a1a` (test)

## Files Created/Modified
- `src/ct/tools/genomics.py` - Added _PHYLO_DISTANCES_MYA, _phylo_weight(), and genomics.ortholog_map tool (236 lines)
- `tests/test_genomics_plant.py` - Added TestOrthologMap (6 tests) and 3 standalone tests (216 lines)

## Decisions Made
- `frozenset` keys in `_PHYLO_DISTANCES_MYA` — symmetric pairs stored once, O(1) lookup without ordering logic in caller
- 200 Mya default for unknown taxon pairs — conservative estimate avoids false high weights for distant/uncatalogued pairs
- `compara=plants` hardcoded in params dict not as a parameter default — prevents callers from accidentally omitting it; critical correctness requirement
- Sort orthologs by `phylo_weight` descending then `percent_identity` descending — evolutionary closeness ranks first, sequence similarity breaks ties

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. Pre-existing failures exist in unrelated test files (test_mention_completer.py, test_omics.py, test_sandbox.py, test_shell.py, test_terminal.py — 57 total). These are out-of-scope; all 22 tests in test_genomics_plant.py pass and no regressions were introduced.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ortholog mapping complete — agent can now map query genes to plant orthologs and rank by evolutionary closeness
- Ready for Phase 04-03: GFF3 parsing tools (genomics.gff3_features tool)
- All three ortholog tool truths satisfied: compara=plants enforced, phylo distance matrix covers registry species, empty list returned when no orthologs found

---
*Phase: 04-plant-genomics-tools*
*Completed: 2026-02-28*
