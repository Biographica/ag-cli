# Technology Stack: ag-cli Plant Science Platform

**Project:** ag-cli — agricultural biotech target identification platform
**Researched:** 2026-02-25
**Research mode:** Ecosystem (brownfield — forking celltype-cli)

> **Tooling note:** This research was produced under tool restrictions (no live WebSearch, WebFetch, or Bash execution). All versions and claims are from training knowledge through August 2025 unless explicitly noted otherwise. Every section carries a confidence rating. Versions tagged [VERIFY] should be checked against PyPI before pinning in pyproject.toml.

---

## Recommended Stack

### Core Framework (Inherited — Keep As-Is)

| Technology | Version (keep) | Purpose | Keep? |
|------------|---------------|---------|-------|
| `anthropic` (Claude Agent SDK) | `>=0.74.0` | LLM client + agentic loop | YES — core engine |
| `claude-agent-sdk` | `>=0.1` | Agent orchestration | YES — core engine |
| `typer` | `>=0.12` | CLI entrypoint | YES |
| `rich` | `>=13.0` | Terminal UI formatting | YES |
| `prompt-toolkit` | `>=3.0` | Interactive terminal input | YES |
| `pandas` | `>=2.0` | Tabular data manipulation | YES — critical for scoring |
| `numpy` | `>=1.24` | Numerical computation | YES |
| `scipy` | `>=1.10` | Statistical functions | YES |
| `httpx` | `>=0.27` | HTTP client for APIs | YES |
| `python-dotenv` | `>=1.0` | Config/secrets | YES |
| `markdown` | `>=3.5` | Report rendering | YES |
| `nbformat` | `>=5.7` | Notebook export | YES |

**Confidence: HIGH** — These are confirmed from the existing `pyproject.toml` and are unchanged.

---

### Plant Science Domain Stack (New Additions)

#### 1. Genomics and Sequence Processing

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `biopython` | `>=1.83` [VERIFY] | GFF/FASTA/GenBank parsing, sequence analysis, Entrez API | The de-facto standard for bioinformatics in Python. Already in celltype-cli optional deps as `>=1.81`. Handles GFF3 parsing (`BCBio.GFF`), FASTA sequence retrieval, and cross-reference lookups via Bio.Entrez. Used by every bioinformatics tool in the ecosystem. |
| `gffutils` | `>=0.12` [VERIFY] | GFF/GTF database creation and querying | Superior to raw GFF parsing for feature lookup. Creates a SQLite-backed database from GFF3 files that enables fast feature queries (get all transcripts for a gene, all exons for a transcript). Critical for plant genome annotation workflows where GFF3 is the standard format from Ensembl Plants / Phytozome. |
| `pyranges` | `>=0.0.129` [VERIFY] | Genomic interval operations | Fast, pandas-based genomic range operations. More Pythonic than pybedtools (which wraps BEDTools CLI). Use for overlap queries, interval merging, finding PAM sites in gene bodies, regulatory region annotation. Built on pandas so integrates naturally with the existing data pipeline. |
| `pybedtools` | `>=0.9.1` [VERIFY] | BEDTools wrapper for complex interval operations | Fallback for operations pyranges doesn't cover. Requires BEDTools CLI installed. Use only when pyranges is insufficient — keep as optional dependency. |

**Confidence: MEDIUM** — Libraries are correct; versions need PyPI verification.

**What NOT to use:**
- `HTSeq` — older, slower, largely superseded by pyranges for interval work
- `pysam` — C extension, complex installation, overkill for this use case (we're reading local files, not BAM/CRAM alignment streams)

---

#### 2. Plant Database Data Loaders (Local-First Pattern)

The PROJECT.md specifies local-first data access. The following databases should be bulk-downloaded to local storage. Each requires a loader following the existing `loaders.py` pattern.

| Database | Format | Download Method | Loader Pattern | Priority |
|----------|--------|-----------------|---------------|----------|
| **Ensembl Plants** | GFF3, FASTA, TSV (orthologs, variation) | FTP bulk download per release | `load_ensembl_plants(species, release)` | HIGH — gene models, orthologs, variation |
| **PlantExp** | TSV/Parquet (expression matrices + metadata) | Direct download from plantexp.org | `load_plantexp(species)` | HIGH — expression breadth, tissue specificity |
| **TAIR** (Arabidopsis) | GFF3, TSV (GO, functional annotations) | FTP bulk download | `load_tair()` | HIGH — best-annotated reference species |
| **Gramene** | GFF3, VCF (plant QTL/GWAS) | FTP / API bulk + local cache | `load_gramene_qtl(species, trait)` | HIGH — QTL/efficacy evidence |
| **STRING** (plant networks) | TSV (protein interaction edges + scores) | FTP bulk per taxon | `load_string_ppi(taxon_id)` | HIGH — pleiotropic risk via network centrality |
| **PlantTFDB** | TSV (TF family classifications per species) | HTTP bulk download | `load_plant_tfdb(species)` | MEDIUM — TF identification, regulatory annotation |
| **Phytozome** (JGI) | GFF3, FASTA (crop genomes) | JGI account required, wget | `load_phytozome(species)` | MEDIUM — major crop species not in Ensembl |
| **PLEXdb** | CSV (microarray/RNA-seq cross-experiment) | HTTP per experiment | `load_plexdb(experiment_id)` | LOW — legacy, PlantExp is better |
| **Plant Reactome** | TSV/JSON (plant pathway annotations) | FTP bulk download | `load_plant_reactome(species)` | MEDIUM — pathway context for pleiotropic risk |

**No additional Python libraries are needed for these loaders beyond what's already in the stack** — they are TSV/CSV/GFF3 files read with pandas + gffutils + biopython.

**Confidence: MEDIUM** — Database existence is correct; specific download URLs and file formats should be verified against each database's current documentation before implementation.

**Access patterns by database:**

```
Ensembl Plants FTP:
  ftp://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-XX/
  → gff3/{species}/{species}.{assembly}.{release}.gff3.gz
  → tsv/ensembl-compara/homologies/

PlantExp:
  https://plantexp.org/download/
  → Species-specific expression matrices (read counts + TPM + metadata)

TAIR:
  https://www.arabidopsis.org/download/
  → TAIR10_GFF3_genes.gff, TAIR10_functional_descriptions.txt, GO annotations

Gramene:
  https://ensembl.gramene.org/
  → Uses Ensembl Plants REST API + FTP — same FTP as Ensembl Plants

STRING:
  https://string-db.org/cgi/download
  → {taxon_id}.protein.links.detailed.v12.0.txt.gz
  → Plant taxon IDs: Arabidopsis=3702, Rice=39947, Maize=4577, etc.
```

---

#### 3. Co-Expression Analysis

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `PyWGCNA` | `>=1.1.9` [VERIFY] | Python WGCNA — weighted gene co-expression network analysis | The standard method in plant transcriptomics. PyWGCNA is the maintained Python port of the R WGCNA package. Identifies co-expression modules from RNA-seq data, computes module-trait correlations, hub genes. Used extensively in crop science (maize, soybean, rice papers). Works with pandas DataFrames. |
| `networkx` | `>=3.0` | Graph operations on co-expression + PPI networks | Already implicitly available (likely a transitive dep). Standard Python graph library. Use for: network centrality metrics (betweenness, degree), community detection, PPI subgraph extraction for pleiotropic risk scoring. |
| `leidenalg` | `>=0.10` [VERIFY] | Community detection in gene networks | The current best-practice community detection algorithm (supersedes Louvain). Used in scanpy (already in optional deps) and applicable to gene networks. Faster and higher quality than Louvain for plant-scale networks. |
| `scikit-learn` | `>=1.3` | Correlation computation, clustering (fallback) | Already in optional deps as `analysis` extra. Use for Pearson/Spearman correlation matrices when PyWGCNA is overkill. |

**Confidence: MEDIUM-HIGH** — PyWGCNA is an established library; networkx and scikit-learn are in the existing stack.

**What NOT to use:**
- `rpy2` + R WGCNA directly — adds R dependency, fragile environment, not portable. PyWGCNA eliminates this.
- `CEMiTool` — R-only, same problem
- Rolling your own correlation matrix clustering — PyWGCNA is well-tested and expected by plant biologists

---

#### 4. Orthology Analysis

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `OrthoFinder` (via subprocess) | `>=2.5.5` [VERIFY] | De novo ortholog group inference | The gold-standard tool for ortholog detection in plants. Not a Python library — called via subprocess or pre-computed results loaded from output files. For ag-cli: pre-compute OrthoFinder runs for target species sets offline; loaders read the Orthogroups.tsv output. |
| `ete3` | `>=3.1.3` [VERIFY] | Phylogenetic tree parsing and manipulation | ETE Toolkit. Use for: reading OrthoFinder species trees, computing phylogenetic distances between species for cross-species evidence downweighting, tree visualisation. Includes NCBI taxonomy integration. |
| `pandas` (existing) | — | Loading Ensembl Compara homology TSVs | For simpler orthology lookups: Ensembl Compara provides pre-computed 1-to-1, 1-to-many, many-to-many ortholog tables as bulk TSV downloads. No additional library needed — pandas reads these directly. Faster than running OrthoFinder for well-annotated species. |

**Confidence: MEDIUM** — OrthoFinder is the established standard; ETE3 is the standard tree library. Verify OrthoFinder still at >=2.5.x.

**Recommended pattern:**
```
Tier 1 (fast, pre-computed): Ensembl Compara homology TSVs → pandas
Tier 2 (deeper, offline): OrthoFinder output files → pandas
Tier 3 (phylogenetic distances): ete3 → distance matrix for downweighting
```

**What NOT to use:**
- InParanoid (API-dependent, slow, less comprehensive than Ensembl Compara)
- BLAST-only approaches (too slow, no grouping)

---

#### 5. CRISPR Guide Design and Gene Editing Assessment

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `crisprtools` / `FlashFry` | via subprocess | Fast guide enumeration across genome | FlashFry (Java, via subprocess) is the fastest tool for genome-wide PAM site enumeration and off-target scoring at scale. For plant genomes (500Mb–2Gb), pure-Python guides are too slow. Run FlashFry offline to generate guide libraries; loaders read pre-computed output. |
| `crispritz` | via subprocess [VERIFY] | Off-target and variant-aware guide analysis | CRISPRitz handles variant-aware off-target search (important for crop varieties with high SNP density). Subprocess call, pre-compute. |
| `biopython` (existing) | — | Sequence retrieval for PAM site analysis | Bio.SeqUtils + Bio.Seq for: reverse complement, finding PAM motifs (NGG for SpCas9, TTTV for AsCpf1) in retrieved sequences. Used for targeted, per-gene guide analysis in the agent loop. |
| `numpy` (existing) | — | Guide scoring computation | On-target scoring rules (Doench 2016/Rule Set 2) are pure numpy computations once you have the 30-nt sequence features. Implement as a scoring function — no additional library needed. |

**Editability scoring components (no additional libs needed):**
1. **PAM density** — count NGG/PAM sites in coding sequence + upstream regulatory region via pyranges + biopython
2. **On-target efficiency** — Doench 2016 Rule Set 2 implemented in numpy (position weight matrix on 30-nt context)
3. **Off-target risk** — pre-computed FlashFry scores loaded from local files
4. **Regulatory element conflicts** — overlap guides with known promoter/enhancer regions via pyranges
5. **Homolog interference risk** — check if editing site is conserved in paralogs via biopython pairwise alignment

**Confidence: MEDIUM** — FlashFry is established; the scoring scheme above is grounded in the plant CRISPR literature as of 2025. CRISPRitz verification recommended.

**What NOT to use:**
- `chopchop` (web-only, no good Python API)
- `Cas-OFFinder` (GPU-dependent, overkill for local use)
- `CRISPOR` web API (violates local-first principle; rate-limited)

---

#### 6. Literature and Patent Search

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `metapub` | `>=0.5.5` [VERIFY] | PubMed full metadata fetch with MeSH terms | Better than raw Bio.Entrez for bulk metadata. Handles rate limiting, returns structured objects. Use for plant-specific literature scoring (novelty evidence stream). |
| `requests` / `httpx` (existing) | — | Lens.org API, Europe PMC, OpenAlex | The literature tools already in celltype-cli use httpx. Extend for: Lens.org patent search (free tier, plant-relevant), Europe PMC (plant-specific full-text search), OpenAlex (already used). |
| `crossref-commons` | `>=0.0.7` [VERIFY] | CrossRef metadata lookup for DOI resolution | Useful for resolving citations from gene databases back to literature. Low-priority addition. |

**Existing celltype-cli literature tools (keep, adapt for plant queries):**
- `literature.pubmed_search` — works fine, add plant MeSH terms to system prompt guidance
- `literature.openalex_search` — works fine as-is
- Lens.org patent search — add as new tool `literature.patent_search`

**Confidence: MEDIUM** — metapub is established; Lens.org free API is documented.

---

#### 7. Evidence Integration and Scoring Framework

**No additional libraries are needed for the scoring engine.** The existing stack covers everything:

| Computation | Library | Notes |
|------------|---------|-------|
| Percentile normalisation | `scipy.stats.percentileofscore` | Already in stack |
| Z-score normalisation | `scipy.stats.zscore` | Already in stack |
| Rank normalisation | `scipy.stats.rankdata` | Already in stack |
| Weighted aggregation | `numpy` | Simple dot products |
| Missing value imputation | `pandas` + `scipy` | `fillna`, `SimpleImputer` |
| Pseudo-Bayesian posterior update | Pure `numpy` | Formula from spec is simple arithmetic |
| Squashing functions | `scipy.special.expit` (sigmoid) | Already in stack |
| Schema validation | `pydantic` | **NEW — add this** |

**Add `pydantic`:**

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pydantic` | `>=2.5` [VERIFY] | Schema validation for project specs, evidence streams, pipeline outputs | The product spec demands structured, validated inputs and outputs. Pydantic v2 provides fast Python schema validation with clear error messages. Use for: `ProjectSpec`, `EvidenceStream`, `ScoredTarget`, `Dossier` models. Prevents the "gotcha" of malformed inputs passing through silently. Already transitively available (Anthropic SDK uses pydantic). |

**Confidence: HIGH** — pydantic v2 is the clear standard for Python schema validation in 2025; scipy/numpy cover all scoring needs.

---

#### 8. Output and Reporting

| Library | Version | Purpose | Keep/Add |
|---------|---------|---------|---------|
| `markdown` (existing) | `>=3.5` | Report rendering | KEEP |
| `jinja2` | `>=3.1` [VERIFY] | Dossier template rendering | ADD — the dossier generation from PROJECT.md requires structured templates with variable substitution. Jinja2 is the standard Python templating library. More powerful than f-string templates for multi-section dossiers. |
| `openpyxl` | `>=3.1` [VERIFY] | Excel export of ranking tables | ADD — seed breeders and trait developers work in Excel. The canonical ranking table should export to `.xlsx`. Pure Python, no dependencies. |
| `seaborn` | `>=0.13` | Visualisation for dossiers | KEEP (already optional dep) |

**Confidence: MEDIUM-HIGH** — jinja2 and openpyxl are established standards.

---

### Supporting Libraries (Dev and Testing)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `pytest` | `>=8.0` | Test runner | Keep (existing) |
| `pytest-cov` | `>=5.0` | Coverage | Keep (existing) |
| `ruff` | `>=0.5` | Linting + formatting | Keep (existing) |
| `pytest-mock` | `>=3.12` [VERIFY] | Mock for plant data loaders | ADD — the existing mock pattern (`@patch("ct.tools.module.load_X")`) needs this. Currently implicit. Make explicit in dev deps. |
| `responses` | `>=0.25` [VERIFY] | Mock HTTP responses in tests | ADD — for testing Ensembl Plants REST calls, Gramene API calls without hitting live endpoints. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| GFF parsing | `gffutils` | `bcbio-gff` (Bio package) | `gffutils` creates a SQLite DB for fast repeated queries — better for agent tools that query features repeatedly |
| GFF parsing | `gffutils` | Raw `biopython` GFF parse | Raw parsing re-reads the file every call; gffutils indexes once |
| Interval operations | `pyranges` | `pybedtools` | pyranges is pure Python + pandas, no CLI dependency; pybedtools wraps BEDTools binary |
| Co-expression | `PyWGCNA` | Custom Pearson + clustering | WGCNA is the plant science standard; biologists will expect it |
| Co-expression | `PyWGCNA` | `rpy2` + R WGCNA | Avoids R dependency entirely |
| Orthology | Ensembl Compara TSV | InParanoid | Ensembl Compara is pre-computed, comprehensive, and local-first compatible |
| Orthology | OrthoFinder (de novo) | BLAST + custom grouping | OrthoFinder is the community standard; BLAST-only misses ortholog group structure |
| CRISPR guides | FlashFry + numpy scoring | `crispor` API | CRISPOR is web-only, violates local-first; FlashFry runs locally at scale |
| CRISPR guides | FlashFry + numpy scoring | Azimuth (Microsoft) | Azimuth is Python but requires a model download and has dependency complexity; Doench Rule Set 2 is equivalent for plant contexts |
| Schema validation | `pydantic` | `marshmallow` | pydantic v2 is faster, more Pythonic, better IDE support, has become the ecosystem standard |
| Templating | `jinja2` | f-strings | Dossiers are complex multi-section documents; f-strings don't scale |
| Single-cell (existing) | `scanpy` | Keep as optional | Single-cell rarely used for plants; keep as optional dep, don't remove |

---

## What to Drop (Runtime Filter, Not Delete)

Per FEASIBILITY_REPORT.md and PROJECT.md decision: filter at runtime, don't delete from codebase.

| Tool Module | Runtime Filter Category | Why Hidden for ag-cli |
|-------------|------------------------|----------------------|
| `chemistry.py` | pharma | Drug chemistry, ADMET — not plant editing |
| `clinical.py` | pharma | Clinical trials — no plant analog |
| `safety.py` | pharma | ADMET, DDI profiling — no plant analog |
| `cro.py` | pharma | Contract research orgs for pharma |
| `viability.py` | pharma | Cancer cell viability |
| `combination.py` | pharma | Drug combinations |
| `structure.py` | pharma | Protein docking for drug design |
| `biomarker.py` | pharma | Cancer biomarkers |
| `pk.py` | pharma | Pharmacokinetics |
| `repurposing.py` | pharma | Drug repurposing |
| `translational.py` | pharma | Translational medicine |
| `cellxgene.py` | pharma | Human cell atlas — not plant |
| `singlecell.py` | pharma | Human single-cell — not plant |
| `clue.py` | pharma | CLUE connectivity map — human |

**Keep but adapt:** `genomics.py`, `expression.py`, `literature.py`, `network.py`, `protein.py`, `dna.py`, `data_api.py`, `statistics.py`, `code.py`, `files.py`, `ops.py`

---

## Installation

### Core dependencies (update pyproject.toml)

```toml
[project]
name = "ag-cli"
version = "0.1.0"

dependencies = [
    # Inherited from celltype-cli
    "typer>=0.12",
    "rich>=13.0",
    "prompt-toolkit>=3.0",
    "anthropic>=0.74.0",
    "openai>=1.0",
    "claude-agent-sdk>=0.1",
    "httpx>=0.27",
    "pandas>=2.0",
    "numpy>=1.24",
    "scipy>=1.10",
    "python-dotenv>=1.0",
    "markdown>=3.5",
    "nbformat>=5.7",
    # New additions
    "pydantic>=2.5",
    "jinja2>=3.1",
    "openpyxl>=3.1",
    "biopython>=1.83",
    "gffutils>=0.12",
    "pyranges>=0.0.129",
    "networkx>=3.0",
    "ete3>=3.1.3",
    "metapub>=0.5.5",
    "jinja2>=3.1",
]

[project.optional-dependencies]
plants = [
    "PyWGCNA>=1.1.9",
    "leidenalg>=0.10",
    "pybedtools>=0.9.1",
]
analysis = [
    "seaborn>=0.13",
    "scikit-learn>=1.3",
]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "responses>=0.25",
    "ruff>=0.5",
]
```

### External tools (non-Python, pre-installed)

```bash
# FlashFry — fast guide enumeration (Java, pre-installed separately)
# Download: https://github.com/mckennalab/FlashFry/releases
# Version: >=1.12 [VERIFY]
# Used by: gene_editing.enumerate_guides tool

# BEDTools — optional for pybedtools fallback
# brew install bedtools  OR  conda install -c bioconda bedtools
# Version: >=2.31 [VERIFY]
```

---

## Data Volume Estimates

| Dataset | Approximate Size | Format | Local Path |
|---------|-----------------|--------|-----------|
| Ensembl Plants GFF3 (per species) | 50–300 MB | GFF3.gz | `~/.ag/data/ensembl_plants/{species}/` |
| Ensembl Plants orthologs (per release) | 2–5 GB | TSV.gz | `~/.ag/data/ensembl_plants/compara/` |
| PlantExp (all species) | 5–20 GB | Parquet | `~/.ag/data/plantexp/` |
| STRING plant networks (per species) | 50–200 MB | TSV.gz | `~/.ag/data/string/{taxon_id}/` |
| TAIR annotations | ~500 MB | GFF3 + TSV | `~/.ag/data/tair/` |
| Gramene QTL/GWAS | 1–3 GB | VCF + TSV | `~/.ag/data/gramene/` |
| PlantTFDB (all species) | ~200 MB | TSV | `~/.ag/data/planttfdb/` |
| Pre-computed CRISPR guides (per genome) | 1–5 GB | TSV | `~/.ag/data/crispr/{species}/` |
| **Total (4–5 species)** | **~30–50 GB** | — | `~/.ag/data/` |

**Recommendation:** Use the `ct data pull` pattern from celltype-cli to build `ag data pull <dataset>` commands. These run bulk downloads into the configured `data.base` path.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Core inherited stack | HIGH | Directly read from pyproject.toml — no uncertainty |
| Bioinformatics libraries (biopython, gffutils, pyranges) | MEDIUM | Established libraries; versions need PyPI verification |
| Plant databases (existence and format) | MEDIUM | Well-documented databases; download URLs may have changed |
| Co-expression (PyWGCNA, networkx) | MEDIUM | PyWGCNA is established but smaller community; verify active maintenance |
| Orthology (Ensembl Compara, OrthoFinder) | MEDIUM-HIGH | Both are gold-standard tools; versions need checking |
| CRISPR tools (FlashFry, scoring scheme) | MEDIUM | Plant CRISPR is mature; specific tool versions need verification |
| Scoring engine (pydantic, scipy/numpy) | HIGH | These are industry standards with no viable alternatives |
| Output and reporting (jinja2, openpyxl) | HIGH | Industry standards, low risk |
| Items tagged [VERIFY] | LOW until verified | All version pins in this document tagged [VERIFY] must be confirmed against PyPI before use |

---

## Pre-Implementation Checklist

Before coding begins, verify:

- [ ] All `[VERIFY]` version tags confirmed against PyPI current releases
- [ ] `PlantExp` download URL and data format confirmed at plantexp.org
- [ ] `Ensembl Plants` FTP structure confirmed for release 60 (current as of 2025)
- [ ] `Gramene` GFF3 vs REST API strategy decided (bulk download vs cached API calls)
- [ ] `FlashFry` current release version and Java requirement confirmed
- [ ] `PyWGCNA` actively maintained (check GitHub last commit date)
- [ ] `leidenalg` compatible with target Python version (historically had issues on Python 3.12+)
- [ ] `ete3` Python 3.12 compatibility confirmed (has had compatibility issues historically)
- [ ] `Phytozome` JGI account access process confirmed (institutional login required)

---

## Sources

All findings from training knowledge through August 2025. No live web verification was possible during this research session due to tool restrictions. The following are the authoritative sources to consult during the pre-implementation verification phase:

- PyPI (https://pypi.org) — all library versions
- Ensembl Plants FTP (https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/) — database structure and formats
- PlantExp (https://plantexp.org) — download availability and format
- STRING-DB (https://string-db.org/cgi/download) — plant network downloads
- TAIR (https://www.arabidopsis.org/download/) — Arabidopsis data files
- Gramene (https://www.gramene.org) — plant QTL/GWAS data
- OrthoFinder GitHub (https://github.com/davidemms/OrthoFinder) — current release
- FlashFry GitHub (https://github.com/mckennalab/FlashFry) — current release
- PyWGCNA GitHub (https://github.com/mortazavilab/PyWGCNA) — maintenance status
- ETE Toolkit (https://etetoolkit.org) — Python 3.12 compatibility
