---
phase: 01-foundation
verified: 2026-02-25T15:00:00Z
status: passed
score: 12/12 must-haves verified
---

# Phase 1: Foundation Verification Report

**Phase Goal:** ag-cli operates as a plant science agent — answering open-ended plant biology questions using the inherited agentic loop, without surfacing pharma tools or oncology reasoning
**Verified:** 2026-02-25T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

**Plan 01-01 (FOUN-01, FOUN-02) — Agent identity and tool filtering:**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent responds to plant biology questions with plant-focused reasoning, no oncology or drug discovery framing | VERIFIED | `build_system_prompt([])` returns prompt with "plant" present, "oncology"/"drug discovery"/"IC50" absent — confirmed by live Python assertion |
| 2 | `ag tool list` shows only plant-relevant and general-purpose tools; pharma-category tools are absent | VERIFIED | `cli.py:303` passes `PLANT_SCIENCE_CATEGORIES` to `list_tools_table(include_categories=...)` — 20 pharma categories excluded including chemistry, clinical, safety, cro, viability, combination, structure, biomarker, pk |
| 3 | Agent never calls pharma-category tools during a plant biology query (tools are invisible at MCP layer) | VERIFIED | `runner.py:318` computes `exclude_cats = (all_categories - PLANT_SCIENCE_CATEGORIES) | EXPERIMENTAL_CATEGORIES` and passes `exclude_categories=exclude_cats` to `create_ct_mcp_server()` — hard invisible at registration |
| 4 | System prompt refers to the agent as "Harvest" and describes plant biology/ag biotech domain expertise | VERIFIED | `AGENT_NAME = "Harvest"` at `system_prompt.py:21`; f-string injected into `_IDENTITY`; `_IDENTITY` describes "plant biology and agricultural biotechnology", genomics, expression, ortholog, trait development, gene editing |
| 5 | System prompt contains no references to drug discovery, clinical trials, IC50, or pharma workflows | VERIFIED | Live assertion: oncology=False, drug discovery=False, IC50=False. Pharma workflow injection commented out at `system_prompt.py:138-148` with explanatory note |

**Plan 01-02 (FOUN-03, FOUN-04) — Species architecture and CLI rebrand:**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Running `ag --version` returns the ag-cli version correctly | VERIFIED | `pyproject.toml:6-7` name="ag-cli", version="0.1.0"; `scripts.ag = "ct.cli:entry"` at line 84; `__version__` imported from `ct` in cli.py |
| 7 | The CLI command is `ag` (not `ct`) and routes to the same entry point | VERIFIED | `pyproject.toml:84` `ag = "ct.cli:entry"`; `entry()` function uses `prog_name="ag"` at `cli.py:1454` |
| 8 | Every surviving-category tool with former human species reference now accepts an optional `species` parameter defaulting to Arabidopsis thaliana | VERIFIED | `network.ppi_analysis`: `species: str = "Arabidopsis thaliana"`; `data_api.uniprot_lookup`: `organism: str = "Arabidopsis thaliana"`; `data_api.ensembl_lookup`: `species: str = "Arabidopsis thaliana"`; `protein.function_predict` and `protein.domain_annotate`: `species` param; `parity.mygene_lookup`: default Arabidopsis. No hardcoded `9606` as default in any surviving-category function signature |
| 9 | Calling a tool with `species='rice'` resolves to NCBI taxon ID 4530 via the interim species helper | VERIFIED | `_species.py` `resolve_species_taxon('rice') == 4530` confirmed by live assertion |
| 10 | No tool in a surviving category contains hardcoded `9606`, `homo_sapiens`, or `human` as a default parameter value | VERIFIED | grep confirms only occurrence of `9606` in surviving tools is inside `data_api.py` organism lookup dict (a map, not a default), not a function parameter default. All function defaults are "Arabidopsis thaliana" |
| 11 | Agent refers to itself as "Harvest" in CLI banner and interactive mode | VERIFIED | `cli.py:30-37` HARVEST ASCII art banner; `cli.py:1387` Panel title `"[bold #50fa7b]Harvest[/]"`; `print_banner()` at line 1365 prints "Harvest" panel; Welcome message at line 142: "Welcome to Harvest" |
| 12 | Help text uses plant science language (gene editing, trait development, expression analysis) | VERIFIED | `app` Typer help at `cli.py:41-50` uses "genomics, expression analysis, gene editing assessment, and multi-species evidence synthesis". `print_banner()` line 1381: "genomics · expression · gene editing · orthologs" |

**Score: 12/12 truths verified**

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `src/ct/agent/system_prompt.py` | Plant science agent identity, AGENT_NAME constant | VERIFIED | `AGENT_NAME = "Harvest"` at line 21; `_IDENTITY` is pure plant science; `build_system_prompt()` assembles plant-only prompt; pharma workflows commented out |
| `src/ct/agent/knowledge.py` | Plant biology domain knowledge primer | VERIFIED | `KNOWLEDGE_PRIMER` covers plant genomics, expression biology, regulatory networks (7 hormone pathways), ortholog/comparative genomics, CRISPR in plants, trait development, key databases (TAIR, Phytozome, Gramene, STRING) |
| `src/ct/tools/__init__.py` | PLANT_SCIENCE_CATEGORIES allowlist constant | VERIFIED | `PLANT_SCIENCE_CATEGORIES = frozenset({...})` at lines 21-41 with 19 categories; `list_tools_table(include_categories=...)` implemented; table title "ag Tools" |
| `src/ct/agent/runner.py` | Exclude-set computation from allowlist | VERIFIED | Lines 314-318: `from ct.tools import registry, EXPERIMENTAL_CATEGORIES, PLANT_SCIENCE_CATEGORIES`; `exclude_cats = (all_categories - PLANT_SCIENCE_CATEGORIES) | set(EXPERIMENTAL_CATEGORIES)`; passed to `create_ct_mcp_server()` |
| `src/ct/cli.py` | Filtered tool list, branded AG banner, plant science help text, ag prog_name | VERIFIED | HARVEST ASCII banner at lines 30-37; `prog_name="ag"` at line 1454; `name="ag"` Typer app; PLANT_SCIENCE_CATEGORIES filter at line 303-305; plant science help text throughout |
| `src/ct/tools/_species.py` | Interim species resolution helper | VERIFIED | `_PLANT_TAXON_MAP` with 20+ plant species (64 plant entries); `resolve_species_taxon()`, `resolve_species_binomial()`, `resolve_species_ensembl_name()` all implemented with proper edge case handling |
| `pyproject.toml` | Package rebranding to ag-cli with ag entry point | VERIFIED | `name = "ag-cli"`, `version = "0.1.0"`, `description = "ag-cli — An autonomous plant science research agent"`, `ag = "ct.cli:entry"` at line 84 |

---

### Key Link Verification

**Plan 01-01 key links:**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/__init__.py` | `src/ct/agent/runner.py` | `PLANT_SCIENCE_CATEGORIES` import for exclude-set computation | WIRED | `runner.py:314` `from ct.tools import registry, EXPERIMENTAL_CATEGORIES, PLANT_SCIENCE_CATEGORIES` |
| `src/ct/agent/runner.py` | `src/ct/agent/mcp_server.py` | `exclude_categories` parameter passed to `create_ct_mcp_server()` | WIRED | `runner.py:324-327` `server, sandbox, tool_names, code_trace_buffer = create_ct_mcp_server(self.session, exclude_categories=exclude_cats)` |
| `src/ct/tools/__init__.py` | `src/ct/cli.py` | `PLANT_SCIENCE_CATEGORIES` import for tool list filtering | WIRED | `cli.py:303` `from ct.tools import registry, ensure_loaded, tool_load_errors, PLANT_SCIENCE_CATEGORIES`; `cli.py:305` `registry.list_tools_table(include_categories=PLANT_SCIENCE_CATEGORIES)` |

**Plan 01-02 key links:**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/_species.py` | `src/ct/tools/network.py` | `resolve_species_taxon` for STRING API calls | WIRED | `network.py:64` lazy import `from ct.tools._species import resolve_species_taxon` inside `ppi_analysis` body |
| `src/ct/tools/_species.py` | `src/ct/tools/data_api.py` | `resolve_species_taxon` and `resolve_species_ensembl_name` for API lookups | WIRED | `data_api.py:761` `from ct.tools._species import resolve_species_taxon`; `data_api.py:1300` `from ct.tools._species import resolve_species_ensembl_name` |
| `pyproject.toml` | `src/ct/cli.py` | entry point mapping `ag -> ct.cli:entry` | WIRED | `pyproject.toml:84` `ag = "ct.cli:entry"`; `cli.py:1454` `app(args=argv, prog_name="ag")` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FOUN-01 | 01-01 | Agent uses plant science system prompt replacing all oncology domain knowledge | SATISFIED | `system_prompt.py` AGENT_NAME="Harvest", _IDENTITY is pure plant science, KNOWLEDGE_PRIMER is plant biology (7 sections), no oncology/IC50/drug discovery anywhere |
| FOUN-02 | 01-01 | Runtime domain-based tool filtering hides pharma-specific tools (chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK) from the agent | SATISFIED | `PLANT_SCIENCE_CATEGORIES` frozenset excludes all 9 specified pharma categories plus 11 others (20 total excluded); wired via runner.py to MCP server; confirmed by live assertion that `pharma_cats.issubset(excluded)` |
| FOUN-03 | 01-02 | Species-agnostic architecture — no hardcoded species; species passed as parameter to all tools | SATISFIED | `_species.py` created with `_PLANT_TAXON_MAP`; all surviving-category tools updated to accept `species: str = "Arabidopsis thaliana"`; no hardcoded 9606 as default in surviving tool function signatures |
| FOUN-04 | 01-02 | CLI and pyproject.toml rebranded from celltype-cli to ag-cli | SATISFIED | `pyproject.toml` name="ag-cli", `ag = "ct.cli:entry"`; CLI banner is HARVEST ASCII art; `name="ag"` Typer app; `prog_name="ag"` in entry(); all help text is plant science focused |

All 4 phase requirements satisfied. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ct/cli.py` | 587-588 | `--pharma` flag in `release-check` diagnostic command | Info | Developer-only diagnostic subcommand for deployment policy checks; not user-facing research interface; does not expose pharma tools to the agent or enable pharma reasoning; pharma refers to deployment config, not domain switch |
| `src/ct/tools/__init__.py` | 155, 188 | `"experimental / TODO"` status strings in table rendering | Info | UI label for experimental tool categories; not a placeholder implementation; category status display is functional |
| `src/ct/agent/system_prompt.py` | 138-148 | Pharma workflow injection commented out | Info | Correct and intentional — comment explains plant-specific workflows deferred to later phase; prevents pharma content contamination; not a stub |

No blocker or warning anti-patterns found. All three findings are informational and do not affect goal achievement.

---

### Human Verification Required

#### 1. End-to-end plant biology query

**Test:** Run `ag "What genes regulate drought tolerance in Arabidopsis?"` with a valid API key configured
**Expected:** Agent uses plant science tools (genomics, literature, data_api, network), produces a response about ABA pathway, stress-responsive TFs, and drought-related gene functions — no reference to drug discovery, oncology, clinical trials, or compound optimization
**Why human:** Cannot verify LLM reasoning and tool selection patterns without a live API call

#### 2. Tool list visual verification

**Test:** Run `ag tool list` in a terminal
**Expected:** Table titled "ag Tools"; contains tools from categories: genomics, network, literature, data_api, protein, omics, statistics, dna, code, files, shell, ops, claude, expression, singlecell, notification, remote_data, experiment, parity. No chemistry, clinical, safety, viability, biomarker, combination, structure, pk, cro, target, translational tools visible
**Why human:** Visual inspection of rendered Rich table; confirms the filter actually works in the live command

#### 3. Harvest banner display

**Test:** Run `ag` in a terminal (interactive mode entry)
**Expected:** HARVEST ASCII art banner displays in green gradient, followed by a panel titled "Harvest" showing "Autonomous Plant Science Research Agent" and tool count
**Why human:** ASCII art rendering and terminal color display cannot be verified programmatically

---

### Gaps Summary

No gaps found. All 12 must-have truths verified at all three levels (exists, substantive, wired). All 4 phase requirements (FOUN-01 through FOUN-04) are satisfied with direct evidence in the codebase. All 6 key links are wired and confirmed with grep evidence. No commits referenced in summaries were found to be missing — all 4 feature commits (56fa755, 05aac5c, 5c19cbe, 141d132) exist and are substantive.

The phase goal is achieved: ag-cli operates as a plant science agent ("Harvest") with hard-invisible MCP-layer filtering of 20 pharma categories, a plant biology knowledge primer, a species-agnostic tool architecture (20+ species via `_species.py`), and a fully rebranded CLI.

---

*Verified: 2026-02-25T15:00:00Z*
*Verifier: Claude (gsd-verifier)*
