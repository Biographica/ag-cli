# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Working Plant Science Agent

**Shipped:** 2026-03-02
**Phases:** 7 | **Plans:** 17 | **Timeline:** 7 days (2026-02-25 → 2026-03-02)

### What Was Built
- Plant science agent identity (Harvest) with runtime pharma tool filtering at MCP layer
- Species-agnostic data infrastructure: YAML registry (20+ species), manifest system, @validate_species decorator
- External API connectors: STRING plant PPI, PubMed plant search, Lens.org patent search
- Plant genomics tools: gene annotation, ortholog mapping with phylogenetic weighting, co-expression, GFF3 parsing, GWAS/QTL lookup
- CRISPR gene editing assessment: guide design with PAM scanning, editability scoring, paralogy scoring
- Multi-species evidence gathering orchestration (6 tools x N genes)

### What Worked
- **Fork-first approach:** Inheriting celltype-cli's agentic architecture (agent loop, MCP server, sandbox, session management) saved weeks of infrastructure work. Every v1.0 tool plugged directly into the existing `@registry.register()` pattern.
- **Allowlist over blocklist:** PLANT_SCIENCE_CATEGORIES frozenset meant new unknown tool categories default to hidden — safer for domain swap.
- **Integration audit loop:** Running `/gsd:audit-milestone` after initial phases caught wiring issues (species default form mismatch, parity YAML drift, CLI routing bug) that would have been painful to discover later. Two inserted decimal phases (2.1, 2.2) fixed these cleanly.
- **Lazy import pattern:** Keeping data-heavy imports inside function bodies made tools fast to register and easy to mock in tests.
- **Disk TTL cache:** Shared `_api_cache.py` module provided consistent caching across all Phase 3-5 API tools with zero duplication.

### What Was Inefficient
- **Species registry needed 3 iterations:** Initial `_species.py` used inline dicts, then YAML backing was added (Phase 2), then integration fixes were needed (Phases 2.1, 2.2) to wire YAML registry through all consumers. Starting with YAML-first would have saved 2 phases.
- **PlantExp download URLs still None:** The downloader has placeholder URLs. Data must be manually placed. This is acceptable for v1.0 but will need addressing for onboarding new users.
- **Test count inflation:** 139 tests pass, but some are effectively integration tests that require careful mocking. The e2e tests (gated behind `--run-e2e`) are the most valuable but rarely run.

### Patterns Established
- **Tool registration:** `@registry.register(name="category.tool_name", ...)` with `**kwargs`, lazy imports, dict return with `"summary"` key
- **Species resolution:** `from ct.tools._species import resolve_species_taxon, resolve_species_binomial` — all tools use this
- **API caching:** `from ct.tools._api_cache import cached_api_call` — JSON disk cache with configurable TTL
- **Test mocking:** Patch source modules (`ct.tools._species`, `ct.tools.http_client`) not tool namespaces — lazy imports mean names don't exist at module level
- **Organism validation:** `@validate_species` decorator on data access tools — validates before execution

### Key Lessons
1. **Integration audits catch what unit tests miss.** The milestone audit found 4 cross-phase wiring issues (species form mismatch, standalone dicts, CLI routing, missing dependency) that all had passing unit tests. The lesson: run integration checks early and after every phase that touches shared infrastructure.
2. **YAML registries > inline dicts** for any data that multiple modules reference. The species registry consolidation eliminated a class of drift bugs.
3. **Decimal phases work well** for urgent insertions. Phases 2.1 and 2.2 were scoped tightly, executed fast (6-8 min each), and didn't disrupt the broader milestone numbering.
4. **MCP-layer filtering is the right level** for domain control. Soft filters (prompt instructions) would have leaked pharma tools. Hard MCP exclusion means the agent literally cannot see them.

### Cost Observations
- Model mix: Balanced profile (GSD agents used sonnet/haiku for research/planning; opus for execution)
- Sessions: ~10 sessions across 7 days
- Notable: Phase 2 plans averaged 4 min each — data infrastructure was well-understood. Phase 1 plans averaged 36 min — system prompt and filtering required more exploration.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 7 days | 7 (5 planned + 2 inserted) | First milestone; established tool registration, species resolution, and testing patterns |

### Cumulative Quality

| Milestone | Tests | Requirements | Audit Score |
|-----------|-------|--------------|-------------|
| v1.0 | 139 pass (3 e2e gated) | 20/20 | 20/20 req, 7/7 phases, 20/20 integration, 4/4 E2E |

### Top Lessons (Verified Across Milestones)

1. Integration audits after shared infrastructure changes prevent cross-module drift
2. YAML-first for shared registries — inline dicts create maintenance burden at scale
