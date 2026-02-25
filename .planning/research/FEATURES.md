# Feature Landscape

**Domain:** Agricultural biotech target identification and shortlisting platform (plant science agentic research + structured pipeline)
**Researched:** 2026-02-25
**Milestones:** M1 = Working Plant Science Agent | M2 = Structured Shortlisting Pipeline

---

## Source Notes

Primary sources for this analysis:
- PROJECT.md (authoritative product context and milestone definitions)
- PRODUCT_SPEC.md (detailed evidence integration framework, input/output schemas, gotchas)
- FEASIBILITY_REPORT.md (existing capability assessment and gap analysis)
- Training knowledge of plant science bioinformatics ecosystem (cutoff August 2025, HIGH confidence for established tools, MEDIUM for ecosystem patterns)

Web search and WebFetch were unavailable in this research session. Claims sourced from training data are annotated with confidence levels.

---

## What Existing Tools Provide (Competitive Baseline)

Understanding what the established tools offer defines the table stakes for any platform in this space.

### Ensembl Plants (HIGH confidence — well-established)
- Gene models with functional annotations across 60+ plant species
- Cross-species ortholog mapping via Compara (whole-genome alignment, synteny blocks)
- Variant data (SNPs, indels) with consequence prediction (VEP)
- GWAS/QTL data integration via the NHGRI GWAS Catalog
- REST API and BioMart bulk query interface
- Comparative genomics tracks (gene trees, alignments)
- Expression data integration (some species)

### TAIR — The Arabidopsis Information Resource (HIGH confidence)
- Comprehensive Arabidopsis thaliana gene annotation (GO terms, pathways, publications)
- Mutant phenotype database (T-DNA insertion lines, ethyl methanesulfonate mutants)
- Gene expression data (microarray, some RNA-seq)
- Protein interactions and network data
- Literature-linked gene-function associations
- Bulk download of gene models, sequences, annotations
- Limited to a single species — no multi-species or crop-focused data

### Gramene (HIGH confidence)
- Multi-species plant genome browser (50+ plant genomes)
- Curated pathway databases (Plant Reactome)
- Comparative genomics (synteny, orthologs)
- QTL and GWAS data for crop species
- Ensembl Plants integration

### Phytozome — JGI Plant Genomics Portal (HIGH confidence)
- High-quality plant genome assemblies and annotation
- BLAST, synteny browser, gene family analysis
- Focused on genome quality and assembly, not target ranking

### STRING Database — Plant Networks (HIGH confidence)
- Protein-protein interaction networks for selected plant species (Arabidopsis, rice, maize)
- Interaction confidence scores combining co-expression, text mining, experimental evidence
- Network centrality metrics calculable
- Does NOT provide gene editing feasibility, scoring, or ranking

### Kosmos (MEDIUM confidence — limited public documentation)
- Internal agentic shortlisting tool referenced in PRODUCT_SPEC.md as prior tool
- Known issues documented in PRODUCT_SPEC.md: agent ignores constraints, uses wrong-organism datasets, outputs inconsistent across runs, adds genes outside provided longlist
- Used for internal shortlisting but lacks the structured pipeline, audit trail, and configurability described in the product spec

### Gene Atlas / eFP Browser / PLEXdb (MEDIUM confidence)
- Plant expression atlases with tissue-specific expression profiles
- Good for expression breadth assessment (pleiotropic risk proxy)
- No integration with gene editing or shortlisting workflows

### Lens.org / Google Patents (HIGH confidence)
- Patent landscape search for novelty scoring
- No structured integration with genomic evidence or target ranking

**Key gap in the ecosystem:** No existing tool combines (a) cross-species plant data integration, (b) gene editing feasibility assessment, (c) structured evidence integration with configurable output metrics, and (d) auditable ranked output with dossiers. That combination is the product differentiation space.

---

## M1: Working Plant Science Agent — Feature Landscape

### Table Stakes (must have — without these M1 is not a plant science agent)

| Feature | Why Expected | Complexity | Milestone | Notes |
|---------|--------------|------------|-----------|-------|
| Plant-domain system prompt | Without this the agent answers using oncology context, giving wrong domain framing | Low | M1 | Replace oncology knowledge with plant science, gene editing, crop contexts |
| Runtime pharma tool filtering | 60 pharma tools surfaced to the agent create confusion and wrong tool selection | Low | M1 | Config-driven filtering, tools hidden not deleted |
| PlantExp RNA-seq loader | RNA-seq expression data is the single most-used evidence type in plant science — expected by any plant research tool | Medium | M1 | Bulk download, local-first; metadata + count matrices |
| Ensembl Plants data loader | Ortholog mapping and cross-species evidence is fundamental to plant research; no other tool covers 60+ species | Medium | M1 | Gene models, orthologs, variation; API or bulk download |
| TAIR / Gramene annotation loaders | Functional annotation (GO terms, phenotypes) is table stakes for any gene-centric research tool | Medium | M1 | TAIR for Arabidopsis depth; Gramene for crop breadth |
| Basic gene annotation lookup | User asks "what does gene X do?" — any plant science tool must answer this | Low | M1 | GO terms, gene name, functional description, linked publications |
| Cross-species ortholog mapping | Plant science research routinely uses Arabidopsis functional knowledge to inform crop gene candidates | Medium | M1 | OrthoFinder or Ensembl Compara; confidence/distance scoring |
| Co-expression analysis tools | Co-expression is a primary evidence type for inferring gene function in plants | Medium | M1 | Network construction from RNA-seq; cluster membership; centrality |
| GFF/genome annotation parsing | Plant genomics workflows always start from GFF files; without this the agent cannot handle genomic coordinates | Low | M1 | GFF3 parsing, feature extraction, coordinate lookups |
| Plant GWAS/QTL lookup | GWAS/QTL colocalisation is the standard causal evidence type for trait-gene associations | Medium | M1 | Gramene QTL, GWAS catalog plant entries; species-aware queries |
| Open-ended plant Q&A | Users must be able to ask arbitrary questions ("what evidence exists for gene X in drought tolerance?") | Low | M1 | This is the agent loop working with plant tools — no extra build |
| Species-agnostic architecture | Real customers work across Arabidopsis, rice, maize, wheat, soybean, tomato — hardcoding species is a dealbreaker | Medium | M1 | No hardcoded species IDs; species passed as parameter throughout |
| Organism validation middleware | PRODUCT_SPEC.md documents wrong-organism data as a known failure mode — must prevent at data access layer | Medium | M1 | Tool-level species match check before returning data |
| Local-first data access | API throttling and availability failures make API-only tools unreliable for research sessions | Medium | M1 | Bulk download scripts; local path config; loaders read local first |
| Literature search (plant-adapted) | Any research agent must search published literature | Low | M1 | PubMed with plant-specific query construction; OpenAlex for OA papers |

### Differentiators for M1 (above baseline plant science tools)

| Feature | Value Proposition | Complexity | Milestone | Notes |
|---------|-------------------|------------|-----------|-------|
| STRING plant PPI network loader | Adds protein interaction evidence for pleiotropic risk — not available in Ensembl or TAIR | Low | M1 | Plant species subset of STRING; centrality metrics |
| PlantTFDB transcription factor loader | TF regulatory network evidence relevant to gene regulation and editing strategy selection | Low | M1 | Bulk download; TF family annotation; target gene lists |
| CRISPR guide design tools | Gene editing assessment is not provided by any existing plant database tool | High | M1 | Guide scoring, PAM site analysis, off-target prediction |
| Editability scoring | Combining guide design, gene structure, regulatory complexity into a single editability estimate | High | M1 | Novel; no existing tool does this for plants systematically |
| Paralogy/redundancy scoring | Functional redundancy from paralogs is a known risk for gene editing efficacy — not surfaced by existing tools | Medium | M1 | Paralog count, co-expression overlap, shared GO terms |
| Patent landscape search (Lens.org) | Commercial users need novelty relative to IP landscape, not just literature | Low | M1 | Lens.org API or bulk; plant-specific patent classes |
| Evidence gathering across species for a gene list | Existing tools require per-gene, per-species manual queries; the agent does this systematically | Medium | M1 | Agentic orchestration of multi-species evidence collection |
| Session persistence and export | Research sessions that can be resumed and exported for audit | Low | M1 | Already in celltype-cli; expose in plant context |
| Markdown + HTML report generation | Structured output of research findings — above what any database portal provides | Low | M1 | Already in celltype-cli; adapt templates for plant science |

### Anti-Features for M1 (things to deliberately not build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Hardcoded Arabidopsis bias | Invalidates tool for crop species — 90% of commercial value is in crops | Species parameter required everywhere; test with rice and maize |
| API-only data access for core databases | API failures/throttling break research sessions unpredictably | Local-first data; API as fallback only |
| Pharma tool surfacing (ADMET, DDI, CRO, clinical) | Creates confusion and wrong tool selection in plant research context | Runtime filtering by tool category tag |
| Real-time collaboration features | Single-user research tool; adding collaboration creates infrastructure debt with no near-term user need | Defer until web product |
| Field trial design features | Different enough workflow that it would distract from the core plant science agent | Scope out explicitly; mark as future framework |
| In-context database queries only (no pre-computation) | Co-expression networks and orthology tables are too slow to compute per-session | Pre-compute standard evidence once per species; cache |
| Unrestricted internet-based data fetching | Reproducibility requires versioned local datasets; open internet fetching is non-reproducible | Local-first with version tracking |

---

## M2: Shortlisting Pipeline Framework — Feature Landscape

### Table Stakes for M2 (must have — without these it is not a shortlisting pipeline)

| Feature | Why Expected | Complexity | Milestone | Notes |
|---------|--------------|------------|-----------|-------|
| Project specification schema (JSON) | Every structured pipeline needs a machine-readable project spec; without this the pipeline cannot be configured reproducibly | Medium | M2 | Pydantic schema; includes metric weights, species, allowed editing strategies, longlist |
| Target construction (longlist × strategy enumeration) | The pipeline must know which targets it is ranking before any scoring | Low | M2 | Cartesian product of genes × allowed strategies; constraint enforcement |
| Hard target-set locking after construction | PRODUCT_SPEC.md documents post-hoc gene additions as a key failure mode — must be prevented programmatically | Low | M2 | Immutable target table after Stage 1; no agent additions |
| Evidence stream framework (EvidenceStream class) | Without a structured evidence abstraction, evidence scoring is ad hoc and non-reproducible | High | M2 | Raw extraction + normalisation_spec + exclusion_rule_spec per stream |
| Batch normalisation (percentile/z-score/rank with clipping) | Heterogeneous raw evidence values must be normalized before combination | Medium | M2 | Three normalisation modes; missingness handling; outlier clipping |
| Exclusion gating (hard pass/fail rules) | Some targets must be excluded regardless of score (e.g. essential genes, no edit site); without gating rankings are invalid | Medium | M2 | Chi functions; global eligibility check; audit output |
| Four output metrics (novelty, efficacy, pleiotropic risk, editability) | These are the agreed customer-facing deliverables specified in PRODUCT_SPEC.md | Medium | M2 | Each metric = weighted aggregation of relevant evidence streams |
| Pseudo-Bayesian posterior update (prior + delta + squashing) | Standard probabilistic framing for evidence integration; more principled than raw averaging | High | M2 | Per PRODUCT_SPEC.md §3.5 formula; deterministic code not agent judgement |
| Configurable metric weights | Customers reweight novelty vs efficacy vs risk depending on project | Low | M2 | Weights in project spec JSON; scoring engine reads from spec |
| Target ranking table (gene × edit level, aggregated to gene level) | Primary customer deliverable — without this the pipeline produces no output | Low | M2 | Gene-level: max over edit strategies; recommended strategy per gene |
| Evidence provenance and audit tables | Auditable pipeline is non-negotiable for scientific credibility | Medium | M2 | Long-format attribution; every score traceable to source evidence item |
| Single canonical ranking table | PRODUCT_SPEC.md documents "PDF drift" as a known failure mode — all outputs must derive from one table | Low | M2 | Pipeline architecture decision; enforce in code |
| Pipeline state management (resume after interruption) | Long pipelines will be interrupted; no resume = lost work and non-reproducibility | Medium | M2 | Stage-level checkpointing; state file serialisation |
| Transform spec versioning | Reproducibility requires that scoring transforms are versioned and replayable | Medium | M2 | Content-hashed transform_spec DSL; stored with pipeline run |
| Hard organism validation on all external data | PRODUCT_SPEC.md documents wrong-organism data as a key failure mode | Low | M2 | Carried forward from M1; enforced at evidence computation stage too |
| Target dossier generation (top-K targets) | Customer-facing written output — without this the shortlist is just numbers | High | M2 | Executive summary, quantitative profile, mechanistic hypothesis, editing strategy, risks, uncertainties, references |

### Differentiators for M2 (competitive advantage over existing tools)

| Feature | Value Proposition | Complexity | Milestone | Notes |
|---------|-------------------|------------|-----------|-------|
| Evidence planning agent | Identifies which studies and evidence streams are most relevant for a given project spec — no existing tool does project-specific evidence curation | High | M2 | Specialised agent subprompt; outputs justified evidence plan for scientist review |
| Dynamic metric re-weighting without re-running pipeline | Customers adjust novelty/efficacy/risk tradeoffs post-scoring without recomputing all evidence | Medium | M2 | Separating evidence scoring from metric aggregation; weights applied at final aggregation step |
| Stream independence validation | Prevents double-counting correlated evidence streams — most platforms silently aggregate correlated signals | Medium | M2 | Correlation check between streams before aggregation; agent-justified independence claim |
| Evidence stream reliability and applicability scoring | Formal weighting of evidence quality (experimental directness, species distance) — more principled than ad hoc weighting | Medium | M2 | Per PRODUCT_SPEC.md §3.2; r_e and a_{e,t} scores per stream per target |
| Scientist-in-the-loop evidence review gate | Checkpoint after evidence planning before computing evidence — humans review and approve plan | Low | M2 | Pipeline gate; structured evidence plan output for review |
| Mechanistic hypothesis generation per target | Written causal hypothesis for why the gene+edit combination should affect the trait | High | M2 | Dossier section; specialised agent with chain-of-thought over evidence |
| Alternative strategy presentation with quantitative tradeoffs | Showing second/third-best editing strategies per gene with their scores, not just top-ranked | Low | M2 | Aggregation step; top-3 strategies per gene in output |
| Validation priority recommendations per target | Specific experimental validation steps recommended per target — actionable output | Medium | M2 | Dossier section; agent synthesises over evidence gaps |
| Pipeline determinism (same spec + same data = same ranking) | Reproducibility is rare in agentic scientific tools; this is a trust-building differentiator | Medium | M2 | Achieved via deterministic scoring code + versioned transform specs + project_spec_id |
| Coverage tracking guardrail | Flags when evidence is too sparse for reliable scoring — prevents overconfident rankings on thin evidence | Low | M2 | Coverage metrics per target; flag targets below coverage threshold |
| Conflict detection guardrail | Flags when evidence streams disagree strongly — surfaces uncertainty rather than hiding it | Medium | M2 | Pairwise stream agreement check; conflict flag in output |

### Anti-Features for M2 (things to deliberately not build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Fully probabilistic Bayesian model (MCMC/variational) | Intractable likelihood estimation; opaque to customers; hard to configure | Pseudo-Bayesian: prior + delta updates with squashing (per product spec) |
| Agent-judged numerical scores | Hallucination risk in quantitative outputs is unacceptable | Deterministic code for all scoring; agent only plans and interprets |
| Free-form evidence aggregation without schema | Non-reproducible; different runs produce different weightings | EvidenceStream class with mandatory schema; transform_spec DSL |
| Multiple output tables that can diverge | "PDF drift" is a documented failure mode | Single canonical ranking DataFrame; all reports generated from it |
| Post-hoc target additions by agent | Documented failure mode: agent "fixes" by adding genes outside longlist | Programmatic target set lock after Stage 1; no agent additions |
| Regression-based scoring models requiring training data | Needs labelled training data that doesn't exist for novel crop+trait combinations | Evidence integration framework; no trained models in scoring path |
| Per-session evidence computation for standard streams | Too slow; results must be reproducible regardless of when pipeline runs | Pre-compute standard evidence streams; cache with content hash |
| Black-box ML scoring (e.g. transformer-based gene ranking) | Non-interpretable; breaks auditability requirement; customer cannot explain rankings | Interpretable scoring with quantitative evidence attribution |
| Dagster integration (M2) | Valuable eventually; premature abstraction before local-first pattern is validated | Local-first data pattern for M2; Dagster as future enhancement |

---

## Feature Dependencies

```
# M1 Dependencies
Local-first data loaders → All M1 evidence tools
  (PlantExp, Ensembl Plants, TAIR, Gramene, STRING all depend on download scripts + loader pattern)

Species-agnostic architecture → All M1 tools
  (Must be established before any tool is written; retrofitting is expensive)

Organism validation middleware → All M1 data-fetching tools
  (Wraps every loader; implemented once, applied everywhere)

Ensembl Plants ortholog loader → Cross-species evidence gathering
  (Ortholog mapping is a prerequisite for cross-species evidence transfer)

Co-expression analysis → Paralogy/redundancy scoring (partial)
  (Co-expressed paralogs require co-expression network first)

PlantExp loader → Co-expression analysis → Expression breadth scoring
  (Expression breadth and TAU score need raw expression data)

GFF parsing → Gene structure assessment → CRISPR guide design → Editability scoring
  (Editability requires gene structure; guide design requires genomic sequence context)

Literature search → Patent landscape search (parallel, independent)
  (Both feed novelty; no dependency between them)

# M2 Dependencies
M1 (all plant tools and loaders) → M2 pipeline (evidence streams use M1 tools)

Project specification schema → Target construction → Target set lock
  (Pipeline cannot start without a valid spec)

Target construction → Evidence aggregation → Batch normalisation → Exclusion gating → Pseudo-Bayesian update → Ranking
  (Linear pipeline stage dependency)

Evidence stream framework → Evidence planning agent → Evidence computation
  (Agent plans within the framework; computation executes the plan)

Evidence computation (all streams) → Batch normalisation
  (Cannot normalise until all evidence is computed)

Batch normalisation → Pseudo-Bayesian update → Ranking
  (Normalised scores feed the posterior update)

Exclusion gating (parallel with normalisation) → Ranking
  (Excluded targets removed before final ranking)

Ranking table → Target dossier generation
  (Dossiers generated for top-K from ranking table)

Transform spec versioning → Pipeline determinism
  (Reproducibility depends on versioned transforms)

Pipeline state management (independent of above — wraps all stages)
Evidence provenance tracking (independent — wraps all stages)
```

---

## MVP Recommendation

### M1 MVP (minimum viable plant science agent)

Build in this order:

1. **Runtime tool filtering + plant system prompt** — immediate; unlocks plant-appropriate agent behaviour
2. **PlantExp loader + co-expression tools** — highest evidence value; expression data is used in nearly every project
3. **Ensembl Plants loader + ortholog mapping** — cross-species evidence is essential; many tools depend on it
4. **TAIR/Gramene annotation loaders** — functional annotation unlocks gene description, GO enrichment, phenotype lookup
5. **GFF parsing + gene structure tools** — prerequisite for CRISPR guide design
6. **CRISPR guide design + editability scoring** — differentiating; establishes the gene editing angle
7. **Literature + patent search (plant-adapted)** — novelty evidence gathering

Defer for post-MVP: STRING PPI loader, PlantTFDB loader, TAU score computation (depends on having full expression atlas per species)

### M2 MVP (minimum viable shortlisting pipeline)

Build in this order:

1. **Project spec schema + target construction + target set lock** — pipeline gates depend on this
2. **Evidence stream framework (EvidenceStream class + transform DSL)** — all scoring depends on the abstraction
3. **Three hardcoded evidence streams** (literature novelty, expression breadth, ortholog evidence) — validate end-to-end flow
4. **Batch normalisation + exclusion gating** — prerequisite for any scoring output
5. **Pseudo-Bayesian update for novelty + efficacy metrics only** — partial metric coverage to validate scoring engine
6. **Target ranking table** — first customer-facing output
7. **Basic dossier template** — narrative output for top-K targets

Defer for post-MVP: evidence planning agent (use hardcoded streams first), full four-metric coverage, dynamic re-weighting UI, conflict detection, coverage tracking guardrails

---

## Sources

- PROJECT.md — authoritative milestone definitions and scope boundaries (primary source)
- PRODUCT_SPEC.md — evidence integration framework, input/output schemas, known failure modes (primary source)
- FEASIBILITY_REPORT.md — existing capability analysis, tool category mapping, gap analysis (primary source)
- Training knowledge of Ensembl Plants, TAIR, Gramene, Phytozome, STRING capabilities (HIGH confidence for established tools)
- Training knowledge of plant science bioinformatics patterns and CRISPR guide design tools (MEDIUM confidence for ecosystem patterns — verify against current tool documentation during implementation)
- Kosmos capabilities: MEDIUM confidence — sourced from PRODUCT_SPEC.md references and training knowledge; no direct tool documentation available
