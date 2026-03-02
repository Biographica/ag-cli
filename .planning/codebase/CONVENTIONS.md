# Coding Conventions

**Analysis Date:** 2026-02-25

## Naming Patterns

**Files:**
- Lowercase with underscores: `target.py`, `clinical.py`, `omics.py`
- Files in `src/ct/tools/` are domain-specific: `repurposing.py`, `cellxgene.py`, `knowledge.py`
- Test files prefixed with `test_`: `test_target.py`, `test_registry.py`

**Functions:**
- Lowercase with underscores: `neosubstrate_score()`, `pipeline_watch()`, `cmap_query()`
- Tool functions defined with `@registry.register()` decorator
- Helper functions prefixed with underscore: `_make_proteomics()`, `_extract_l1000fwd_hits()`, `_downloads_dir()`
- Functions always accept `**kwargs` to support framework tool orchestration

**Variables:**
- Lowercase with underscores: `max_trials`, `gene_signature`, `content_length`
- Private/internal variables prefixed with underscore: `_inflight`, `_to_int()`, `_downloads_dir()`
- Constants in UPPERCASE: `MODEL_PRICING`, `BANNER`, `US_INCIDENCE`, `LINEAGE_TO_CANCER`

**Types and Dataclasses:**
- PascalCase for classes: `Tool`, `ToolRegistry`, `ExecutionResult`, `LLMResponse`, `LLMClient`, `UsageTracker`
- Dataclasses use `@dataclass` decorator: defined in `src/ct/agent/types.py` and `src/ct/models/llm.py`
- Type hints used throughout: `def tool_name(param: str = "default", **kwargs) -> dict:`

## Code Style

**Formatting:**
- Ruff with line length 100 (configured in `pyproject.toml`)
- `line-length = 100`
- `target-version = "py310"`
- No external formatter configured (rely on ruff)

**Linting:**
- Ruff for linting and formatting
- Configuration in `pyproject.toml` under `[tool.ruff]`
- Run locally: `ruff check .` and `ruff format .`

## Import Organization

**Order:**
1. Standard library imports: `import os`, `import json`, `from pathlib import Path`
2. Third-party imports: `import pandas as pd`, `import numpy as np`, `from rich.console import Console`
3. Local imports: `from ct.tools import registry`, `from ct.agent.config import Config`

**Path Aliases:**
- Relative imports used within packages: `from ct.tools import registry`
- Lazy imports for optional dependencies inside function bodies: `from ct.data.loaders import load_proteomics` (inside function, not at top level)
- Domain imports organized by category: `from ct.tools.http_client import request`, `from ct.tools.clinical import trial_search`

**Example pattern from `src/ct/tools/repurposing.py`:**
```python
import numpy as np
from ct.tools import registry
from ct.tools.http_client import request_json
```

**Lazy import example from `src/ct/tools/target.py`:**
```python
if proteomics_path is None:
    try:
        from ct.data.loaders import load_proteomics
        prot = load_proteomics()
    except FileNotFoundError:
        return {"error": "Proteomics data not available.", ...}
```

## Error Handling

**Patterns:**
- Tools always return a dict with a `"summary"` key, never raise exceptions
- Error cases included in return dict: `{"error": "...", "summary": "..."}`
- Data unavailability handled gracefully with fallback flags: `data_unavailable`, `remote_used`, `remote_error`
- Try/except used for optional dependencies and API calls
- Helper functions use defensive checks: `if not query or not query.strip()` before processing

**Example from `src/ct/tools/target.py`:**
```python
try:
    from ct.data.loaders import load_proteomics
    prot = load_proteomics()
except FileNotFoundError:
    return {
        "error": "Proteomics data not available.",
        "summary": "Proteomics data not available — skipping...",
    }
```

**Example from `src/ct/tools/repurposing.py`:**
```python
def _to_float(value):
    """Best-effort float conversion for heterogeneous API payloads."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

## Logging

**Framework:** Python's built-in `logging` module

**Patterns:**
- Module-level logger: `logger = logging.getLogger("ct.module_name")`
- Used in agent and system modules: `logging.getLogger("ct.runner")`, `logging.getLogger("ct.orchestrator")`
- Warnings for recoverable issues: `logger.warning("...")`
- Info for successful operations: `logger.info("...")`
- Errors for failures: `logger.error("...")`
- Configuration in each module: `logger = logging.getLogger(__name__)` pattern not always used; explicit module paths preferred

**Examples from `src/ct/agent/runner.py`:**
```python
logger = logging.getLogger("ct.runner")
logger.warning("Failed to flush trace: %s", e)
logger.error("Agent SDK query failed: %s\n%s", e, traceback.format_exc())
```

## Comments

**When to Comment:**
- Module docstrings describe purpose and public API: `"""Target discovery tools: neosubstrate scoring, degron prediction, co-essentiality."""`
- Complex algorithms get inline comments explaining the formula/logic
- Helper function purposes documented: `"""Best-effort float conversion for heterogeneous API payloads."""`
- Sections marked with comment dividers: `# ─── Config subcommand ────────────────────────────────`

**JSDoc/TSDoc:**
- Not used; plain Python docstrings preferred
- Tool functions include a simple one-line docstring: `def neosubstrate_score(proteomics_path: str = None, top_n: int = 50, **kwargs) -> dict: """Score proteins for neosubstrate potential."""`
- Comprehensive docstrings in dataclass/agent modules: `"""Process an async iterable of SDK messages into structured results."""`

## Function Design

**Size:**
- Functions typically 20–100 lines for tool implementations
- Longer functions (200+ lines) extracted into modules with helpers
- Example: `src/ct/tools/repurposing.py` has many helper functions to keep main tools readable

**Parameters:**
- Tool functions use keyword arguments with defaults: `def cmap_query(gene_signature: dict, mode: str = "reverse", top_n: int = 10, **kwargs) -> dict:`
- Always include `**kwargs` for framework compatibility
- Parameters documented in `@registry.register()` decorator, not in docstring

**Return Values:**
- All tools return a dict with at minimum a `"summary"` key (string)
- Additional keys for structured data: `"top_targets"`, `"hits"`, `"n_proteins_scored"`, `"data_unavailable"`, `"remote_used"`
- Consistent pattern: `return {"summary": "...", "key1": value1, "key2": value2}`

**Example from `src/ct/tools/target.py`:**
```python
return {
    "summary": f"No neosubstrate candidates found in {len(prot)} proteins (none degraded below -0.5 LFC)",
    "top_targets": [],
    "n_proteins_scored": 0,
}
```

## Module Design

**Exports:**
- No `__all__` used; rely on explicit imports via decorator registration
- Tool modules export via `@registry.register()` decorator at function definition
- Public functions not explicitly exported; all public tools registered

**Barrel Files:**
- Not used; imports are explicit
- Each module imports what it needs: `from ct.tools import registry`
- Agent modules import from submodules directly: `from ct.agent.session import Session`

**Organization:**
- Tools grouped by domain: `src/ct/tools/target.py`, `src/ct/tools/clinical.py`, `src/ct/tools/omics.py`
- Agent logic separated: `src/ct/agent/runner.py`, `src/ct/agent/orchestrator.py`, `src/ct/agent/config.py`
- Data loaders isolated: `src/ct/data/loaders.py` (lazy imported in tools)
- UI components grouped: `src/ct/ui/terminal.py`, `src/ct/ui/traces.py`, `src/ct/ui/status.py`

---

*Convention analysis: 2026-02-25*
