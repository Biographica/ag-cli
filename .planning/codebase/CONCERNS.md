# Codebase Concerns

**Analysis Date:** 2026-02-25

## Tech Debt

**Experimental Tool Categories:**
- Issue: `compute` and `cro` categories marked as experimental/TODO — outputs are placeholder or limited
- Files: `src/ct/tools/__init__.py` (lines 15, 121-122, 154-155)
- Impact: Agent may invoke incomplete tools without proper feedback. Users get unexpected results. Tools may silently fail or return stub data.
- Fix approach: Either complete these tool implementations or remove them from the registry. Add runtime warnings when experimental tools are invoked, with fallback mechanisms. Flag in system prompt to avoid these categories unless explicitly requested.

**Broad Exception Handlers in Agent Layer:**
- Issue: 18 instances of `except Exception as e:` across agent orchestration layer — masks specific failures
- Files: `src/ct/agent/runner.py`, `src/ct/agent/mcp_server.py`, `src/ct/agent/system_prompt.py`, `src/ct/agent/trajectory.py`
- Impact: Makes debugging difficult. Tool failures are logged as warnings but don't surface root causes to user. Concurrent thread failures in orchestrator can cascade silently.
- Fix approach: Replace broad `except Exception` with specific exception types (`ValueError`, `FileNotFoundError`, `TimeoutError`). Preserve exception context in logs. Add trace context to help identify which tool/thread failed.

**Data Loader Cache Invalidation Issues:**
- Issue: LRU caches in data loaders (`load_crispr`, `load_l1000`, `load_prism`, `load_proteomics`) use `@lru_cache(maxsize=1)` — cached data persists for entire session
- Files: `src/ct/data/loaders.py` (lines 89-106, 118-143, 193-214)
- Impact: If a dataset is updated or data path changes mid-session, the old cached version continues to be used. Multi-agent runs (ThreadPoolExecutor) all share the same cache — if one thread detects a data path change, other threads don't see it.
- Fix approach: Either clear cache between threads or switch to session-scoped caching instead of process-scoped. Add cache invalidation hook in `Config` when data paths change. Consider adding explicit cache management commands.

**Missing Dataset Handling is Silent:**
- Issue: Tools that require data don't gracefully degrade — FileNotFoundError bubbles up immediately
- Files: `src/ct/tools/biomarker.py` (requires_data declarations), `src/ct/tools/_compound_resolver.py` (lines 209, 275, 295)
- Impact: Agent halts mid-workflow instead of suggesting which datasets are needed or using fallback tools. Users must manually debug dataset issues.
- Fix approach: Add a data availability check phase before invoking tools with `requires_data`. Populate an "available_tools" context into system prompt based on actual data presence, so agent avoids tools that will fail.

## Known Bugs

**LRU Cache Keys Can Be Corrupted by Path Variations:**
- Symptoms: Same dataset loaded twice under different path variations (e.g., `/home/user/data` vs `/home/user/./data`) are cached separately, doubling memory usage
- Files: `src/ct/data/loaders.py` (lines 35-67 path resolution)
- Trigger: User sets data path, then later changes it but old sessions still have old cache entries
- Workaround: Restart the CLI session to clear cache. Explicitly run `ct config set data.base <path>` with normalized path.

**Tool Load Errors are Logged but Not Reported to User:**
- Symptoms: Agent runs normally even though some tool modules failed to import. User doesn't know which tools are unavailable.
- Files: `src/ct/tools/__init__.py` (lines 164-177, 193-195) - `tool_load_errors()` function exists but isn't called at startup
- Trigger: Missing optional dependency (e.g., `rdkit` not installed) causes a tool module import to fail silently
- Workaround: Run `ct doctor` to see which tool modules failed. Check logs with `--debug`.

**Shell Execution Allows Piping to Unsafe Commands:**
- Symptoms: Complex shell pipelines can be constructed that bypass safety checks
- Files: `src/ct/tools/shell.py` (lines 36-70) — regex doesn't catch all dangerous compositions
- Trigger: Attempting `cat file.txt | tee /etc/passwd` or similar (tee is not in `_SAFE_PIPE_RHS`)
- Workaround: Only allow whitelisted combinations. Current whitelist: `head`, `tail`, `grep`, `wc`, `sort`, `uniq`, `cut`, `awk`, `sed`, `cat`, `less`, `more`, `tr`, `tee`, `xargs`.

## Security Considerations

**API Keys Stored in Plain Text in Config:**
- Risk: All sensitive config (API keys, tokens) are stored in `~/.ct/config.json` unencrypted
- Files: `src/ct/agent/config.py` (lines 33, 47, 60-61, 63, 67)
- Current mitigation: File is not world-readable (depends on umask), but any process with user access can read it
- Recommendations:
  1. Add encryption layer (e.g., use keyring library for secrets)
  2. Load secrets from environment variables preferentially (already supports `dotenv`)
  3. Add explicit warning in config display when secrets are present
  4. Add command to validate secrets file permissions

**Shell Tool Can Escalate Through Symlinks and Relative Paths:**
- Risk: Although `sudo` and `rm -rf` are blocked, commands like `python -c` or `bash -c` can still execute arbitrary code
- Files: `src/ct/tools/shell.py` (lines 14-34 blocklist incomplete)
- Current mitigation: Blocklist approach (inherently incomplete), single-pipe allowlist
- Recommendations:
  1. Switch to allowlist model — only permit explicitly safe commands
  2. Add sandbox (containerize shell execution)
  3. Require explicit user confirmation for any shell command invocation

**Subprocess Timeouts Not Enforced Consistently:**
- Risk: Some subprocess calls have timeouts (`subprocess.run` with `timeout=120`), others don't
- Files: `src/ct/tools/structure.py` (lines 54, 105, 241, 425) — some have timeouts, some don't. Popen (line 105) has no timeout.
- Current mitigation: Process limits and memory limits at OS level if configured
- Recommendations:
  1. Audit all subprocess calls for timeout
  2. Add global timeout config with per-category overrides
  3. Implement proper signal handling for cleanup

**JSON Deserialization Without Validation:**
- Risk: Tool results are dicts that are json.dumps'd and json.loads'd without schema validation
- Files: `src/ct/agent/trajectory.py` (line 123) — `json.JSONDecodeError` is caught but malformed data isn't validated
- Current mitigation: Tools are trusted to return valid dicts
- Recommendations:
  1. Add Pydantic models for all tool result types
  2. Validate result dicts against schema before serializing
  3. Add pre-flight validation in MCP tool handler

## Performance Bottlenecks

**Multi-Agent Orchestrator Shares LRU Cache Across ThreadPoolExecutor:**
- Problem: Multiple research threads load the same datasets (DepMap, PRISM, L1000) independently, but LRU cache means the first thread locks the dataset in memory for all threads
- Files: `src/ct/agent/orchestrator.py` (lines 354-497), shared cache in `src/ct/data/loaders.py`
- Cause: Python's `@lru_cache` is thread-safe (uses global lock) but only caches at function level, not at matrix level. Threads block each other waiting for I/O.
- Improvement path:
  1. Pre-load datasets before spawning thread pool (eliminate contention)
  2. Switch to read-only numpy/pandas sharing (via `multiprocessing.managers.SyncManager`)
  3. Lazy-load per-thread with separate cache instances
  4. Profile actual contention: check if this is real bottleneck vs. premature optimization

**Large Tool Files Have Linear Import Time:**
- Problem: `omics.py` (3330 lines), `data_api.py` (2114 lines), `genomics.py` (1387 lines) take time to import
- Files: `src/ct/tools/omics.py`, `src/ct/tools/data_api.py`, `src/ct/tools/genomics.py`
- Cause: All 44 tool modules are imported upfront during `_load_tools()` even if only 1-2 are used per query
- Improvement path:
  1. Implement lazy import per tool (only import when invoked)
  2. Split massive modules into submodules (e.g., `omics/geo.py`, `omics/cellxgene.py`, `omics/gdc.py`)
  3. Add startup profiling to identify slowest imports
  4. Consider stub generation for fast registry population without full imports

**Synchronous Tool Execution Blocks Event Loop:**
- Problem: MCP server runs tools via `asyncio.to_thread`, but tools themselves may be blocking (network I/O, file I/O, subprocess)
- Files: `src/ct/agent/mcp_server.py` (lines 135, 200, 318) — offload to thread but no pooling strategy
- Cause: Each tool invocation spawns a new thread. No backpressure or queue depth limits.
- Improvement path:
  1. Add explicit `ThreadPoolExecutor` with bounded queue in MCP server
  2. Implement per-tool timeout enforcement with cancellation
  3. Monitor thread pool depth and warn if saturated

**Large DataFrame Operations in Memory:**
- Problem: Data loaders return full matrices without pagination. Tools like biomarker scoring iterate over entire PRISM matrix (>300K compounds × >700 cell lines)
- Files: `src/ct/data/loaders.py` (lines 89-214), `src/ct/tools/biomarker.py` — no chunking
- Cause: No streaming/chunking strategy. Everything is eagerly loaded into RAM.
- Improvement path:
  1. Add optional chunking parameters to data loaders
  2. Implement incremental result streaming for large operations
  3. Add memory profiling to identify peak usage
  4. Consider DuckDB or Polars lazy evaluation for large operations

## Fragile Areas

**Tool Parameter Type Coercion is Lossy:**
- Files: `src/ct/agent/mcp_server.py` (lines 113-132)
- Why fragile: MCP sends all params as strings. Code tries `int()`, then `float()`, then boolean. If a tool expects a list but gets a string, this fails silently with a type mismatch.
- Safe modification:
  1. Add explicit type hints to all tool parameter definitions (not just descriptions)
  2. Use Pydantic for validation
  3. Call tool with validated args, raise clear error if coercion fails
- Test coverage: No test for invalid parameter type coercion

**Agent Planner Prompt Injection Via Tool Descriptions:**
- Files: `src/ct/tools/__init__.py` (lines 133-156) — tool descriptions are directly embedded in system prompt without escaping
- Why fragile: If a tool's description contains `<injection>` or prompt directives, it could affect agent behavior
- Safe modification:
  1. Add prompt injection detection/escaping before embedding
  2. Use structured prompt format (XML, JSON) instead of string interpolation
- Test coverage: No injection test

**Orchestrator Thread Failure Can Cause Deadlock:**
- Files: `src/ct/agent/orchestrator.py` (lines 354-497) — uses threading.Lock() around shared state updates
- Why fragile: If a thread raises an exception while holding the lock, the lock is released via exception handler (line 362 has `state_lock`) but subsequent threads might wait forever
- Safe modification:
  1. Use context managers (`with state_lock:`) exclusively
  2. Add timeout to lock acquisitions
  3. Add unit test for thread exception during lock hold
- Test coverage: `test_orchestrator.py` exists but doesn't test exception paths

**Config File Corruption Could Cause Startup Failure:**
- Files: `src/ct/agent/config.py` (lines 340-345) — JSON parsing with recovery to defaults
- Why fragile: If user manually edits config.json and adds syntax error, the entire app fails to start
- Safe modification:
  1. Add JSON schema validation
  2. Auto-backup before each save
  3. Add `ct config repair` command to recover from corruption
  4. Show helpful error message with line number on parse failure
- Test coverage: No test for malformed JSON

**Test Coverage Gaps:**
- Issues: 62 test files vs 85 source files, but critical paths under-tested:
  - `src/ct/agent/mcp_server.py` — MCP tool handler exception paths (no test for tool errors)
  - `src/ct/data/loaders.py` — path resolution fallbacks, missing file handling (uses mock paths in tests)
  - `src/ct/agent/orchestrator.py` — multi-threaded execution, thread failure scenarios
  - `src/ct/tools/shell.py` — security blocklist edge cases (no tests for pipe safety)
  - `src/ct/api/` — API endpoints (minimal test coverage)
- Files: Most of `src/ct/api/` has no corresponding test
- Risk:
  - MCP handler failures don't bubble up correctly
  - Data loading fallbacks untested in integration
  - Shell command blocklist regressions
  - API endpoint bugs go undetected
- Priority: High — add integration tests for critical paths before next release

## Scaling Limits

**Maximum Concurrent Agents Limited by Config:**
- Current capacity: `agent.parallel_max_threads` default = 5 threads
- Limit: ThreadPoolExecutor spawns one future per thread, each loading full datasets. At 5 threads × 3GB per dataset = 15GB+ memory needed.
- Scaling path:
  1. Implement dataset reference counting to share across threads
  2. Add memory budget enforcement (fail gracefully if exceeded)
  3. Use process pool instead of thread pool for true parallelism
  4. Document recommended limits for different hardware profiles

**Tool Registry Can Grow Without Bound:**
- Current capacity: 44 tool modules, ~190+ individual tools registered
- Limit: MCP tool list discovery is O(N), system prompt embedding is O(N tools × M chars per description)
- Scaling path:
  1. Implement tool categorization and selective loading (agent requests only relevant tools)
  2. Add tool aliasing to reduce redundancy
  3. Split tool descriptions to separate "full" vs "compact" modes
  4. Cache MCP tool list after first discovery

## Dependencies at Risk

**Optional Dependencies Without Graceful Degradation:**
- Risk: Tools assume `rdkit`, `biopython`, `pandas`, `numpy` are available, but ImportError handling doesn't provide fallback
- Impact: User invokes `chemistry.smiles_similarity` but rdkit isn't installed → immediate error instead of helpful message suggesting tool alternative
- Files: `src/ct/tools/chemistry.py`, `src/ct/tools/protein.py`, `src/ct/tools/structure.py` (scattered ImportError handlers)
- Migration plan:
  1. Implement a "tool availability checker" that runs at startup
  2. Populate system prompt with only available tools
  3. Add clear error message: "This tool requires rdkit. Install: pip install rdkit-pypi" with suggested alternative tools

**Pinned vs Floating Dependencies in pyproject.toml:**
- Risk: Claude Agent SDK and core dependencies (anthropic, pandas) are likely pinned to specific versions but exact pins unknown without viewing pyproject.toml
- Impact: Breaking API changes in upstream packages could cause incompatibilities
- Recommendations:
  1. Add upper bound constraints (e.g., `anthropic >= 0.20, < 1.0`)
  2. Implement dependency update bot (Dependabot)
  3. Add CI/CD step to test against latest compatible versions quarterly

## Missing Critical Features

**No Request Timeout at Agent Level:**
- Problem: Individual tools have timeouts, but orchestrator doesn't enforce a wall-clock timeout for entire research query
- Blocks: Long-running queries can hang indefinitely. No graceful degradation.
- Impact: Users stuck waiting without knowing if the process is hung or still computing
- Workaround: Kill process manually with Ctrl+C
- Recommendation: Add `--timeout` flag to main query commands, configurable via `ct config set agent.timeout`

**No Audit Trail for Multi-Agent Runs:**
- Problem: Orchestrator executes parallel threads but doesn't log which thread produced which result
- Blocks: Reproducing results, understanding which agent angle found key evidence
- Files: `src/ct/agent/orchestrator.py` (lines 62-73 ThreadResult tracks thread_id but not logged consistently)
- Recommendation: Add per-thread trace export, aggregate into single timeline report

**No Incremental Save for Long Queries:**
- Problem: If query is interrupted mid-execution, all results are lost
- Blocks: Large discovery workflows cannot be resumed
- Recommendation: Auto-save session state every N steps, implement resume command

## Summary of Priority Fixes

**Immediate (High Risk):**
1. Replace broad `except Exception` handlers with specific types
2. Implement data availability check before tool invocation
3. Add JSON validation for tool results
4. Audit and add timeouts to all subprocess calls

**Short-term (Medium Risk):**
1. Complete or remove experimental tool categories
2. Add thread-safe data loader caching
3. Add comprehensive test coverage for orchestrator exception paths
4. Implement shell command execution sandbox

**Long-term (Scaling/Tech Debt):**
1. Lazy-load tool modules
2. Split massive tool files into submodules
3. Implement dataset reference counting for multi-agent runs
4. Add audit trail and incremental state save
5. Encrypt config file secrets

---

*Concerns audit: 2026-02-25*
