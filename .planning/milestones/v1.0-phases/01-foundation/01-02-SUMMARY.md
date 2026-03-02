---
phase: 01-foundation
plan: 02
subsystem: cli
tags: [typer, ncbi-taxon, species-resolution, branding, ascii-art, plant-science]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: PLANT_SCIENCE_CATEGORIES allowlist, Harvest agent identity, filtered tool registry

provides:
  - Interim species resolution helper (_species.py) with 20+ plant species mapped to NCBI taxon IDs
  - All surviving-category tools accept optional species parameter defaulting to Arabidopsis thaliana
  - CLI rebranded to ag-cli/ag with Harvest visual identity and plant science help text
  - ag entry point registered in pyproject.toml

affects:
  - All future plans that add new tools (must use species parameter pattern)
  - Integration testing (ag command is the CLI entry point)
  - Data layer plans (species-aware API calls established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Species resolution via lazy import: from ct.tools._species import resolve_species_taxon inside function body"
    - "_PLANT_TAXON_MAP dict maps lowercase keys to (taxon_id, canonical_binomial) tuples"
    - "Tool species parameter: species: str = 'Arabidopsis thaliana' before **kwargs"
    - "ag entry point maps to ct.cli:entry (package namespace unchanged)"

key-files:
  created:
    - src/ct/tools/_species.py
  modified:
    - pyproject.toml
    - src/ct/__init__.py
    - src/ct/cli.py
    - src/ct/ui/terminal.py
    - src/ct/ui/suggestions.py
    - src/ct/agent/doctor.py
    - src/ct/tools/network.py
    - src/ct/tools/data_api.py
    - src/ct/tools/protein.py
    - src/ct/tools/parity.py
    - tests/test_cli.py

key-decisions:
  - "Arabidopsis thaliana (3702) chosen as default species across all tools — it is the model plant organism, analogous to how the original tools defaulted to human"
  - "genomics.py coloc function left with homo_sapiens reference — Open Targets Platform is human-only API, not a surviving-category species issue"
  - "ct Python package namespace retained unchanged — only the installed CLI command name changes to ag via pyproject.toml scripts"
  - "resolve_species_binomial returns exact stored casing (e.g. 'Oryza sativa') not .title() — avoids breaking Ensembl URL construction"
  - "MyGene.info plant species use numeric taxon ID strings ('3702') not named strings — API only supports named strings for human/mouse"

patterns-established:
  - "Species resolution pattern: lazy import resolve_species_taxon inside tool body, default='Arabidopsis thaliana'"
  - "Interim helper prefix: _species.py uses underscore prefix indicating it is a shared internal module"
  - "Branding separation: CLI user-facing strings use Harvest/ag; Python imports use ct namespace throughout"

requirements-completed:
  - FOUN-03
  - FOUN-04

# Metrics
duration: 60min
completed: 2026-02-25
---

# Phase 01 Plan 02: Species Resolution and CLI Rebrand Summary

**Species-agnostic tool layer via _PLANT_TAXON_MAP (20+ plant species) and CLI rebranded to ag-cli/ag with HARVEST ASCII identity and plant science help text**

## Performance

- **Duration:** ~60 min (continued from prior session)
- **Started:** 2026-02-25T12:00:00Z
- **Completed:** 2026-02-25T14:27:55Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Created `src/ct/tools/_species.py` with `_PLANT_TAXON_MAP` covering 20+ plant species (plus human/mouse for cross-species interoperability), `resolve_species_taxon()`, `resolve_species_binomial()`, and `resolve_species_ensembl_name()` functions
- Updated 4 tool files (network.py, data_api.py, protein.py, parity.py) to accept `species: str = "Arabidopsis thaliana"` and call species helpers instead of hardcoding 9606/human
- Rebranded CLI: pyproject.toml `name="ag-cli"` with `ag = "ct.cli:entry"`, HARVEST ASCII art banner, plant science help text and subcommand descriptions, doctor.py table title, 200+ plant science interactive suggestions replacing pharma/drug-discovery set

## Task Commits

Each task was committed atomically:

1. **Task 1: Create species resolution helper and add species parameter to surviving tools** - `5c19cbe` (feat)
2. **Task 2: Rebrand CLI from celltype-cli/ct to ag-cli/ag** - `141d132` (feat)

## Files Created/Modified

- `src/ct/tools/_species.py` - Interim species resolution helper with _PLANT_TAXON_MAP and three public resolve_ functions
- `src/ct/tools/network.py` - Added species param to ppi_analysis; replaced 3x hardcoded 9606 with resolve_species_taxon
- `src/ct/tools/data_api.py` - Added species param to ensembl_lookup (uses resolve_species_ensembl_name) and uniprot_lookup (uses resolve_species_taxon); expanded organism_ids map
- `src/ct/tools/protein.py` - Added species param to function_predict and domain_annotate; replaced organism_id:9606 with species_taxon
- `src/ct/tools/parity.py` - Expanded _MYGENE_SPECIES_MAP with plant taxon ID strings; updated mygene_lookup default to Arabidopsis thaliana
- `pyproject.toml` - name=ag-cli, version=0.1.0, description and authors updated, scripts.ag entry point added
- `src/ct/__init__.py` - Module docstring updated to ag-cli plant science description
- `src/ct/cli.py` - HARVEST ASCII banner, ag prog_name, plant science help text throughout, Harvest panel titles
- `src/ct/ui/terminal.py` - Dataset candidates updated (gramene, plaza, bar added), session export header updated
- `src/ct/ui/suggestions.py` - Complete replacement: 200+ plant science queries across 16 topic categories
- `src/ct/agent/doctor.py` - Table title ag Doctor, command references updated ct->ag
- `tests/test_cli.py` - Updated 3 tests: prog_name assertions and sys.argv examples use ag not ct, ag Doctor assertion

## Decisions Made

- **Arabidopsis thaliana as default:** Chosen as the model plant (NCBI 3702) to replace human (9606) as the default across all tools. Consistent with how the original tools used human as the reference organism.
- **genomics.py coloc scoped out:** The inner `_resolve_ensembl_id` function calls Open Targets Platform API which is human-only. Left `homo_sapiens` unchanged by design — it reflects API capability, not a tool default that can be parameterized.
- **ct namespace unchanged:** The Python package directory stays `src/ct/` and all imports remain `from ct.xxx`. Only the installed CLI script name changes from `ct` to `ag` via pyproject.toml.
- **No .title() on binomials:** The initial implementation used `.title()` on canonical binomial names which produced wrong casing (e.g., "Arabidopsis Thaliana" instead of "Arabidopsis thaliana"). Removed .title() to preserve stored casing for API URL compatibility.
- **MyGene.info plant species:** MyGene.info API accepts named strings ("human", "mouse") for model organisms but requires numeric taxon IDs for plants. The _MYGENE_SPECIES_MAP returns string taxon IDs ("3702") for plant species.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed .title() on resolve_species_binomial returning wrong casing**
- **Found during:** Task 2 (verification run)
- **Issue:** `resolve_species_binomial('at')` returned `'Arabidopsis Thaliana'` (Title Case) instead of `'Arabidopsis thaliana'` (standard binomial casing). This would have broken Ensembl URL construction via `resolve_species_ensembl_name` which calls `resolve_species_binomial` then lowercases.
- **Fix:** Removed `.title()` call from both lookup paths in `resolve_species_binomial`. The map stores canonical casing; return it directly.
- **Files modified:** `src/ct/tools/_species.py`
- **Verification:** `resolve_species_binomial('at') == 'Arabidopsis thaliana'`, `resolve_species_ensembl_name('at') == 'arabidopsis_thaliana'` both pass
- **Committed in:** `141d132` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed 3 tests asserting prog_name="ct" after entry() was updated to "ag"**
- **Found during:** Task 2 (pytest run)
- **Issue:** `test_entry_routes_plain_invocation_to_hidden_run`, `test_entry_preserves_explicit_subcommand`, `test_entry_preserves_trace_subcommand` all checked `called["prog_name"] == "ct"` and used `sys.argv = ["ct", ...]`. After updating `entry()` to pass `prog_name="ag"`, these tests failed.
- **Fix:** Updated all three tests to check `called["prog_name"] == "ag"` and use `sys.argv = ["ag", ...]`.
- **Files modified:** `tests/test_cli.py`
- **Verification:** All 3 tests pass
- **Committed in:** `141d132` (Task 2 commit)

**3. [Rule 1 - Bug] Fixed test_doctor_subcommand_not_treated_as_query asserting "ct Doctor"**
- **Found during:** Task 2 (pytest run)
- **Issue:** Test checked for `"ct Doctor"` in stdout. After updating doctor.py table title to `"ag Doctor"`, the test assertion was stale.
- **Fix:** Updated test assertion to `assert "ag Doctor" in result.stdout`.
- **Files modified:** `tests/test_cli.py`
- **Verification:** Test passes
- **Committed in:** `141d132` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All auto-fixes were necessary for correctness. The .title() bug would have silently broken Ensembl URL construction. The test fixes were direct consequences of the CLI rebrand. No scope creep.

## Issues Encountered

- **Pre-existing test failures (not caused by this plan):** `test_trace_diagnose_command_outputs_summary`, `test_trace_diagnose_strict_exits_on_unclosed_query`, `test_trace_export_creates_bundle` all fail with `NameError: name 'TraceLogger' is not defined` — TraceLogger is not imported in the test file. Verified as pre-existing via `git stash` before our changes. Additionally, 5 `test_release_check_*` tests fail with `ModuleNotFoundError: No module named 'ct.agent.trace'` — also pre-existing. These are tracked as deferred items.
- **genomics.py coloc function:** Had a `homo_sapiens` reference in the inner `_resolve_ensembl_id` helper that queries Open Targets Platform API (human-only). Left unchanged by design — it is not a species default that can be parameterized, it is an API constraint.

## User Setup Required

None - no external service configuration required. Run `pip install -e .` after pulling to register the `ag` entry point.

## Next Phase Readiness

- Species resolution helper ready for all new tool implementations
- ag entry point registered and tested: `ag --version` returns `ag v0.1.0`
- All surviving-category tools are species-agnostic with Arabidopsis thaliana defaults
- CLI Harvest identity established — ready for data layer and tool expansion phases

## Self-Check: PASSED

- FOUND: `src/ct/tools/_species.py`
- FOUND: `pyproject.toml`
- FOUND: `src/ct/cli.py`
- FOUND: `.planning/phases/01-foundation/01-02-SUMMARY.md`
- FOUND: commit `141d132` (Task 2 - CLI rebrand)
- FOUND: commit `5c19cbe` (Task 1 - species helper)

---
*Phase: 01-foundation*
*Completed: 2026-02-25*
