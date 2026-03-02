# Architecture

**Analysis Date:** 2026-02-25

## Pattern Overview

**Overall:** Autonomous Agentic Loop with Tool-Based Orchestration

celltype-cli uses a **single-session agentic architecture** powered by the Claude Agent SDK. The agent directly orchestrates all research workflows within a stateless loop that can execute up to 30 tool-use turns per query. Unlike traditional plan-then-execute pipelines, Claude plans and executes concurrently via tool calls.

**Key Characteristics:**
- **Agentic loop**: Claude Agent SDK provides the reasoning loop; no separate planner/executor phases
- **MCP-based tool exposure**: All ~190 domain tools are registered via a custom MCP server and exposed to the agent as callable functions
- **Session-based memory**: Multi-turn interactive mode maintains trajectory (conversation history and results) across queries
- **Async streaming**: Tool execution and streaming is handled via `process_messages()` async iterator
- **Flexible deployment**: CLI (interactive/batch), FastAPI data query endpoint, or headless invocation

## Layers

**Agent Orchestration:**
- Purpose: Main agentic loop that processes queries, handles tool calls, and manages reasoning
- Location: `src/ct/agent/runner.py`, `src/ct/agent/loop.py`, `src/ct/agent/orchestrator.py`
- Contains: `AgentRunner` (SDK client), `AgentLoop` (multi-turn sessions), message processing, trajectory persistence
- Depends on: Claude Agent SDK, MCP server, session/config management
- Used by: CLI (`cli.py`), interactive terminal (`ui/terminal.py`), external callers

**Tool Registry & Execution:**
- Purpose: Central registry of all domain tools; tools are decorated functions that the agent can invoke
- Location: `src/ct/tools/__init__.py` and 44+ tool modules (e.g., `chemistry.py`, `genomics.py`, `expression.py`)
- Contains: `ToolRegistry` class, `Tool` dataclass, 190+ registered functions via `@registry.register()` decorator
- Depends on: Tool implementations (RDKit, BioPython, external APIs), data loaders
- Used by: MCP server (exposes tools to agent), direct CLI invocation (`ct tool run`)

**MCP Server (Model Context Protocol):**
- Purpose: Bridges ct tools to Claude Agent SDK as callable MCP tools
- Location: `src/ct/agent/mcp_server.py`
- Contains: `create_sdk_mcp_server()`, tool handler wrapping, result formatting, JSON schema generation
- Depends on: Tool registry, Claude Agent SDK MCP integration
- Used by: `AgentRunner` to pass tools to the SDK client

**Data Loading Layer:**
- Purpose: Lazy loading of large datasets (DepMap, PRISM, L1000, proteomics) with configurable paths
- Location: `src/ct/data/loaders.py`
- Contains: `load_crispr()`, `load_prism()`, `load_l1000()`, `load_proteomics()`, `load_mutations()`, `load_msigdb()`
- Depends on: Pandas, Parquet/CSV loaders, configured data paths via `Config`
- Used by: Tools that require omics/expression/cell viability data

**LLM Client Abstraction:**
- Purpose: Unified interface for multiple LLM backends (Anthropic, OpenAI, local, CellType models)
- Location: `src/ct/models/llm.py`
- Contains: `LLMResponse`, `UsageTracker`, pricing/cost estimation, provider switching
- Depends on: Individual provider SDKs (claude_agent_sdk, openai, etc.)
- Used by: `AgentRunner` when bypassing Agent SDK (fallback mode)

**Configuration & Session:**
- Purpose: Persistent user settings, API keys, data paths, agent tuning parameters
- Location: `src/ct/agent/config.py`, `src/ct/agent/session.py`
- Contains: `Config` (loads from `~/.ct/config.json`), `Session` (request-scoped context)
- Depends on: dotenv for environment variables
- Used by: All layers; initialized early in CLI startup

**Terminal UI & Interactive Mode:**
- Purpose: Rich terminal interface for multi-turn interactive sessions
- Location: `src/ct/ui/terminal.py`, `src/ct/ui/status.py`, `src/ct/ui/suggestions.py`
- Contains: `InteractiveTerminal` (REPL-style loop), progress spinners, trace rendering
- Depends on: Rich library, `AgentLoop`
- Used by: `ct` command with no arguments (interactive mode)

**Report Generation:**
- Purpose: Transform execution results into markdown and HTML reports
- Location: `src/ct/reports/html.py`, `src/ct/reports/notebook.py`
- Contains: HTML template rendering, Jupyter notebook export
- Depends on: `ExecutionResult` dataclass, Jinja2 templates
- Used by: CLI after query execution, auto-published if configured

**API Endpoint (Data Query):**
- Purpose: FastAPI server for querying large datasets via DuckDB filters
- Location: `src/ct/api/app.py`, `src/ct/api/engine.py`
- Contains: `/query`, `/datasets`, `/health` endpoints, DuckDB query engine
- Depends on: FastAPI, DuckDB, dataset registry
- Used by: External systems querying PerturbAtlas, ChEMBL, etc.

**Knowledge Substrate:**
- Purpose: Domain knowledge ingestion, reasoning, governance
- Location: `src/ct/kb/` (reasoning.py, ingest.py, substrate.py, governance.py)
- Contains: Knowledge base schemas, ingestion pipelines, reasoning augmentation
- Depends on: Data models, validation frameworks
- Used by: Agent system prompts, grounding mechanisms

## Data Flow

**Interactive Query Flow:**

1. User enters query at terminal (or provides via CLI argument)
2. `InteractiveTerminal` or `cli.py` → `AgentLoop.run(query)`
3. `AgentRunner` constructs messages, invokes SDK client with query + MCP tools
4. Claude Agent SDK orchestrates agentic loop:
   - Claude reasons about query and generates tool use blocks
   - SDK invokes MCP tools (wrapped domain tools) with parameters
   - Tool returns results (wrapped in `{"summary": "...", ...}` format)
   - Claude synthesizes results and either calls more tools or finalizes
   - Loop continues until Claude decides complete (up to 30 turns)
5. `process_messages()` collects all tool calls and final text into `ExecutionResult`
6. `AgentLoop` records turn in `Trajectory` (multi-turn memory)
7. `ExecutionResult` → markdown report generation → terminal display + auto-publish HTML

**Tool Execution Flow:**

1. Tool decorator stores metadata (`@registry.register(...)`)
2. MCP server discovers all registered tools and converts to JSON Schema
3. Agent calls tool via MCP with parameters from its reasoning
4. Tool handler extracts parameters, invokes wrapped function with `**kwargs`
5. Function executes:
   - May lazy-load data via `ct.data.loaders` (memoized with @lru_cache)
   - Calls external APIs (PubChem, ChEMBL, UniProt, etc.) via `http_client`
   - Returns `{"summary": "...", ...}` dict
6. MCP server truncates result to 8000 chars, formats for LLM consumption
7. Result flows back to agent as tool result block

**Batch Query Flow:**

1. `ct "your question"` → `AgentRunner.run(query)` (single-turn, no Trajectory)
2. Same as interactive, but no multi-turn memory
3. Report written to `outputs/reports/` by default

**State Management:**

- **Trajectory**: Persisted to `~/.ct/trajectories/{session_id}.jsonl`; loaded on `ct` (resume latest) or `ct resume --id`
- **Traces**: Execution logs written to `~/.ct/traces/{session_id}.trace.jsonl` for debugging
- **Results**: Markdown reports in `sandbox.output_dir/reports/`; HTML in same directory if auto-publish enabled
- **Config**: Singleton `Config` instance loaded from `~/.ct/config.json` at startup; reloaded if explicitly set

## Key Abstractions

**ExecutionResult:**
- Purpose: Encapsulates complete query result (plan, summary, step results, metadata)
- Examples: `src/ct/agent/types.py`
- Pattern: Generated by `AgentRunner`, serialized to markdown and JSON, optionally published as HTML report

**Tool:**
- Purpose: Represents a single domain capability (molecule analysis, gene expression, literature search, etc.)
- Examples: `src/ct/tools/chemistry.py`, `src/ct/tools/genomics.py`, `src/ct/tools/expression.py`
- Pattern: Function decorated with `@registry.register()`, accepts `**kwargs`, returns `{"summary": "...", ...}` dict

**Session:**
- Purpose: Request-scoped context carrying config, mode (batch/interactive), user ID
- Examples: `src/ct/agent/session.py`
- Pattern: Created once at CLI startup, passed through agent/tool layers

**Plan & Step:**
- Purpose: Structured representation of research workflow (legacy/compatibility)
- Examples: `src/ct/agent/types.py`
- Pattern: `Plan` contains list of `Step` objects; each step has tool, args, dependencies, status

## Entry Points

**CLI (main):**
- Location: `src/ct/cli.py`
- Triggers: `ct`, `ct "question"`, `ct config set ...`, `ct data pull ...`, `ct tool list`, etc.
- Responsibilities: Argument parsing (Typer), config initialization, session creation, routing to appropriate subcommand

**Interactive Mode:**
- Location: `src/ct/cli.py` → `InteractiveTerminal` (`src/ct/ui/terminal.py`)
- Triggers: `ct` (no args)
- Responsibilities: REPL loop, multi-turn memory, suggestions, trace display

**Batch Query:**
- Location: `src/ct/cli.py` → `AgentLoop.run(query)` → `AgentRunner.run(query)`
- Triggers: `ct "your question"`
- Responsibilities: Single-turn execution, no trajectory persistence

**API Endpoint:**
- Location: `src/ct/api/app.py`
- Triggers: `uvicorn ct.api.app:app --host 0.0.0.0 --port 8000`
- Responsibilities: Serve `/query`, `/datasets`, `/health` endpoints

**Doctor (health check):**
- Location: `src/ct/cli.py` → `src/ct/agent/doctor.py`
- Triggers: `ct doctor`
- Responsibilities: Validate config, check API keys, test data paths, report issues

## Error Handling

**Strategy:** Graceful degradation with informative error messages. Errors at tool execution layer do not crash the agent; they are caught and returned as failed steps.

**Patterns:**

- **Tool-level errors**: Tool function catches exceptions (e.g., invalid SMILES), returns `{"error": "...", "summary": "..."}`. Agent sees failed step and can retry or pivot.
- **Data loading errors**: Loaders raise `FileNotFoundError` if dataset not found; caught by CLI with helpful message (e.g., "Run: `ct data pull depmap`").
- **SDK errors**: Caught by `AgentRunner._run_async()`, logged to trace, result marked as failed.
- **Config errors**: Caught at startup by `Config.load()` and `ct doctor` command; user is guided to fix via error message.

## Cross-Cutting Concerns

**Logging:** Uses Python `logging` module with per-module loggers (e.g., `ct.runner`, `ct.agent`, `ct.tools.chemistry`). Logs to stderr and optional log files via config.

**Validation:** Input validation happens at tool level (e.g., SMILES validity via RDKit, gene name normalization). Agent prompts tools to validate early; failures are caught and reported.

**Authentication:** LLM API keys stored in config (`~/.ct/config.json`), loaded via `Config.get()`. External API keys (PubChem, UniProt, IBM RXN, etc.) also configurable. `Session` carries API key state.

**Tracing & Observability:**
- `TraceLogger` writes every agent action (query start, tool call, tool result, synthesis) to JSONL for post-execution analysis
- Traces enable debugging, reproducibility, and cost tracking
- `ct trace diagnose` and `ct trace export` provide introspection

---

*Architecture analysis: 2026-02-25*
