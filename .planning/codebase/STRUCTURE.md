# Codebase Structure

**Analysis Date:** 2026-02-25

## Directory Layout

```
cli/
├── src/ct/                        # Main source tree
│   ├── agent/                     # Agentic loop, orchestration, session management
│   ├── tools/                     # Domain tools (190+) organized by category
│   ├── data/                      # Data loaders and downloaders
│   ├── models/                    # LLM client abstraction
│   ├── kb/                        # Knowledge substrate and reasoning
│   ├── ui/                        # Terminal UI components
│   ├── api/                       # FastAPI data query endpoint
│   ├── reports/                   # Report generation (HTML, Jupyter)
│   ├── cli.py                     # Main CLI entry point
│   └── __init__.py
├── tests/                         # Test suite
│   ├── fixtures/                  # Test data and mocks
│   ├── test_*.py                  # Unit and integration tests
│   └── conftest.py                # Pytest configuration
├── scripts/                       # Development scripts
├── assets/                        # Images, templates, documentation
├── openspec/                      # OpenAPI/specification artifacts
└── .planning/codebase/            # GSD codebase maps (this directory)
```

## Directory Purposes

**`src/ct/agent/`:**
- Purpose: Agentic loop orchestration, session management, trajectory persistence
- Contains: `runner.py` (AgentRunner, SDK integration), `loop.py` (multi-turn loop), `mcp_server.py` (tool exposure), `orchestrator.py` (parallel multi-agent), `config.py` (settings), `session.py` (request context)
- Key files:
  - `runner.py`: Main agent execution with async message processing
  - `loop.py`: Multi-turn session wrapper for interactive mode
  - `mcp_server.py`: MCP tool server for Agent SDK integration
  - `orchestrator.py`: Parallel agent execution for complex queries
  - `config.py`: Config schema and loader (~/.ct/config.json)
  - `system_prompt.py`: Agent system prompt construction
  - `trajectory.py`: Multi-turn conversation history persistence
  - `trace_store.py`: Execution trace logging

**`src/ct/tools/`:**
- Purpose: All domain capabilities (~190 tools) organized by category
- Contains: Tool module files (one per category), registry, tool decorators
- Key files:
  - `__init__.py`: `ToolRegistry` class, tool decorator, discovery
  - `chemistry.py`: Molecular descriptors, SAR, fingerprints (RDKit)
  - `expression.py`: Gene expression analysis, L1000 lookups
  - `genomics.py`: DNA/RNA analysis, variant calling, alignment
  - `data_api.py`: Large dataset queries (DepMap, PRISM, Perturbatlas)
  - `literature.py`: PubMed search, citation parsing
  - `clinical.py`: Clinical trial lookups, indication data
  - `target.py`: Gene/protein target analysis
  - `omics.py`: Bulk omics analysis tools
  - `singlecell.py`: Single-cell expression queries (CellXGene)
  - `code.py`: Sandboxed Python execution (guarded/opt-in)
  - `files.py`: File handling, markdown rendering
  - And 40+ more categories...
- Naming: Tool modules named by category; functions use `category.tool_name` naming

**`src/ct/data/`:**
- Purpose: Data loading, caching, and management
- Contains: Loaders for large datasets, dataset downloader
- Key files:
  - `loaders.py`: `load_crispr()`, `load_prism()`, `load_l1000()`, `load_proteomics()`, etc. (memoized with @lru_cache)
  - `downloader.py`: `download_dataset()` for DepMap, PRISM, MSigDB, AlphaFold
  - `compute_providers.json`: Compute provider configurations

**`src/ct/models/`:**
- Purpose: LLM provider abstraction
- Contains: Unified client interface for Anthropic, OpenAI, local, CellType models
- Key files:
  - `llm.py`: `LLMResponse`, `UsageTracker`, provider selection, cost estimation

**`src/ct/kb/`:**
- Purpose: Knowledge substrate, reasoning augmentation, validation
- Contains: Knowledge schema, ingestion, governance
- Key files:
  - `substrate.py`: Knowledge base schema and queries
  - `reasoning.py`: Reasoning augmentation for planner/agent
  - `ingest.py`: Knowledge ingestion pipeline
  - `governance.py`: Knowledge quality gates

**`src/ct/ui/`:**
- Purpose: Terminal user interface components
- Contains: Interactive REPL, status spinners, trace rendering
- Key files:
  - `terminal.py`: `InteractiveTerminal` class (REPL loop, multi-turn)
  - `status.py`: Progress indicators, thinking status
  - `suggestions.py`: Auto-suggestions for next steps
  - `traces.py`: Trace visualization and export

**`src/ct/api/`:**
- Purpose: FastAPI endpoint for data queries
- Contains: Query API, DuckDB engine, dataset registry
- Key files:
  - `app.py`: FastAPI server, `/query`, `/datasets`, `/health` endpoints
  - `engine.py`: DuckDB query executor
  - `config.py`: Dataset registry and schema validation

**`src/ct/reports/`:**
- Purpose: Transform results into publishable reports
- Contains: HTML and Jupyter notebook rendering
- Key files:
  - `html.py`: HTML template rendering with Jinja2
  - `notebook.py`: Jupyter notebook export

**`src/ct/cli.py`:**
- Purpose: Main CLI entry point and command dispatcher
- Contains: Typer app definition, all subcommands
- Key commands: `ct`, `ct "question"`, `ct config`, `ct data`, `ct tool`, `ct doctor`, `ct trace`, `ct knowledge`

**`tests/`:**
- Purpose: Unit and integration tests
- Contains: Test modules mirroring src structure, fixtures, mocks
- Key files:
  - `conftest.py`: Pytest fixtures (mocked data loaders, config)
  - `test_engine.py`: Query engine tests
  - `test_tools.py`: Tool invocation tests
  - `test_registry.py`: Tool registry tests
  - `test_workflows.py`: End-to-end workflow tests

## Key File Locations

**Entry Points:**
- `src/ct/cli.py`: Main CLI entry point (Typer app)
- `src/ct/ui/terminal.py`: Interactive terminal REPL

**Configuration:**
- `src/ct/agent/config.py`: Configuration schema and loader (reads `~/.ct/config.json`)
- `src/ct/agent/session.py`: Session context (API key, mode, user ID)

**Core Logic:**
- `src/ct/agent/runner.py`: Agentic loop (Agent SDK integration)
- `src/ct/agent/loop.py`: Multi-turn session wrapper
- `src/ct/tools/__init__.py`: Tool registry and decorator
- `src/ct/agent/mcp_server.py`: MCP tool server

**Data Loading:**
- `src/ct/data/loaders.py`: All data loaders (DepMap, PRISM, L1000, etc.)
- `src/ct/data/downloader.py`: Dataset download and update

**LLM Integration:**
- `src/ct/models/llm.py`: LLM client abstraction and cost tracking

**Testing:**
- `tests/conftest.py`: Shared fixtures and mocks
- `tests/test_*.py`: Unit and integration tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `mcp_server.py`, `tool_registry.py`)
- Test files: `test_<module>.py` (e.g., `test_engine.py`, `test_tools.py`)

**Directories:**
- Package directories: `lowercase` (e.g., `agent`, `tools`, `data`)
- Test directories: `tests` (root level)

**Functions & Variables:**
- Functions: `snake_case` (e.g., `load_prism()`, `run_query()`)
- Classes: `PascalCase` (e.g., `AgentRunner`, `ToolRegistry`, `Session`)
- Private/internal: Leading underscore (e.g., `_extract_smiles()`, `_format_tool_result()`)
- Constants: `UPPER_CASE` (e.g., `DEFAULTS`, `MODEL_PRICING`)

**Tool Names:**
- Format: `category.tool_name` (e.g., `chemistry.descriptors`, `expression.l1000_lookup`)
- Example: `@registry.register(name="chemistry.descriptors", category="chemistry", ...)`

## Where to Add New Code

**New Tool:**
1. Determine category (e.g., "genomics", "safety")
2. Add to existing `src/ct/tools/<category>.py` OR create new file if new category
3. Define function, decorate with `@registry.register(name="<category>.<tool>", ...)`
4. Lazy import data loaders inside function: `from ct.data.loaders import load_X`
5. Return `{"summary": "...", ...}` dict
6. Tests: Create `tests/test_<category>.py` if new category, else add to existing

**New Data Loader:**
1. Add function to `src/ct/data/loaders.py`
2. Use `@lru_cache(maxsize=1)` for memoization
3. Check configured path via `Config.get(f"data.<key>")`
4. Fall back to `_find_file()` helper for standard locations
5. Raise `FileNotFoundError` with helpful message if not found

**New CLI Subcommand:**
1. Add to `src/ct/cli.py`
2. Create sub-app with `typer.Typer()` and add to main `app` via `app.add_typer(..., name="<cmd>")`
3. Use `@sub_app.command()` for individual commands
4. Follow pattern: take user input, validate, import module, call function, display result

**Utilities & Helpers:**
- Shared utilities: `src/ct/tools/http_client.py`, `src/ct/tools/_compound_resolver.py`
- Add new helpers as needed; prefer lazy imports in tools to avoid circular dependencies

**Tests:**
- Unit tests: Mirror source structure in `tests/`, e.g., `tests/test_tools.py` for `src/ct/tools/`
- Mocks: Use `@patch("ct.data.loaders.load_X")` to mock data loaders in tests (never load real datasets)
- Fixtures: Add to `tests/conftest.py` for reuse

## Special Directories

**`~/.ct/`:**
- Purpose: User home directory for ct state (not in repo)
- Contains: `config.json` (user settings), `data/` (downloaded datasets), `traces/`, `trajectories/`, `exports/`
- Generated: Yes (created by `Config.load()` and `ct data pull`)
- Committed: No

**`outputs/`:**
- Purpose: Default sandbox output directory (configurable via `sandbox.output_dir`)
- Contains: `reports/` (markdown and HTML), `notebooks/`, trace files
- Generated: Yes (created by report writers)
- Committed: No (usually ignored in .gitignore)

**`tests/fixtures/`:**
- Purpose: Test data and mock objects
- Contains: Small sample CSVs, parquet files, fixture definitions
- Generated: No (committed to repo)
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: GSD (Generative System Design) codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Generated: Yes (by GSD orchestrator)
- Committed: Yes (part of codebase documentation)

---

*Structure analysis: 2026-02-25*
