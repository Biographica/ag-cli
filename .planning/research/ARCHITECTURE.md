# Architecture Patterns

**Domain:** Agricultural biotech target identification platform (agentic + deterministic pipeline)
**Researched:** 2026-02-25
**Confidence:** MEDIUM — derived from available project specifications, CLAUDE.md codebase instructions, and established patterns for hybrid agentic/deterministic systems. WebSearch unavailable during this research session; findings rely on project context and training knowledge.

---

## Recommended Architecture

### Two-Layer System: Engine + Framework

```
┌─────────────────────────────────────────────────────────────┐
│  FRAMEWORK LAYER  (shortlist/ package)                      │
│                                                             │
│  PipelineRunner ──► StageOrchestrator ──► ScoringEngine     │
│       │                   │                    │            │
│  EvidenceStream       AgentBridge          ScoreStore       │
│  (transform DSL)      (per-stage)          (SQLite)         │
└───────────────────────────┬─────────────────────────────────┘
                            │ imports only
┌───────────────────────────▼─────────────────────────────────┐
│  ENGINE LAYER  (ag-cli / ct/ package)                       │
│                                                             │
│  ToolRegistry ──► MCPServer ──► AgentRunner                 │
│       │                              │                      │
│  DomainFilter                   ClaudeSDKClient             │
│  (category-based)               (agentic loop)              │
│       │                                                     │
│  DataLoaderCache                                            │
│  (local-first, lazy)                                        │
└─────────────────────────────────────────────────────────────┘
```

**Dependency rule:** framework imports from engine. Engine never imports from framework. This is non-negotiable for maintaining modularity and preventing circular dependencies.

---

## Component Boundaries

| Component | Layer | Responsibility | Communicates With |
|-----------|-------|---------------|-------------------|
| `ToolRegistry` | Engine | Registers all tools via `@registry.register()` decorator, stores metadata | `MCPServer`, `DomainFilter` |
| `DomainFilter` | Engine | Filters registered tools by category/domain tags for a given pipeline stage | `MCPServer` (tells it which tools to expose) |
| `MCPServer` | Engine | In-process MCP server; exposes filtered tool subset to Claude | `AgentRunner`, `ToolRegistry` |
| `AgentRunner` | Engine | Wraps `ClaudeSDKClient`; executes agentic loop up to N turns; returns structured output | `MCPServer`, `ClaudeSDKClient` |
| `DataLoaderCache` | Engine | Lazy-loads bulk datasets (PRISM, DepMap equivalents for plant science); caches in memory | All tools that call `load_X()` |
| `AgentBridge` | Framework | Calls `AgentRunner` with a domain-filtered tool set; extracts evidence from agent output | `PipelineRunner`, `AgentRunner` |
| `StageOrchestrator` | Framework | Sequences pipeline stages; manages stage dependencies and pass/fail conditions | `AgentBridge`, `ScoringEngine` |
| `EvidenceStream` | Framework | Collects raw agent findings; applies transform DSL to normalize into scored evidence units | `ScoringEngine`, `AgentBridge` |
| `ScoringEngine` | Framework | Applies deterministic scoring formula (weighted sum, penalties, thresholds) to evidence | `ScoreStore`, `EvidenceStream` |
| `ScoreStore` | Framework | Persists candidate scores, evidence, and run provenance (SQLite or equivalent) | `ScoringEngine`, `PipelineRunner` |
| `PipelineRunner` | Framework | Top-level entrypoint; reads pipeline config; drives `StageOrchestrator`; produces final shortlist | `StageOrchestrator`, `ScoreStore` |

---

## Data Flow

### High-Level Flow

```
User Query / Pipeline Config
         │
         ▼
  PipelineRunner
  (reads config, instantiates stages)
         │
         ▼ for each stage
  StageOrchestrator
  (resolves stage order, gate conditions)
         │
         ├──► AgentBridge
         │         │
         │         ├──► DomainFilter (selects tools for this stage's domain)
         │         │
         │         ├──► MCPServer (exposes filtered tools)
         │         │
         │         └──► AgentRunner (agentic loop: Claude plans → calls tools → synthesizes)
         │                   │
         │              structured findings dict
         │                   │
         ▼                   ▼
  EvidenceStream ◄──── raw evidence units
  (transform DSL normalizes, tags, weights)
         │
         ▼
  ScoringEngine
  (deterministic formula: weighted sum of evidence signals)
         │
         ▼
  ScoreStore
  (persist candidate + score + provenance)
         │
         ▼ after all stages complete
  PipelineRunner
  (rank candidates, apply cutoff, emit shortlist)
         │
         ▼
  Report / Output
```

### Tool Call Data Flow (within Engine)

```
AgentRunner → MCPServer (tool call request)
MCPServer   → ToolRegistry (look up tool function)
ToolRegistry→ tool function (executes)
tool function → DataLoaderCache (lazy load if needed)
DataLoaderCache → local filesystem (bulk dataset files)
tool function → returns dict with "summary" key
MCPServer   → AgentRunner (tool result)
AgentRunner → Claude (tool result in context)
```

---

## Patterns to Follow

### Pattern 1: Domain-Based Tool Filtering at MCP Server Instantiation

**What:** Each pipeline stage specifies a `domain` (e.g., `"genomics"`, `"phenomics"`, `"literature"`, `"cheminformatics"`). Before invoking `AgentRunner`, the framework calls `DomainFilter.filter(domain)` which returns the subset of registered tools whose category matches. The MCP server is instantiated (or reconfigured) with only those tools exposed.

**When:** Every time `AgentBridge` invokes an agent for a pipeline stage.

**Why:** Prevents tool bloat from confusing the agent (190+ tools become 20-30 relevant ones). Reduces token usage. Keeps stage behavior predictable and auditable.

**Example:**
```python
# In DomainFilter (engine layer)
class DomainFilter:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def filter(self, domain: str) -> list[ToolSpec]:
        """Return tools whose category matches domain."""
        return [
            tool for tool in self.registry.all_tools()
            if tool.category == domain or domain in tool.tags
        ]

# In AgentBridge (framework layer)
class AgentBridge:
    def run_stage(self, stage_config: StageConfig) -> AgentFindings:
        filtered_tools = self.domain_filter.filter(stage_config.domain)
        runner = AgentRunner(tools=filtered_tools, max_turns=stage_config.max_turns)
        return runner.run(stage_config.prompt)
```

**Confidence:** HIGH — direct extension of existing `@registry.register(category=...)` pattern in CLAUDE.md.

---

### Pattern 2: Local-First Data Loader with Lazy Initialization

**What:** All bulk datasets (genome databases, expression atlases, compound libraries) are downloaded once to a local cache directory. Tools use `load_X()` functions that check cache existence before loading. The `DataLoaderCache` singleton holds in-memory references after first load.

**When:** Any tool that touches a dataset.

**Why:** Agricultural datasets (e.g., plant genome databases, crop expression atlases) can be multi-GB. Network calls during an agentic loop add latency and introduce failure modes. Local-first makes the loop deterministic and fast.

**Example:**
```python
# In engine data layer (ct/data/loaders.py)
_cache: dict[str, Any] = {}

def load_crop_expression(species: str = "arabidopsis") -> pd.DataFrame:
    """Load crop expression atlas. Lazy: loads once, caches in memory."""
    key = f"crop_expression_{species}"
    if key not in _cache:
        path = DATA_DIR / f"{species}_expression.parquet"
        if not path.exists():
            raise DataNotPulledError(
                f"Run `ct data pull {species}-expression` first"
            )
        _cache[key] = pd.read_parquet(path)
    return _cache[key]

# In tool (ct/tools/genomics.py)
@registry.register(name="genomics.expression_profile", category="genomics", ...)
def expression_profile(gene_id: str, **kwargs) -> dict:
    df = load_crop_expression()  # lazy, cached
    ...
```

**Confidence:** HIGH — mirrors existing `load_X` pattern from CLAUDE.md.

---

### Pattern 3: Pipeline Stage as Agentic Unit

**What:** Each pipeline stage is an isolated agentic sub-task. The `StageOrchestrator` defines stage dependency order. Each stage receives: a natural language prompt (templated from pipeline config + prior stage outputs), a domain filter, and a max-turns budget. The stage produces a structured `AgentFindings` dict.

**When:** All pipeline stages.

**Why:** Isolating each stage as its own agentic loop prevents context window overflow across the full pipeline (which might span genomics → phenomics → literature → cheminformatics). It also enables stage-level caching/replay and deterministic re-scoring without re-running agents.

**Example:**
```python
# Pipeline config (YAML)
stages:
  - name: target_discovery
    domain: genomics
    max_turns: 20
    prompt_template: |
      Identify candidate genes for {trait} in {species}.
      Focus on: {focus_criteria}
    gate:
      min_candidates: 5

  - name: phenomics_validation
    domain: phenomics
    depends_on: [target_discovery]
    max_turns: 15
    prompt_template: |
      For each candidate from target_discovery:
      {candidates}
      Assess phenotypic evidence for {trait} association.
```

**Confidence:** MEDIUM — established pattern in multi-agent orchestration (LangGraph, CrewAI style), applied to this codebase's single-agentic-loop approach.

---

### Pattern 4: Evidence Stream with Transform DSL

**What:** Agent findings are raw text/dicts. The `EvidenceStream` applies a transform pipeline to normalize them into typed `EvidenceUnit` objects: `{source, type, signal_value, confidence, candidate_id}`. The transform DSL supports: `extract(field)`, `normalize(min, max)`, `weight(factor)`, `filter(predicate)`, `tag(label)`.

**When:** Between `AgentBridge` output and `ScoringEngine` input.

**Why:** Decouples the agent (which produces variable-format text/dicts) from the scorer (which needs structured numeric inputs). Allows scoring formula to change without touching agent prompts, and vice versa.

**Example:**
```python
# Transform DSL definition (in pipeline config or code)
evidence_transforms = EvidenceStreamConfig(
    transforms=[
        Extract("gwas_hits", from_field="genomics.associations"),
        Normalize(0, 1, method="minmax"),
        Weight(factor=0.35),
        Tag("genetic_evidence"),
        Filter(lambda e: e.confidence > 0.3),
    ]
)

# EvidenceUnit (typed)
@dataclass
class EvidenceUnit:
    candidate_id: str
    source: str          # e.g., "genomics.expression_profile"
    evidence_type: str   # e.g., "genetic_evidence"
    signal_value: float  # normalized 0-1
    confidence: float    # 0-1
    raw: dict            # original agent output, for provenance
```

**Confidence:** MEDIUM — transform pipeline pattern is well-established in ETL and ML feature engineering; DSL approach adds project-specific structure.

---

### Pattern 5: Deterministic Scoring Engine with Weighted Sum

**What:** The `ScoringEngine` applies a deterministic formula over collected `EvidenceUnit` objects per candidate. The formula is a weighted sum across evidence types, with optional penalty terms and threshold gates. Formula parameters are configuration, not code.

**When:** After all evidence for a candidate has been collected (either per-stage or final aggregation).

**Why:** Scoring must be reproducible, auditable, and explainable for a biotech shortlisting context. Free-form agent synthesis is not sufficient — downstream decisions (field trials, investment) require traceable numerical justification.

**Example:**
```python
# Scoring formula (deterministic, config-driven)
class ScoringEngine:
    def score(self, candidate_id: str, evidence: list[EvidenceUnit]) -> CandidateScore:
        # Group by evidence_type
        by_type = group_by_type(evidence)

        # Weighted sum
        raw_score = sum(
            self.weights[e.evidence_type] * e.signal_value
            for e in evidence
            if e.evidence_type in self.weights
        )

        # Penalty terms (e.g., off-target risk, poor druggability)
        penalties = sum(
            self.penalties[e.evidence_type] * e.signal_value
            for e in evidence
            if e.evidence_type in self.penalties
        )

        final_score = raw_score - penalties

        return CandidateScore(
            candidate_id=candidate_id,
            score=final_score,
            breakdown=by_type,      # per-type contribution for explainability
            evidence_count=len(evidence),
        )

# Config-driven weights (not hardcoded)
weights:
  genetic_evidence: 0.35
  phenomics_evidence: 0.25
  literature_evidence: 0.20
  pathway_evidence: 0.15
  orthology_evidence: 0.05

penalties:
  off_target_risk: 0.10
  low_expressivity: 0.05
```

**Confidence:** HIGH — standard weighted-sum scoring for target prioritization is the industry norm in drug/ag-chem discovery pipelines.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Framework Importing from Engine at Runtime (Dependency Inversion Violation)

**What:** Framework code calling engine internals other than the public API (`AgentRunner`, `ToolRegistry`, `DomainFilter`, data loaders).

**Why bad:** Creates circular dependency risk, makes engine layer impossible to use standalone (e.g., for `ct` CLI without the full shortlist pipeline), and couples the two layers tightly.

**Instead:** Engine exposes a clean public API. Framework only calls that API. Any shared types (e.g., `AgentFindings`) live in the engine layer and are imported upward.

---

### Anti-Pattern 2: Running the Full Tool Set per Agent Stage

**What:** Exposing all 190+ tools to the agent on every pipeline stage invocation.

**Why bad:** Token cost of tool definitions in the context window is substantial at 190+ tools. Agent confusion increases — it may call genomics tools during a phenomics stage. Auditability suffers because it's unclear which tools were "in scope."

**Instead:** Use `DomainFilter` to expose 15-30 tools per stage based on the stage's declared domain.

---

### Anti-Pattern 3: Embedding Scoring Logic in Agent Prompts

**What:** Asking Claude to apply numerical weights and produce a final score in free-form text, then parsing that output.

**Why bad:** Non-deterministic. Two runs with identical inputs can produce different scores. Unparseable if Claude changes output format. Unauditable for regulatory/commercial contexts.

**Instead:** Agent produces evidence (qualitative + quantitative findings). Deterministic `ScoringEngine` applies formula to that evidence.

---

### Anti-Pattern 4: Loading Full Datasets at Import Time

**What:** `from ct.data.loaders import crop_expression_df` at module top level, where `crop_expression_df` is a DataFrame computed at import.

**Why bad:** Multi-second startup on every `ct` invocation, even for commands that don't need data. Tests cannot mock loaders easily.

**Instead:** Lazy `load_X()` functions called inside tool bodies. `DataLoaderCache` holds references after first call.

---

### Anti-Pattern 5: Single Monolithic Agentic Session for Full Pipeline

**What:** One Claude session, one context window, running all pipeline stages sequentially.

**Why bad:** A full ag-biotech pipeline (genomics → phenomics → literature → cheminformatics → pathway) could require hundreds of tool calls and tens of thousands of tokens of intermediate state. Context window limits become a hard ceiling.

**Instead:** Each stage is its own isolated `AgentRunner` session. Stage outputs are structured dicts, not raw context. `StageOrchestrator` passes only the relevant subset of prior-stage outputs as prompt context to the next stage.

---

## Component Build Order

Components must be built in dependency order. The engine layer is built first; the framework layer builds on top.

```
Phase 1 — Engine Foundation
  1. ToolRegistry (already exists, extend with plant science categories)
  2. DataLoaderCache + load_X() functions for plant datasets
  3. DomainFilter (new — category-based tool subset selection)
  4. MCPServer refactor (accept filtered tool list at instantiation)
  5. AgentRunner public API stabilization (clean interface for framework to call)

Phase 2 — Framework Scaffolding
  6. EvidenceUnit type definitions (shared data contract)
  7. AgentBridge (calls engine AgentRunner, extracts structured findings)
  8. EvidenceStream + transform DSL (normalize agent output → EvidenceUnits)
  9. ScoringEngine (deterministic formula, config-driven weights)
  10. ScoreStore (SQLite persistence layer)

Phase 3 — Pipeline Orchestration
  11. StageOrchestrator (stage sequencing, gate conditions, dependency resolution)
  12. PipelineRunner (top-level entrypoint, config loading, final shortlist output)
  13. Pipeline config schema (YAML/TOML validation, stage templates)

Phase 4 — Integration + CLI
  14. `shortlist` CLI commands (run pipeline, show scores, explain candidate)
  15. End-to-end integration tests with mocked agents and loaders
```

**Rationale for this order:**
- `ToolRegistry` and `DataLoaderCache` are the root dependencies — everything else builds on them.
- `DomainFilter` must exist before `AgentBridge` can be written.
- `EvidenceUnit` type must be stable before `EvidenceStream` and `ScoringEngine` can be written — it is the data contract between them.
- `ScoringEngine` and `ScoreStore` must exist before `StageOrchestrator` can aggregate across stages.
- `PipelineRunner` is last because it depends on all orchestration components being complete.

---

## How the Agentic Loop and Deterministic Pipeline Coexist

The coexistence is achieved through strict role separation and a typed hand-off contract:

```
AGENTIC (Claude):                HAND-OFF:              DETERMINISTIC:
- Interprets biology             EvidenceUnit[]         - Applies formula
- Calls domain tools                                    - Computes scores
- Synthesizes findings      ◄── typed, normalized ──►  - Ranks candidates
- Handles ambiguity              evidence dicts         - Applies thresholds
- Follows research threads                             - Produces shortlist
- NOT responsible for scoring                          - NOT responsible for
                                                         biological reasoning
```

**The contract is `EvidenceUnit`** — a typed, normalized struct that carries a signal value (float 0-1), confidence, source, and type. The agent produces evidence; the scorer consumes it. Neither layer needs to understand the internals of the other.

**Re-scoring without re-running agents:** Because `EvidenceUnit` objects are persisted in `ScoreStore`, you can change scoring weights and re-run `ScoringEngine` against stored evidence without invoking Claude again. This is critical for tuning the pipeline without burning agent API costs.

**Prompt seeding with prior scores:** `StageOrchestrator` can include top candidates from prior stage scores in the prompt template for the next stage agent, creating a feedback loop where the deterministic scorer informs agent focus. This is "structured guidance" not "agent control."

---

## Scalability Considerations

| Concern | At 10 candidates | At 1,000 candidates | At 100,000 candidates |
|---------|-----------------|--------------------|-----------------------|
| Agent invocations | 1 session/stage | Batch by candidate group | Async parallel sessions |
| Scoring | In-memory, trivial | In-memory or SQLite | SQLite with indexes or Postgres |
| Data loading | Single-process cache | Single-process cache | Shared memory or Arrow IPC |
| Context window | Not a concern | Stage isolation required | Stage isolation + chunked prompts |
| Provenance storage | SQLite | SQLite | Partitioned SQLite or DuckDB |

For the MVP (agricultural target identification, typically 10-500 candidate genes), the single-process in-memory approach with SQLite persistence is sufficient and avoids premature complexity.

---

## Key Interfaces (Public API Surface)

### Engine Public API (what framework calls)
```python
# Tool registration (used by tool authors)
registry.register(name, description, category, parameters, requires_data)

# Domain filtering (used by AgentBridge)
DomainFilter(registry).filter(domain: str) -> list[ToolSpec]

# Agent execution (used by AgentBridge)
AgentRunner(tools, max_turns, system_prompt).run(query: str) -> AgentFindings

# Data loading (used by tools internally)
load_X(species: str, **kwargs) -> pd.DataFrame
```

### Framework Public API (what CLI/user calls)
```python
# Pipeline execution
PipelineRunner(config_path).run(query: str, candidates: list[str]) -> Shortlist

# Score inspection
ScoreStore(db_path).get_scores(run_id) -> list[CandidateScore]
ScoreStore(db_path).get_evidence(candidate_id, run_id) -> list[EvidenceUnit]

# Re-scoring with new weights
ScoringEngine(weights_config).rescore(run_id, score_store) -> list[CandidateScore]
```

---

## Sources

- CLAUDE.md codebase instructions (tool registry pattern, MCP server structure, `load_X()` convention) — HIGH confidence
- Milestone context specification (two-layer engine/framework separation, 5 architectural challenges) — HIGH confidence
- Established patterns: ETL transform pipelines, weighted-sum scoring in target prioritization, multi-agent stage isolation (training knowledge, not externally verified in this session) — MEDIUM confidence
- Anti-patterns: derived from known failure modes in LLM agent systems (context overflow, non-deterministic scoring, import-time data loading) — MEDIUM confidence

**Note:** WebSearch was unavailable during this research session. Findings are based on project specifications and established software architecture principles. External verification of specific library choices (e.g., MCP Python SDK tool filtering APIs, SQLite provenance patterns) should be done during implementation phases.
