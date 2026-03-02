# Milestones

## v1.0 Working Plant Science Agent (Shipped: 2026-03-02)

**Delivered:** A working plant science agent that answers open-ended biology questions and executes multi-step research workflows using 15+ computational biology tools across species.

**Stats:**
- Phases: 1-5 (+ 2.1, 2.2 inserted) — 7 phases, 17 plans
- Files modified: 109 | Lines added: 23,540
- Source: 43,524 LOC Python (src/) | 19,299 LOC (tests/)
- Timeline: 7 days (2026-02-25 → 2026-03-02)
- Commits: 113 | Requirements: 20/20 satisfied
- Git range: `feat(01-foundation-01)` → `feat(05-03)`

**Key accomplishments:**
1. Plant science agent identity (Harvest) with runtime pharma tool filtering at MCP layer
2. Species-agnostic data infrastructure with YAML registry, manifest system, and organism validation
3. External API connectors: STRING plant PPI, PubMed plant search, Lens.org patent search
4. Plant genomics tools: gene annotation, ortholog mapping, co-expression, GFF3 parsing, GWAS/QTL
5. CRISPR gene editing assessment: guide design, editability scoring, paralogy scoring
6. Multi-species evidence gathering orchestration across the full tool suite

**Tech debt (10 items, 0 blockers):** See `milestones/v1.0-MILESTONE-AUDIT.md`

**Archives:**
- `milestones/v1.0-ROADMAP.md`
- `milestones/v1.0-REQUIREMENTS.md`
- `milestones/v1.0-MILESTONE-AUDIT.md`

---

