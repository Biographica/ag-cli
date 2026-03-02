"""
CRISPR editing tools: guide design and editability scoring.

These tools assess gene editability by enumerating CRISPR guide RNAs,
scoring on-target efficiency, counting off-targets, and aggregating
structural factors.
"""

import re

from ct.tools import registry


# ---------------------------------------------------------------------------
# Cas system registry — extensible for adding new nucleases
# ---------------------------------------------------------------------------

_CAS_SYSTEMS: dict[str, dict] = {
    "SpCas9": {
        "pam_pattern_3prime": r"[ACGT]GG",  # NGG on non-template strand
        "guide_len": 20,
        "pam_len": 3,
        "pam_position": "3prime",  # PAM is 3' of guide
        "description": "Streptococcus pyogenes Cas9 (NGG PAM)",
    },
    "Cas12a": {
        "pam_pattern_5prime": r"TTT[ACG]",  # TTTV on non-template strand
        "guide_len": 20,
        "pam_len": 4,
        "pam_position": "5prime",  # PAM is 5' of guide
        "description": "Cas12a/Cpf1 (TTTV PAM)",
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _reverse_complement(seq: str) -> str:
    """Return the reverse complement of a DNA sequence."""
    table = str.maketrans("ACGTN", "TGCAN")
    return seq.translate(table)[::-1]


def _gc_content(seq: str) -> float:
    """Return GC fraction (0.0-1.0) for a DNA sequence."""
    seq = seq.upper()
    if not seq:
        return 0.0
    return (seq.count("G") + seq.count("C")) / len(seq)


def _score_guide_heuristic(guide: str) -> float:
    """Return a 0-1 heuristic on-target score for a CRISPR guide.

    Based on published heuristics from CRISPR literature (Doench 2016
    Rule Set 2 distilled):
    - GC content: 40-70% optimal
    - Avoid polyT runs (>3 T) — premature Pol III termination
    - Avoid homopolymer runs >4 nt
    - Penalize extreme GC (<25% or >85%)
    """
    score = 0.5  # baseline
    gc = _gc_content(guide)

    # GC content reward/penalty
    if 0.40 <= gc <= 0.70:
        score += 0.2
    elif gc < 0.25 or gc > 0.85:
        score -= 0.3

    # PolyT penalty (Pol III terminator signal)
    if "TTTT" in guide.upper():
        score -= 0.2

    # Homopolymer penalty (any base repeated 5+)
    for base in "ACGT":
        if base * 5 in guide.upper():
            score -= 0.1

    return round(max(0.0, min(1.0, score)), 3)


def _tier_label(score: float) -> str:
    """Classify guide into confidence tier based on on-target score."""
    if score >= 0.65:
        return "high_confidence"
    elif score >= 0.40:
        return "acceptable"
    return "poor"


def _scan_pam_sites(sequence: str, cas_system: str = "SpCas9") -> list[dict]:
    """Scan both strands for PAM sites and extract guide sequences.

    Uses re.finditer with lookahead patterns to handle overlapping matches
    (critical for adjacent NGG PAM sites that share nucleotides).

    Args:
        sequence: DNA sequence to scan (will be uppercased).
        cas_system: Key into _CAS_SYSTEMS registry.

    Returns:
        List of dicts with guide_sequence, pam, strand, position, gc_content,
        on_target_score, and tier.
    """
    config = _CAS_SYSTEMS[cas_system]
    guides = []
    seq = sequence.upper()
    rc_seq = _reverse_complement(seq)
    guide_len = config["guide_len"]

    for strand, s in [("+", seq), ("-", rc_seq)]:
        if config["pam_position"] == "3prime":
            # SpCas9: guide is 20 nt immediately upstream of NGG PAM
            # Lookahead to catch overlapping matches
            pattern = re.compile(r"(?=([ACGT]{" + str(guide_len) + r"}[ACGT]GG))")
            for m in pattern.finditer(s):
                full = m.group(1)
                guide_seq = full[:guide_len]
                pam = full[guide_len:]
                pos = m.start()
                gc = _gc_content(guide_seq)
                on_score = _score_guide_heuristic(guide_seq)
                guides.append({
                    "guide_sequence": guide_seq,
                    "pam": pam,
                    "strand": strand,
                    "position": pos,
                    "gc_content": round(gc, 3),
                    "on_target_score": on_score,
                    "tier": _tier_label(on_score),
                })
        else:
            # Cas12a: PAM (TTTV) is 5' of guide, guide is 20 nt downstream
            pattern = re.compile(r"TTT[ACG]([ACGT]{" + str(guide_len) + r"})")
            for m in pattern.finditer(s):
                guide_seq = m.group(1)
                pam = m.group(0)[:config["pam_len"]]
                pos = m.start()
                gc = _gc_content(guide_seq)
                on_score = _score_guide_heuristic(guide_seq)
                guides.append({
                    "guide_sequence": guide_seq,
                    "pam": pam,
                    "strand": strand,
                    "position": pos,
                    "gc_content": round(gc, 3),
                    "on_target_score": on_score,
                    "tier": _tier_label(on_score),
                })

    return guides


def _count_off_targets_regex(guide_seq: str, reference_seq: str, max_mismatches: int = 3) -> int:
    """Count approximate off-target sites using simple mismatch scan.

    This is the fallback when no external aligner (Bowtie2/minimap2) is
    available. Scans a reference sequence for 20-mer windows with at most
    max_mismatches differences from the guide.

    Only counts sites with 1-max_mismatches mismatches (exact match = the
    on-target site, excluded from off-target count).

    Args:
        guide_seq: 20 nt guide sequence.
        reference_seq: Reference DNA to scan.
        max_mismatches: Maximum substitutions allowed (default 3).

    Returns:
        Number of off-target sites found.
    """
    guide = guide_seq.upper()
    ref = reference_seq.upper()
    guide_len = len(guide)
    count = 0
    for i in range(len(ref) - guide_len + 1):
        window = ref[i:i + guide_len]
        if "N" in window:
            continue
        mismatches = sum(1 for a, b in zip(guide, window) if a != b)
        if 1 <= mismatches <= max_mismatches:
            count += 1
    # Also scan reverse complement
    rc_ref = _reverse_complement(ref)
    for i in range(len(rc_ref) - guide_len + 1):
        window = rc_ref[i:i + guide_len]
        if "N" in window:
            continue
        mismatches = sum(1 for a, b in zip(guide, window) if a != b)
        if 1 <= mismatches <= max_mismatches:
            count += 1
    return count


def _fetch_gene_region_fasta(
    gene: str,
    species_url: str,
    context_bp: int = 5000,
) -> tuple[str | None, str | None]:
    """Fetch a gene region FASTA from Ensembl Plants REST API.

    Uses the sequence/region endpoint to get genomic context around a gene.
    First resolves gene coordinates via lookup/symbol, then fetches the region.

    Args:
        gene: Gene symbol or locus code.
        species_url: Ensembl-formatted species (e.g. "arabidopsis_thaliana").
        context_bp: Flanking bases on each side (default 5000).

    Returns:
        Tuple of (fasta_string, error). Exactly one is non-None.
    """
    from ct.tools.http_client import request_json, request

    ensembl_base = "https://rest.ensembl.org"

    # Resolve gene coordinates
    gene_data, err = request_json(
        "GET",
        f"{ensembl_base}/lookup/symbol/{species_url}/{gene}",
        params={"content-type": "application/json"},
        timeout=15,
        retries=2,
    )
    if err or gene_data is None:
        return None, f"Could not resolve gene '{gene}' in Ensembl: {err or 'Not found'}"

    chrom = gene_data.get("seq_region_name", "")
    start = gene_data.get("start", 0)
    end = gene_data.get("end", 0)
    if not chrom or not start or not end:
        return None, f"Incomplete coordinate data for gene '{gene}'"

    # Fetch region with flanking context
    region_start = max(1, start - context_bp)
    region_end = end + context_bp
    seq_url = f"{ensembl_base}/sequence/region/{species_url}/{chrom}:{region_start}..{region_end}"

    resp, seq_err = request(
        "GET",
        seq_url,
        params={"content-type": "text/plain"},
        timeout=60,
        retries=1,
    )
    if seq_err:
        return None, f"Ensembl sequence download failed: {seq_err}"

    fasta_text = resp.text if hasattr(resp, "text") else str(resp)
    if not fasta_text or len(fasta_text) < 10:
        return None, "Empty sequence returned from Ensembl"

    return fasta_text, None


# ---------------------------------------------------------------------------
# editing.crispr_guide_design — CRISPR guide enumeration and scoring
# ---------------------------------------------------------------------------

@registry.register(
    name="editing.crispr_guide_design",
    description=(
        "Enumerate PAM sites, score guide RNAs, and predict off-targets "
        "for a gene in a supported species. Supports SpCas9 (NGG) and "
        "Cas12a/Cpf1 (TTTV) nuclease systems."
    ),
    category="editing",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140')",
        "species": "Species name (default: Arabidopsis thaliana)",
        "cas_system": "Nuclease system: 'SpCas9' or 'Cas12a' (default: SpCas9)",
        "genome_fasta": "Path to local genome FASTA (optional; auto-downloads gene region from Ensembl if absent)",
        "max_guides": "Maximum guides to return, sorted by score (default: 20)",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Enumerates CRISPR guide RNAs for a gene, scoring each for on-target "
        "efficiency and counting predicted off-targets. Returns guides ranked "
        "by composite score with tier classifications "
        "(high_confidence / acceptable / poor)."
    ),
)
def crispr_guide_design(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    cas_system: str = "SpCas9",
    genome_fasta: str = None,
    max_guides: int = 20,
    force: bool = False,
    **kwargs,
) -> dict:
    """Design CRISPR guide RNAs for a gene with PAM scanning and scoring."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools._api_cache import get_cached, set_cached

    gene = str(gene or "").strip()
    if not gene:
        return {
            "error": "Missing required parameter: gene",
            "summary": "crispr_guide_design requires a non-empty gene symbol or locus code.",
        }

    # Validate Cas system
    if cas_system not in _CAS_SYSTEMS:
        available = ", ".join(_CAS_SYSTEMS.keys())
        return {
            "error": f"Unknown Cas system: {cas_system!r}. Available: {available}",
            "summary": f"Cas system not recognised: {cas_system!r}.",
        }

    # Species validation
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0 and not force:
        return {
            "error": f"Unknown species: {species!r}. Use force=True to override.",
            "summary": f"Species not recognised: {species!r}.",
        }
    binomial = resolve_species_binomial(species) or species

    # Cache check
    cache_key = f"crispr_guide:{taxon_id}:{gene}:{cas_system}:{max_guides}"
    cached = get_cached("editing_guides", cache_key)
    if cached is not None:
        return cached

    # Acquire genome sequence via data resolution chain:
    # 1. User-provided FASTA file
    # 2. Ensembl REST sequence/region download
    sequence = None
    fasta_source = None
    off_target_ref = None

    if genome_fasta:
        # User-provided file
        from pathlib import Path
        fasta_path = Path(genome_fasta)
        if not fasta_path.exists():
            return {
                "error": f"Genome FASTA not found: {genome_fasta}",
                "summary": f"File not found: {genome_fasta}",
            }
        try:
            content = fasta_path.read_text()
            # Parse FASTA: skip header lines, join sequence lines
            seq_lines = [
                line.strip() for line in content.splitlines()
                if line.strip() and not line.startswith(">")
            ]
            sequence = "".join(seq_lines)
            off_target_ref = sequence
            fasta_source = f"local file: {genome_fasta}"
        except Exception as exc:
            return {
                "error": f"Failed to read FASTA: {exc}",
                "summary": f"Error reading genome FASTA: {exc}",
            }
    else:
        # Auto-download gene region from Ensembl Plants
        species_url = binomial.lower().replace(" ", "_")
        fasta_text, dl_err = _fetch_gene_region_fasta(gene, species_url)
        if dl_err:
            # Proceed without off-target counting — PAM scanning can still work
            # if the gene sequence is available from gff_parse or other sources
            return {
                "summary": (
                    f"Could not retrieve genome sequence for {gene} in {binomial}: {dl_err}. "
                    "Provide a local genome FASTA via the genome_fasta parameter."
                ),
                "gene": gene,
                "species": binomial,
                "cas_system": cas_system,
                "guides": [],
                "error": dl_err,
            }
        # Parse plain text sequence (Ensembl text/plain returns raw sequence)
        sequence = "".join(
            line.strip() for line in fasta_text.splitlines()
            if line.strip() and not line.startswith(">")
        )
        off_target_ref = sequence
        fasta_source = "Ensembl Plants REST sequence/region"

    if not sequence or len(sequence) < 23:
        return {
            "summary": f"Sequence too short for guide design ({len(sequence or '')} bp).",
            "gene": gene,
            "species": binomial,
            "cas_system": cas_system,
            "guides": [],
            "error": "Sequence too short",
        }

    # Step 1: Scan PAM sites
    guides = _scan_pam_sites(sequence, cas_system)

    # Step 2: Off-target counting
    off_target_method = None
    if off_target_ref and guides:
        # Try external aligner first
        from ct.tools._local_tools import check_tool_available
        aligner = None
        for tool in ("bowtie2", "minimap2"):
            if check_tool_available(tool):
                aligner = tool
                break

        if aligner:
            # External aligner — for M1, note that full alignment pipeline
            # requires genome indexing which is complex. Use regex fallback
            # for now and mark the method. Full aligner integration is a
            # future enhancement.
            off_target_method = "gene_region_scan"
            for g in guides:
                g["off_target_count"] = _count_off_targets_regex(
                    g["guide_sequence"], off_target_ref
                )
        else:
            # Pure Python regex fallback on gene region
            off_target_method = "gene_region_scan"
            for g in guides:
                g["off_target_count"] = _count_off_targets_regex(
                    g["guide_sequence"], off_target_ref
                )
    else:
        off_target_method = None
        for g in guides:
            g["off_target_count"] = None

    # Step 3: Sort by on_target_score descending and cap
    guides.sort(key=lambda g: -g["on_target_score"])
    max_guides = min(int(max_guides), 50)  # hard cap at 50
    guides = guides[:max_guides]

    # Step 4: Build result
    n_high = sum(1 for g in guides if g["tier"] == "high_confidence")
    n_acceptable = sum(1 for g in guides if g["tier"] == "acceptable")
    n_poor = sum(1 for g in guides if g["tier"] == "poor")

    cas_desc = _CAS_SYSTEMS[cas_system]["description"]

    result = {
        "summary": (
            f"Designed {len(guides)} guide(s) for {gene} in {binomial} "
            f"using {cas_desc}: {n_high} high-confidence, {n_acceptable} acceptable, "
            f"{n_poor} poor."
        ),
        "gene": gene,
        "species": binomial,
        "taxon_id": taxon_id,
        "cas_system": cas_system,
        "cas_description": cas_desc,
        "sequence_length": len(sequence),
        "fasta_source": fasta_source,
        "guide_count": len(guides),
        "tier_counts": {
            "high_confidence": n_high,
            "acceptable": n_acceptable,
            "poor": n_poor,
        },
        "off_target_method": off_target_method,
        "max_guides": max_guides,
        "guides": guides,
    }

    set_cached("editing_guides", cache_key, result)
    return result


# ---------------------------------------------------------------------------
# editing.editability_score — thin aggregator of editing-relevant sub-scores
# ---------------------------------------------------------------------------

@registry.register(
    name="editing.editability_score",
    description=(
        "Estimate editability of a gene by aggregating sub-scores: guide RNA "
        "quality, gene structure complexity, and regulatory complexity. "
        "Returns per-factor scores without an opinionated composite."
    ),
    category="editing",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140')",
        "species": "Species name (default: Arabidopsis thaliana)",
        "cas_system": "Nuclease system for guide design (default: SpCas9)",
        "gff_path": "Path to local GFF3 file (optional; passed to gff_parse)",
        "genome_fasta": "Path to local genome FASTA (optional; passed to guide design)",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Aggregates guide RNA quality, gene structure complexity, and regulatory "
        "complexity into per-factor sub-scores for editability assessment. "
        "Does not produce a composite score — downstream analysis decides weighting."
    ),
)
def editability_score(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    cas_system: str = "SpCas9",
    gff_path: str = None,
    genome_fasta: str = None,
    force: bool = False,
    **kwargs,
) -> dict:
    """Aggregate editability sub-scores for a gene."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial

    gene = str(gene or "").strip()
    if not gene:
        return {
            "error": "Missing required parameter: gene",
            "summary": "editability_score requires a non-empty gene symbol or locus code.",
        }

    # Species validation
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0 and not force:
        return {
            "error": f"Unknown species: {species!r}. Use force=True to override.",
            "summary": f"Species not recognised: {species!r}.",
        }
    binomial = resolve_species_binomial(species) or species

    # Sub-score 1: Guide quality — call crispr_guide_design
    guide_result = crispr_guide_design(
        gene=gene,
        species=species,
        cas_system=cas_system,
        genome_fasta=genome_fasta,
        force=force,
    )

    guides = guide_result.get("guides", [])
    n_high = sum(1 for g in guides if g.get("tier") == "high_confidence")
    guide_quality_score = round(n_high / len(guides), 3) if guides else 0.0

    # Sub-score 2: Structure complexity — call gff_parse
    from ct.tools.genomics import gff_parse
    structure_result = gff_parse(
        gene=gene,
        species=species,
        gff_path=gff_path,
        force=force,
    )

    exon_count = structure_result.get("total_exons")
    intron_count = structure_result.get("total_introns")
    gene_span_bp = structure_result.get("gene_span_bp")

    # Sub-score 3: Regulatory complexity — stub for M1
    # Future: derive from promoter size, regulatory annotations, etc.
    regulatory_complexity_score = None

    result = {
        "summary": (
            f"Editability sub-scores for {gene} in {binomial}: "
            f"guide quality {guide_quality_score:.2f} "
            f"({len(guides)} guides, {n_high} high-confidence), "
            f"structure: {exon_count} exon(s), {intron_count} intron(s)"
            + (f", {gene_span_bp:,} bp span" if gene_span_bp else "")
            + ". Regulatory complexity: not available (M1)."
        ),
        "gene": gene,
        "species": binomial,
        "taxon_id": taxon_id,
        "guide_quality_score": guide_quality_score,
        "n_guides_total": len(guides),
        "n_guides_high_confidence": n_high,
        "structure_complexity": {
            "exon_count": exon_count,
            "intron_count": intron_count,
            "gene_span_bp": gene_span_bp,
        },
        "regulatory_complexity_score": regulatory_complexity_score,
        "guide_result": guide_result,
        "structure_result": structure_result,
    }

    return result
