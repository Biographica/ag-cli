# Phase 5: Gene Editing and Evidence Tools - Research

**Researched:** 2026-03-02
**Domain:** CRISPR guide design, paralogy scoring, local bioinformatics tool invocation, multi-species evidence orchestration
**Confidence:** HIGH (architecture and patterns), MEDIUM (scoring algorithm specifics), HIGH (integration patterns)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CRISPR guide design (editing.crispr_guide_design)**
- Extensible Cas system registry — pluggable architecture for adding new nucleases
- Ship SpCas9 (NGG PAM) and Cas12a/Cpf1 (TTTV PAM) for M1
- Off-target prediction via local alignment against reference genome
- Data resolution chain for genome FASTA: user-provided file > locally cached reference > auto-download from NCBI
- Guide scoring returns both a ranked list with composite on-target scores AND tier classification (high confidence / acceptable / poor) per guide
- Return all viable guides, capped at 20 per default
- Each guide includes: on-target score, off-target count, GC%, position in gene, tier label

**Editability scoring (editing.editability_score)**
- Thin wrapper / convenience aggregator — calls guide design + gene structure + regulatory info tools
- Returns structured per-factor sub-scores (guide quality, structure complexity, regulatory complexity)
- No opinionated composite score or weighting — the agent or downstream pipeline decides what "editable" means in context
- Atomic tools philosophy: this is a building block, not a scoring engine

**Paralogy scoring (genomics.paralogy_score)**
- Data resolution: OrthoFinder results (local) > Ensembl Compara API (fallback)
- Returns paralog count, co-expression overlap with paralogs, shared GO annotations
- Follows same local-first philosophy as off-target prediction

**Evidence gathering (TOOL-09)**
- NOT a new tool — validated as an end-to-end test
- Test: given a gene list and species, verify the agent naturally chains expression, ortholog, GWAS, PPI, literature, and editing tools into a structured per-gene evidence summary
- If the agent can't compose the workflow naturally, that's a signal for system prompt tuning or M2 meta-prompting — not a new tool

**Local bioinformatics tool invocation (new infrastructure)**
- New shell executor utility — wraps subprocess calls with timeout, error handling, "tool not installed" detection
- Pluggable tool registry for adding new bioinformatics tools over time
- Minimum tool set for M1: BLAST+, OrthoFinder, Bowtie2/minimap2
- Graceful degradation: if a local tool isn't installed, fall back to API equivalent where available
- Establishes the reusable pattern for all future local tool integrations

### Claude's Discretion
- Shell executor design and API (dedicated utility vs. other patterns)
- Guide scoring algorithms (Rule Set 2, DeepCpf1, or simpler heuristics)
- Editability sub-score definitions and factor extraction approach
- Bowtie2 vs. minimap2 selection for off-target alignment
- NCBI genome download mechanism and caching strategy
- Bioinformatics tool registry design

### Deferred Ideas (OUT OF SCOPE)
- Retrofit `genomics.ortholog_map` to support local-first OrthoFinder data — Phase 4 scope
- Expand bioinformatics toolbelt beyond BLAST+/OrthoFinder/Bowtie2 — future phases
- Meta-prompting framework for evidence orchestration workflows — M2 pipeline scope
- Opinionated scoring rubrics and composite editability scores — M2 pipeline scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOOL-06 | User can assess CRISPR guide design (PAM sites, guide scoring, off-target prediction) for a gene | PAM scanning via regex, heuristic on-target scoring (GC%, position biases), off-target via Bowtie2 subprocess or fallback regex scan; genome FASTA via data resolution chain |
| TOOL-07 | User can estimate editability of a gene based on gene structure, guide availability, and regulatory complexity | Thin aggregator calling `editing.crispr_guide_design` + `genomics.gff_parse` (already built Phase 4) + stub regulatory complexity factor; no composite weighting |
| TOOL-08 | User can score paralogy/functional redundancy for a gene (paralog count, co-expression overlap, shared annotations) | Ensembl Compara `type=paralogues` endpoint mirrors `ortholog_map` pattern exactly; local OrthoFinder Orthogroups.tsv as primary source; co-expression via existing `genomics.coexpression_network`; GO via existing `genomics.gene_annotation` |
| TOOL-09 | User can gather evidence across species for a given gene list (multi-species evidence collection orchestrated by agent) | NOT a new tool — validated via end-to-end test; agent composes Phase 3-5 tools naturally; test verifies tool composition succeeds for 5+ gene list |
</phase_requirements>

---

## Summary

Phase 5 delivers four capabilities: two new editing tools (`editing.crispr_guide_design`, `editing.editability_score`), one new genomics tool (`genomics.paralogy_score`), a new shared infrastructure utility (`_local_tools.py` shell executor), and an end-to-end test validating multi-species evidence orchestration. All three tools follow patterns established in Phases 3 and 4 exactly.

The CRISPR guide design tool requires the most novel implementation: PAM scanning is pure Python regex (no external library needed), on-target scoring uses heuristics derivable from published rule sets without heavy ML dependencies, and off-target counting uses Bowtie2 as a subprocess (with graceful fallback to a simple regex mismatch scan when Bowtie2 is absent). The genome FASTA data resolution chain mirrors the GFF3 pattern in `genomics.gff_parse` (local file > cached download > NCBI auto-download).

Paralogy scoring reuses `ortholog_map` architecture almost verbatim — the Ensembl Compara API accepts `type=paralogues` as a parameter, and the local OrthoFinder output (Orthogroups.tsv + Gene_Duplication_Events/Duplications.tsv) provides an unambiguous paralog source. Co-expression overlap and shared GO terms reuse existing Phase 4 tools as sub-calls. The editability score tool is a thin data aggregator with no novel algorithmic content.

**Primary recommendation:** Implement `editing.crispr_guide_design` with pure-Python PAM scanning and heuristic scoring, Bowtie2 subprocess for off-target (with "not installed" graceful degradation), and NCBI eutils for genome FASTA auto-download. Mirror `ortholog_map` exactly for `genomics.paralogy_score`, swapping `type=orthologues` for `type=paralogues`.

---

## Standard Stack

### Core (what the project already uses — no new additions needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | HTTP calls for Ensembl Compara and NCBI eutils | Already in core deps |
| gffutils | >=0.13 | GFF3 parsing (editability sub-score) | Already in core deps |
| pyyaml | >=6.0 | YAML registry files | Already in core deps |
| subprocess (stdlib) | Python 3.10+ | Shell executor for Bowtie2/OrthoFinder | stdlib, no install |
| shutil (stdlib) | Python 3.10+ | `shutil.which()` for tool detection | stdlib, no install |
| re (stdlib) | Python 3.10+ | PAM site regex scanning | stdlib, no install |

### Supporting (optional, already in extras)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| biopython | >=1.81 | `Bio.Entrez` for NCBI FASTA download; `SeqIO` for FASTA parsing | Available as `biology` optional extra; lazy-import inside function |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| biopython for NCBI download | httpx + direct eutils URL | httpx already in core deps; biopython adds robustness with Entrez rate limiting. Decision: use httpx direct URL for FASTA downloads to avoid optional dep in core path; biopython as fallback if needed |
| Bowtie2 subprocess | minimap2 subprocess | Bowtie2 is more standard for short-read alignment (20 nt guides); minimap2 is better for long reads. Decision: Bowtie2 primary, minimap2 acceptable alternative — detect whichever is installed first |
| Ensembl Compara paralogues API | OrthoFinder local output | OrthoFinder is more precise (gene tree-based); Ensembl is always available. Decision: OrthoFinder first, Ensembl fallback — mirrors local-first philosophy |
| Full Rule Set 2 (sklearn needed) | Heuristic scoring | Rule Set 2 requires scikit-learn (optional dep only). Decision: heuristic scoring as default; Rule Set 2 available only if sklearn installed — check at runtime |

**Installation:** No new core dependencies required. `biopython` is already in the `biology` optional extra. `scikit-learn` is already in the `analysis` optional extra.

---

## Architecture Patterns

### Recommended File Structure
```
src/ct/tools/
├── editing.py              # NEW: editing.crispr_guide_design, editing.editability_score
├── _local_tools.py         # NEW: shell executor utility, bio tool registry
├── genomics.py             # EXTEND: add genomics.paralogy_score function
└── __init__.py             # EXTEND: add "editing" to PLANT_SCIENCE_CATEGORIES + _TOOL_MODULES

tests/
├── test_editing.py         # NEW: unit tests for editing.py tools
├── test_paralogy.py        # NEW: unit tests for genomics.paralogy_score
├── test_local_tools.py     # NEW: unit tests for _local_tools.py
└── test_e2e_evidence.py    # NEW: end-to-end test for TOOL-09 evidence orchestration
```

### Pattern 1: PAM Site Scanning (pure Python, no dependencies)
**What:** Regex scan of both strands of a gene sequence for PAM patterns.
**When to use:** Core of `editing.crispr_guide_design` before off-target prediction.
**Key facts:**
- SpCas9: PAM is NGG on the non-template strand, guide is 20 nt upstream of PAM (3' PAM)
- Cas12a/Cpf1: PAM is TTTV (V = A/C/G) on the non-template strand, guide is 20 nt downstream of PAM (5' PAM)
- Scan both strands; reverse complement handles the complementary strand

```python
# Source: domain knowledge + CRISPR literature, confidence HIGH
import re

_CAS_REGISTRY = {
    "SpCas9": {
        "pam_pattern": r"(?=[ACGT]{20}([CGT]GG))",    # NGG, guide upstream
        "guide_len": 20,
        "pam_len": 3,
        "pam_position": "3prime",
    },
    "Cas12a": {
        "pam_pattern": r"(TTT[ACG])([ACGT]{20})",      # TTTV, guide downstream
        "guide_len": 20,
        "pam_len": 4,
        "pam_position": "5prime",
    },
}

def _scan_pam_sites(sequence: str, cas_system: str = "SpCas9") -> list[dict]:
    """Scan both strands for PAM sites and extract guide sequences."""
    config = _CAS_REGISTRY[cas_system]
    guides = []
    seq = sequence.upper()
    rc_seq = _reverse_complement(seq)  # reuse from dna.py pattern

    for strand, s in [("+", seq), ("-", rc_seq)]:
        if config["pam_position"] == "3prime":
            # Guide is immediately upstream of PAM (SpCas9 NGG)
            for m in re.finditer(r"(?=([ACGT]{20}[CGT]GG))", s):
                guide_seq = m.group(1)[:20]
                pam = m.group(1)[20:]
                pos = m.start()
                guides.append({"guide": guide_seq, "pam": pam, "strand": strand, "position": pos})
        else:
            # Guide is immediately downstream of PAM (Cas12a TTTV)
            for m in re.finditer(r"TTT[ACG]([ACGT]{20})", s):
                guide_seq = m.group(1)
                pam = m.group(0)[:4]
                pos = m.start()
                guides.append({"guide": guide_seq, "pam": pam, "strand": strand, "position": pos})
    return guides
```

### Pattern 2: Heuristic On-Target Scoring
**What:** Rule-based guide quality score without ML dependencies. Based on published heuristics from CRISPR literature.
**When to use:** Default scoring path. Rule Set 2 / DeepHF optional if sklearn available.

Key heuristics (MEDIUM confidence — from peer-reviewed literature, not directly verified in a single source):
- GC content: 40-70% optimal (penalize outside range)
- Avoid polyT runs (>3 T in guide — premature transcription termination for Pol III)
- Avoid G at position 1 (5' end) for some Cas9 systems
- Terminal dinucleotide GG at 3' end correlates with higher efficiency (Doench Rule Set 2)
- Avoid homopolymer runs >4 nt

```python
# Source: Doench 2016 NatBiotech Rule Set 2 heuristics (distilled), MEDIUM confidence
def _score_guide_heuristic(guide: str) -> float:
    """Return a 0-1 heuristic on-target score."""
    score = 0.5  # baseline
    gc = (guide.count("G") + guide.count("C")) / len(guide)
    # GC penalty
    if 0.40 <= gc <= 0.70:
        score += 0.2
    elif gc < 0.25 or gc > 0.85:
        score -= 0.3
    # PolyT penalty (Pol III terminator)
    if "TTTT" in guide:
        score -= 0.2
    # Homopolymer penalty
    for base in "ACGT":
        if base * 5 in guide:
            score -= 0.1
    return max(0.0, min(1.0, score))

def _tier_label(score: float) -> str:
    if score >= 0.65:
        return "high_confidence"
    elif score >= 0.40:
        return "acceptable"
    return "poor"
```

### Pattern 3: Off-Target Counting via Subprocess
**What:** Run Bowtie2 (or minimap2) as subprocess against reference FASTA; count alignments with 1-3 mismatches.
**When to use:** When a reference genome FASTA is available (local or downloaded).
**Graceful degradation:** Fall back to a simple regex mismatch scan when neither Bowtie2 nor minimap2 is installed.

```python
# Source: subprocess stdlib docs + bioinformatics convention, HIGH confidence
import shutil
import subprocess

def _detect_aligner() -> str | None:
    """Return 'bowtie2', 'minimap2', or None if neither installed."""
    for tool in ("bowtie2", "minimap2"):
        if shutil.which(tool):
            return tool
    return None

def _run_subprocess(cmd: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """Run subprocess, return (stdout, stderr, returncode). Never raises."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout expired", 1
    except FileNotFoundError:
        return "", f"Tool not found: {cmd[0]}", 127
    except Exception as exc:
        return "", str(exc), 1
```

### Pattern 4: Shell Executor Utility (`_local_tools.py`)
**What:** Reusable infrastructure mirroring `http_client.py` but for subprocess calls.
**Design:** Mirrors `http_client.request()` signature: returns `(result, error)` tuple; never raises.

```python
# Source: mirrors existing http_client.py pattern in codebase, HIGH confidence
# File: src/ct/tools/_local_tools.py

_BIO_TOOL_REGISTRY = {
    "bowtie2": {"check_cmd": ["bowtie2", "--version"], "install_hint": "conda install -c bioconda bowtie2"},
    "minimap2": {"check_cmd": ["minimap2", "--version"], "install_hint": "conda install -c bioconda minimap2"},
    "blastn": {"check_cmd": ["blastn", "-version"], "install_hint": "conda install -c bioconda blast"},
    "orthofinder": {"check_cmd": ["orthofinder", "--help"], "install_hint": "conda install -c bioconda orthofinder"},
}

def run_local_tool(
    cmd: list[str],
    *,
    timeout: int = 120,
    tool_name: str | None = None,
) -> tuple[str | None, str | None]:
    """Run a local bioinformatics tool.

    Returns (stdout, error). Exactly one is non-None.
    Detects 'not installed' via FileNotFoundError and provides install hints.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return None, f"{cmd[0]} failed (exit {result.returncode}): {result.stderr[:300]}"
        return result.stdout, None
    except FileNotFoundError:
        hint = ""
        if tool_name and tool_name in _BIO_TOOL_REGISTRY:
            hint = f" Install with: {_BIO_TOOL_REGISTRY[tool_name]['install_hint']}"
        return None, f"Tool not installed: {cmd[0]}.{hint}"
    except subprocess.TimeoutExpired:
        return None, f"{cmd[0]} timed out after {timeout}s"
    except Exception as exc:
        return None, str(exc)

def check_tool_available(tool_name: str) -> bool:
    """Return True if a named tool is installed and executable."""
    if tool_name not in _BIO_TOOL_REGISTRY:
        return bool(shutil.which(tool_name))
    check_cmd = _BIO_TOOL_REGISTRY[tool_name]["check_cmd"]
    _, err = run_local_tool(check_cmd, timeout=5, tool_name=tool_name)
    return err is None
```

### Pattern 5: NCBI Genome FASTA Download
**What:** Auto-download reference genome FASTA via NCBI eutils when no local file exists.
**Data resolution chain:** user-provided path → `~/.ct/cache/genomes/{taxon_id}.fasta` → NCBI download.

Key NCBI eutils endpoint for whole genome FASTA:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term={organism}[Organism]+AND+reference[refseq]&retmode=json
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=assembly&db=nuccore&id={assembly_id}&retmode=json
```
Note: Full genome FASTA downloads can be 100MB+. For M1, limit to gene region (±5kb context) by fetching just the gene's chromosome coordinates via Ensembl, then using `efetch` with `seq_start`/`seq_stop` parameters. This keeps downloads small and targeted.

```python
# Source: NCBI eutils docs, MEDIUM confidence (URL formats verified via web search)
# Simplified: fetch gene region only, not full chromosome
NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def _fetch_gene_fasta(
    gene_id: str,   # Ensembl gene ID e.g. AT5G10140
    chromosome: str,
    start: int,
    end: int,
    taxon_id: int,
    context_bp: int = 5000,
) -> tuple[str | None, str | None]:
    """Fetch a gene region FASTA from NCBI. Returns (fasta_str, error)."""
    # Use Ensembl DAS/REST to get sequence directly — simpler than NCBI for plant genomes
    from ct.tools.http_client import request
    ensembl_seq_url = f"https://rest.ensembl.org/sequence/region/{species_url}/{chromosome}:{max(1,start-context_bp)}..{end+context_bp}"
    resp, err = request("GET", ensembl_seq_url, params={"content-type": "text/plain"}, timeout=60)
    if err:
        return None, err
    return resp.text, None
```

**Recommendation:** Use Ensembl Plants REST `sequence/region` endpoint for gene region FASTA rather than NCBI eutils. It is simpler, returns the exact genomic context needed, and the Ensembl base URL is already used throughout the codebase. NCBI eutils is a fallback for species not in Ensembl Plants.

### Pattern 6: Paralogy Scoring via Ensembl Compara API
**What:** Mirror of `genomics.ortholog_map` with `type=paralogues` parameter.
**Ensembl endpoint:** `GET /homology/symbol/{species}/{gene}` with `type=paralogues&compara=plants`

The Ensembl Compara REST API accepts exactly the same URL structure as ortholog_map. Only two differences:
1. `type=paralogues` instead of `type=orthologues`
2. No `target_species` filter (paralogs are within the same species)

```python
# Source: Ensembl REST docs verified via web search, HIGH confidence
# Paralogy response structure mirrors ortholog response

params = {
    "content-type": "application/json",
    "type": "paralogues",              # KEY DIFFERENCE from ortholog_map
    "compara": "plants",               # Always required — same as ortholog_map
    "format": "condensed",
}
# Response: same structure as ortholog_map — data[0].homologies list
# homology type will be "within_species_paralog" or "other_paralog"
```

### Pattern 7: Local OrthoFinder Paralogy Data
**What:** Parse OrthoFinder output files for paralog relationships.
**OrthoFinder key output files:**
- `Orthogroups/Orthogroups.tsv` — tab-separated, one orthogroup per row, species as columns
- `Gene_Duplication_Events/Duplications.tsv` — maps duplication events to orthogroups
- `Phylogenetic_Hierarchical_Orthogroups/N0.tsv` — hierarchical orthogroups with duplication/speciation node labels

**Lookup pattern:** Given gene X in species A, find its orthogroup in Orthogroups.tsv, then find all genes in the same species column as X — those are the paralogs.

```python
# Source: OrthoFinder GitHub docs + Biostars community, MEDIUM confidence
# Verified: Orthogroups.tsv format confirmed as tab-delimited with species columns

def _parse_orthofinder_paralogs(
    gene: str,
    species_col: str,     # column header matching species name in OrthoFinder output
    orthogroups_tsv: str, # path to Orthogroups.tsv
) -> list[str]:
    """Return list of paralog gene IDs for gene from OrthoFinder Orthogroups.tsv."""
    import csv
    with open(orthogroups_tsv) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            species_genes = [g.strip() for g in (row.get(species_col) or "").split(",") if g.strip()]
            if gene in species_genes:
                # All other genes in the same species column are paralogs
                return [g for g in species_genes if g != gene]
    return []
```

### Pattern 8: Editability Score Aggregation
**What:** Call three existing tools and aggregate sub-scores. No novel algorithm.
**Sub-scores:**
1. `guide_quality`: from `editing.crispr_guide_design` — count of tier="high_confidence" guides / total guides
2. `structure_complexity`: from `genomics.gff_parse` — number of exons (proxy for complexity)
3. `regulatory_complexity`: stub (return `None` with note "regulatory data not available for M1") — or based on promoter size from GFF

```python
# Source: CONTEXT.md locked decision, HIGH confidence
def editability_score(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    from ct.tools.editing import crispr_guide_design
    from ct.tools.genomics import gff_parse

    guide_result = crispr_guide_design(gene=gene, species=species)
    structure_result = gff_parse(gene=gene, species=species)

    # Sub-score 1: guide quality
    guides = guide_result.get("guides", [])
    n_high = sum(1 for g in guides if g.get("tier") == "high_confidence")
    guide_quality_score = n_high / len(guides) if guides else 0.0

    # Sub-score 2: structure complexity (exon count)
    exon_count = structure_result.get("total_exons", None)

    # Sub-score 3: regulatory complexity (stub for M1)
    regulatory_complexity_score = None  # Deferred to M2

    return {
        "summary": f"Editability sub-scores for {gene} in {species}: ...",
        "gene": gene,
        "species": species,
        "guide_quality_score": guide_quality_score,
        "n_guides_total": len(guides),
        "n_guides_high_confidence": n_high,
        "structure_complexity": {"exon_count": exon_count},
        "regulatory_complexity_score": regulatory_complexity_score,
        "guide_result": guide_result,
        "structure_result": structure_result,
    }
```

### Anti-Patterns to Avoid
- **Importing ML scoring libraries at module level:** Rule Set 2 requires scikit-learn; lazy-import only, guard with try/except ImportError
- **Full genome download for off-target prediction:** Always use gene-region FASTA (±5kb context) not whole chromosome
- **Blocking subprocess calls without timeout:** `subprocess.run(..., timeout=120)` always; never omit timeout
- **Hardcoding Bowtie2 availability:** Always detect with `shutil.which()` and degrade gracefully
- **Storing raw guide sequences in cache without compression:** 20+ guides per call with metadata; cache the full result dict via `_api_cache.set_cached()` as usual
- **Skipping species validation in editing tools:** All tools must call `resolve_species_taxon()` first, consistent with Phases 3-4

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reverse complement | Custom base mapping | Reuse `_reverse_complement()` from `dna.py` (or inline the same logic in editing.py) | Already correct and tested |
| GFF3 gene structure for editability | Parse GFF3 again | Call `genomics.gff_parse()` tool directly | Phase 4 already solved this; editability is a thin wrapper |
| Co-expression overlap with paralogs | Custom correlation logic | Call `genomics.coexpression_network()` for each paralog | Phase 4 already built and tested |
| GO term lookup for paralogs | Custom GO API query | Call `genomics.gene_annotation()` for each paralog | Phase 4 already built and tested |
| HTTP with retries for Ensembl/NCBI | Custom retry logic | `ct.tools.http_client.request_json()` | Already handles retry/backoff/error normalization |
| API result caching | Custom file-based cache | `ct.tools._api_cache.get_cached()` / `set_cached()` | Already handles TTL, hash keys, silent failure |
| Species resolution | Inline dict lookups | `ct.tools._species.resolve_species_taxon()` | Central authority — avoids drift |

**Key insight:** Phase 5 is largely composition, not invention. The hard infrastructure (HTTP, caching, species resolution, GFF3 parsing, co-expression, GO terms) already exists from Phases 3-4. The editing module adds PAM scanning and guide scoring; everything else delegates.

---

## Common Pitfalls

### Pitfall 1: PAM Regex for SpCas9 — Overlapping Matches
**What goes wrong:** Python `re.findall` with non-overlapping matches misses adjacent PAM sites.
**Why it happens:** `re.findall()` advances past the match; consecutive NGG PAMs share nucleotides.
**How to avoid:** Use `re.finditer()` with a lookahead pattern `(?=...)` to detect overlapping hits.
**Warning signs:** Guide count much lower than expected for GC-rich sequences.

### Pitfall 2: Cas12a PAM on Wrong Strand
**What goes wrong:** Cas12a TTTV PAM is 5' of the guide, on the non-template strand (opposite of SpCas9 convention).
**Why it happens:** Implementation copies SpCas9 strand logic without adjusting for 5' vs 3' PAM position.
**How to avoid:** Explicitly test Cas12a guide extraction on a known sequence with verified PAM/guide positions.
**Warning signs:** Guide positions off by 24 nt (PAM length + guide length) or guides on wrong strand.

### Pitfall 3: Ensembl `type=paralogues` Returns Empty for Non-Model Species
**What goes wrong:** Ensembl Compara has sparse paralog data for non-Arabidopsis plant species.
**Why it happens:** Paralogy requires gene tree analysis; tree coverage is uneven across species.
**How to avoid:** Return informative sparse-result message consistent with Phase 4 pattern ("data coverage is limited"); never error on empty response.
**Warning signs:** Test with rice (Oryza sativa) or maize showing empty paralog lists where OrthoFinder would find paralogs.

### Pitfall 4: subprocess `shell=True` Security Issue
**What goes wrong:** Using `shell=True` with user-supplied gene names/paths creates shell injection risk.
**Why it happens:** Developer takes shortcut for complex command construction.
**How to avoid:** Always use `shell=False` (the default) and pass command as a list. Sanitize file paths before passing to subprocess.
**Warning signs:** Any `subprocess.run("bowtie2 " + user_input, shell=True)` pattern.

### Pitfall 5: Full Genome FASTA Download (100MB+)
**What goes wrong:** Auto-download of full reference genome blocks the tool call for minutes and wastes disk.
**Why it happens:** Naive implementation fetches the entire genome FASTA from NCBI.
**How to avoid:** Fetch only the gene region (±5 kb context) using Ensembl `sequence/region` endpoint.
**Warning signs:** `requests.get(full_genome_fasta_url)` without `params={"seq_start":..., "seq_stop":...}`.

### Pitfall 6: `_local_tools.py` Imported at Module Level Causing Import Failures
**What goes wrong:** `import subprocess` at module level works fine; but if `_local_tools.py` conditionally imports Bowtie2-related Python wrappers at module level, ImportError breaks tool loading.
**Why it happens:** Unlike HTTP tools, subprocess is always available — but any Python wrappers around bioinformatics tools may not be installed.
**How to avoid:** Keep `_local_tools.py` to stdlib only (`subprocess`, `shutil`, `pathlib`). No third-party imports at module level.

### Pitfall 7: `type=paralogues` vs `type=paralogs` in Ensembl API
**What goes wrong:** API call returns 400 or empty result because parameter is misspelled.
**Why it happens:** "paralogue" (British spelling) is what Ensembl uses, not "paralog".
**How to avoid:** Use `"type": "paralogues"` (with 'ue') — verified from Ensembl REST docs.
**Warning signs:** `homologies` list empty but no error returned.

### Pitfall 8: `editing` Category Not in PLANT_SCIENCE_CATEGORIES
**What goes wrong:** Agent never sees the new editing tools because they are filtered out at the MCP layer.
**Why it happens:** CONTEXT.md noted that the category allowlist needs "editing" added — easy to forget.
**How to avoid:** `src/ct/tools/__init__.py` — add `"editing"` to `PLANT_SCIENCE_CATEGORIES` frozenset and `"editing"` to `_TOOL_MODULES` tuple. Verify with `ct tool list`.
**Warning signs:** `ct tool list` shows no `editing.*` tools.

---

## Code Examples

Verified patterns from the codebase and research:

### Full editing.py Module Skeleton
```python
# Source: mirrors Phase 4 genomics.py structure, HIGH confidence
"""
CRISPR editing tools: guide design and editability scoring.
"""
import re
from ct.tools import registry

# ---------------------------------------------------------------------------
# Cas system registry
# ---------------------------------------------------------------------------
_CAS_SYSTEMS = {
    "SpCas9": {
        "pam_3prime": r"[CGT]GG",  # NGG
        "guide_len": 20,
        "context_len": 4,  # bases flanking guide for scoring context
    },
    "Cas12a": {
        "pam_5prime": r"TTT[ACG]",  # TTTV
        "guide_len": 20,
        "context_len": 4,
    },
}

def _reverse_complement(seq: str) -> str:
    table = str.maketrans("ACGTN", "TGCAN")
    return seq.translate(table)[::-1]

def _gc_content(seq: str) -> float:
    seq = seq.upper()
    return (seq.count("G") + seq.count("C")) / len(seq) if seq else 0.0

# ... PAM scanning, scoring, off-target ...

@registry.register(
    name="editing.crispr_guide_design",
    description="...",
    category="editing",
    parameters={...},
    requires_data=[],
    usage_guide="...",
)
def crispr_guide_design(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    cas_system: str = "SpCas9",
    genome_fasta: str = None,
    max_guides: int = 20,
    **kwargs,
) -> dict:
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools._api_cache import get_cached, set_cached
    # ... implementation ...
```

### Test Pattern for editing.py
```python
# Source: mirrors test_genomics_plant.py Phase 4 pattern, HIGH confidence
from unittest.mock import patch
import ct.tools.editing as _editing_module
from ct.tools import ensure_loaded, registry

ensure_loaded()

class TestCrisprGuideDesign:
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._api_cache.set_cached")
    def test_pam_scanning_spcas9(self, mock_set, mock_get, mock_binomial, mock_taxon):
        # Provide short synthetic sequence with known PAM sites
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            # inject synthetic sequence via mock or fixture
        )
        assert "guides" in result
        assert isinstance(result["guides"], list)
        for g in result["guides"]:
            assert "guide_sequence" in g
            assert "tier" in g
            assert g["tier"] in ("high_confidence", "acceptable", "poor")
            assert 0.0 <= g["gc_content"] <= 1.0
```

### `__init__.py` Changes Required
```python
# src/ct/tools/__init__.py — two changes:

# 1. Add "editing" to PLANT_SCIENCE_CATEGORIES
PLANT_SCIENCE_CATEGORIES = frozenset({
    "genomics",
    "editing",       # ADD THIS
    # ... existing ...
})

# 2. Add "editing" to _TOOL_MODULES
_TOOL_MODULES = (
    # ... existing ...
    "editing",       # ADD THIS
    # ...
)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Whole-genome FASTA download for off-target prediction | Gene-region FASTA via Ensembl `sequence/region` | 100x smaller download; seconds vs. minutes |
| External ML model (Rule Set 2, DeepHF) for on-target scoring | Heuristic scoring as default; ML optional | No ML dependency in core path; usable on any hardware |
| OrthoFinder as monolithic pipeline | OrthoFinder output file parsing only (pre-run separately) | Agent reads results, doesn't orchestrate OrthoFinder runs |
| Off-target prediction requiring full genome index | Short mismatch scan for fallback when aligner absent | Graceful degradation preserves tool usability |

**Deprecated/outdated:**
- CRISPR-P and CRISPR-PLANT web tools: useful for validation but not embeddable; not appropriate for agent tool calls
- Cas9 OFFinder: Java-based, requires genome index; too heavy for M1 agent calls
- Rule Set 1 (Doench 2014): superseded by Rule Set 2 (Doench 2016) and Rule Set 3; use Rule Set 2 heuristics or newer

---

## Open Questions

1. **Bowtie2 vs. minimap2 for off-target alignment**
   - What we know: Bowtie2 is standard for 20-nt short reads; minimap2 handles both short and long reads but is typically used for long-read alignment
   - What's unclear: Performance difference on plant genomes for 20-nt CRISPR guide alignment specifically
   - Recommendation: Detect Bowtie2 first (`shutil.which("bowtie2")`), then minimap2 as fallback. Document in tool description that Bowtie2 is preferred. For M1, either works for the "count approximate off-targets" use case.

2. **Scope of "off-target count" without aligner**
   - What we know: Regex mismatch scan (allowing 0-3 substitutions) can be done in pure Python against a gene sequence or small genomic region
   - What's unclear: Whether the pure-Python fallback should scan only the gene region (fast, incomplete) or raise a "requires aligner" warning
   - Recommendation: Pure-Python fallback scans a ±5kb gene region only; return `off_target_method: "gene_region_scan"` in result so agent can report caveat. If no FASTA available at all, return `off_target_count: null` with explanation.

3. **OrthoFinder data location convention**
   - What we know: OrthoFinder output goes to a directory specified by the user at run time
   - What's unclear: Where does the user put OrthoFinder results for the agent to find?
   - Recommendation: Check `~/.ct/orthofinder/` as default path; allow override via `orthofinder_dir` parameter. If not found, fall back to Ensembl Compara API silently.

4. **FlashFry requirement**
   - STATE.md has a blocker: "FlashFry version and Java requirements must be confirmed before Phase 5 CRISPR tooling"
   - What we know: FlashFry v1.15 requires Java 8+; it is a Scala/JVM tool run as a jar
   - Recommendation: FlashFry is out of scope for the M1 implementation. The CONTEXT.md locked decisions use pure-Python PAM scanning + optional Bowtie2, which covers the same use case without a JVM dependency. FlashFry could be added as an optional executor in `_local_tools.py` in a future phase.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_editing.py tests/test_paralogy.py tests/test_local_tools.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-06 | PAM sites found for FLC in Arabidopsis using SpCas9 | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_pam_scanning_spcas9 -x` | ❌ Wave 0 |
| TOOL-06 | Cas12a guides returned with TTTV PAM | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_cas12a_guides -x` | ❌ Wave 0 |
| TOOL-06 | Off-target count returned (0 when no aligner) | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_off_target_fallback -x` | ❌ Wave 0 |
| TOOL-06 | Tier labels assigned (high_confidence/acceptable/poor) | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_tier_labels -x` | ❌ Wave 0 |
| TOOL-06 | Guide cap at max_guides=20 enforced | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_max_guides_cap -x` | ❌ Wave 0 |
| TOOL-06 | Unknown species without force returns error | unit | `pytest tests/test_editing.py::TestCrisprGuideDesign::test_unknown_species -x` | ❌ Wave 0 |
| TOOL-06 | editing.crispr_guide_design registered in allowlist | unit | `pytest tests/test_editing.py::test_editing_tools_registered -x` | ❌ Wave 0 |
| TOOL-07 | editability_score returns guide_quality_score, structure_complexity | unit | `pytest tests/test_editing.py::TestEditabilityScore::test_sub_scores_returned -x` | ❌ Wave 0 |
| TOOL-07 | regulatory_complexity_score is None (stub for M1) | unit | `pytest tests/test_editing.py::TestEditabilityScore::test_regulatory_stub -x` | ❌ Wave 0 |
| TOOL-08 | paralogy_score returns paralog_count, co-expression overlap, shared GO | unit | `pytest tests/test_paralogy.py::TestParalogyScore::test_success -x` | ❌ Wave 0 |
| TOOL-08 | Ensembl `type=paralogues&compara=plants` sent in API call | unit | `pytest tests/test_paralogy.py::TestParalogyScore::test_compara_paralogues_param -x` | ❌ Wave 0 |
| TOOL-08 | Empty paralog list returns informative sparse-result summary | unit | `pytest tests/test_paralogy.py::TestParalogyScore::test_empty_response -x` | ❌ Wave 0 |
| TOOL-08 | OrthoFinder local path used when available | unit | `pytest tests/test_paralogy.py::TestParalogyScore::test_local_orthofinder_priority -x` | ❌ Wave 0 |
| TOOL-09 | Agent chains 5+ tools for a gene list naturally | e2e | `pytest tests/test_e2e_evidence.py -x --run-e2e` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_editing.py tests/test_paralogy.py tests/test_local_tools.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_editing.py` — covers TOOL-06 and TOOL-07
- [ ] `tests/test_paralogy.py` — covers TOOL-08
- [ ] `tests/test_local_tools.py` — covers `_local_tools.py` shell executor
- [ ] `tests/test_e2e_evidence.py` — covers TOOL-09 (e2e, requires `--run-e2e` flag)
- [ ] `tests/fixtures/FLC_mini_region.fasta` — synthetic FASTA with known NGG PAM sites for guide design tests

---

## Sources

### Primary (HIGH confidence)
- Ensembl REST API docs (`/homology/symbol` endpoint) — `type=paralogues` parameter verified, `compara=plants` mirrored from Phase 4 `ortholog_map` implementation
- Project codebase (`genomics.py`, `http_client.py`, `_api_cache.py`, `_species.py`, `dna.py`) — established patterns for all new tools to follow
- `pyproject.toml` — confirmed no new core dependencies required
- `CONTEXT.md` (Phase 5) — all locked decisions

### Secondary (MEDIUM confidence)
- OrthoFinder GitHub docs + Biostars community — Orthogroups.tsv format and Gene_Duplication_Events/Duplications.tsv structure
- CRISPR literature (Doench 2016 NatBiotech Rule Set 2, Cas12a TTTV PAM convention) — heuristic scoring rules
- NCBI eutils docs — genome FASTA download endpoint (Ensembl sequence/region preferred instead)
- FlashFry README/BMC Biology 2018 — confirmed FlashFry is Java/Scala, not needed for M1

### Tertiary (LOW confidence)
- WebSearch findings on Bowtie2 vs minimap2 for 20-nt CRISPR guide off-target alignment — not definitively resolved; both options acceptable

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tools use existing libraries
- Architecture: HIGH — direct extension of Phase 4 patterns; Ensembl Compara paralogy API verified
- CRISPR guide scoring algorithms: MEDIUM — heuristics from published literature, not a direct tested implementation
- Off-target subprocess pattern: HIGH — standard Python subprocess pattern, verified against existing shell.py patterns in codebase
- Pitfalls: HIGH — most derived from codebase inspection (e.g., overlapping regex, species validation, category allowlist)

**Research date:** 2026-03-02
**Valid until:** 2026-06-01 (Ensembl REST API is stable; CRISPR scoring literature is settled)
