# Phase 1: Foundation - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fork celltype-cli into a working plant science agent. This phase delivers: a plant science system prompt replacing oncology domain knowledge, runtime tool filtering that hides pharma-specific tools, species-agnostic tool architecture (species as explicit parameter, no hardcoded references), and CLI rebranding from celltype-cli/ct to ag-cli/ag. No new plant-specific tools are built — that's Phases 2–5.

</domain>

<decisions>
## Implementation Decisions

### System prompt voice
- Expert collaborator tone — assumes domain knowledge, uses technical language, focuses on evidence and reasoning
- Clean slate identity — no acknowledgment of pharma/drug discovery heritage; the agent presents as purpose-built for plant science
- Ag biotech is the framing lens, but the domain knowledge must be deeply plant biology — genomics, expression, regulatory networks, orthologs, trait development, gene editing, breeding — because all of that is needed to do ag biotech well
- Do NOT pre-bake shortlisting metric language (novelty, efficacy, pleiotropic risk, editability) into the system prompt — the agent should be an exceptionally competent plant biology expert that serves as the best substrate for whatever meta-prompting is layered on top
- The agent's name is "Harvest" (keep this as a single configurable value — the name may change later)

### Tool filtering
- Category allowlist approach — define a list of plant-relevant and general-purpose categories that are exposed; everything else is hidden
- Categories to exclude include: chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK (and any other pharma-specific categories identified during implementation)

### Claude's Discretion
- Whether filtered tools are hard invisible (agent has no awareness) or soft-filtered (acknowledges but declines) — pick the cleanest approach
- Whether filtering is config-driven (domain = "plant_science") or hardcoded for ag-cli — pick based on codebase patterns and future flexibility
- Whether filtering is enforced at the MCP server layer only (hiding from agent) or also blocks programmatic execution — pick based on architecture
- Audit scope for species cleanup: whether to fix all tools or only tools that survive the allowlist filter

### Species parameter design
- Agent infers species from conversation context; if ambiguous, it asks the user — tools have an optional species parameter that the agent fills in
- Flexible input format — accept common names ("rice"), binomial ("Oryza sativa"), abbreviations ("Os"), and resolve to canonical internal form (binomial)
- The full species registry is Phase 2; Phase 1 needs an interim resolution approach (simple lookup dict or pass-through — Claude's discretion on the best bridge)

### CLI identity & branding
- Branded ASCII art banner for "AG" or "AG-CLI" — distinct visual identity from celltype
- CLI command is `ag` (not `ct`)
- Agent refers to itself as "Harvest" in conversation
- Help text uses plant science specific language — mentions gene editing, trait development, expression analysis, orthologs, species comparison, etc.
- pyproject.toml rebranded from celltype-cli to ag-cli

</decisions>

<specifics>
## Specific Ideas

- The system prompt should make the agent an exceptionally competent plant biology / ag biotech expert — the best substrate for whatever is layered on top, not pre-optimized for any specific workflow
- "Harvest" as agent name — keep it as a trivially swappable config value since it may change
- Think of the relationship like: Claude Code doesn't need GSD's language to be a great coding agent; similarly, Harvest doesn't need shortlisting language to be a great plant science agent

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-25*
