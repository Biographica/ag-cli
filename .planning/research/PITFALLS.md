# Domain Pitfalls

**Domain:** Agentic agricultural biotech target identification platform
**Researched:** 2026-02-25
**Confidence:** HIGH (critical pitfalls) / MEDIUM (architecture/data pitfalls) / HIGH (known gotchas — directly observed)

---

## Known Gotchas (Directly Observed — HIGH Confidence)

These are documented failures from production Kosmos runs against the same product spec. They are not
hypothetical. Every one of them has already happened.

### Gotcha G1: Post-Hoc Constraint "Fixing" Without Invalidating Prior Output

**What goes wrong:** Agent completes a full run (ranking, PDF, dossier) violating a hard constraint
(e.g. including known/non-novel genes). Agent detects the violation post-hoc during report
generation, silently creates a corrected ranking — but does not update already-generated outputs.
Result: PDF shows invalid targets, final ranking shows different targets, user receives contradictory
deliverables.

**Why it happens:** Free-form agentic loops are optimised for forward progress. The agent "fixes"
the nearest visible error (the ranking) without backtracking to regenerate all downstream outputs.
Prompt-only constraints are invisible to the agent by the time it reaches dossier generation.

**Consequences:** Customer receives two inconsistent rankings. Trust in the tool evaporates. No
audit trail to identify which output is canonical.

**Prevention:**
- Lock the target set programmatically at Stage 1 (target construction). No code path exists to
  add targets after this stage gate.
- All downstream outputs (dossier, PDF, ranking table) MUST derive from the single canonical
  ranking DataFrame. Generate the DataFrame first; generate all formatted outputs from it.
- Single canonical ranking table is the source of truth. Enforce via pipeline architecture, not
  instructions.
- Add a pre-flight validation step that counts excluded genes and logs the exclusion audit before
  any ranking begins.

**Detection:** If the target count in the PDF differs from the target count in the ranking JSON, a
constraint was violated. Implement an automated cross-check between all output artifacts.

**Phase:** Milestone 2 — Pipeline stage gate design (Stage 1 target construction + artifact
derivation chain)

---

### Gotcha G2: Wrong-Organism Dataset Used for Evidence

**What goes wrong:** Agent retrieves a dataset by GEO accession number or keyword search that
appears relevant (e.g. "CCA1/LHY ChIP-seq") but belongs to the wrong organism (e.g. human kidney
methylation). Evidence from this dataset is used to support a mechanistic hypothesis, invalidating
the analysis.

**Why it happens:** Agents search databases by keyword and trust the retrieved metadata. GEO
accessions are not organism-namespaced. A search for "CCA1 ChIP-seq" may return a human result if
the human paper mentions the same gene name. The agent has no programmatic check — it reads the
title, judges it plausible, and proceeds.

**Consequences:** Entire mechanistic argument for a target is built on wrong-species data. If
undetected, this propagates to the dossier and ranking.

**Prevention:**
- Organism validation must be **programmatic middleware**, not a prompt instruction. Every
  data-fetching tool must validate the organism field of retrieved metadata before returning results
  to the agent.
- Maintain a controlled allowlist of approved dataset accessions per project. Agent can only access
  datasets on this list.
- For any external dataset access outside the allowlist, require explicit human approval with
  organism confirmation step.
- The project spec must carry a `target_organism` field that every data loader reads and validates
  against.
- Local-first data pattern reduces exposure: if all approved datasets are pre-loaded locally with
  organism metadata already validated during curation, the agent cannot accidentally access wrong-
  organism data via keyword search.

**Detection:** Log organism field of every dataset accessed. Flag any dataset where the organism
field does not match `project_spec.target_organism`. Halt the pipeline if a mismatch is detected.

**Phase:** Milestone 1 — Organism validation middleware (tool-level enforcement)

---

### Gotcha G3: Target Added Outside the Longlist

**What goes wrong:** Agent, when "correcting" a constraint violation, introduces a gene that was
never in the provided longlist. In the observed case, Kosmos created a corrected top-15 that
included a gene not submitted by the customer.

**Why it happens:** The agent's training optimises for "produce a helpful, complete answer." When
forced to regenerate a ranking with fewer valid targets, the agent fills gaps from its own knowledge
rather than acknowledging the gap.

**Consequences:** Customer is ranked a target they never asked about, with no provenance, and
potentially no IP protection for that gene.

**Prevention:**
- Target set must be **frozen as a programmatic object** (a set or frozenset) at pipeline
  initialisation. Any target that appears in a downstream step that is not in this frozen set
  raises a hard error, not a warning.
- Dossier generation must receive only targets from the canonical ranking table, which is itself
  restricted to the frozen target set.
- Never allow the agent free text-to-gene-name translation after target construction. All gene
  references must resolve against the frozen target set.

**Detection:** Before writing any output, validate that every gene name in every output artifact is
a member of the original longlist. If not, abort and raise an error with the offending gene name.

**Phase:** Milestone 2 — Target set locking (Stage 1 hard gate)

---

### Gotcha G4: Inconsistent Output Format Across Runs and Targets

**What goes wrong:** Different runs of the same pipeline on the same data produce dossiers with
different depth, structure, and included sections. Within a single run, top-ranked targets receive
detailed mechanistic discussion while lower-ranked targets receive shallow bullet lists.

**Why it happens:** Free-form generation with only prompt-level format instructions. LLM generation
variance means field completeness varies. Long dossier generation runs hit context limits and the
agent shortcuts later targets.

**Consequences:** Intra-run inconsistency makes cross-target comparison impossible. Inter-run
inconsistency means results cannot be reproduced. Customer trust is damaged when re-running the
pipeline produces a different top-5.

**Prevention:**
- Dossier template must be a **schema-enforced structure**, not a prose prompt. Use a Pydantic
  model or JSON schema with required fields. Validation runs against every dossier before output.
- Each target dossier must be generated as an independent agent call (not one giant call for all
  targets). This prevents context drift and ensures consistent depth.
- Required dossier sections (from product spec §4): executive summary, quantitative profile,
  mechanistic hypothesis, editing strategy, risks/alternatives, uncertainties, validation
  priorities, references. All must be present and non-empty or the dossier is rejected.
- Scoring pipeline (the quantitative part of the dossier) must be generated from code, not agent
  prose. Scores come from the canonical ranking table; the agent only writes the narrative.

**Detection:** Run schema validation on every generated dossier. Track field completeness as a
metric. Alert if completeness drops below threshold for any target.

**Phase:** Milestone 2 — Dossier generation (schema enforcement + per-target independent calls)

---

### Gotcha G5: PDF Drift — Outputs Generated from Different Data Than the Canonical Ranking

**What goes wrong:** The PDF report is generated from a different version of the ranking or
evidence than the canonical output table. This can happen when: (a) the ranking is updated post-
hoc (see G1), (b) the dossier writer is given different inputs than the scorer, or (c) parallel
agents merge results without a single canonical merge point.

**Why it happens:** Multi-output pipelines where report generation and scoring are independent
agent calls with no enforced data lineage.

**Consequences:** PDF and data table are inconsistent. Neither can be trusted as authoritative.

**Prevention:**
- Single canonical ranking table is generated once and persisted. All formatted outputs read from
  this table. No reformatting or recalculation during report generation.
- Implement output derivation chain: `scoring_engine.run()` → `ranking_table.parquet` →
  `dossier_writer(ranking_table)` → `report_generator(dossiers, ranking_table)`. Each step reads
  from the previous step's output file, never from in-memory state.
- Content-hash the canonical ranking table at write time. Include this hash in all formatted
  outputs. At report generation, verify the hash still matches.
- Pipeline state manager tracks which version of the ranking table each output was derived from.

**Detection:** Hash mismatch between canonical ranking table and the hash embedded in any formatted
output is a hard error. Fail loudly.

**Phase:** Milestone 2 — Single canonical ranking table + artifact derivation chain

---

## Critical Pitfalls

Mistakes that cause rewrites or fundamental loss of trust. Have not all been observed yet, but are
near-certain failure modes given the architecture.

### Pitfall C1: Scoring as Agent Judgement Instead of Deterministic Code

**What goes wrong:** Agent is asked to score evidence and produce a numerical metric. Agent writes
prose ("this gene has high pleiotropic risk due to broad expression") rather than executing the
specified formula. Scores are not reproducible. Re-running produces different numbers.

**Why it happens:** The boundary between "agent plans the scoring pipeline" and "agent executes the
scoring pipeline" is not enforced architecturally. If the code.execute sandbox is available but
not required, the agent will sometimes use it and sometimes not.

**Consequences:** Scores are not reproducible. Customers cannot validate. Re-weighting metrics
requires re-running the full agent. Pipeline is not auditable.

**Prevention:**
- Scoring engine must be a Python module (`shortlist/scoring/`), not an agent-generated function.
  The pseudo-Bayesian update formula, normalisation functions, and exclusion gating are implemented
  as typed, tested Python code.
- The agent's role is to (a) select which evidence streams apply to which metrics, and (b)
  configure the normalisation_spec and reliability/applicability values. The agent DOES NOT compute
  the scores.
- All numerical outputs in the ranking table must be traceable to a specific function call in
  `shortlist/scoring/` with versioned transform_spec.
- Use the code.execute sandbox for bespoke, project-specific evidence extraction. Never use it for
  the core scoring formula.

**Detection:** All score values in the canonical ranking table should have a `transform_spec_id`
attribute. Any score without a versioned transform_spec is a pipeline integrity failure.

**Phase:** Milestone 2 — Scoring engine (deterministic code, not agent judgement)

---

### Pitfall C2: Species-Hardcoding Early in the Codebase

**What goes wrong:** First implementation targets Arabidopsis. Species-specific assumptions
accumulate in tool implementations (TAIR-specific IDs, At prefix gene names, chromosome naming
conventions, ploidy assumptions). When the second project requires wheat or soybean, refactoring
cost is 3-4x what it would have been.

**Why it happens:** It's faster to hardcode the known species. "We'll generalise later" becomes
technical debt. Gene ID formats differ enormously: AT1G01010 (Arabidopsis), TraesCS1A02G000100
(wheat), Glyma.01G000100 (soybean).

**Consequences:** Major refactoring cost. Customer-facing bugs when switching species. Ortholog
mapping breaks. Data loaders silently return empty results for non-Arabidopsis queries.

**Prevention:**
- Every data loader, tool, and pipeline step receives `species` as an explicit parameter from day
  one. No defaults to "arabidopsis" except in examples.
- Gene ID format validation is species-aware. Maintain a species registry mapping species names to
  ID formats, chromosome naming conventions, and reference genome versions.
- Test suite includes at least two species from the start. If a tool only passes tests for
  Arabidopsis, it is incomplete.
- PlantExp loaders must be designed to query by species + gene_id, not by hardcoded column names
  that only exist for Arabidopsis.
- The project spec `target_organism` field drives all species-specific behaviour. Nothing reads
  species from config or environment variable.

**Detection:** Grep for hardcoded "arabidopsis", "TAIR", "AT[0-9]G", "thaliana" in tool
implementations. Any occurrence outside of test fixtures or data loader species registries is a
bug.

**Phase:** Milestone 1 — Species-agnostic architecture from day one

---

### Pitfall C3: Evidence Double-Counting via Correlated Streams

**What goes wrong:** Multiple evidence streams are mapped to the same output metric (e.g. efficacy)
without checking for correlation. Expression in trait-relevant tissue (from RNA-seq) and co-
expression with known causal genes (from the same RNA-seq dataset) are highly correlated. Treating
them as independent streams double-counts the signal and inflates efficacy scores for genes that
are merely co-expressed with well-studied genes.

**Why it happens:** Evidence streams are planned by an agent that may not reason carefully about
data independence. Correlation between streams is not automatically detected.

**Consequences:** Ranking is biased toward genes that happen to be highly expressed rather than
genes with genuine causal evidence. Novelty-filtered longlist may still be dominated by
"expression-rich" genes.

**Prevention:**
- Product spec already requires: "Justify, and validate where possible, that the chosen evidence
  streams are sufficiently independent to avoid systematic double-counting." This must be enforced
  as a validation step, not just a prompt instruction.
- After evidence plan is generated, compute pairwise Pearson/Spearman correlations between all
  stream scores across the target set. Flag any pair with |r| > 0.7 as potentially correlated.
- Require the evidence-planner agent to explicitly annotate the upstream data source for each
  stream. If two streams share an upstream source (same RNA-seq dataset), treat them as correlated
  by default.
- When merging correlated streams, use a single merged stream with explicit combination rule rather
  than two weighted streams.

**Detection:** Correlation check is a mandatory pipeline gate after evidence computation, before
metric integration. Output the correlation matrix as a diagnostic artifact.

**Phase:** Milestone 2 — Evidence planning + stream reliability scoring

---

### Pitfall C4: Context Window Exhaustion in Large Longlists

**What goes wrong:** A longlist of 200-300 genes with multi-stream evidence exceeds the agent's
context window. The agent silently truncates evidence, processes only the first N genes, or
hallucinates scores for genes it never processed.

**Why it happens:** Agentic loops accumulate tool outputs in the context window. 200 genes × 5
evidence streams × average evidence summary = context overflow. The agent does not announce
truncation; it just stops seeing earlier content.

**Consequences:** Lower-ranked genes (later in the context) are scored with less evidence than
higher-ranked genes. The ranking is biased by context position, not evidence quality.

**Prevention:**
- Batch scoring pipeline operates over the full target set in code (pandas), not in agent context.
  The agent never holds all 200 genes' evidence simultaneously.
- Multi-agent architecture: separate evidence researcher per stream (or per stream × species
  combination). Each agent processes one stream across all targets, returns a scored vector. The
  orchestrator merges vectors.
- Evidence summaries stored to disk, not in context. The agent reads file references and accesses
  specific genes on demand.
- Maximum longlist size (e.g. 500 genes) documented as a hard limit. Warn users who provide larger
  longlists to pre-filter.

**Detection:** Monitor context utilisation during pipeline runs. Log a warning if any agent's
context exceeds 60% utilisation during evidence gathering.

**Phase:** Milestone 2 — Multi-agent evidence stream architecture

---

### Pitfall C5: Local Dataset Version Drift

**What goes wrong:** PlantExp, Ensembl Plants, and other local datasets are bulk-downloaded once
and never updated. Over 6-12 months, the local copy diverges from the canonical version.
Reproducibility breaks when a re-run of the same project spec produces different scores because the
underlying data changed.

**Why it happens:** Local-first data pattern is excellent for API independence and curation, but
requires discipline about version tracking. Without explicit dataset versioning, it is impossible
to know whether a score change is due to pipeline changes or data changes.

**Consequences:** Cannot reproduce historical rankings. Audits fail. Customer who re-runs a
previous project gets different results with no explanation.

**Prevention:**
- Every local dataset has a metadata file: `{dataset}.meta.json` containing `source_url`,
  `download_date`, `version`, `sha256_hash`. This is mandatory, not optional.
- Project spec references specific dataset versions by content hash. Pipeline refuses to run if
  the local dataset hash does not match the spec's reference hash.
- PlantExp and other datasets are treated like software dependencies: pinned, versioned, change-
  tracked.
- Updates to datasets are explicit operations (`ct data pull plantexp --version 2024-Q4`) that
  log the version change.

**Detection:** At pipeline initialisation, validate dataset hashes against project spec references.
Fail fast with a clear error if any hash mismatches.

**Phase:** Milestone 1 — Local-first data loader pattern (version tracking)

---

## Moderate Pitfalls

### Pitfall M1: Fork Maintenance Trap

**What goes wrong:** celltype-cli upstream merges useful improvements (bug fixes, new tools, SDK
updates). Because ag-cli is a fork, these improvements are not automatically available. Either
team tracks upstream manually (expensive) or diverges so far that cherry-picking becomes
impractical.

**Why it happens:** Forks without a clear upstream tracking strategy accumulate divergence. The
longer the gap, the more expensive the merge.

**Prevention:**
- Maintain a clear `UPSTREAM_TRACKING.md` documenting which celltype-cli commit ag-cli forked from
  and which upstream changes have been considered or cherry-picked.
- Review celltype-cli releases quarterly. Cherry-pick only changes that affect: agent SDK
  compatibility, MCP server stability, tool registry, sandbox, session management.
- All ag-cli-specific changes to `ct/` must be confined to new files or clearly marked extension
  points. Do not modify celltype-cli's core tool implementations in-place.
- Long-term: propose plant science tools upstream to celltype-cli where they have general value.
  Reduces maintenance burden.

**Detection:** If cherry-picking from upstream requires touching more than 3 files, the fork has
drifted too far.

**Phase:** Milestone 1 — Fork setup

---

### Pitfall M2: Transform Spec DSL Complexity Spiral

**What goes wrong:** The `transform_spec` DSL is designed as a versioned, machine-readable
normalisation specification. In practice, real evidence streams require normalisation logic that
cannot be expressed in a simple DSL (e.g. bimodal distributions requiring mixture modelling,
sequence-level features requiring CRISPR guide design output). The DSL is extended repeatedly until
it is effectively a programming language with poor tooling.

**Why it happens:** Every edge case in evidence scoring motivates a DSL extension. Without a clear
scope limit, the DSL grows unbounded.

**Prevention:**
- DSL scope: cover the 90% case (percentile normalisation, z-score, rank-based, min-max, binary
  threshold). For the 10% case, fall back to code reference + content hash + typed signature as
  allowed by the product spec.
- Never add a new DSL construct without a corresponding test. Complexity is only justified by test
  coverage.
- When in doubt, use the code reference fallback. A well-tested Python function with a content hash
  is more auditable than a complex DSL.

**Detection:** If the DSL requires more than 200 lines of parser code, it has exceeded its scope.

**Phase:** Milestone 2 — Transform spec DSL design

---

### Pitfall M3: Evidence Planner Hallucinating Dataset Existence

**What goes wrong:** The evidence-planner agent is asked to identify relevant studies from
"available/approved datasets." It invents dataset accessions or study titles that do not exist in
the approved local databases. Evidence computation then fails silently when the dataset lookup
returns empty.

**Why it happens:** Evidence planning is an agent reasoning task. The agent's training data
includes many dataset names and accessions. It may confidently cite a dataset that does not exist
in the curated local repository.

**Prevention:**
- Evidence planner must be given an explicit, machine-readable manifest of available datasets
  (the `{dataset}.meta.json` files). It can only cite datasets present in the manifest.
- After evidence planning, a validation step checks every cited dataset against the manifest.
  Any citation that does not resolve to an available local dataset is flagged as a hallucination
  and rejected.
- The evidence planner outputs a structured plan (JSON, not prose), validated against a schema
  before execution.

**Detection:** Evidence computation step that returns empty results for > 20% of targets on a
stream is a signal that the dataset does not exist or is malformed. Log and alert.

**Phase:** Milestone 2 — Evidence planning validation

---

### Pitfall M4: Ortholog Evidence Without Species Distance Weighting

**What goes wrong:** Ortholog evidence from close relatives (e.g. Brassica napus for Arabidopsis
targets) is treated with the same reliability weight as ortholog evidence from distant relatives
(e.g. maize). A gene implicated in yield in maize provides much weaker evidence for an Arabidopsis
efficacy score than a gene implicated in the same trait in Brassica.

**Why it happens:** Orthology mapping identifies "ortholog exists" but does not automatically
provide a species distance penalty.

**Consequences:** Efficacy scores are inflated by distant-species evidence. Targets with many
distantly-related orthologs rank above targets with strong evidence from close relatives.

**Prevention:**
- Species distance must be a first-class concept in the evidence reliability score. Implement a
  phylogenetic distance function that reduces reliability as a function of divergence time or
  evolutionary distance from the target species.
- Use a simple tiered system initially: same genus (0.9 reliability), same family (0.7), same
  order (0.5), other angiosperms (0.3), non-plant ortholog (0.1).
- Every ortholog evidence item must carry the source species. Any ortholog evidence without species
  metadata is rejected.

**Detection:** Check reliability scores for all ortholog evidence streams. If any ortholog stream
has reliability > 0.5 for a source species more than 2 taxonomic ranks removed from the target
species, the reliability model is wrong.

**Phase:** Milestone 1 — Orthology tools; Milestone 2 — Reliability scoring

---

### Pitfall M5: Editing Strategy Constraints Ignored at Target Construction

**What goes wrong:** The project spec says "KO and transcriptional activation only." The target
construction step includes GOF (gain-of-function) overexpression targets because the constraint
was expressed in natural language and the agent interpreted it loosely.

**Why it happens:** Strategy enumeration is done by an agent interpreting the project spec. Natural
language constraints are ambiguous. "Transcriptional activation" and "overexpression" are not
synonymous but agents treat them as equivalent.

**Consequences:** Pipeline scores targets that the customer cannot implement. Editability scores are
meaningless for disallowed strategies. Customer receives recommendations they cannot action.

**Prevention:**
- Editing strategies must be a controlled vocabulary defined in the project spec. The spec carries
  an `allowed_strategies: [list]` field with values from a controlled set
  (`["KO", "KD", "OE", "TA", "epigenetic_silencing", "base_edit", "prime_edit"]`).
- Target construction code reads `allowed_strategies` from the project spec and enumerates only
  those strategies. No agent reasoning is involved in this step.
- Any strategy not in the controlled vocabulary is rejected at spec validation time, before the
  pipeline runs.
- Audit the target table at Stage 1 gate: verify that every strategy in the target table is a
  member of `allowed_strategies`.

**Detection:** After target construction, compute `target_table['strategy'].unique()`. Any value
not in `project_spec.allowed_strategies` is a Stage 1 failure.

**Phase:** Milestone 2 — Target construction (Stage 1)

---

## Minor Pitfalls

### Pitfall L1: Rich Output Masking Shallow Evidence

**What goes wrong:** Agent generates a beautifully formatted dossier with confident mechanistic
language. The dossier reads well. But the underlying evidence is thin: one low-confidence
ortholog hit and a co-expression cluster with poor GO enrichment. The presentation quality exceeds
the evidence quality.

**Prevention:** Every claim in the dossier narrative must be linked to a specific evidence item
with its reliability and applicability scores. Include an evidence summary table at the start of
each dossier showing stream count, mean reliability, and missingness rate. A dossier with mean
stream reliability < 0.3 should be flagged as "low confidence" at the top.

**Phase:** Milestone 2 — Dossier generation

---

### Pitfall L2: Pharma Tools Leaking Into Plant Science Agent

**What goes wrong:** Runtime tool filtering is misconfigured. Plant science agent accidentally
exposes drug-safety tools (ADMET scoring, PK tools, clinical trial lookup) to the agent. Agent
uses these tools on plant proteins and returns nonsensical results.

**Prevention:** Tool filtering must be tested as part of CI. Include a test that instantiates the
ag-cli agent configuration and asserts that the exposed tool list contains no pharma-specific
categories (`chemistry`, `safety`, `clinical`, `cro`, `viability`, `biomarker`, `pk`).

**Phase:** Milestone 1 — Runtime domain filtering

---

### Pitfall L3: Missing Data Treated as Negative Evidence

**What goes wrong:** A target gene has no PlantExp expression data (e.g. it's only expressed in
a tissue not represented in the dataset). The absence of expression evidence is treated as evidence
of low expression, reducing efficacy and pleiotropic risk scores. The gene is ranked incorrectly.

**Prevention:** Missing data must be explicitly modelled. If a stream returns NA for a target, the
target receives neither a positive nor negative contribution from that stream. Missingness tracking
(what fraction of targets have data for each stream) must be a diagnostic output. Do not impute
zero for missing values.

**Phase:** Milestone 2 — Batch normalisation (missingness handling)

---

### Pitfall L4: Gene Name Ambiguity Across Species

**What goes wrong:** "FT" (FLOWERING LOCUS T) means something specific in Arabidopsis. In wheat,
the FT ortholog has different gene names in different databases (TaFT, TraesCS1A02G123456). The
agent conflates Arabidopsis FT literature with wheat FT analysis.

**Prevention:** All gene references in the pipeline must be anchored to species-qualified stable
IDs (Ensembl Plants stable IDs or equivalent), not gene symbols. Gene symbol lookup is allowed
only at input/output; internally, stable IDs are used throughout.

**Phase:** Milestone 1 — Plant genomics tools (gene ID normalisation)

---

### Pitfall L5: System Prompt Oncology Residue

**What goes wrong:** celltype-cli's system prompt references oncology concepts, drug targets,
ADMET properties, clinical endpoints. These concepts leak into plant science reasoning. Agent
assesses "drug-likeness" of gene targets or asks about "clinical precedent" for plant editing
strategies.

**Prevention:** Complete system prompt replacement is required before any plant science tool work.
The system prompt is the agent's identity. Partial replacement leaves oncology concepts active.
Search for and remove: "cancer", "tumour", "drug", "clinical", "patient", "therapeutic", "ADMET",
"pharmacology" in the plant science system prompt.

**Detection:** Run a prompt coverage test: load the system prompt, run it through a keyword filter,
fail if any pharma-domain terms are present.

**Phase:** Milestone 1 — Plant science system prompt replacement

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| M1: Fork setup | Fork maintenance trap (M1) | Establish upstream tracking discipline day one |
| M1: System prompt | Oncology residue (L5) | Full replacement, not partial edit; automated keyword test |
| M1: Data loaders | Dataset version drift (C5) | Metadata + content hash from the first loader |
| M1: Species support | Species-hardcoding (C2) | Species registry + two-species test suite from day one |
| M1: Tool filtering | Pharma tool leakage (L2) | CI test for exposed tool list |
| M1: Orthology tools | Species distance weighting (M4) | Implement phylogenetic tier from day one |
| M2: Target construction | Strategy constraint ignored (M5) | Controlled vocabulary + programmatic enforcement |
| M2: Target construction | Gene outside longlist (G3) | Frozen target set; validation against every output |
| M2: Evidence planning | Dataset hallucination (M3) | Manifest-driven planning; JSON output schema |
| M2: Evidence planning | Evidence double-counting (C3) | Post-plan correlation check as mandatory gate |
| M2: Evidence computation | Context window exhaustion (C4) | Per-stream agents; disk-backed evidence |
| M2: Scoring | Scoring as agent judgement (C1) | Scoring engine is code, not prose; transform_spec required |
| M2: Normalisation | Missing data as negative (L3) | Explicit NA handling; missingness diagnostic output |
| M2: Ranking | Post-hoc constraint fixing (G1) | Stage gates; canonical table first; all outputs derived |
| M2: Organism check | Wrong-organism dataset (G2) | Programmatic middleware; local-first allowlist |
| M2: DSL design | Transform spec complexity spiral (M2) | Scope limit; code fallback for edge cases |
| M2: Dossier | Rich output masking thin evidence (L1) | Evidence summary table; confidence flag in header |
| M2: Dossier | Inconsistent format (G4) | Schema-enforced structure; per-target independent calls |
| M2: Artifact derivation | PDF drift (G5) | Hash-linked derivation chain; canonical table is source of truth |
| M1+M2: Gene IDs | Name ambiguity (L4) | Species-qualified stable IDs throughout pipeline |

---

## Sources

- PRODUCT_SPEC.md (Gotchas section) — directly observed failures in Kosmos production runs (HIGH confidence)
- FEASIBILITY_REPORT.md (Risk assessment §5) — architecture risk analysis (HIGH confidence)
- PROJECT.md (Previous learnings, Key Decisions) — design rationale informed by known failures (HIGH confidence)
- Training knowledge: agentic pipeline failure modes, LLM constraint violations, bioinformatics reproducibility, plant science data landscape, evidence integration anti-patterns (MEDIUM confidence — corroborated by project documentation)
