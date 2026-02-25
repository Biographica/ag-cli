---
phase: 02-data-infrastructure
plan: 04
subsystem: species
tags: [species-resolution, gap-closure, uat, error-handling]

# Dependency graph
requires:
  - phase: 02-data-infrastructure
    provides: YAML-backed species registry and _species.py resolution module
provides:
  - "Unknown species input returns taxon 0 and empty binomial instead of silent Arabidopsis fallback"
  - "network.ppi_analysis, protein.function_predict, protein.domain_annotate return clear error dicts for unrecognised species"
  - "parity.py _normalize_mygene_species no longer silently assumes Arabidopsis for empty species"
  - "genome_build YAML schema comment and docstring document the single-primary-assembly limitation"
affects:
  - 03-agent-tools
  - 04-analytics
  - 05-crispr

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sentinel pattern: 0 / empty string as unknown-species markers rather than a default species"
    - "Guard pattern: if species_taxon == 0: return error dict immediately in all API-calling tools"

key-files:
  created: []
  modified:
    - src/ct/tools/_species.py
    - src/ct/data/species_registry.yaml
    - src/ct/tools/parity.py
    - src/ct/tools/network.py
    - src/ct/tools/protein.py
    - tests/test_species.py

key-decisions:
  - "Sentinel 0 / '' chosen for unknown species rather than raising an exception — allows callers to decide error handling strategy"
  - "Guards added at API call entry points (network.py, protein.py) rather than inside _species.py — keeps resolution module simple, puts error messaging close to the failing API call"
  - "parity.py empty species passes through as '' to MyGene API rather than defaulting — lets the API surface its own error or return cross-species results"

patterns-established:
  - "Sentinel pattern: all species resolution functions return 0 / '' to indicate unknown — never a plausible default species"
  - "Caller guard: tools that call external APIs check species_taxon == 0 immediately after resolution and return a user-readable error dict with 'ag species list' hint"

requirements-completed: [DATA-02]

# Metrics
duration: 1min
completed: 2026-02-25
---

# Phase 2 Plan 4: Unknown-Species Default Fix Summary

**Silent Arabidopsis fallback replaced with explicit 0 / '' sentinels plus caller-level error guards in network.py and protein.py — all 46 tests pass**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-25T21:42:12Z
- **Completed:** 2026-02-25T21:43:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `_DEFAULT_TAXON` changed from 3702 to 0; `_DEFAULT_BINOMIAL` changed from "Arabidopsis thaliana" to "" — unknown species no longer silently masquerade as Arabidopsis
- `network.ppi_analysis`, `protein.function_predict`, and `protein.domain_annotate` now return error dicts immediately when `species_taxon == 0`, preventing invalid STRING/UniProt/InterPro queries
- `parity.py _normalize_mygene_species` no longer coerces empty/None species input to "arabidopsis thaliana"
- `resolve_species_genome_build` docstring and `species_registry.yaml` schema comment both document that `genome_build` is the primary reference assembly only (single string per species, not a pangenome enumeration)
- `test_resolve_species_taxon_unknown_returns_default` updated to assert `0` instead of `3702`
- All 46 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _species.py defaults and add genome_build documentation** - `9a81b82` (fix)
2. **Task 2: Fix callers, parity.py, and update test assertion** - `55cdd98` (fix)

## Files Created/Modified
- `src/ct/tools/_species.py` - Changed sentinels to 0/"", updated docstrings, fixed ensembl_name default
- `src/ct/data/species_registry.yaml` - Updated schema comment for genome_build single-assembly limitation
- `src/ct/tools/parity.py` - _normalize_mygene_species no longer defaults empty species to arabidopsis thaliana
- `src/ct/tools/network.py` - ppi_analysis guards against species_taxon == 0
- `src/ct/tools/protein.py` - function_predict and domain_annotate guard against species_taxon == 0
- `tests/test_species.py` - Updated unknown-species test to assert 0; updated rice subspecies comment

## Decisions Made
- Sentinel values (0 / '') chosen over raising exceptions — maintains backward compatibility with callers that pass species through and simplifies error routing
- Guards placed at API entry points rather than inside `_species.py` — resolution stays simple, error messages are context-aware (STRING vs UniProt vs InterPro)
- `parity.py` passes "" through to MyGene rather than substituting a taxon ID — lets the API return cross-species results or surface its own error rather than silently narrowing scope

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- UAT gaps 1 and 2 from Phase 02 are now closed
- Phase 03 (agent tools) can build on the corrected species-resolution contract with confidence that unknown species will surface errors rather than producing plausible-looking Arabidopsis results

---
*Phase: 02-data-infrastructure*
*Completed: 2026-02-25*
