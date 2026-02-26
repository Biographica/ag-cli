# Phase 3: External Connectors - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Three API connectors — STRING (plant PPI networks), PubMed (literature search), Lens.org (patent search) — with plant-specific query construction and organism validation. These are evidence-source tools the agent calls during research workflows. Connectors are best-effort for the generalist agent; robust ID harmonization (pan-genome disambiguation, Dagster-backed connectors) is future scope.

</domain>

<decisions>
## Implementation Decisions

### Query construction
- STRING gene-to-protein ID resolution: Claude's discretion on approach (best-match vs disambiguation), keeping in mind that ID harmonization is acknowledged as hard — robust solutions are deferred to Dagster backend and advanced tooling in future iterations
- PubMed: basic query construction in the tool (species + gene), agent-driven refinement for synonyms and broader terms. Tool returns the query it used so agent can iterate
- Lens.org: two query templates — gene-focused (narrow, for specific target assessment) and landscape (broad, crop + trait combo for freedom-to-operate). Agent selects which mode fits the question
- STRING species resolution: wire through species registry for taxon IDs (Claude's discretion on exact mechanism)

### Response shaping
- STRING PPI results: configurable `limit` and `min_score` parameters with a hard ceiling to protect the agent's context window
- PubMed citations: standard fields — title, abstract, authors, journal, year, PMID. Rich enough for agent to assess relevance without follow-up calls
- Lens.org patents: include abstract and claims information (Claude's discretion on exact balance — informed by user's experience that claims and abstract are crucial for relevance assessment in analyst-led patent searches with PatSnap)
- Summary field in tool responses: Claude's discretion, follow existing codebase conventions

### Rate limiting & authentication
- API keys managed via ag config + environment variable fallback (config checked first, env var as fallback). Consistent with existing config pattern
- Persistent disk cache with TTL for API responses. Data in these databases changes slowly enough that 24h-ish TTL is reasonable. Survives across sessions for iterative research
- PubMed works without API key at lower rate limits; warn user once per session that rate limits may apply without a configured key
- Lens.org: tool is disabled/hidden from the agent when API token is not configured — agent shouldn't consider it as available if user hasn't set up credentials
- STRING: free API, no key needed
- Rate limit handling (retry/backoff strategy): Claude's discretion

### Error & edge cases
- Empty results: return structured empty response with context (query used, species queried, database queried). Let the agent reason about pivots — don't hardcode alternative suggestions that may be wrong in context
- STRING species pre-validation: Claude's discretion on whether to maintain a supported-species list or let the API respond
- PubMed zero results: echo back the constructed query so agent can debug and refine

### Claude's Discretion
- STRING ID resolution approach (best-match vs multi-match handling)
- STRING species pre-validation strategy
- Lens.org response detail level (abstract always, claims on-demand or always)
- Summary field conventions
- Rate limit retry/backoff strategy
- Persistent cache implementation details (TTL values, cache location, eviction)

</decisions>

<specifics>
## Specific Ideas

- "Robust ID harmonization is future scope — Dagster backend and pan-genome-based disambiguation tools exist internally but are out of scope for the generalist agent"
- "In analyst-led patent searches with PatSnap, claims and abstract were crucial to assess whether a patent is actually relevant"
- "If a user hasn't set their API token for Lens then the agent just shouldn't consider Lens as a tool it can use" — hide, don't fail
- Config system should feel like a `.ag` folder with settings, similar to how Claude Code does it

</specifics>

<deferred>
## Deferred Ideas

- Robust ID harmonization via pan-genome-based disambiguation (exists in other internal tools, future iteration)
- Dagster-backed connectors for production-grade data pipelines (v2+ scope)
- PatSnap-style deep patent analysis (richer than Lens.org API alone)

</deferred>

---

*Phase: 03-external-connectors*
*Context gathered: 2026-02-26*
