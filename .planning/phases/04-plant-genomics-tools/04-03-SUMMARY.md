---
phase: 04-plant-genomics-tools
plan: 03
subsystem: genomics
tags: [gffutils, gff3, ensembl-plants, atted-ii, coexpression, pandas, gzip]

# Dependency graph
requires:
  - phase: 04-02
    provides: ortholog_map tool and phylogenetic distance matrix in genomics.py
provides:
  - genomics.gff_parse tool: GFF3 parsing with gffutils, local/auto-download, exon/intron/UTR extraction
  - genomics.coexpression_network tool: ATTED-II co-expression data with MR scores and cluster membership
  - tests/fixtures/FLC_mini.gff3: minimal 2-exon test fixture
  - TestGffParse: 6 unit tests covering all gff_parse paths
  - TestCoexpressionNetwork: 6 unit tests covering all coexpression_network paths
affects: [05-crispr-tools, phase-04-integration]

# Tech tracking
tech-stack:
  added: [gffutils (already in pyproject.toml since 04-01), pandas (existing dep)]
  patterns:
    - Lazy gffutils import inside function body (consistent with lazy import convention)
    - gffutils .db file cached alongside .gff3 file (db_path = gff_local.with_suffix(".db"))
    - Gene lookup with ID -> gene:ID prefix -> Name attribute fallback chain
    - ATTED-II flat file cached in _CACHE_BASE/atted/{species}_coexp.tsv
    - Graceful download fallback with fallback=True flag in result dict
    - Module-level _ATTED_DOWNLOAD_URLS dict for configurable download URLs

key-files:
  created:
    - tests/fixtures/FLC_mini.gff3
  modified:
    - src/ct/tools/genomics.py
    - tests/test_genomics_plant.py
    - .gitignore

key-decisions:
  - "gff_parse uses gene: prefix retry before Name attribute scan — Ensembl GFF3 IDs have gene: prefix, raw locus code lookup fails without it"
  - "_ATTED_DOWNLOAD_URLS module-level dict allows URL updates without touching function code — ATTED-II URLs are known to change between versions"
  - "TestGffParse test_auto_download patches _CACHE_BASE with tmp_path to avoid real disk writes during test"
  - "*.db added to .gitignore — gffutils SQLite databases are generated caches that should not be version-controlled"
  - "TestGffParse has 6 tests (not 5 as in plan spec) — added test_unknown_species to match coexpression parity and improve coverage"

patterns-established:
  - "Bulk flat-file tools: download-once to _CACHE_BASE/{tool}/{species}_data.tsv, parse with pandas on each call"
  - "Species validation gate: taxon_id == 0 and not force -> return error dict immediately"
  - "Test fixture in tests/fixtures/ for file-based parsing tools — avoids network calls in tests"

requirements-completed: [TOOL-03, TOOL-04]

# Metrics
duration: 20min
completed: 2026-02-28
---

# Phase 04 Plan 03: GFF3 Parsing and Co-Expression Network Tools Summary

**GFF3 genome annotation parser (gffutils + Ensembl Plants FTP auto-download) and ATTED-II co-expression network tool added to genomics.py, completing the Phase 4 genomics tool suite**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-28T14:00:00Z
- **Completed:** 2026-02-28T14:20:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `genomics.gff_parse`: parses GFF3 files with gffutils, supports local files and Ensembl Plants FTP auto-download, extracts exons/UTRs/introns, ID->gene:ID->Name attribute fallback chain, .db file cached alongside .gff3 for fast subsequent calls
- `genomics.coexpression_network`: queries ATTED-II bulk flat-file co-expression data, returns top partners with MR scores and cluster membership, handles download failures gracefully with clear fallback messaging
- `tests/fixtures/FLC_mini.gff3`: minimal 2-exon GFF3 fixture (FLC gene with 5' UTR, 2 exons, intronic gap, 3' UTR) — enables GFF3 parsing tests without network calls
- 12 new unit tests across TestGffParse (6) and TestCoexpressionNetwork (6) — all pass; 34 total genomics tests pass
- `test_all_tools_registered` updated to verify all 5 Phase 4 tools registered

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GFF3 test fixture and add gff_parse and coexpression_network tools** - `4f4dced` (feat)
2. **Task 2: Write unit tests for gff_parse and coexpression_network** - `680f870` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/ct/tools/genomics.py` - Added gff_parse and coexpression_network tools (~360 lines)
- `tests/fixtures/FLC_mini.gff3` - Minimal 2-exon GFF3 fixture for FLC (AT5G10140)
- `tests/test_genomics_plant.py` - Appended TestGffParse (6 tests), TestCoexpressionNetwork (6 tests), updated test_all_tools_registered
- `.gitignore` - Added *.db to exclude gffutils SQLite cache files

## Decisions Made
- `gene: prefix retry before Name attribute scan` — Ensembl GFF3 stores gene IDs as `gene:AT5G10140` not bare `AT5G10140`; the retry chain handles both formats transparently
- `_ATTED_DOWNLOAD_URLS` as module-level dict — ATTED-II URLs are documented as unstable between versions; centralising them makes URL updates easy
- `*.db` added to `.gitignore` — gffutils SQLite databases are generated caches, not source files; the smoke test created one in tests/fixtures/ which prompted this fix
- TestGffParse gets 6 tests (added `test_unknown_species`) for parity with TestCoexpressionNetwork and improved coverage

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added *.db to .gitignore**
- **Found during:** Task 1 smoke test
- **Issue:** Running `gff_parse` with the test fixture created `tests/fixtures/FLC_mini.db` which git tracked as untracked file
- **Fix:** Added `*.db` entry to `.gitignore`
- **Files modified:** `.gitignore`
- **Verification:** `git status` no longer shows `FLC_mini.db` as untracked
- **Committed in:** `4f4dced` (Task 1 commit)

**2. [Rule 1 - Bug / Plan addition] Added test_unknown_species to TestGffParse**
- **Found during:** Task 2 (writing tests)
- **Issue:** Plan spec listed 5 tests for TestGffParse but test_unknown_species wasn't listed despite species validation being implemented and the same test existing for TestCoexpressionNetwork
- **Fix:** Added test_unknown_species as a 6th test (matches coexpression parity)
- **Files modified:** `tests/test_genomics_plant.py`
- **Verification:** Test passes; validates species guard returns error dict correctly

---

**Total deviations:** 2 (1 missing gitignore entry fixed, 1 additional test added for coverage parity)
**Impact on plan:** Both additions improve correctness and hygiene. No scope creep.

## Issues Encountered
None — both tools implemented cleanly on first pass. ATTED-II URL handling implemented as specified; the fallback path was tested via the download_fallback test rather than a real network call.

## User Setup Required
None - no external service configuration required. ATTED-II data downloads automatically on first use; GFF3 files download from Ensembl Plants FTP. Both tools function with fallback messaging if downloads fail.

## Next Phase Readiness
- Phase 4 genomics tool suite complete: gene_annotation, gwas_qtl_lookup, ortholog_map, gff_parse, coexpression_network all registered and tested
- `gff_parse` provides the exon boundary data required for Phase 5 CRISPR guide design
- `coexpression_network` provides pathway context for the shortlisting pipeline
- All 5 Phase 4 tools are registered under `genomics` category in the plant allowlist

---
*Phase: 04-plant-genomics-tools*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: src/ct/tools/genomics.py
- FOUND: tests/fixtures/FLC_mini.gff3
- FOUND: tests/test_genomics_plant.py
- FOUND: .planning/phases/04-plant-genomics-tools/04-03-SUMMARY.md
- FOUND commit: 4f4dced (Task 1)
- FOUND commit: 680f870 (Task 2)
