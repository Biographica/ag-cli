# Phase 1: Foundation - Research

**Researched:** 2026-02-25
**Domain:** Python CLI rebranding, tool registry filtering, system prompt replacement, species parameter architecture
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**System prompt voice:**
- Expert collaborator tone — assumes domain knowledge, uses technical language, focuses on evidence and reasoning
- Clean slate identity — no acknowledgment of pharma/drug discovery heritage; the agent presents as purpose-built for plant science
- Ag biotech is the framing lens, but the domain knowledge must be deeply plant biology — genomics, expression, regulatory networks, orthologs, trait development, gene editing, breeding — because all of that is needed to do ag biotech well
- Do NOT pre-bake shortlisting metric language (novelty, efficacy, pleiotropic risk, editability) into the system prompt — the agent should be an exceptionally competent plant biology expert that serves as the best substrate for whatever meta-prompting is layered on top
- The agent's name is "Harvest" (keep this as a single configurable value — the name may change later)

**Tool filtering:**
- Category allowlist approach — define a list of plant-relevant and general-purpose categories that are exposed; everything else is hidden
- Categories to exclude include: chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK (and any other pharma-specific categories identified during implementation)

**Species parameter design:**
- Agent infers species from conversation context; if ambiguous, it asks the user — tools have an optional species parameter that the agent fills in
- Flexible input format — accept common names ("rice"), binomial ("Oryza sativa"), abbreviations ("Os"), and resolve to canonical internal form (binomial)
- The full species registry is Phase 2; Phase 1 needs an interim resolution approach (simple lookup dict or pass-through — Claude's discretion on the best bridge)

**CLI identity & branding:**
- Branded ASCII art banner for "AG" or "AG-CLI" — distinct visual identity from celltype
- CLI command is `ag` (not `ct`)
- Agent refers to itself as "Harvest" in conversation
- Help text uses plant science specific language — mentions gene editing, trait development, expression analysis, orthologs, species comparison, etc.
- pyproject.toml rebranded from celltype-cli to ag-cli

### Claude's Discretion

- Whether filtered tools are hard invisible (agent has no awareness) or soft-filtered (acknowledges but declines) — pick the cleanest approach
- Whether filtering is config-driven (domain = "plant_science") or hardcoded for ag-cli — pick based on codebase patterns and future flexibility
- Whether filtering is enforced at the MCP server layer only (hiding from agent) or also blocks programmatic execution — pick based on architecture
- Audit scope for species cleanup: whether to fix all tools or only tools that survive the allowlist filter

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUN-01 | Agent uses plant science system prompt replacing all oncology domain knowledge | System prompt is built in `src/ct/agent/system_prompt.py`; `_IDENTITY` and `KNOWLEDGE_PRIMER` (in `knowledge.py`) are the two top-level pharma-specific blobs to replace |
| FOUN-02 | Runtime domain-based tool filtering hides pharma-specific tools from the agent | `create_ct_mcp_server()` in `mcp_server.py` already accepts `exclude_categories: set[str]`; the runner passes this set at startup; allowlist approach means defining `PLANT_SCIENCE_CATEGORIES` constant and computing the exclude set from it |
| FOUN-03 | Species-agnostic architecture — no hardcoded species; species passed as parameter to all tools | 8 surviving-category tools contain hardcoded `9606` or default `"human"` in `network.py`, `data_api.py`, `protein.py`, `parity.py`, `genomics.py`; all require adding a `species` parameter + interim resolution dict |
| FOUN-04 | CLI and pyproject.toml rebranded from celltype-cli to ag-cli | Changes span: `pyproject.toml` (name, description, scripts entry point), `src/ct/__init__.py` (description string), `src/ct/cli.py` (BANNER, app name, help text, `entry()` prog_name, `print_banner()` metadata) |
</phase_requirements>

---

## Summary

Phase 1 is a surgical rebrand and domain-swap of celltype-cli into ag-cli. The core agentic machinery (Claude Agent SDK loop, MCP server, runner, session, sandbox) is inherited unchanged. The deliverable is four targeted modifications: a new plant science system prompt, runtime exclusion of pharma-specific tool categories, addition of a `species` parameter to tools that survive the allowlist, and CLI/packaging renaming.

The codebase is structured cleanly for this work. Tool filtering already exists at the MCP server layer — `create_ct_mcp_server()` accepts an `exclude_categories` parameter that the runner passes through. The tool registry exposes all categories, and the MCP server filters at tool-registration time. This means filtered tools are genuinely invisible to the agent (hard invisible), which is the cleanest approach.

The species hardcoding problem is scoped: only tools in categories that survive the allowlist filter need remediation. Of the tools examined, hardcoded species references appear in `network.py` (STRING API: `"species": 9606`), `data_api.py` (UniProt/Ensembl defaults), `protein.py` (UniProt query), `genomics.py` (Ensembl URL), `target.py` (Ensembl URL), and `parity.py` (mygene default). Surviving-category tools in `genomics`, `network`, `literature`, `data_api`, `protein`, `omics`, `statistics`, `dna`, `code`, `files`, `shell`, `ops`, `claude`, `expression`, `singlecell`, `repurposing`, `experiment`, `notification`, `remote_data`, `cellxgene`, and `clue` need audit; pharma-excluded categories (`chemistry`, `clinical`, `safety`, `cro`, `viability`, `combination`, `structure`, `biomarker`, `pk`, `target`, `translational`, `regulatory`, `intel`, `report`, `imaging`) do not.

**Primary recommendation:** Implement the four FOUN requirements as discrete, sequential changes in this order: (1) CLI rebrand, (2) tool category filtering, (3) system prompt replacement, (4) species parameter cleanup on surviving tools. Each is independently testable and low-risk.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | >=0.12 (pinned in pyproject.toml) | CLI framework — app definition, argument parsing, subcommands | Already in use; `ag` command is just a renamed entry point |
| rich | >=13.0 (pinned) | Terminal rendering — panels, tables, ASCII art banner | Already in use for BANNER, console output |
| anthropic + claude-agent-sdk | >=0.74.0 / >=0.1 (pinned) | LLM client + agentic loop | Core of the existing architecture; no change needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hatchling | (build system) | Package build backend | pyproject.toml `[build-system]` — required for `pip install -e .` to expose `ag` command |
| python-dotenv | >=1.0 | .env loading | Config layer already uses it; no change |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Allowlist filter (define allowed categories) | Blocklist (enumerate pharma categories) | Allowlist is safer for a new domain — unknown future categories default to hidden. Blocklist risks silently exposing unintended tools. |
| Hard invisible (MCP layer filter) | Soft-filtered (agent told to decline) | Hard invisible is cleaner — agent never wastes turns trying then declining pharma tools, and the system prompt need not reference them |
| Config-driven domain filtering | Hardcoded for ag-cli | Hardcoded is simpler and appropriate for Phase 1; config-driven is a Phase 2+ concern if ag-cli needs runtime domain switching |

---

## Architecture Patterns

### Recommended Project Structure (Phase 1 changes only)

```
src/ct/
├── __init__.py               # Change: update description string
├── cli.py                    # Change: BANNER, app name, entry(), print_banner(), help text
├── agent/
│   ├── system_prompt.py      # Change: replace _IDENTITY, update tool catalog hints
│   ├── knowledge.py          # Change: replace KNOWLEDGE_PRIMER with plant science primer
│   ├── mcp_server.py         # Change: add PLANT_SCIENCE_CATEGORIES constant; pass allowlist to runner
│   └── runner.py             # Change: pass derived exclude_categories to create_ct_mcp_server()
└── tools/
    ├── __init__.py           # Change: add PLANT_SCIENCE_CATEGORIES, PHARMA_CATEGORIES constants
    ├── network.py            # Change: add species param to ppi_analysis, pathway_crosstalk
    ├── data_api.py           # Change: update defaults on uniprot_lookup, ensembl_lookup, mygene_lookup
    ├── protein.py            # Change: add species param where organism_id:9606 is hardcoded
    ├── genomics.py           # Change: add species param where homo_sapiens URL is hardcoded
    ├── parity.py             # Change: update _normalize_mygene_species defaults
    └── ...                   # Other surviving-category tools: audit and add species param
pyproject.toml                # Change: name, description, scripts.ag entry point
```

### Pattern 1: Tool Category Allowlist

**What:** Define `PLANT_SCIENCE_CATEGORIES` in `src/ct/tools/__init__.py` as a frozenset of categories the agent is allowed to use. The runner computes the exclude set as all registered categories minus the allowlist.

**When to use:** Every time a query is run — the exclusion set is passed to `create_ct_mcp_server()`.

**Example:**
```python
# In src/ct/tools/__init__.py
PLANT_SCIENCE_CATEGORIES = frozenset({
    "genomics",
    "network",
    "literature",
    "data_api",
    "protein",
    "omics",
    "statistics",
    "dna",
    "code",
    "files",
    "shell",
    "ops",
    "claude",
    "expression",
    "singlecell",
    "repurposing",
    "experiment",
    "notification",
    "remote_data",
    "cellxgene",
    "clue",
    "parity",
})

# In src/ct/agent/runner.py, inside _run_async():
from ct.tools import registry, EXPERIMENTAL_CATEGORIES, PLANT_SCIENCE_CATEGORIES
all_categories = set(registry.categories())
exclude_cats = (all_categories - PLANT_SCIENCE_CATEGORIES) | set(EXPERIMENTAL_CATEGORIES)
```

### Pattern 2: Species Parameter with Interim Resolution

**What:** Each surviving-category tool that currently hardcodes `"human"` / `9606` gets a `species: str = "Arabidopsis thaliana"` parameter (plant-appropriate default). An interim `_resolve_species_taxon()` helper maps common names, abbreviations, and binomials to NCBI taxon IDs for APIs that require them.

**When to use:** Any tool that calls a species-aware external API (STRING, UniProt, Ensembl, MyGene).

**Example:**
```python
# Interim resolution helper (in a shared location, e.g., src/ct/tools/_species.py)
_PLANT_TAXON_MAP = {
    # Binomial → taxon ID
    "arabidopsis thaliana": 3702,
    "oryza sativa": 4530,
    "zea mays": 4577,
    "solanum lycopersicum": 4081,
    "solanum tuberosum": 4113,
    "triticum aestivum": 4565,
    "glycine max": 3847,
    "brassica napus": 3708,
    "nicotiana tabacum": 4097,
    "populus trichocarpa": 3694,
    # Common names / abbreviations → canonical binomial
    "arabidopsis": "arabidopsis thaliana",
    "at": "arabidopsis thaliana",
    "rice": "oryza sativa",
    "os": "oryza sativa",
    "maize": "zea mays",
    "corn": "zea mays",
    "zm": "zea mays",
    "tomato": "solanum lycopersicum",
    "potato": "solanum tuberosum",
    "wheat": "triticum aestivum",
    "soybean": "glycine max",
    "oilseed rape": "brassica napus",
    "canola": "brassica napus",
    "tobacco": "nicotiana tabacum",
    "poplar": "populus trichocarpa",
    # Human/mouse retained for cross-species lookups on general tools
    "human": 9606,
    "homo sapiens": 9606,
    "mouse": 10090,
    "mus musculus": 10090,
}

def resolve_species_taxon(species: str, default_taxon: int = 3702) -> int:
    """Resolve species string to NCBI taxon ID. Returns default (Arabidopsis) on unknown."""
    s = (species or "").strip().lower()
    if s.isdigit():
        return int(s)
    val = _PLANT_TAXON_MAP.get(s)
    if val is None:
        return default_taxon
    if isinstance(val, str):
        return _PLANT_TAXON_MAP.get(val, default_taxon)
    return val

def resolve_species_binomial(species: str, default: str = "Arabidopsis thaliana") -> str:
    """Resolve species string to canonical binomial. Returns default on unknown."""
    s = (species or "").strip().lower()
    # Try alias first
    val = _PLANT_TAXON_MAP.get(s)
    if isinstance(val, str):
        return val.title()
    # If it maps to a taxon ID, reverse lookup
    for name, tid in _PLANT_TAXON_MAP.items():
        if tid == _PLANT_TAXON_MAP.get(s) and " " in name:
            return name.title()
    # Try direct match with title case
    for name in _PLANT_TAXON_MAP:
        if " " in name and name.lower() == s:
            return name.title()
    return default
```

### Pattern 3: CLI Entry Point Rename

**What:** The `[project.scripts]` section in `pyproject.toml` maps a command name to a Python entry point. Renaming `ct` to `ag` requires changing one line in pyproject.toml and updating the `entry()` function's `prog_name`.

**When to use:** This is a one-time change at Phase 1.

**Example:**
```toml
# pyproject.toml
[project.scripts]
ag = "ct.cli:entry"

# The ct module path stays as-is (src/ct/) — no directory rename needed in Phase 1.
# The installed command is named by the scripts key, not the package name.
```

```python
# src/ct/cli.py — entry() function
def entry():
    """Package entry point."""
    # ... existing passthrough logic unchanged ...
    app(args=argv, prog_name="ag")   # was "ct"
```

### Pattern 4: System Prompt Construction

**What:** The system prompt is assembled in `build_system_prompt()` in `system_prompt.py`. It composes `_IDENTITY` + tool catalog + `workflows` + `KNOWLEDGE_PRIMER` + code-gen hints + `SYNTHESIZER_PRIMER` + synthesis instructions + data context + history. The plant science version replaces `_IDENTITY` (3 paragraphs) and `KNOWLEDGE_PRIMER` (the drug discovery domain knowledge section in `knowledge.py`).

**When to use:** Both `_IDENTITY` and `KNOWLEDGE_PRIMER` must be replaced. `_SYNTHESIS_INSTRUCTIONS` can be adapted (the "actionable" point should reference plant biology outputs, not IC50/trials). The `SYNTHESIZER_PRIMER` grounding rules are domain-agnostic and can be kept.

**Key insight:** The agent name "Harvest" should appear only in `_IDENTITY` (and potentially the banner), stored as a module-level constant so it can be changed in one place.

```python
# src/ct/agent/system_prompt.py
AGENT_NAME = "Harvest"   # single configurable value

_IDENTITY = f"""\
You are **{AGENT_NAME}**, an autonomous plant science research agent.

You have access to computational tools covering genomics, expression analysis, network biology,
ortholog mapping, literature search, DNA design, and data analysis — plus a persistent Python
sandbox (``run_python``) for custom analyses.

Your domain: plant biology and agricultural biotechnology. You reason about gene function,
regulatory networks, trait development, gene editing strategies, ortholog relationships,
and multi-species evidence synthesis across crop and model plant species.

Your job: take a research question and answer it completely, using the right tools and code,
self-correcting as you go, and producing a rigorous synthesis at the end.

## Operating Mode
- You are in an agentic loop: call tools, see results, call more tools, then
  write your final answer as plain text (no tool call).
- Think step-by-step. Use tools to gather evidence, then synthesize.
- If a tool fails or returns unhelpful data, try a different approach or use
  your own knowledge to fill gaps.
- For data analysis questions, use ``run_python`` to load data, explore it,
  and compute the answer. Variables persist between calls.
- When a species is not specified in the question, infer from context. If ambiguous, ask.
"""
```

### Anti-Patterns to Avoid

- **Renaming the `src/ct/` directory in Phase 1:** The Python package namespace is `ct`. Renaming the source directory breaks all imports across the entire codebase. The `ag` command name comes from `pyproject.toml [project.scripts]`, not from the package directory. Phase 1 should NOT rename `src/ct/` to `src/ag/`.
- **Adding pharma tools to the system prompt tool catalog:** The tool catalog hint in `build_system_prompt()` currently lists `viability.dose_response`, `clinical.indication_map`, `chemistry.descriptors`, `safety.classify` etc. All pharma-category tool hints must be removed; only surviving-category tools should appear.
- **Fixing species params on pharma-excluded tools:** The context says to audit scope at implementation time, but fixing species on excluded tools wastes effort — those tools are invisible to the agent anyway.
- **Hardcoding the agent name "Harvest" in multiple places:** The name may change; it belongs in a single constant.
- **Removing the ct module path from imports:** All internal imports (`from ct.agent...`, `from ct.tools...`) must remain unchanged since the package is still `ct`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Custom argparse | typer (already installed) | Complex edge cases (flags vs subcommands vs positional args); typer handles them and is already fully wired |
| ASCII art banner | Hand-crafted pixel art | Use an online ASCII art generator, then encode as a Python string literal | Consistent font, easier to iterate |
| Species name normalization | Full-featured species database | Simple lookup dict for Phase 1 | Phase 2 will build a proper registry; over-engineering the bridge makes migration harder |
| Tool category enumeration | Dynamic introspection of registered tools | Explicit frozenset constant | Explicit list is readable, testable, and intentional; dynamic introspection hides the category decision from reviewers |

**Key insight:** All the mechanism for tool filtering, system prompt building, and CLI routing already exists. Phase 1 is configuration and content replacement, not infrastructure.

---

## Common Pitfalls

### Pitfall 1: Installing the package after renaming leaves stale `ct` binary

**What goes wrong:** After changing `[project.scripts]` from `ct = ...` to `ag = ...` and running `pip install -e .`, both `ct` and `ag` may be present in the environment PATH (the old `ct` binary is not deleted automatically on macOS).

**Why it happens:** `pip install -e .` adds new entry points but does not remove old ones when the key changes in `pyproject.toml`. The old `ct` console script persists in the virtualenv's `bin/` directory.

**How to avoid:** After the pyproject.toml change, run `pip uninstall celltype-cli -y && pip install -e .` to force a clean reinstall. Or manually remove the stale `ct` binary from the virtualenv's bin.

**Warning signs:** Running `ct --version` still works after the rename; running `ag --version` works but the version string says "ct".

### Pitfall 2: System prompt references pharma tools that the MCP filter has hidden

**What goes wrong:** The tool catalog section in `build_system_prompt()` lists tools by name. If the agent sees `chemistry.descriptors` in the system prompt but the MCP server never exposes it, the agent will attempt to call it, get a tool-not-found error, and waste turns.

**Why it happens:** `system_prompt.py` has a hardcoded tool catalog hint (not derived from the live MCP tool list). It must be updated in sync with the filtering constants.

**How to avoid:** When defining `PLANT_SCIENCE_CATEGORIES`, simultaneously update the tool catalog hint text in `build_system_prompt()` to reference only surviving-category tools. Treat them as a matched pair.

**Warning signs:** Agent logs show tool call attempts followed immediately by "tool not found" errors during a plant biology query.

### Pitfall 3: `ct tool list` still shows pharma tools

**What goes wrong:** `ct tool list` (which becomes `ag tool list`) calls `registry.list_tools_table()` which iterates the full registry — including pharma-excluded categories. This is cosmetically wrong for FOUN-02.

**Why it happens:** `list_tools_table()` in `tools/__init__.py` does not filter by domain; it lists everything. The MCP server is what filters at runtime.

**How to avoid:** The `tool list` command should filter by `PLANT_SCIENCE_CATEGORIES`. Pass the allowlist into `list_tools_table()` or create a `list_plant_tools()` variant. The simplest fix: add an `include_categories` parameter to `list_tools_table()`.

**Warning signs:** Running `ag tool list` shows `chemistry.descriptors`, `clinical.indication_map`, etc.

### Pitfall 4: Hardcoded `"ct"` strings persist in interactive UI

**What goes wrong:** Various UI strings reference "ct" — the help text in `run_cmd` docstring, the interactive terminal prompt, the Panel titles in `print_banner()`, and potentially the `InteractiveTerminal` class. These are cosmetic but will confuse users.

**Why it happens:** The rebrand touches a large number of string literals scattered across `cli.py` and `ui/terminal.py`. Easy to miss some.

**How to avoid:** Run `grep -r '"ct"' src/ct/` and `grep -r "'ct'" src/ct/` after the rebrand to catch leftover references.

**Warning signs:** Interactive mode shows "Type a research question, or /help for commands." prefixed with a `ct` panel header.

### Pitfall 5: Species parameter default breaks existing tool tests

**What goes wrong:** Changing a tool's default `species` from `"human"` to `"Arabidopsis thaliana"` causes test assertions that expected human data to fail.

**Why it happens:** The test suite for `network.py`, `data_api.py`, `protein.py` etc. was written for human-default tools. When the default changes, mock setups that relied on `species="human"` may break.

**How to avoid:** When changing defaults, also update the corresponding test fixtures. Tests should mock at the HTTP layer (`@patch("ct.tools.http_client.request_json")`), not at the species default.

**Warning signs:** `pytest tests/ -v` fails on `test_network.py`, `test_parity_tools.py`, `test_data_api.py` after species default changes.

---

## Code Examples

Verified patterns from existing codebase:

### Registering a tool with species parameter

```python
# Source: src/ct/tools/network.py (modified pattern)
@registry.register(
    name="network.ppi_analysis",
    description="Analyze protein-protein interaction network for a gene using STRING database",
    category="network",
    parameters={
        "gene": "Gene symbol or comma-separated list (e.g. 'FT' or 'FT,CO,SOC1')",
        "species": "Species name or taxon ID (default: Arabidopsis thaliana)",
        "min_score": "Minimum interaction confidence score 0-1 (default 0.4 = medium)",
        "network_depth": "1=direct partners only, 2=partners of partners (default 1)",
    },
    usage_guide="Understand what proteins interact with a plant gene using STRING. Use for gene function, regulatory network, and co-complex member analysis.",
)
def ppi_analysis(gene: str, species: str = "Arabidopsis thaliana",
                 min_score: float = 0.4, network_depth: int = 1, **kwargs) -> dict:
    from ct.tools._species import resolve_species_taxon
    taxon_id = resolve_species_taxon(species)
    # ... rest of function uses taxon_id instead of hardcoded 9606 ...
```

### Passing exclude_categories to MCP server in runner.py

```python
# Source: src/ct/agent/runner.py, inside _run_async() — modified pattern
from ct.tools import registry, EXPERIMENTAL_CATEGORIES, PLANT_SCIENCE_CATEGORIES

all_categories = set(registry.categories())
exclude_cats = (all_categories - PLANT_SCIENCE_CATEGORIES) | set(EXPERIMENTAL_CATEGORIES)

server, sandbox, tool_names, code_trace_buffer = create_ct_mcp_server(
    self.session,
    exclude_categories=exclude_cats,
)
```

### pyproject.toml entry point change

```toml
# pyproject.toml
[project]
name = "ag-cli"
version = "0.1.0"
description = "ag-cli — An autonomous plant science research agent"

[project.scripts]
ag = "ct.cli:entry"
```

### Tool list filtering in CLI

```python
# src/ct/cli.py — modified tool_list command
@tool_app.command("list")
def tool_list():
    """List all available tools."""
    from ct.tools import registry, ensure_loaded, tool_load_errors, PLANT_SCIENCE_CATEGORIES
    ensure_loaded()
    console.print(registry.list_tools_table(include_categories=PLANT_SCIENCE_CATEGORIES))
    # ...
```

### list_tools_table with include filter

```python
# src/ct/tools/__init__.py — modified list_tools_table
def list_tools_table(self, include_categories: frozenset | None = None) -> Table:
    """Render tool list as a rich table."""
    table = Table(title="ag Tools")
    # ...
    for tool in self.list_tools():
        if include_categories and tool.category not in include_categories:
            continue
        # ... rest unchanged ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plan-then-Execute (Planner → Executor → Synthesis) | Single AgentRunner agentic loop via Claude Agent SDK | Pre-existing in codebase | No change needed — the SDK loop is domain-agnostic |
| Global species hardcoding | Species as explicit parameter | Phase 1 (this phase) | All surviving tools must accept `species` kwarg |

**Deprecated/outdated in this context:**
- `celltype-cli` package name: replaced by `ag-cli` in Phase 1
- `ct` console script entry: replaced by `ag` in Phase 1
- Drug discovery KNOWLEDGE_PRIMER: replaced by plant science primer in Phase 1
- Pharma tool catalog hints in system_prompt.py: replaced by plant science tool orientation in Phase 1

---

## Open Questions

1. **Should `ct tool list` and `ag tool list` be identical commands, or should `ct` be fully removed?**
   - What we know: `pyproject.toml [project.scripts]` maps `ct` to the entry point. Changing the key to `ag` removes `ct` on fresh install.
   - What's unclear: Whether any CI, docs, or scripts reference the `ct` command that would break.
   - Recommendation: Change the scripts key to `ag` only; do not add a `ct` alias. The CONTEXT.md is clear: "CLI command is `ag` (not `ct`)". Stale binaries in existing installs are addressed by a clean reinstall.

2. **Which categories from the existing tool list survive the allowlist?**
   - What we know: The CONTEXT.md specifies exclusions: chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK. From the registered categories audit: `chemistry`, `clinical`, `safety`, `cro`, `viability`, `combination`, `structure`, `biomarker`, `pk`, and also `target` (drug target scoring/druggability — not plant relevant), `translational` (clinical biomarker readiness), `regulatory` (CDISC compliance), `intel` (pharma pipeline watch), `report` (pharma_brief), `imaging` (cell painting/compound morphology).
   - What's unclear: `repurposing` (CMap connectivity map — has some utility for gene mechanism queries but is compound-centric), `cellxgene` (human cell atlas data — primarily human single-cell), `clue` (CLUE platform — compound perturbation signatures).
   - Recommendation: Implement with a conservative allowlist first. The discretion categories (`repurposing`, `cellxgene`, `clue`) should be excluded initially since their APIs are human/compound-centric. Add them back in Phase 2 when plant data connectors are built. The surviving allowlist is: `genomics`, `network`, `literature`, `data_api`, `protein`, `omics`, `statistics`, `dna`, `code`, `files`, `shell`, `ops`, `claude`, `expression`, `singlecell`, `notification`, `remote_data`, `experiment`, `parity`.

3. **What is the right default species for tools that currently default to `"human"`?**
   - What we know: CONTEXT.md says "agent infers species from conversation context; if ambiguous, it asks the user — tools have an optional species parameter that the agent fills in".
   - What's unclear: Whether the tool-level default should be `"Arabidopsis thaliana"` or `None`.
   - Recommendation: Default to `"Arabidopsis thaliana"` (the primary model plant). If the agent does not pass a species, the tool behaves sensibly for the most common use case. `None` defaults require more defensive code in every tool. This is consistent with how the original tools default to `"human"`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `src/ct/agent/system_prompt.py`, `src/ct/agent/mcp_server.py`, `src/ct/agent/runner.py`, `src/ct/tools/__init__.py`, `src/ct/cli.py`, `pyproject.toml` — all mechanisms verified by reading the source
- Direct codebase inspection — `src/ct/tools/network.py`, `src/ct/tools/data_api.py`, `src/ct/tools/protein.py`, `src/ct/tools/genomics.py`, `src/ct/tools/parity.py` — species hardcoding verified by direct grep and file reading

### Secondary (MEDIUM confidence)
- pyproject.toml console_scripts entry point pattern — standard Python packaging, well-established; the `scripts.ag = "ct.cli:entry"` approach is proven in the existing `scripts.ct = "ct.cli:entry"` setup

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are in-use and pinned in pyproject.toml; no new dependencies needed
- Architecture: HIGH — all patterns derived from direct source code reading; no external research required
- Pitfalls: HIGH — species hardcoding verified by grep; entry point behavior verified by existing test_cli.py patterns

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable codebase; no external API changes relevant to this phase)
