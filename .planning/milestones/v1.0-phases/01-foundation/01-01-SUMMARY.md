---
phase: 01-foundation
plan: 01
subsystem: agent-identity
tags: [plant-science, system-prompt, tool-filtering, knowledge-primer, harvest]

# Dependency graph
requires: []
provides:
  - "Plant science agent identity as 'Harvest' in system_prompt.py with AGENT_NAME constant"
  - "Plant biology KNOWLEDGE_PRIMER (genomics, expression, hormones, editing, orthologs)"
  - "PLANT_SCIENCE_CATEGORIES frozenset allowlist (19 categories) in tools/__init__.py"
  - "Runtime tool category filtering: 20 pharma categories hidden at MCP layer"
  - "Filtered tool list command (ag tool list shows only plant-relevant tools)"
affects:
  - "02-foundation: species parameter changes will reference PLANT_SCIENCE_CATEGORIES"
  - "03-foundation: CLI rebrand builds on system_prompt.py AGENT_NAME constant"
  - "All phases: runner.py now passes plant science exclude set to MCP server"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AGENT_NAME single configurable constant in system_prompt.py — change name in one place"
    - "Allowlist pattern for tool filtering: PLANT_SCIENCE_CATEGORIES frozenset; anything not listed is hidden"
    - "Hard invisible tool filtering: excluded tools never reach agent (MCP layer, not soft filter)"
    - "Pharma workflows disabled by commenting out injection — plant workflows added in later phase"

key-files:
  created: []
  modified:
    - "src/ct/agent/system_prompt.py — AGENT_NAME constant, plant science _IDENTITY, plant tool catalog hints, updated _SYNTHESIS_INSTRUCTIONS, disabled pharma workflow injection"
    - "src/ct/agent/knowledge.py — full replacement of KNOWLEDGE_PRIMER with plant biology domain knowledge (7 major sections)"
    - "src/ct/tools/__init__.py — PLANT_SCIENCE_CATEGORIES frozenset added, list_tools_table() updated with include_categories param and 'ag Tools' title"
    - "src/ct/agent/runner.py — MCP server exclude set computed from PLANT_SCIENCE_CATEGORIES allowlist"
    - "src/ct/cli.py — tool list command filters by PLANT_SCIENCE_CATEGORIES"
    - "tests/test_knowledge.py — updated pharma viability test to assert plant science content"

key-decisions:
  - "AGENT_NAME = 'Harvest' as single module-level constant in system_prompt.py (not hardcoded in multiple places)"
  - "Allowlist approach (PLANT_SCIENCE_CATEGORIES) rather than blocklist — safer for new domain; unknown future categories default hidden"
  - "Hard invisible tool filtering at MCP layer (not soft-filter acknowledgement) — agent never wastes turns on pharma tools"
  - "Pharma workflow injection disabled by commenting out in build_system_prompt() — avoids oncology/IC50 content contaminating agent prompt; plant-specific workflows deferred to later phase"
  - "19 categories in allowlist; 20 categories excluded (chemistry, clinical, safety, cro, viability, combination, structure, biomarker, pk, target, translational, regulatory, intel, report, imaging, repurposing, cellxgene, clue, design, compute)"

patterns-established:
  - "Pattern 1: Tool allowlist — define PLANT_SCIENCE_CATEGORIES frozenset; runner computes exclude = all_cats - allowlist | experimental"
  - "Pattern 2: Domain clean slate — no acknowledgment of pharma heritage in _IDENTITY or KNOWLEDGE_PRIMER"
  - "Pattern 3: Single configurable name — AGENT_NAME constant for trivial agent rename"

requirements-completed: [FOUN-01, FOUN-02]

# Metrics
duration: 11min
completed: 2026-02-25
---

# Phase 1 Plan 1: Domain Swap — Plant Science System Prompt and Tool Filtering

**Plant science agent 'Harvest' with comprehensive domain knowledge primer and hard-invisible MCP-layer filtering of 20 pharma tool categories via PLANT_SCIENCE_CATEGORIES allowlist**

## Performance

- **Duration:** 11 min
- **Started:** 2026-02-25T13:51:43Z
- **Completed:** 2026-02-25T14:03:23Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Replaced pharma/drug-discovery `_IDENTITY` with a plant science expert identity for agent "Harvest" — `AGENT_NAME = "Harvest"` as a single configurable module-level constant
- Replaced 500+ line drug-discovery KNOWLEDGE_PRIMER with comprehensive plant biology primer covering: genome architecture (polyploidy, synteny, gene families), expression biology (tissue specificity, stress responses, key databases), regulatory networks (7 hormone pathways, major TF families), ortholog/comparative genomics (6 major crop species), CRISPR gene editing in plants, and trait development (QTL, GWAS, MAS, transgenic vs gene-edited)
- Implemented PLANT_SCIENCE_CATEGORIES frozenset allowlist with 19 plant-relevant categories; runner computes exclude set and passes to MCP server, making 20 pharma categories (chemistry, clinical, safety, cro, viability, combination, structure, biomarker, pk, target, and 10 more) genuinely invisible to the agent
- Updated `ag tool list` CLI command to filter by allowlist — pharma tools absent from tool listing
- Updated tool catalog hints in system prompt to plant-relevant tools only (genomics, network, expression, DNA, omics, literature, data_api, singlecell)
- Updated `_SYNTHESIS_INSTRUCTIONS` to plant biology outputs (gene function, expression patterns, ortholog evidence, editing considerations) — no IC50/clinical trials language

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace system prompt with plant science identity and knowledge primer** - `56fa755` (feat)
2. **Task 2: Implement category allowlist filtering for plant science tools** - `05aac5c` (feat)

**Plan metadata:** *(to be added after final commit)*

## Files Created/Modified

- `src/ct/agent/system_prompt.py` — AGENT_NAME constant, plant science _IDENTITY and _SYNTHESIS_INSTRUCTIONS, plant-only tool catalog hints, pharma workflow injection disabled
- `src/ct/agent/knowledge.py` — full KNOWLEDGE_PRIMER replacement with 7-section plant biology domain primer and updated SYNTHESIZER_PRIMER
- `src/ct/tools/__init__.py` — PLANT_SCIENCE_CATEGORIES frozenset (19 categories), list_tools_table() with include_categories filter and "ag Tools" title
- `src/ct/agent/runner.py` — exclude set computation from PLANT_SCIENCE_CATEGORIES allowlist, passed to create_ct_mcp_server()
- `src/ct/cli.py` — tool_list command imports and passes PLANT_SCIENCE_CATEGORIES to list_tools_table()
- `tests/test_knowledge.py` — pharma viability test replaced with plant science content assertions

## Decisions Made

- Used allowlist (not blocklist) for tool filtering — anything not explicitly approved is hidden, which is safer for a new domain where future categories are unknown
- Hard invisible filtering at MCP layer (not soft-filter) — agent never attempts pharma tools and wastes turns
- Disabled pharma workflows injection by commenting out in build_system_prompt() — prevents oncology/IC50 contamination of plant science agent context; plant-specific workflows are a later-phase deliverable
- Conservative allowlist: excluded borderline categories (repurposing, cellxgene, clue) as human/compound-centric; can be re-added in Phase 2 when plant data connectors exist

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pharma workflow content contaminating system prompt**
- **Found during:** Task 1 (system prompt verification)
- **Issue:** `ct.agent.workflows.format_workflows_for_llm()` returned pharma-domain workflows containing "oncology" and "IC50", which were injected into the system prompt by `build_system_prompt()`. The verification assertion `assert 'oncology' not in prompt.lower()` failed.
- **Fix:** Commented out the workflows injection block in `build_system_prompt()` with an explanatory note. Plant-specific workflows will be added in a later phase.
- **Files modified:** `src/ct/agent/system_prompt.py`
- **Verification:** Re-ran `build_system_prompt([])` — no oncology, no IC50 in prompt. All 4 plan verification checks pass.
- **Committed in:** 56fa755 (Task 1 commit)

**2. [Rule 1 - Bug] test_knowledge_primer_mentions_viability_suite now incorrect**
- **Found during:** Task 2 (test suite run)
- **Issue:** Existing test asserting viability.dose_response, viability.tissue_selectivity, viability.compare_compounds are mentioned in KNOWLEDGE_PRIMER — these pharma tools are no longer in the plant science primer (correctly removed).
- **Fix:** Replaced test with `test_knowledge_primer_mentions_plant_science_tools` that asserts plant-relevant content (genomics, expression, network) and asserts pharma tools are absent.
- **Files modified:** `tests/test_knowledge.py`
- **Verification:** Both knowledge tests pass.
- **Committed in:** 05aac5c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - bug fixes)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- Pre-existing test failures (unrelated to this plan): `test_mention_completer.py` (extract_mentions returns 4 values, tests expect 3), `test_omics.py` (missing muon/pydeseq2 modules), `test_sandbox.py` and `test_shell.py` (security rule regressions), `test_terminal.py` (trajectory/orchestrator API changes), `test_chemistry_new.py` (rdkit not installed). All confirmed pre-existing by stash-and-test verification. Documented in deferred-items scope.

## Next Phase Readiness

- Agent identity and tool filtering foundation complete
- Plan 02 (species parameter architecture) can now reference PLANT_SCIENCE_CATEGORIES to scope which tools need species parameter cleanup
- Plan 03/04 (CLI rebrand) can reference AGENT_NAME constant from system_prompt.py
- Runner now automatically excludes 20 pharma categories on every query — agent sees only plant-relevant tools

## Self-Check: PASSED

All files present, all commits verified, all functional assertions pass:
- AGENT_NAME = "Harvest" in system_prompt.py
- No oncology/IC50/drug discovery in system prompt
- PLANT_SCIENCE_CATEGORIES has 19 allowed categories
- 20 pharma categories excluded (chemistry, clinical, safety, etc.)
- pharma_cats subset of excluded: True

---
*Phase: 01-foundation*
*Completed: 2026-02-25*
