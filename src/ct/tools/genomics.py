"""
Genomics tools: GWAS lookup, eQTL analysis, variant annotation, Mendelian randomization.

These are REST/GraphQL API wrappers -- no local data required.
"""

import math

from ct.tools import registry
from ct.tools.http_client import request, request_json


@registry.register(
    name="genomics.gwas_lookup",
    description="Query the GWAS Catalog for genetic associations for a gene, optionally filtered by trait",
    category="genomics",
    parameters={
        "gene": "Gene symbol (e.g. 'BRCA1', 'TP53')",
        "trait": "Trait or disease name to filter (optional)",
        "p_threshold": "P-value threshold for significance (default 5e-8)",
    },
    requires_data=[],
    usage_guide="You want to find genome-wide significant genetic associations for a specific gene. Optionally add a trait filter to focus disease context.",
)
def gwas_lookup(gene: str = None, trait: str = None, p_threshold: float = 5e-8, **kwargs) -> dict:
    """Query the NHGRI-EBI GWAS Catalog REST API for genetic associations."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx required (pip install httpx)", "summary": "httpx required (pip install httpx)"}
    gene = str(gene or "").strip()
    trait = str(trait or "").strip() or None
    if not gene:
        detail = f" (trait='{trait}')" if trait else ""
        return {
            "error": f"Missing required parameter: gene{detail}",
            "summary": "GWAS lookup requires a non-empty gene symbol (e.g., SNCA, APOE).",
            "gene": gene,
            "trait_filter": trait,
            "suggestion": (
                "First identify candidate genes (e.g., with data_api.opentargets_search), "
                "then run genomics.gwas_lookup with one gene at a time."
            ),
        }

    base = "https://www.ebi.ac.uk/gwas/rest/api"

    # Step 1: Find SNPs associated with the gene
    snp_url = f"{base}/singleNucleotidePolymorphisms/search/findByGene"
    params = {"geneName": gene, "size": 100}

    data, error = request_json(
        "GET",
        snp_url,
        params=params,
        timeout=30,
        retries=2,
    )
    if error:
        return {"error": f"GWAS Catalog query failed: {error}", "summary": f"GWAS Catalog query failed: {error}"}
    embedded = data.get("_embedded", {})
    snps = embedded.get("singleNucleotidePolymorphisms", [])

    if not snps:
        return {
            "summary": f"No GWAS associations found for gene {gene}",
            "gene": gene,
            "associations": [],
            "n_associations": 0,
        }

    # Step 2: For each SNP, fetch associations using the summary projection
    # which embeds EFO traits inline (avoids extra per-trait API calls)
    associations = []
    seen = set()

    for snp_entry in snps[:30]:  # Cap at 30 SNPs to limit API calls
        rsid = snp_entry.get("rsId", "")
        if not rsid:
            continue

        # Use the associationBySnp projection which embeds traits inline
        assoc_url = f"{base}/singleNucleotidePolymorphisms/{rsid}/associations"
        assoc_data, assoc_error = request_json(
            "GET",
            assoc_url,
            params={"projection": "associationBySnp"},
            timeout=10,
            retries=2,
        )
        if assoc_error:
            continue

        assoc_list = assoc_data.get("_embedded", {}).get("associations", [])

        for assoc in assoc_list:
            pval_mantissa = assoc.get("pvalueMantissa")
            pval_exponent = assoc.get("pvalueExponent")
            if pval_mantissa is not None and pval_exponent is not None:
                try:
                    pval = float(pval_mantissa) * (10 ** int(pval_exponent))
                except (ValueError, TypeError):
                    pval = None
            else:
                pval = None

            # Filter by p-value threshold
            if pval is not None and pval > p_threshold:
                continue

            # Extract risk allele info from loci
            loci = assoc.get("loci", [])
            risk_allele_name = ""
            if loci:
                risk_alleles = loci[0].get("strongestRiskAlleles", [])
                if risk_alleles:
                    risk_allele_name = risk_alleles[0].get("riskAlleleName", "")

            # Extract traits from embedded efoTraits (no extra API call needed)
            efo_traits = assoc.get("efoTraits", [])
            trait_names = [t.get("trait", "") for t in efo_traits if t.get("trait")]
            trait_name = "; ".join(trait_names)

            # Filter by trait if specified
            if trait and trait_name:
                if trait.lower() not in trait_name.lower():
                    continue

            or_value = assoc.get("orPerCopyNum")
            beta = assoc.get("betaNum")
            beta_unit = assoc.get("betaUnit", "")
            beta_direction = assoc.get("betaDirection", "")

            assoc_id = f"{rsid}_{pval}_{trait_name}"
            if assoc_id in seen:
                continue
            seen.add(assoc_id)

            associations.append({
                "rsid": rsid,
                "risk_allele": risk_allele_name,
                "p_value": pval,
                "p_value_str": f"{pval_mantissa}e{pval_exponent}" if pval_mantissa else None,
                "trait": trait_name,
                "or_per_copy": or_value,
                "beta": beta,
                "beta_unit": beta_unit,
                "beta_direction": beta_direction,
                "mapped_gene": gene,
            })

        # Stop early if we have enough
        if len(associations) >= 50:
            break

    # Sort by p-value (most significant first)
    associations.sort(key=lambda x: x["p_value"] if x["p_value"] is not None else 1.0)

    trait_str = f" for trait '{trait}'" if trait else ""
    return {
        "summary": (
            f"GWAS associations for {gene}{trait_str}: "
            f"{len(associations)} genome-wide significant hits (p < {p_threshold})"
        ),
        "gene": gene,
        "trait_filter": trait,
        "p_threshold": p_threshold,
        "n_associations": len(associations),
        "associations": associations[:30],  # Return top 30
    }


@registry.register(
    name="genomics.eqtl_lookup",
    description="Query GTEx for expression quantitative trait loci (eQTLs) for a gene across tissues",
    category="genomics",
    parameters={
        "gene": "Gene symbol (e.g. 'BRCA1', 'TP53')",
        "tissue": "GTEx tissue name to filter (optional, e.g. 'Liver', 'Brain_Cortex')",
    },
    requires_data=[],
    usage_guide="You want to find genetic variants that regulate gene expression in specific tissues. Use to understand tissue-specific regulation, identify regulatory variants, and connect GWAS signals to gene function.",
)
def eqtl_lookup(gene: str, tissue: str = None, **kwargs) -> dict:
    """Query the GTEx API for significant eQTLs for a gene."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx required (pip install httpx)", "summary": "httpx required (pip install httpx)"}
    gtex_base = "https://gtexportal.org/api/v2"

    # Step 1: Resolve gene symbol to GENCODE ID
    gene_url = f"{gtex_base}/reference/gene"
    gene_params = {"geneId": gene}

    gene_data, error = request_json(
        "GET",
        gene_url,
        params=gene_params,
        timeout=10,
        retries=2,
    )
    if error:
        return {"error": f"GTEx gene lookup failed: {error}", "summary": f"GTEx gene lookup failed: {error}"}
    genes_list = gene_data.get("data", [])
    if not genes_list:
        return {
            "error": f"Gene '{gene}' not found in GTEx GENCODE v26 reference",
            "suggestion": "Try using the official HGNC gene symbol",
        }

    # Use the first matching gene entry
    gene_info = genes_list[0]
    gencode_id = gene_info.get("gencodeId", "")
    gene_symbol = gene_info.get("geneSymbol", gene)
    description = gene_info.get("description", "")

    if not gencode_id:
        return {"error": f"Could not resolve GENCODE ID for {gene}", "summary": f"Could not resolve GENCODE ID for {gene}"}
    # Step 2: Query significant single-tissue eQTLs
    eqtl_url = f"{gtex_base}/association/singleTissueEqtl"
    eqtl_params = {
        "gencodeId": gencode_id,
        "datasetId": "gtex_v8",
    }
    if tissue:
        eqtl_params["tissueSiteDetailId"] = tissue

    eqtl_data, error = request_json(
        "GET",
        eqtl_url,
        params=eqtl_params,
        timeout=10,
        retries=2,
    )
    if error:
        return {"error": f"GTEx eQTL query failed: {error}", "summary": f"GTEx eQTL query failed: {error}"}
    eqtls_raw = eqtl_data.get("data", [])

    if not eqtls_raw:
        tissue_str = f" in {tissue}" if tissue else ""
        return {
            "summary": f"No significant eQTLs found for {gene_symbol}{tissue_str} in GTEx v8",
            "gene": gene_symbol,
            "gencode_id": gencode_id,
            "eqtls": [],
            "n_eqtls": 0,
        }

    # Parse eQTL results
    eqtls = []
    tissues_found = set()

    for eqtl in eqtls_raw:
        tissue_id = eqtl.get("tissueSiteDetailId", "")
        tissues_found.add(tissue_id)

        eqtls.append({
            "variant_id": eqtl.get("variantId", ""),
            "snp_id": eqtl.get("snpId", ""),
            "tissue": tissue_id,
            "p_value": eqtl.get("pValue"),
            "nes": eqtl.get("nes"),  # Normalized effect size
            "chromosome": eqtl.get("chromosome", ""),
            "pos": eqtl.get("pos"),
            "gene_symbol": eqtl.get("geneSymbol", gene_symbol),
        })

    # Sort by absolute NES (largest effect first)
    eqtls.sort(key=lambda x: abs(x["nes"]) if x["nes"] is not None else 0, reverse=True)

    tissue_str = f" in {tissue}" if tissue else f" across {len(tissues_found)} tissues"
    return {
        "summary": (
            f"GTEx eQTLs for {gene_symbol} ({gencode_id}){tissue_str}: "
            f"{len(eqtls)} significant eQTLs found"
        ),
        "gene": gene_symbol,
        "gencode_id": gencode_id,
        "gene_description": description,
        "n_eqtls": len(eqtls),
        "n_tissues": len(tissues_found),
        "tissues": sorted(tissues_found),
        "eqtls": eqtls[:50],  # Return top 50 by effect size
    }


@registry.register(
    name="genomics.variant_annotate",
    description="Annotate a genetic variant using Ensembl VEP (Variant Effect Predictor)",
    category="genomics",
    parameters={
        "variant": "Variant identifier: rsID (e.g. 'rs1234') or HGVS notation (e.g. '17:g.41245466G>A')",
    },
    requires_data=[],
    usage_guide="You want to understand the functional consequence of a specific genetic variant. Use to get consequence type (missense, synonymous, etc.), impact prediction, amino acid changes, allele frequencies, and clinical significance.",
)
def variant_annotate(variant: str, **kwargs) -> dict:
    """Annotate a variant using the Ensembl VEP REST API."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx required (pip install httpx)", "summary": "httpx required (pip install httpx)"}
    ensembl_base = "https://rest.ensembl.org"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Determine if this is an rsID or HGVS notation
    variant_clean = variant.strip()
    if variant_clean.lower().startswith("rs"):
        url = f"{ensembl_base}/vep/human/id/{variant_clean}"
    else:
        url = f"{ensembl_base}/vep/human/hgvs/{variant_clean}"

    resp, error = request(
        "GET",
        url,
        headers=headers,
        timeout=30,
        retries=2,
        raise_for_status=False,
    )
    if error:
        return {"error": f"Ensembl VEP query failed: {error}", "summary": f"Ensembl VEP query failed: {error}"}
    if resp.status_code == 400:
        return {"error": f"Invalid variant format: '{variant}'. Use rsID (e.g. rs1234) or HGVS (e.g. 17:g.41245466G>A)", "summary": f"Invalid variant format: '{variant}'. Use rsID (e.g. rs1234) or HGVS (e.g. 17:g.41245466G>A)"}
    if resp.status_code >= 400:
        return {"error": f"Ensembl VEP query failed: HTTP {resp.status_code}", "summary": f"Ensembl VEP query failed: HTTP {resp.status_code}"}
    try:
        data = resp.json()
    except Exception:
        return {"error": f"Ensembl VEP query failed: invalid JSON response", "summary": f"Ensembl VEP query failed: invalid JSON response"}
    if not data or not isinstance(data, list):
        return {"error": f"No VEP results for variant {variant}", "summary": f"No VEP results for variant {variant}"}
    vep_result = data[0]

    # Extract variant identifiers
    variant_id = vep_result.get("id", variant)
    input_str = vep_result.get("input", variant)
    most_severe = vep_result.get("most_severe_consequence", "")
    allele_string = vep_result.get("allele_string", "")
    strand = vep_result.get("strand")
    assembly = vep_result.get("assembly_name", "")
    seq_region = vep_result.get("seq_region_name", "")
    start = vep_result.get("start")
    end = vep_result.get("end")

    # Extract colocated variants (for allele frequencies, clinical significance)
    colocated = vep_result.get("colocated_variants", [])
    allele_frequencies = {}
    clinical_significance = []
    existing_ids = []

    for cv in colocated:
        cv_id = cv.get("id", "")
        if cv_id:
            existing_ids.append(cv_id)

        # Allele frequencies from different populations
        freqs = cv.get("frequencies", {})
        for allele, pop_freqs in freqs.items():
            for pop, freq in pop_freqs.items():
                key = f"{allele}_{pop}"
                allele_frequencies[key] = freq

        # Minor allele frequency
        maf = cv.get("minor_allele_freq")
        minor_allele = cv.get("minor_allele", "")
        if maf is not None:
            allele_frequencies["minor_allele"] = minor_allele
            allele_frequencies["minor_allele_freq"] = maf

        # Clinical significance
        clin_sig = cv.get("clin_sig", [])
        if clin_sig:
            clinical_significance.extend(clin_sig)

    # Extract transcript consequences
    transcript_consequences = []
    for tc in vep_result.get("transcript_consequences", []):
        consequence_terms = tc.get("consequence_terms", [])
        transcript_consequences.append({
            "gene_id": tc.get("gene_id", ""),
            "gene_symbol": tc.get("gene_symbol", ""),
            "transcript_id": tc.get("transcript_id", ""),
            "biotype": tc.get("biotype", ""),
            "consequence_terms": consequence_terms,
            "impact": tc.get("impact", ""),
            "amino_acids": tc.get("amino_acids", ""),
            "codons": tc.get("codons", ""),
            "protein_position": tc.get("protein_position", ""),
            "sift_prediction": tc.get("sift_prediction", ""),
            "sift_score": tc.get("sift_score"),
            "polyphen_prediction": tc.get("polyphen_prediction", ""),
            "polyphen_score": tc.get("polyphen_score"),
            "canonical": tc.get("canonical", 0) == 1,
        })

    # Sort: canonical transcripts first, then by impact severity
    impact_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "MODIFIER": 3}
    transcript_consequences.sort(
        key=lambda x: (
            0 if x["canonical"] else 1,
            impact_order.get(x["impact"], 4),
        )
    )

    # Find the most impactful consequence for the summary
    top_consequence = transcript_consequences[0] if transcript_consequences else {}
    gene_symbol = top_consequence.get("gene_symbol", "")
    impact = top_consequence.get("impact", "")
    aa_change = top_consequence.get("amino_acids", "")
    protein_pos = top_consequence.get("protein_position", "")

    aa_str = ""
    if aa_change and protein_pos:
        aa_str = f", p.{aa_change.replace('/', str(protein_pos))}"

    clin_str = ""
    if clinical_significance:
        unique_clin = list(set(clinical_significance))
        clin_str = f" Clinical: {', '.join(unique_clin)}."

    maf_str = ""
    maf_val = allele_frequencies.get("minor_allele_freq")
    if maf_val is not None:
        maf_str = f" MAF={maf_val:.4f} ({allele_frequencies.get('minor_allele', '')})."

    return {
        "summary": (
            f"VEP annotation for {variant_id}: {most_severe} ({impact}) "
            f"in {gene_symbol}{aa_str}.{clin_str}{maf_str}"
        ),
        "variant_id": variant_id,
        "input": input_str,
        "location": f"{seq_region}:{start}-{end}" if seq_region and start else "",
        "assembly": assembly,
        "allele_string": allele_string,
        "most_severe_consequence": most_severe,
        "existing_ids": existing_ids,
        "allele_frequencies": allele_frequencies,
        "clinical_significance": list(set(clinical_significance)),
        "transcript_consequences": transcript_consequences[:10],  # Top 10
        "n_transcript_consequences": len(transcript_consequences),
    }


@registry.register(
    name="genomics.mendelian_randomization_lookup",
    description="Look up Mendelian randomization and genetic evidence for a gene-disease pair via Open Targets",
    category="genomics",
    parameters={
        "gene": "Gene symbol (e.g. 'PCSK9', 'IL6R')",
        "disease": "Disease name or EFO ID (e.g. 'coronary artery disease' or 'EFO_0001645')",
    },
    requires_data=[],
    usage_guide="You want causal genetic evidence linking a gene to a disease. Use to evaluate target-disease relationships using Mendelian randomization, GWAS colocalisation, and genetic association evidence from Open Targets.",
)
def mendelian_randomization_lookup(gene: str, disease: str, **kwargs) -> dict:
    """Look up MR and genetic evidence from Open Targets Platform GraphQL API."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx required (pip install httpx)", "summary": "httpx required (pip install httpx)"}
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Step 1: Resolve gene symbol to Ensembl ID via Open Targets search
    search_query = """
    query searchTarget($queryString: String!) {
        search(queryString: $queryString, entityNames: ["target"], page: {size: 5, index: 0}) {
            hits {
                id
                entity
                name
                description
            }
        }
    }
    """

    search_data, error = request_json(
        "POST",
        ot_url,
        json={"query": search_query, "variables": {"queryString": gene}},
        headers=headers,
        timeout=10,
        retries=2,
    )
    if error:
        return {"error": f"Open Targets search failed: {error}", "summary": f"Open Targets search failed: {error}"}
    hits = search_data.get("data", {}).get("search", {}).get("hits", [])
    target_hits = [h for h in hits if h.get("entity") == "target"]

    if not target_hits:
        return {"error": f"Gene '{gene}' not found in Open Targets", "summary": f"Gene '{gene}' not found in Open Targets"}
    # Match by gene symbol (case-insensitive)
    ensembl_id = None
    target_name = ""
    for hit in target_hits:
        if hit.get("name", "").upper() == gene.upper():
            ensembl_id = hit["id"]
            target_name = hit.get("name", "")
            break
    if not ensembl_id:
        ensembl_id = target_hits[0]["id"]
        target_name = target_hits[0].get("name", "")

    # Step 2: Resolve disease to EFO ID (if not already an EFO ID)
    if disease.upper().startswith("EFO_") or disease.upper().startswith("MONDO_") or disease.upper().startswith("HP_"):
        efo_id = disease
        disease_name = disease
    else:
        disease_search_query = """
        query searchDisease($queryString: String!) {
            search(queryString: $queryString, entityNames: ["disease"], page: {size: 5, index: 0}) {
                hits {
                    id
                    entity
                    name
                    description
                }
            }
        }
        """

        disease_data, error = request_json(
            "POST",
            ot_url,
            json={"query": disease_search_query, "variables": {"queryString": disease}},
            headers=headers,
            timeout=10,
            retries=2,
        )
        if error:
            return {"error": f"Open Targets disease search failed: {error}", "summary": f"Open Targets disease search failed: {error}"}
        disease_hits = disease_data.get("data", {}).get("search", {}).get("hits", [])
        disease_hits = [h for h in disease_hits if h.get("entity") == "disease"]

        if not disease_hits:
            return {"error": f"Disease '{disease}' not found in Open Targets", "summary": f"Disease '{disease}' not found in Open Targets"}
        efo_id = disease_hits[0]["id"]
        disease_name = disease_hits[0].get("name", disease)

    # Step 3: Query genetic evidence (evidences is on Target, not top-level)
    # Genetic datasources: gwas_credible_sets (L2G scores), eva, gene_burden,
    # gene2phenotype, genomics_england, uniprot_literature
    evidence_query = """
    query targetDiseaseEvidence($ensemblId: String!, $efoId: String!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            approvedName
            associatedDiseases(BFilter: $efoId, page: {size: 1, index: 0}) {
                rows {
                    score
                    disease { id name }
                    datasourceScores {
                        id
                        score
                    }
                }
            }
            evidences(
                efoIds: [$efoId]
                datasourceIds: [
                    "gwas_credible_sets", "gene_burden", "eva",
                    "gene2phenotype", "genomics_england", "uniprot_literature"
                ]
                size: 50
            ) {
                count
                rows {
                    datasourceId
                    datatypeId
                    score
                    resourceScore
                    studyId
                    beta
                    oddsRatio
                    confidence
                    studySampleSize
                    publicationYear
                    variantRsId
                    credibleSet {
                        studyLocusId
                        study { id projectId studyType }
                        variant { id rsIds }
                        pValueMantissa
                        pValueExponent
                        beta
                        finemappingMethod
                    }
                }
            }
        }
        disease(efoId: $efoId) {
            id
            name
            description
        }
    }
    """

    result_data, error = request_json(
        "POST",
        ot_url,
        json={
            "query": evidence_query,
            "variables": {"ensemblId": ensembl_id, "efoId": efo_id},
        },
        headers=headers,
        timeout=15,
        retries=2,
    )
    if error:
        return {"error": f"Open Targets evidence query failed: {error}", "summary": f"Open Targets evidence query failed: {error}"}
    if result_data.get("errors"):
        error_msgs = [e.get("message", "") for e in result_data["errors"]]
        return {"error": f"Open Targets GraphQL errors: {'; '.join(error_msgs)}", "summary": f"Open Targets GraphQL errors: {'; '.join(error_msgs)}"}
    data = result_data.get("data", {})

    # Parse target and disease info
    target_info = data.get("target") or {}
    disease_info = data.get("disease") or {}
    approved_symbol = target_info.get("approvedSymbol", gene)
    approved_name = target_info.get("approvedName", "")
    resolved_disease = disease_info.get("name", disease_name if disease_name else disease)

    # Parse overall association score
    assoc_rows = target_info.get("associatedDiseases", {}).get("rows", [])
    overall_score = assoc_rows[0].get("score") if assoc_rows else None
    datasource_scores = {}
    if assoc_rows:
        for ds in assoc_rows[0].get("datasourceScores", []):
            datasource_scores[ds["id"]] = ds["score"]

    # Parse evidence rows
    evidences_obj = target_info.get("evidences") or {}
    evidence_count = evidences_obj.get("count", 0)
    evidence_rows = evidences_obj.get("rows", [])

    # Categorize evidence by datasource
    gwas_evidence = []
    other_genetic_evidence = []

    for row in evidence_rows:
        datasource = row.get("datasourceId", "")

        # Extract variant info from credibleSet if available
        credible_set = row.get("credibleSet") or {}
        variant_info = credible_set.get("variant") or {}
        study_info = credible_set.get("study") or {}
        rs_ids = variant_info.get("rsIds", [])
        variant_rsid = rs_ids[0] if rs_ids else (row.get("variantRsId") or "")

        # Compute p-value from mantissa/exponent
        p_mantissa = credible_set.get("pValueMantissa")
        p_exponent = credible_set.get("pValueExponent")
        p_value = None
        if p_mantissa is not None and p_exponent is not None:
            try:
                p_value = float(p_mantissa) * (10 ** int(p_exponent))
            except (ValueError, TypeError):
                pass

        evidence_item = {
            "datasource": datasource,
            "datatype": row.get("datatypeId", ""),
            "score": row.get("score"),
            "resource_score": row.get("resourceScore"),
            "variant_id": variant_info.get("id", ""),
            "variant_rsid": variant_rsid,
            "study_id": study_info.get("id") or row.get("studyId", ""),
            "study_type": study_info.get("studyType", ""),
            "p_value": p_value,
            "beta": credible_set.get("beta") or row.get("beta"),
            "odds_ratio": row.get("oddsRatio"),
            "finemapping_method": credible_set.get("finemappingMethod", ""),
            "publication_year": row.get("publicationYear"),
        }

        if datasource == "gwas_credible_sets":
            gwas_evidence.append(evidence_item)
        else:
            other_genetic_evidence.append(evidence_item)

    # Compute summary statistics
    all_evidence = gwas_evidence + other_genetic_evidence
    max_score = max((e["score"] for e in all_evidence if e["score"] is not None), default=None)
    n_variants = len(set(e["variant_rsid"] for e in all_evidence if e["variant_rsid"]))
    n_studies = len(set(e["study_id"] for e in all_evidence if e["study_id"]))

    # Build summary
    parts = []
    if gwas_evidence:
        parts.append(f"{len(gwas_evidence)} GWAS credible set(s)")
    if other_genetic_evidence:
        parts.append(f"{len(other_genetic_evidence)} other genetic evidence(s)")
    if not parts:
        parts.append("no genetic evidence found")

    score_str = f" Overall association: {overall_score:.3f}." if overall_score is not None else ""
    max_str = f" Max L2G score: {max_score:.3f}." if max_score is not None else ""
    variant_str = f" {n_variants} unique variant(s) across {n_studies} study(ies)." if n_variants > 0 else ""

    return {
        "summary": (
            f"Genetic evidence for {approved_symbol} -> {resolved_disease}: "
            f"{', '.join(parts)}.{score_str}{max_str}{variant_str}"
        ),
        "gene": approved_symbol,
        "gene_name": approved_name,
        "ensembl_id": ensembl_id,
        "disease": resolved_disease,
        "disease_id": efo_id,
        "overall_association_score": overall_score,
        "datasource_scores": datasource_scores,
        "total_evidence_count": evidence_count,
        "gwas_credible_sets": gwas_evidence,
        "other_genetic_evidence": other_genetic_evidence,
        "max_l2g_score": max_score,
        "n_unique_variants": n_variants,
        "n_studies": n_studies,
    }


@registry.register(
    name="genomics.coloc",
    description="Look up GWAS-eQTL/pQTL colocalization evidence for a gene via Open Targets Platform",
    category="genomics",
    parameters={
        "gene": "Gene symbol (e.g. 'PCSK9', 'IL6R')",
        "study_id": "Specific GWAS study ID to filter (optional)",
    },
    requires_data=[],
    usage_guide="You want to assess whether a GWAS signal and an eQTL/pQTL signal share the same "
                "causal variant at a locus — the gold standard for connecting genetic associations "
                "to gene function. High H4 posterior probability (>0.8) indicates strong colocalization. "
                "Use for target validation and causal gene assignment at GWAS loci.",
)
def coloc(gene: str, study_id: str = None, **kwargs) -> dict:
    """Look up colocalization evidence from Open Targets Platform GraphQL API.

    Queries the Open Targets credibleSets and colocalisations data for a gene
    target, returning GWAS-QTL colocalization information including H4 posterior
    probabilities (evidence of shared causal variant), study details, and tissues.
    """
    try:
        import httpx
    except ImportError:
        return {"error": "httpx required (pip install httpx)", "summary": "httpx required (pip install httpx)"}
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    def _gene_symbol_candidates(input_gene: str) -> list[str]:
        alias_map = {
            "GBA1": "GBA",
            "PARK2": "PRKN",
        }
        token = (input_gene or "").strip()
        if not token:
            return []
        candidates = [token]
        mapped = alias_map.get(token.upper())
        if mapped:
            candidates.append(mapped)

        # Stable de-dup preserving order (case-insensitive).
        deduped = []
        seen = set()
        for c in candidates:
            k = c.upper()
            if k in seen:
                continue
            seen.add(k)
            deduped.append(c)
        return deduped

    def _resolve_ensembl_id(symbol: str) -> tuple[str | None, str | None]:
        ens_resp, resolve_error = request(
            "GET",
            f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{symbol}",
            params={"content-type": "application/json"},
            timeout=10,
            retries=2,
            headers={"Content-Type": "application/json"},
            raise_for_status=False,
        )
        if resolve_error:
            return None, f"Failed to resolve {symbol} to Ensembl ID: {resolve_error}"
        if ens_resp.status_code != 200:
            return None, f"Gene {symbol} not found in Ensembl (human)"
        try:
            ens_data = ens_resp.json()
        except Exception:
            return None, f"Failed to parse Ensembl response for {symbol}"
        ensembl = ens_data.get("id", "")
        if not ensembl:
            return None, f"Gene {symbol} not found in Ensembl (human)"
        return ensembl, None

    # Step 2: Query Open Targets for credible sets with colocalization data.
    # We keep a full query and a lower-complexity fallback query because some
    # genes can hit Open Targets GraphQL complexity limits.
    query_full = """
    query geneColoc($ensemblId: String!, $size: Int!, $colocSize: Int!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            approvedName
            credibleSets(page: {index: 0, size: $size}) {
                count
                rows {
                    studyLocusId
                    studyId
                    studyType
                    study {
                        id
                        studyType
                        traitFromSource
                        diseases {
                            id
                            name
                        }
                        nSamples
                    }
                    variant {
                        id
                        rsIds
                        chromosome
                        position
                    }
                    pValueMantissa
                    pValueExponent
                    beta
                    colocalisation(page: {index: 0, size: $colocSize}) {
                        count
                        rows {
                            h4
                            h3
                            clpp
                            colocalisationMethod
                            rightStudyType
                            betaRatioSignAverage
                            numberColocalisingVariants
                            otherStudyLocus {
                                studyLocusId
                                studyId
                                studyType
                                qtlGeneId
                                study {
                                    id
                                    traitFromSource
                                    condition
                                    biosample {
                                        biosampleId
                                        biosampleName
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    query_lean = """
    query geneColocLean($ensemblId: String!, $size: Int!, $colocSize: Int!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            approvedName
            credibleSets(page: {index: 0, size: $size}) {
                count
                rows {
                    studyLocusId
                    studyId
                    studyType
                    study {
                        id
                        studyType
                        traitFromSource
                        diseases {
                            id
                            name
                        }
                    }
                    colocalisation(page: {index: 0, size: $colocSize}) {
                        count
                        rows {
                            h4
                            h3
                            clpp
                            colocalisationMethod
                            rightStudyType
                            otherStudyLocus {
                                studyLocusId
                                studyId
                                studyType
                                qtlGeneId
                                study {
                                    id
                                    traitFromSource
                                    condition
                                    biosample {
                                        biosampleId
                                        biosampleName
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    def _query_target_coloc(ensembl: str) -> tuple[dict | None, str | None]:
        def _run_query(query_text: str, page_attempts: tuple[tuple[int, int], ...]) -> tuple[dict | None, str | None]:
            last_err = None
            for size, coloc_size in page_attempts:
                resp, query_error = request(
                    "POST",
                    ot_url,
                    json={
                        "query": query_text,
                        "variables": {
                            "ensemblId": ensembl,
                            "size": size,
                            "colocSize": coloc_size,
                        },
                    },
                    headers=headers,
                    timeout=15,
                    retries=2,
                    raise_for_status=False,
                )
                if query_error:
                    last_err = f"Open Targets API error: {query_error}"
                    continue
                if resp.status_code != 200:
                    last_err = f"Open Targets API returned HTTP {resp.status_code}"
                    # Retry with smaller page sizes for likely complexity-related rejections.
                    if resp.status_code in {400, 413, 422, 429, 500, 502, 503, 504}:
                        continue
                    break

                try:
                    payload = resp.json()
                except Exception:
                    last_err = "Open Targets API returned invalid JSON"
                    continue

                gql_errors = payload.get("errors") or []
                if gql_errors:
                    msgs = "; ".join(e.get("message", "") for e in gql_errors)
                    last_err = f"Open Targets GraphQL errors: {msgs}"
                    lower = msgs.lower()
                    if any(tok in lower for tok in ("complex", "depth", "cost", "too many", "timeout")):
                        continue
                    break
                return payload, None
            return None, (last_err or "Open Targets colocalization query failed")

        # Try richer query first, then lower-complexity fallback.
        attempts = (
            ("full", query_full, ((60, 40), (30, 20), (15, 10))),
            ("lean", query_lean, ((40, 20), (20, 10), (10, 5))),
        )
        errors = []
        for label, query_text, page_attempts in attempts:
            payload, err = _run_query(query_text, page_attempts)
            if payload is not None:
                return payload, None
            if err:
                errors.append(f"{label} query: {err}")
        if errors:
            return None, "; ".join(errors)
        return None, "Open Targets colocalization query failed"

    # Try primary symbol first, then common aliases (e.g., GBA1 -> GBA) if needed.
    gene_candidates = _gene_symbol_candidates(gene)
    ensembl_id = None
    result_data = None
    target_data = None
    candidate_errors = []
    query_failures = []
    resolved_candidates = []

    for gene_candidate in gene_candidates:
        ensembl_candidate, resolve_error = _resolve_ensembl_id(gene_candidate)
        if resolve_error:
            candidate_errors.append(resolve_error)
            continue
        resolved_candidates.append((gene_candidate, ensembl_candidate))

        payload, query_error = _query_target_coloc(ensembl_candidate)
        if query_error:
            candidate_errors.append(f"{gene_candidate}: {query_error}")
            query_failures.append((gene_candidate, ensembl_candidate, query_error))
            continue

        target_candidate = (payload or {}).get("data", {}).get("target")
        if not target_candidate:
            candidate_errors.append(
                f"{gene_candidate}: Open Targets has no entry for {ensembl_candidate}"
            )
            query_failures.append(
                (gene_candidate, ensembl_candidate, f"Open Targets has no entry for {ensembl_candidate}")
            )
            continue

        ensembl_id = ensembl_candidate
        result_data = payload
        target_data = target_candidate
        break

    if not target_data:
        last_error = candidate_errors[-1] if candidate_errors else "Open Targets colocalization query failed"
        if candidate_errors and all("not found in Ensembl" in e for e in candidate_errors):
            return {
                "error": last_error,
                "summary": f"Gene symbol {gene} could not be resolved to an Ensembl ID",
            }
        # Resolved gene(s) but Open Targets could not return colocalization payload.
        # Return a non-fatal unavailable result so workflows can continue.
        if resolved_candidates:
            chosen_symbol, chosen_ensembl = resolved_candidates[0]
            warning = query_failures[0][2] if query_failures else last_error
            return {
                "summary": (
                    f"Colocalization for {chosen_symbol}: unavailable from Open Targets "
                    f"(query failed). Try genomics.eqtl_lookup for orthogonal evidence."
                ),
                "gene": chosen_symbol,
                "ensembl_id": chosen_ensembl,
                "total_gwas_loci": 0,
                "n_colocalizations": 0,
                "n_strong_coloc": 0,
                "n_moderate_coloc": 0,
                "n_tissues": 0,
                "n_studies": 0,
                "tissues": [],
                "colocalizations": [],
                "data_unavailable": True,
                "warning": warning,
            }
        if "GraphQL errors" in last_error:
            return {
                "error": last_error,
                "summary": f"GraphQL query errors for {gene} colocalization",
            }
        return {
            "error": last_error,
            "summary": f"Open Targets colocalization query failed for {gene}",
        }

    approved_symbol = target_data.get("approvedSymbol", gene)
    # Backward-compatibility: some mocked test fixtures still use legacy field names.
    credible_sets = target_data.get("credibleSets") or target_data.get("gwasCredibleSets") or {}
    rows = credible_sets.get("rows", []) if isinstance(credible_sets, dict) else []

    # Keep only GWAS credible sets for this tool.
    def _is_gwas(row: dict) -> bool:
        st = (row.get("studyType") or (row.get("study") or {}).get("studyType") or "")
        return str(st).lower() == "gwas"

    if target_data.get("gwasCredibleSets") is not None:
        gwas_rows = rows
        total_loci = credible_sets.get("count", len(rows))
    else:
        gwas_rows = [row for row in rows if _is_gwas(row)]
        total_loci = len(gwas_rows)

    # Parse colocalization results
    coloc_results = []
    tissues_seen = set()
    studies_seen = set()

    for row in gwas_rows:
        study = row.get("study") or {}
        gwas_study_id = row.get("studyId") or study.get("id", "")

        # Filter by study_id if provided
        if study_id and gwas_study_id != study_id:
            continue

        variant = row.get("variant") or {}
        rs_ids = variant.get("rsIds", [])
        lead_rsid = rs_ids[0] if rs_ids else ""

        # Compute p-value
        p_mantissa = row.get("pValueMantissa")
        p_exponent = row.get("pValueExponent")
        p_value = None
        if p_mantissa is not None and p_exponent is not None:
            try:
                p_value = float(p_mantissa) * (10 ** int(p_exponent))
            except (ValueError, TypeError):
                pass

        # Extract L2G score for this gene
        l2g_score = None
        l2g_preds_raw = row.get("l2GPredictions") or []
        if isinstance(l2g_preds_raw, dict):
            l2g_preds = l2g_preds_raw.get("rows") or []
        else:
            l2g_preds = l2g_preds_raw
        for pred in l2g_preds:
            pred_target = pred.get("target") or {}
            if pred_target.get("id") == ensembl_id:
                l2g_score = pred.get("score")
                if l2g_score is None:
                    l2g_score = pred.get("yProbaModel")
                break

        trait = study.get("traitFromSource", "")
        diseases = study.get("diseases") or []
        disease_names = [d.get("name", "") for d in diseases if d.get("name")]

        # Parse current Open Targets schema: colocalisation.rows
        coloc_obj = row.get("colocalisation") or {}
        qtl_colocs = coloc_obj.get("rows", []) if isinstance(coloc_obj, dict) else []
        for qtl in qtl_colocs:
            h4 = qtl.get("h4")
            h3 = qtl.get("h3")
            right_study_type = str(qtl.get("rightStudyType") or "").lower()
            if right_study_type and "qtl" not in right_study_type:
                continue

            other = qtl.get("otherStudyLocus") or {}
            other_study = other.get("study") or {}
            biosample = other_study.get("biosample") or {}

            tissue_name = (
                biosample.get("biosampleName")
                or other_study.get("condition")
                or other_study.get("traitFromSource")
                or ""
            )
            tissue_id = biosample.get("biosampleId", "")
            qtl_study = other.get("studyId") or other_study.get("id", "")
            phenotype = other.get("qtlGeneId", "")

            log2_h4_h3 = None
            if h4 is not None and h3 not in (None, 0):
                try:
                    if float(h4) > 0 and float(h3) > 0:
                        log2_h4_h3 = math.log2(float(h4) / float(h3))
                except (TypeError, ValueError, ZeroDivisionError):
                    log2_h4_h3 = None

            if tissue_name:
                tissues_seen.add(tissue_name)
            studies_seen.add(gwas_study_id)

            coloc_results.append({
                "gwas_study_id": gwas_study_id,
                "trait": trait,
                "diseases": disease_names,
                "lead_variant": variant.get("id", ""),
                "lead_rsid": lead_rsid,
                "p_value": p_value,
                "l2g_score": round(l2g_score, 4) if l2g_score is not None else None,
                "qtl_study_id": qtl_study,
                "phenotype_id": phenotype,
                "tissue": tissue_name,
                "tissue_id": tissue_id,
                "h4": round(h4, 4) if h4 is not None else None,
                "h3": round(h3, 4) if h3 is not None else None,
                "log2_h4_h3": round(log2_h4_h3, 4) if log2_h4_h3 is not None else None,
                "colocalisation_method": qtl.get("colocalisationMethod"),
                "right_study_type": qtl.get("rightStudyType"),
                "clpp": round(qtl.get("clpp"), 4) if qtl.get("clpp") is not None else None,
            })

        # Backward compatibility with legacy schema field name used in old fixtures.
        legacy_qtls = row.get("colocalisationsQtl") or []
        for qtl in legacy_qtls:
            h4 = qtl.get("h4")
            tissue_info = qtl.get("tissue") or {}
            tissue_name = tissue_info.get("name", "")
            tissue_id = tissue_info.get("id", "")
            qtl_study = qtl.get("qtlStudyId", "")
            phenotype = qtl.get("phenotypeId", "")

            if tissue_name:
                tissues_seen.add(tissue_name)
            studies_seen.add(gwas_study_id)

            coloc_results.append({
                "gwas_study_id": gwas_study_id,
                "trait": trait,
                "diseases": disease_names,
                "lead_variant": variant.get("id", ""),
                "lead_rsid": lead_rsid,
                "p_value": p_value,
                "l2g_score": round(l2g_score, 4) if l2g_score is not None else None,
                "qtl_study_id": qtl_study,
                "phenotype_id": phenotype,
                "tissue": tissue_name,
                "tissue_id": tissue_id,
                "h4": round(h4, 4) if h4 is not None else None,
                "h3": round(qtl.get("h3", 0), 4) if qtl.get("h3") is not None else None,
                "log2_h4_h3": round(qtl.get("log2h4h3", 0), 4) if qtl.get("log2h4h3") is not None else None,
                "colocalisation_method": None,
                "right_study_type": None,
                "clpp": None,
            })

    # Sort by H4 (strongest colocalization first)
    coloc_results.sort(key=lambda x: x["h4"] if x["h4"] is not None else 0, reverse=True)

    n_strong = sum(1 for c in coloc_results if c["h4"] is not None and c["h4"] > 0.8)
    n_moderate = sum(1 for c in coloc_results if c["h4"] is not None and 0.5 < c["h4"] <= 0.8)

    # Build summary
    study_filter_str = f" (study {study_id})" if study_id else ""
    if coloc_results:
        top_coloc = coloc_results[0]
        top_str = (
            f"Strongest: {top_coloc['trait']} / {top_coloc['tissue']} "
            f"(H4={top_coloc['h4']:.3f})" if top_coloc['h4'] is not None
            else f"Strongest: {top_coloc['trait']} / {top_coloc['tissue']}"
        )
        summary = (
            f"Colocalization for {approved_symbol}{study_filter_str}: "
            f"{len(coloc_results)} GWAS-QTL pairs across {len(tissues_seen)} tissues, "
            f"{len(studies_seen)} GWAS studies. "
            f"{n_strong} strong (H4>0.8), {n_moderate} moderate (0.5<H4<=0.8). "
            f"{top_str}"
        )
    else:
        summary = (
            f"Colocalization for {approved_symbol}{study_filter_str}: "
            f"no QTL colocalization data found ({total_loci} GWAS loci scanned)"
        )

    return {
        "summary": summary,
        "gene": approved_symbol,
        "ensembl_id": ensembl_id,
        "total_gwas_loci": total_loci,
        "n_colocalizations": len(coloc_results),
        "n_strong_coloc": n_strong,
        "n_moderate_coloc": n_moderate,
        "n_tissues": len(tissues_seen),
        "n_studies": len(studies_seen),
        "tissues": sorted(tissues_seen),
        "colocalizations": coloc_results[:50],  # Cap at 50
    }


# ---------------------------------------------------------------------------
# Variant classification (code-gen tool)
# ---------------------------------------------------------------------------

VARIANT_CLASSIFY_PROMPT = """You are an expert bioinformatics data analyst classifying and analyzing genomic variants.

{namespace_description}

## Available Data
{data_files_description}

## DATA LOADING
- **ZIP files**: Extract first with `zipfile.ZipFile(path, "r").extractall("/tmp/extracted")`
- **Excel .xls**: `pd.read_excel(path, engine='xlrd')`
- **Excel .xlsx**: `pd.read_excel(path, engine='openpyxl')`
- **VCF**: parse with pandas or cyvcf2; standard columns: CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO

Always check `pd.ExcelFile(path).sheet_names` and try both `skiprows=0` and `skiprows=1`
(clinical variant files often have multi-row headers).

## DATA EXPLORATION (DO THIS FIRST)
```python
print("Columns:", df.columns.tolist())
print("Shape:", df.shape)
print("Head:\\n", df.head(3))
print("Dtypes:\\n", df.dtypes)
```

## VARIANT ANALYSIS

### VAF (Variant Allele Frequency) Column Discovery
VAF columns have many naming conventions. Search broadly:
```python
vaf_terms = ['variant allele freq', 'allele freq', 'allele frac', 'vaf',
             'tumor_f', 't_alt_freq', 'af', 'allelic fraction']
vaf_col = None
for col in df.columns:
    if any(term in str(col).lower() for term in vaf_terms):
        vaf_col = col
        break
# Fallback: find float column with values in [0, 1]
if vaf_col is None:
    for col in df.columns:
        if df[col].dtype in [float, np.float64]:
            vals = df[col].dropna()
            if len(vals) > 0 and vals.min() >= 0 and vals.max() <= 1:
                vaf_col = col
                break
```

### Effect/Consequence Annotation
Variant files often have multiple annotation columns at different granularity levels.
Always use the most granular (e.g., Sequence Ontology terms over broad "Effect" categories).
```python
effect_cols = [c for c in df.columns if any(k in str(c).lower()
               for k in ['effect', 'consequence', 'ontology', 'classification'])]
for col in effect_cols:
    print(f"  {{col}}: {{sorted(df[col].dropna().unique())}}")
```

### Coding vs Noncoding Classification
**Coding** (affect protein sequence): synonymous_variant, missense_variant, frameshift_variant,
stop_gained, stop_lost, start_lost, inframe_insertion, inframe_deletion,
splice_donor_variant, splice_acceptor_variant.

**Noncoding**: intron_variant, intergenic_variant, 3_prime_UTR_variant, 5_prime_UTR_variant,
splice_region_variant, upstream_gene_variant, downstream_gene_variant.

### Ts/Tv Ratio (Transition/Transversion)
Only count SNPs using REF and the first ALT allele (`ALT.split(',')[0]`) so multi-allelic
records with SNP first-alleles are not discarded.
For raw bacterial VCFs, apply a high-confidence depth filter using the sample FORMAT depth
(`FORMAT` field DP, not INFO-level DP): keep SNPs with FORMAT/DP >= 12 before final Ts/Tv
reporting unless the question explicitly requests unfiltered raw calls.
```python
transitions = {{'AG', 'GA', 'CT', 'TC'}}
transversions = {{'AC', 'CA', 'AT', 'TA', 'GC', 'CG', 'GT', 'TG'}}
ts = tv = 0
for _, row in df.iterrows():
    ref = str(row['REF']).upper()
    alt = str(row['ALT']).split(',')[0].upper()
    if len(ref) == 1 and len(alt) == 1:
        pair = ref + alt
        if pair in transitions: ts += 1
        elif pair in transversions: tv += 1
tstv = ts / tv if tv > 0 else 0
```

### Carrier/Cohort Analysis
When analyzing multiple samples:
1. Explore directory to find all variant files and any metadata/annotation files
2. Read metadata to identify sample groups (carriers vs controls, etc.)
3. Match variant files to samples by ID patterns in filenames
4. Filter variants per sample (e.g., non-reference zygosity, VAF thresholds)

## Rules
1. Do NOT import libraries already in the namespace (pd, np, plt, sns, scipy_stats, etc.)
2. Save plots to OUTPUT_DIR: `plt.savefig(OUTPUT_DIR / "filename.png", dpi=150, bbox_inches="tight")`; `plt.close()`
3. Assign result: `result = {{"summary": "...", "answer": "PRECISE_ANSWER"}}`
4. Use print() for intermediate output to verify correctness.
5. If 0 results from a filter: print the column values and debug — do not return "N/A".

Write ONLY the Python code. No explanation, no markdown fences.
"""


@registry.register(
    name="genomics.variant_classify",
    description=(
        "Classify and analyze genomic variants from VCF, Excel, or clinical variant files "
        "(VAF filtering, coding/noncoding classification, ClinVar annotation, carrier analysis)"
    ),
    category="genomics",
    parameters={"goal": "Variant analysis to perform"},
    usage_guide=(
        "Use for variant classification tasks: VAF filtering, Ts/Tv ratios, coding vs noncoding, "
        "CHIP analysis, carrier genotype analysis, ClinVar classification lookups. "
        "Handles multi-row Excel headers, various VAF column naming conventions. "
        "Do NOT use for GWAS, eQTL, or Mendelian randomization — use genomics.gwas_lookup for those."
    ),
)
def variant_classify(goal: str, _session=None, _prior_results=None, **kwargs) -> dict:
    """Classify and analyze genomic variants using generated code in a sandbox."""
    from ct.tools.code import _generate_and_execute_code

    return _generate_and_execute_code(
        goal=goal,
        system_prompt_template=VARIANT_CLASSIFY_PROMPT,
        session=_session,
        prior_results=_prior_results,
    )


@registry.register(
    name="genomics.gene_annotation",
    description=(
        "Look up gene annotation (GO terms, functional description, linked publications) "
        "for a gene in any supported plant species using Ensembl Plants and UniProt."
    ),
    category="genomics",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'GW5')",
        "species": "Species name (default: Arabidopsis thaliana)",
        "force": "Skip species registry check and try any species string (default: False)",
    },
    usage_guide=(
        "Retrieves GO terms, functional description, genomic location, and linked "
        "PubMed IDs for a plant gene from Ensembl Plants and UniProt. "
        "Related tools: genomics.ortholog_map, literature.pubmed_plant_search."
    ),
)
def gene_annotation(gene: str = "", species: str = "Arabidopsis thaliana", force: bool = False, **kwargs) -> dict:
    """Look up gene annotation from Ensembl Plants and UniProt for a plant gene."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    gene = str(gene or "").strip()
    if not gene:
        return {"error": "Missing required parameter: gene", "summary": "gene_annotation requires a non-empty gene symbol or locus code."}

    # Species validation
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0 and not force:
        return {
            "error": f"Unknown species: {species!r}. Use force=True to override.",
            "summary": f"Species not recognised: {species!r}.",
        }
    binomial = resolve_species_binomial(species) or species

    # Cache check
    cache_key = f"gene_annotation:{taxon_id}:{gene}"
    cached = get_cached("ensembl_gene", cache_key)
    if cached is not None:
        return cached

    ensembl_base = "https://rest.ensembl.org"
    species_url = binomial.lower().replace(" ", "_")

    # Step 1 — Ensembl Plants gene lookup by symbol
    gene_data, err = request_json(
        "GET",
        f"{ensembl_base}/lookup/symbol/{species_url}/{gene}",
        params={"content-type": "application/json"},
        timeout=15,
        retries=2,
    )
    if err or gene_data is None:
        return {
            "summary": f"Gene '{gene}' not found in Ensembl Plants for {binomial}.",
            "gene": gene,
            "species": binomial,
            "error": err or "Not found",
        }

    ensembl_id = gene_data.get("id", "")
    description = gene_data.get("description", "")
    display_name = gene_data.get("display_name", gene)
    biotype = gene_data.get("biotype", "")
    chromosome = gene_data.get("seq_region_name", "")
    start = gene_data.get("start")
    end = gene_data.get("end")
    strand = gene_data.get("strand")

    # Step 2 — GO cross-references from Ensembl
    go_terms = []
    seen_go_ids: set = set()
    if ensembl_id:
        go_data, _ = request_json(
            "GET",
            f"{ensembl_base}/xrefs/id/{ensembl_id}",
            params={"content-type": "application/json", "external_db": "GO", "all_levels": 0},
            timeout=15,
            retries=2,
        )
        for xref in (go_data or []):
            go_id = xref.get("primary_id", "")
            if go_id.startswith("GO:") and go_id not in seen_go_ids:
                seen_go_ids.add(go_id)
                go_terms.append({
                    "go_id": go_id,
                    "term": xref.get("description", ""),
                    "evidence": xref.get("info_type", ""),
                    "namespace": "",
                })

    # Step 3 — UniProt for protein-level GO + publications
    pubmed_ids = []
    uniprot_function = ""
    uniprot_data, _ = request_json(
        "GET",
        "https://rest.uniprot.org/uniprotkb/search",
        params={
            "query": f"gene:{gene} AND organism_id:{taxon_id} AND reviewed:true",
            "fields": "gene_names,go,cc_function,lit_pubmed_id",
            "format": "json",
            "size": 1,
        },
        timeout=15,
        retries=2,
    )
    results = (uniprot_data or {}).get("results", [])
    if results:
        entry = results[0]
        # UniProt GO terms
        for xref in (entry.get("uniProtKBCrossReferences") or []):
            if xref.get("database") == "GO":
                go_id = xref.get("id", "")
                if go_id and go_id not in seen_go_ids:
                    seen_go_ids.add(go_id)
                    namespace = ""
                    term = ""
                    for prop in (xref.get("properties") or []):
                        if prop.get("key") == "GoTerm":
                            val = prop.get("value", "")
                            if val.startswith("C:"):
                                namespace = "cellular_component"
                                term = val[2:]
                            elif val.startswith("F:"):
                                namespace = "molecular_function"
                                term = val[2:]
                            elif val.startswith("P:"):
                                namespace = "biological_process"
                                term = val[2:]
                            else:
                                term = val
                    go_terms.append({"go_id": go_id, "term": term, "evidence": "", "namespace": namespace})
        # PubMed IDs
        for ref in (entry.get("references") or []):
            citation = ref.get("citation", {})
            title = citation.get("title", "")
            for cross_ref in (citation.get("citationCrossReferences") or []):
                if cross_ref.get("database") == "PubMed":
                    pubmed_ids.append({"pmid": cross_ref.get("id", ""), "title": title})
        # Function description
        for comment in (entry.get("comments") or []):
            if comment.get("commentType") == "FUNCTION":
                texts = [t.get("value", "") for t in (comment.get("texts") or [])]
                uniprot_function = " ".join(t for t in texts if t)

    result = {
        "summary": (
            f"Gene annotation for {display_name} ({ensembl_id}) in {binomial}: "
            f"{len(go_terms)} GO terms, {len(pubmed_ids)} linked publications."
        ),
        "gene": gene,
        "ensembl_id": ensembl_id,
        "display_name": display_name,
        "species": binomial,
        "taxon_id": taxon_id,
        "description": description,
        "biotype": biotype,
        "location": {"chromosome": chromosome, "start": start, "end": end, "strand": strand},
        "go_terms": go_terms,
        "function_description": uniprot_function or description,
        "pubmed_ids": pubmed_ids,
        "pubmed_count": len(pubmed_ids),
    }
    set_cached("ensembl_gene", cache_key, result)
    return result


@registry.register(
    name="genomics.gwas_qtl_lookup",
    description=(
        "Look up GWAS hits and QTL/phenotype annotations for a gene in a plant species "
        "using the Ensembl Plants phenotype endpoint."
    ),
    category="genomics",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'GW5')",
        "species": "Species name (default: Arabidopsis thaliana)",
        "trait": "Optional trait keyword to filter results (e.g. 'flowering time', 'yield')",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Retrieves GWAS hits and phenotype/QTL annotations for a plant gene from "
        "the Ensembl Plants phenotype endpoint. Returns trait descriptions, sources, "
        "associated studies, and PubMed IDs where available."
    ),
)
def gwas_qtl_lookup(gene: str = "", species: str = "Arabidopsis thaliana", trait: str = None, force: bool = False, **kwargs) -> dict:
    """Look up GWAS hits and phenotype/QTL annotations from Ensembl Plants for a plant gene."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    gene = str(gene or "").strip()
    if not gene:
        return {"error": "Missing required parameter: gene", "summary": "gwas_qtl_lookup requires a non-empty gene symbol or locus code."}
    trait = str(trait or "").strip() or None

    # Species validation
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0 and not force:
        return {
            "error": f"Unknown species: {species!r}. Use force=True to override.",
            "summary": f"Species not recognised: {species!r}.",
        }
    binomial = resolve_species_binomial(species) or species

    # Cache check
    cache_key = f"gwas_qtl:{taxon_id}:{gene}:{trait or ''}"
    cached = get_cached("ensembl_phenotype", cache_key)
    if cached is not None:
        return cached

    ensembl_base = "https://rest.ensembl.org"
    species_url = binomial.lower().replace(" ", "_")

    # Step 1 — Resolve gene to Ensembl ID (best-effort; failure is non-fatal)
    _gene_data, _err = request_json(
        "GET",
        f"{ensembl_base}/lookup/symbol/{species_url}/{gene}",
        params={"content-type": "application/json"},
        timeout=15,
        retries=2,
    )
    # Proceed regardless — phenotype endpoint accepts gene symbols directly

    # Step 2 — Ensembl phenotype/gene endpoint
    phenotype_data, _ph_err = request_json(
        "GET",
        f"{ensembl_base}/phenotype/gene/{species_url}/{gene}",
        params={
            "content-type": "application/json",
            "include_associated": 1,
            "include_pubmed_id": 1,
            "non_specified": 1,
        },
        timeout=15,
        retries=2,
    )

    # Step 3 — Parse and optionally filter by trait
    raw_phenotypes = []
    for entry in (phenotype_data or []):
        raw_phenotypes.append({
            "description": entry.get("description", ""),
            "source": entry.get("source", ""),
            "study": entry.get("study", ""),
            "pubmed_id": entry.get("pubmed_id", ""),
            "attributes": entry.get("attributes", {}),
        })

    if trait:
        phenotypes = [p for p in raw_phenotypes if trait.lower() in p["description"].lower()]
    else:
        phenotypes = raw_phenotypes

    # Sort: entries with pubmed_id first
    phenotypes.sort(key=lambda p: (0 if p["pubmed_id"] else 1))

    suggestion = ""
    if not phenotypes and species_url != "arabidopsis_thaliana":
        suggestion = (
            f"No phenotype annotations found for {gene} in {binomial}. "
            "Phenotype data coverage is limited for this species in Ensembl Plants."
        )
    elif not phenotypes:
        suggestion = (
            f"No phenotype annotations found for {gene} in Ensembl Plants. "
            "Phenotype data coverage is limited for this gene."
        )

    result = {
        "summary": (
            f"Found {len(phenotypes)} phenotype annotation(s) for {gene} in {binomial}"
            + (f" matching '{trait}'" if trait else "")
            + "."
            + (f" {suggestion}" if suggestion and not phenotypes else "")
        ),
        "gene": gene,
        "species": binomial,
        "taxon_id": taxon_id,
        "trait_filter": trait,
        "phenotype_count": len(phenotypes),
        "phenotypes": phenotypes,
        "suggestion": suggestion if not phenotypes else "",
    }
    set_cached("ensembl_phenotype", cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Phylogenetic distance matrix (millions of years, approximate)
# Curated from published plant phylogenomics (Zeng et al. 2017, APG IV).
# Used by ortholog_map for distance-based weighting.
# Key: frozenset of two taxon IDs. Value: approximate divergence time in Mya.
# Default for unknown pairs: 200 Mya.
# ---------------------------------------------------------------------------
_PHYLO_DISTANCES_MYA: dict[frozenset, float] = {
    # Brassicaceae internal
    frozenset({3702, 3708}): 43.0,       # Arabidopsis vs Brassica napus
    # Solanaceae internal
    frozenset({4081, 4113}): 8.0,        # Tomato vs potato
    frozenset({4081, 4097}): 30.0,       # Tomato vs tobacco
    frozenset({4113, 4097}): 30.0,       # Potato vs tobacco
    # Fabaceae internal
    frozenset({3847, 3880}): 54.0,       # Soybean vs Medicago
    frozenset({3847, 34305}): 54.0,      # Soybean vs Lotus
    frozenset({3880, 34305}): 50.0,      # Medicago vs Lotus
    # Poaceae (grasses) internal
    frozenset({4530, 4577}): 50.0,       # Rice vs maize
    frozenset({4530, 4565}): 50.0,       # Rice vs wheat
    frozenset({4530, 4513}): 50.0,       # Rice vs barley
    frozenset({4530, 4558}): 50.0,       # Rice vs sorghum
    frozenset({4577, 4565}): 25.0,       # Maize vs wheat
    frozenset({4577, 4513}): 25.0,       # Maize vs barley
    frozenset({4577, 4558}): 12.0,       # Maize vs sorghum
    frozenset({4565, 4513}): 12.0,       # Wheat vs barley
    frozenset({4565, 4558}): 25.0,       # Wheat vs sorghum
    frozenset({4513, 4558}): 25.0,       # Barley vs sorghum
    frozenset({4530, 214687}): 100.0,    # Rice vs banana (monocot divergence)
    frozenset({4577, 214687}): 100.0,    # Maize vs banana
    frozenset({4565, 214687}): 100.0,    # Wheat vs banana
    # Eudicot vs monocot (major split ~150 Mya)
    frozenset({3702, 4530}): 150.0,      # Arabidopsis vs rice
    frozenset({3702, 4577}): 150.0,      # Arabidopsis vs maize
    frozenset({3702, 4565}): 150.0,      # Arabidopsis vs wheat
    frozenset({3702, 4513}): 150.0,      # Arabidopsis vs barley
    frozenset({3702, 4558}): 150.0,      # Arabidopsis vs sorghum
    frozenset({3702, 214687}): 150.0,    # Arabidopsis vs banana
    frozenset({3708, 4530}): 150.0,      # Brassica vs rice
    frozenset({4081, 4530}): 150.0,      # Tomato vs rice
    frozenset({3847, 4530}): 150.0,      # Soybean vs rice
    frozenset({4081, 4577}): 150.0,      # Tomato vs maize
    frozenset({3847, 4577}): 150.0,      # Soybean vs maize
    # Core eudicot cross-family
    frozenset({3702, 4081}): 112.0,      # Arabidopsis vs tomato (rosid vs asterid)
    frozenset({3702, 3847}): 90.0,       # Arabidopsis vs soybean (rosids)
    frozenset({3702, 3880}): 90.0,       # Arabidopsis vs Medicago
    frozenset({3702, 3694}): 100.0,      # Arabidopsis vs poplar (rosids)
    frozenset({3702, 29760}): 112.0,     # Arabidopsis vs grape
    frozenset({3702, 3983}): 112.0,      # Arabidopsis vs cassava
    frozenset({3702, 3635}): 112.0,      # Arabidopsis vs cotton
    frozenset({3702, 57918}): 90.0,      # Arabidopsis vs strawberry (rosids)
    frozenset({3847, 4081}): 112.0,      # Soybean vs tomato (rosid vs asterid)
    frozenset({3694, 4081}): 112.0,      # Poplar vs tomato
    frozenset({3694, 3847}): 100.0,      # Poplar vs soybean
    frozenset({3694, 3702}): 100.0,      # Poplar vs Arabidopsis
    # Self-distances (identity)
    frozenset({3702, 3702}): 0.0,
    frozenset({4530, 4530}): 0.0,
    frozenset({4577, 4577}): 0.0,
}


def _phylo_weight(taxon_a: int, taxon_b: int) -> float:
    """Return a 0-1 weight inversely proportional to phylogenetic distance.

    Uses the curated distance matrix ``_PHYLO_DISTANCES_MYA``. Unknown
    pairs default to 200 Mya. Weight formula: ``1 / (1 + dist_mya / 100)``.

    Returns:
        Float in [0, 1] rounded to 3 decimal places. Higher = more closely related.
    """
    if taxon_a == taxon_b:
        return 1.0
    key = frozenset({taxon_a, taxon_b})
    dist = _PHYLO_DISTANCES_MYA.get(key, 200.0)
    return round(1.0 / (1.0 + dist / 100.0), 3)


@registry.register(
    name="genomics.ortholog_map",
    description=(
        "Map a gene to its orthologs across plant species using Ensembl Compara, "
        "with phylogenetic distance weighting. Returns ortholog gene IDs, species, "
        "orthology type, percent identity, and distance weight."
    ),
    category="genomics",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'OsMADS51')",
        "species": "Source species (default: Arabidopsis thaliana)",
        "target_species": "Filter to a specific target species (optional; default: all species)",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Maps a gene to its orthologs across plant species using Ensembl Compara. "
        "Returns ortholog gene IDs, species, orthology type, percent identity, and "
        "a phylogenetic distance weight (higher = more closely related)."
    ),
)
def ortholog_map(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    target_species: str = None,
    force: bool = False,
    **kwargs,
) -> dict:
    """Map a gene to its orthologs across plant species using Ensembl Compara."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    gene = str(gene or "").strip()
    if not gene:
        return {
            "error": "Missing required parameter: gene",
            "summary": "ortholog_map requires a non-empty gene symbol or locus code.",
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
    cache_key = f"ortholog_map:{taxon_id}:{gene}:{target_species or 'all'}"
    cached = get_cached("ensembl_orthologs", cache_key)
    if cached is not None:
        return cached

    ensembl_base = "https://rest.ensembl.org"
    species_url = binomial.lower().replace(" ", "_")

    # Step 1 — Resolve gene to Ensembl ID
    gene_data, err = request_json(
        "GET",
        f"{ensembl_base}/lookup/symbol/{species_url}/{gene}",
        params={"content-type": "application/json"},
        timeout=15,
        retries=2,
    )
    if err or gene_data is None:
        return {
            "summary": f"Gene '{gene}' not found in Ensembl Plants for {binomial}.",
            "gene": gene,
            "species": binomial,
            "error": err or "Not found",
            "orthologs": [],
        }
    ensembl_id = gene_data.get("id", "")

    # Step 2 — Ensembl Compara ortholog lookup
    params = {
        "content-type": "application/json",
        "type": "orthologues",
        "compara": "plants",        # CRITICAL — never use vertebrates default
        "format": "condensed",
    }
    if target_species:
        target_binomial = resolve_species_binomial(target_species)
        if target_binomial:
            params["target_species"] = target_binomial.lower().replace(" ", "_")
        else:
            params["target_species"] = target_species.lower().replace(" ", "_")

    homology_data, hom_err = request_json(
        "GET",
        f"{ensembl_base}/homology/id/{species_url}/{ensembl_id}",
        params=params,
        timeout=30,
        retries=2,
    )
    if hom_err:
        return {
            "summary": f"Ensembl Compara query failed for {gene} ({ensembl_id}): {hom_err}",
            "gene": gene,
            "ensembl_id": ensembl_id,
            "species": binomial,
            "error": hom_err,
            "orthologs": [],
        }

    # Step 3 — Parse orthologs and apply phylogenetic distance weight
    homologies = (homology_data or {}).get("data", [{}])[0].get("homologies", [])
    orthologs = []
    for entry in homologies:
        target = entry.get("target", {})
        target_id = target.get("id", "")
        target_species_name = target.get("species", "").replace("_", " ").title()
        target_taxon = resolve_species_taxon(target_species_name)
        perc_id = target.get("perc_id", 0)
        perc_pos = target.get("perc_pos", 0)
        orthology_type = entry.get("type", "")
        phylo_weight = _phylo_weight(taxon_id, target_taxon)
        orthologs.append({
            "gene_id": target_id,
            "species": target_species_name,
            "taxon_id": target_taxon,
            "orthology_type": orthology_type,
            "percent_identity": perc_id,
            "percent_positive": perc_pos,
            "phylo_weight": phylo_weight,
        })

    # Sort by phylo_weight descending (closest relatives first), then percent_identity descending
    orthologs.sort(key=lambda o: (-o["phylo_weight"], -o["percent_identity"]))

    if orthologs:
        summary = (
            f"Found {len(orthologs)} ortholog(s) for {gene} ({ensembl_id}) in {binomial} "
            f"across {len(set(o['species'] for o in orthologs))} species."
        )
    else:
        summary = f"No orthologs found for {gene} in Ensembl Plants Compara."

    result = {
        "summary": summary,
        "gene": gene,
        "ensembl_id": ensembl_id,
        "species": binomial,
        "taxon_id": taxon_id,
        "target_species_filter": target_species,
        "ortholog_count": len(orthologs),
        "orthologs": orthologs,
    }
    set_cached("ensembl_orthologs", cache_key, result)
    return result


# ---------------------------------------------------------------------------
# genomics.gff_parse — GFF3 genome annotation parsing
# ---------------------------------------------------------------------------

@registry.register(
    name="genomics.gff_parse",
    description=(
        "Parse a GFF3 genome annotation file and extract gene structure: "
        "exon positions, UTR boundaries, and intron positions for a gene. "
        "Accepts a local file path or auto-downloads from Ensembl Plants."
    ),
    category="genomics",
    parameters={
        "gene": "Gene ID or symbol (e.g. 'AT5G10140', 'FLC')",
        "species": "Species (default: Arabidopsis thaliana)",
        "gff_path": "Path to local GFF3 file (optional; auto-downloads from Ensembl Plants if absent)",
        "transcript": "Specific transcript ID to parse (optional; uses first/primary mRNA if absent)",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Extracts gene structure (exon positions, intron positions, UTR boundaries) "
        "from a GFF3 genome annotation file. Accepts a local file path or "
        "auto-downloads from Ensembl Plants FTP."
    ),
)
def gff_parse(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    gff_path: str = None,
    transcript: str = None,
    force: bool = False,
    **kwargs,
) -> dict:
    """Parse a GFF3 file and extract exon/UTR/intron structure for a gene."""
    from pathlib import Path
    import gzip

    from ct.tools._species import resolve_species_taxon, resolve_species_binomial, _build_lookup
    from ct.tools.http_client import request
    from ct.tools._api_cache import _CACHE_BASE

    gene = str(gene or "").strip()
    if not gene:
        return {"summary": "Missing required parameter: gene", "error": "Missing gene"}

    # Species validation
    taxon_id = resolve_species_taxon(species)
    binomial = resolve_species_binomial(species)
    if taxon_id == 0 and not force:
        return {
            "summary": f"Unknown species: '{species}'. Use force=True to skip validation.",
            "gene": gene,
            "error": f"Unknown species: '{species}'",
        }
    if not binomial:
        binomial = species

    # File acquisition
    if gff_path is not None:
        gff_local = Path(gff_path)
        if not gff_local.exists():
            return {
                "summary": f"GFF3 file not found: {gff_path}",
                "gene": gene,
                "error": f"File not found: {gff_path}",
            }
    else:
        # Auto-download from Ensembl Plants FTP
        lookup = _build_lookup()
        entry = lookup.get(species.lower(), (0, "", ""))
        genome_build = entry[2] if entry[2] else ""
        if not genome_build:
            # Try with binomial
            entry = lookup.get(binomial.lower(), (0, "", ""))
            genome_build = entry[2] if entry[2] else ""
        if not genome_build:
            return {
                "summary": (
                    f"No genome build known for '{binomial}'. "
                    "Please provide gff_path= pointing to a local GFF3 file."
                ),
                "gene": gene,
                "error": "No genome_build in registry for this species",
            }

        gff_cache_dir = _CACHE_BASE / "gff3"
        gff_cache_dir.mkdir(parents=True, exist_ok=True)
        species_url = binomial.lower().replace(" ", "_")
        species_cap = binomial.replace(" ", "_")
        gff_local = gff_cache_dir / f"{species_url}.gff3"

        if not gff_local.exists():
            url = (
                f"https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-62/gff3/"
                f"{species_url}/{species_cap}.{genome_build}.62.gff3.gz"
            )
            resp, err = request("GET", url, timeout=120, retries=1)
            if err or resp is None:
                return {
                    "summary": (
                        f"Failed to download GFF3 for {binomial} from Ensembl Plants. "
                        f"URL: {url}. Error: {err}. "
                        f"Download manually and provide gff_path=."
                    ),
                    "gene": gene,
                    "error": err or "Download failed",
                    "url": url,
                }
            try:
                raw = gzip.decompress(resp.content)
                with open(gff_local, "wb") as fh:
                    fh.write(raw)
            except Exception as exc:
                return {
                    "summary": f"Failed to decompress GFF3 for {binomial}: {exc}",
                    "gene": gene,
                    "error": str(exc),
                }

    # gffutils database creation or load from cache
    import gffutils

    db_path = gff_local.with_suffix(".db")
    try:
        if db_path.exists():
            db = gffutils.FeatureDB(str(db_path))
        else:
            db = gffutils.create_db(
                str(gff_local),
                dbfn=str(db_path),
                force=True,
                merge_strategy="merge",
                disable_infer_genes=True,
                disable_infer_transcripts=True,
            )
    except Exception as exc:
        return {
            "summary": f"Failed to create/load gffutils database: {exc}",
            "gene": gene,
            "error": str(exc),
        }

    # Gene lookup: ID, then gene: prefix, then Name attribute fallback
    gene_feature = None
    try:
        gene_feature = db[gene]
    except gffutils.FeatureNotFoundError:
        try:
            gene_feature = db[f"gene:{gene}"]
        except gffutils.FeatureNotFoundError:
            # Fallback: search by Name attribute
            for feat in db.features_of_type("gene"):
                names = feat.attributes.get("Name", [])
                if gene in names or gene.upper() in [n.upper() for n in names]:
                    gene_feature = feat
                    break

    if gene_feature is None:
        return {
            "summary": f"Gene '{gene}' not found in GFF3 file.",
            "gene": gene,
            "error": "Gene not found in GFF3",
        }

    # Extract transcript features
    selected_mrna = None
    mrnas = sorted(db.children(gene_feature, featuretype="mRNA"), key=lambda f: f.start)
    if not mrnas:
        # Fallback: try "transcript" feature type
        mrnas = sorted(db.children(gene_feature, featuretype="transcript"), key=lambda f: f.start)

    if not mrnas:
        return {
            "summary": f"No transcript features found for gene '{gene}'.",
            "gene": gene,
            "gene_id": gene_feature.id,
            "error": "No mRNA/transcript features found",
        }

    if transcript:
        for m in mrnas:
            if m.id == transcript or transcript in m.id:
                selected_mrna = m
                break
        if selected_mrna is None:
            selected_mrna = mrnas[0]
    else:
        selected_mrna = mrnas[0]

    # Extract exons, UTRs, and compute introns
    exons = sorted(db.children(selected_mrna, featuretype="exon"), key=lambda f: f.start)
    five_utrs = sorted(db.children(selected_mrna, featuretype="five_prime_UTR"), key=lambda f: f.start)
    three_utrs = sorted(db.children(selected_mrna, featuretype="three_prime_UTR"), key=lambda f: f.start)

    exon_list = [{"start": e.start, "end": e.end, "length": e.end - e.start + 1} for e in exons]
    five_utr_list = [{"start": u.start, "end": u.end, "length": u.end - u.start + 1} for u in five_utrs]
    three_utr_list = [{"start": u.start, "end": u.end, "length": u.end - u.start + 1} for u in three_utrs]

    # Compute introns from exon gaps
    introns = []
    for i in range(len(exons) - 1):
        intron_start = exons[i].end + 1
        intron_end = exons[i + 1].start - 1
        if intron_end >= intron_start:
            introns.append({
                "start": intron_start,
                "end": intron_end,
                "length": intron_end - intron_start + 1,
            })

    result = {
        "summary": (
            f"Gene structure for {gene} ({gene_feature.id}): "
            f"{len(exon_list)} exon(s), {len(introns)} intron(s), "
            f"{gene_feature.end - gene_feature.start + 1:,} bp span."
        ),
        "gene": gene,
        "gene_id": gene_feature.id,
        "transcript": selected_mrna.id,
        "species": binomial,
        "chromosome": gene_feature.seqid,
        "strand": gene_feature.strand,
        "gene_start": gene_feature.start,
        "gene_end": gene_feature.end,
        "gene_span_bp": gene_feature.end - gene_feature.start + 1,
        "total_exons": len(exon_list),
        "total_introns": len(introns),
        "exons": exon_list,
        "introns": introns,
        "five_prime_utrs": five_utr_list,
        "three_prime_utrs": three_utr_list,
    }
    return result


# ---------------------------------------------------------------------------
# genomics.coexpression_network — ATTED-II co-expression analysis
# ---------------------------------------------------------------------------

_ATTED_DOWNLOAD_URLS = {
    "arabidopsis_thaliana": "https://atted.jp/download/Ath-r.c7-0.MR.lst.gz",
    "oryza_sativa": "https://atted.jp/download/Osa-r.c7-0.MR.lst.gz",
}


@registry.register(
    name="genomics.coexpression_network",
    description=(
        "Retrieve co-expressed genes for a plant gene from ATTED-II co-expression data. "
        "Returns top co-expression partners with Mutual Rank (MR) scores and cluster membership."
    ),
    category="genomics",
    parameters={
        "gene": "Gene locus code (e.g. 'AT5G10140', 'Os01g0100100')",
        "species": "Species (default: Arabidopsis thaliana)",
        "top_n": "Number of top co-expressed genes to return (default 20, max 100)",
        "mr_threshold": "Maximum MR score for cluster membership (default 30.0)",
        "force": "Skip species registry check (default: False)",
    },
    usage_guide=(
        "Retrieves co-expressed genes for a query gene from ATTED-II bulk data. "
        "Returns top partners ranked by Mutual Rank (MR) score and cluster membership. "
        "MR < 5 = very strong co-expression, MR 5-30 = moderate, MR > 30 = weak."
    ),
)
def coexpression_network(
    gene: str = "",
    species: str = "Arabidopsis thaliana",
    top_n: int = 20,
    mr_threshold: float = 30.0,
    force: bool = False,
    **kwargs,
) -> dict:
    """Retrieve co-expressed genes from ATTED-II bulk co-expression data."""
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request
    from ct.tools._api_cache import get_cached, set_cached, _CACHE_BASE

    gene = str(gene or "").strip()
    if not gene:
        return {"summary": "Missing required parameter: gene", "error": "Missing gene"}

    # Species validation
    taxon_id = resolve_species_taxon(species)
    binomial = resolve_species_binomial(species)
    if taxon_id == 0 and not force:
        return {
            "summary": f"Unknown species: '{species}'. Use force=True to skip validation.",
            "gene": gene,
            "error": f"Unknown species: '{species}'",
        }
    if not binomial:
        binomial = species

    # Cap top_n
    top_n = min(int(top_n), 100)

    # Cache check
    cache_key = f"coexp:{taxon_id}:{gene}:{top_n}:{mr_threshold}"
    cached = get_cached("atted_coexp", cache_key, ttl_seconds=604800)
    if cached is not None:
        return cached

    # Load ATTED-II data
    atted_dir = _CACHE_BASE / "atted"
    atted_dir.mkdir(parents=True, exist_ok=True)
    species_key = binomial.lower().replace(" ", "_")
    atted_file = atted_dir / f"{species_key}_coexp.tsv"

    if not atted_file.exists():
        if species_key not in _ATTED_DOWNLOAD_URLS:
            return {
                "summary": (
                    f"ATTED-II co-expression data coverage is limited for {binomial}. "
                    f"Data is currently available for Arabidopsis thaliana and Oryza sativa. "
                    f"Additional species data can be placed at {atted_file}."
                ),
                "gene": gene,
                "species": binomial,
                "coexpressed_genes": [],
                "cluster_size": 0,
                "data_source": "ATTED-II (unsupported species)",
                "fallback": True,
            }
        url = _ATTED_DOWNLOAD_URLS[species_key]
        resp, err = request("GET", url, timeout=120, retries=1)
        if err or resp is None:
            return {
                "summary": (
                    f"ATTED-II co-expression data unavailable for {binomial}. "
                    "Download may have failed — ATTED-II URLs change between versions. "
                    f"Try downloading manually from https://atted.jp and placing at {atted_file}."
                ),
                "gene": gene,
                "species": binomial,
                "coexpressed_genes": [],
                "cluster_size": 0,
                "data_source": "ATTED-II (unavailable)",
                "fallback": True,
            }
        try:
            import gzip
            raw = gzip.decompress(resp.content)
            with open(atted_file, "wb") as fh:
                fh.write(raw)
        except Exception as exc:
            return {
                "summary": f"Failed to decompress ATTED-II data for {binomial}: {exc}",
                "gene": gene,
                "species": binomial,
                "coexpressed_genes": [],
                "cluster_size": 0,
                "data_source": "ATTED-II (decompression failed)",
                "fallback": True,
                "error": str(exc),
            }

    # Parse ATTED-II file
    import pandas as pd

    try:
        df = pd.read_csv(
            atted_file,
            sep="\t",
            header=None,
            names=["gene_a", "gene_b", "mr_score"],
            comment="#",
            usecols=[0, 1, 2],
        )
        # Ensure mr_score is numeric
        df["mr_score"] = pd.to_numeric(df["mr_score"], errors="coerce")
        df = df.dropna(subset=["mr_score"])
    except Exception as exc:
        # Try alternative: single-column layout or different separator
        try:
            df = pd.read_csv(atted_file, sep=r"\s+", header=None, comment="#")
            df = df.iloc[:, :3]
            df.columns = ["gene_a", "gene_b", "mr_score"]
            df["mr_score"] = pd.to_numeric(df["mr_score"], errors="coerce")
            df = df.dropna(subset=["mr_score"])
        except Exception as exc2:
            return {
                "summary": f"Failed to parse ATTED-II data: {exc2}",
                "gene": gene,
                "species": binomial,
                "coexpressed_genes": [],
                "cluster_size": 0,
                "data_source": "ATTED-II (parse failed)",
                "fallback": True,
                "error": str(exc2),
            }

    # Filter rows involving the query gene
    gene_upper = gene.upper()
    mask = (df["gene_a"].str.upper() == gene_upper) | (df["gene_b"].str.upper() == gene_upper)
    gene_df = df[mask].copy()

    if gene_df.empty:
        result = {
            "summary": (
                f"No co-expression data found for {gene} in ATTED-II ({binomial}). "
                "Ensure gene locus code format (e.g. AT5G10140, not gene symbol)."
            ),
            "gene": gene,
            "species": binomial,
            "taxon_id": taxon_id,
            "top_n": top_n,
            "mr_threshold": mr_threshold,
            "coexpressed_genes": [],
            "cluster_size": 0,
            "data_source": "ATTED-II",
        }
        set_cached("atted_coexp", cache_key, result)
        return result

    # Determine the partner gene for each row
    coexpressed = []
    for _, row in gene_df.iterrows():
        gene_a = str(row["gene_a"]).upper()
        gene_b = str(row["gene_b"]).upper()
        partner = str(row["gene_b"]) if gene_a == gene_upper else str(row["gene_a"])
        coexpressed.append({"partner": partner, "mr_score": float(row["mr_score"])})

    # Sort by MR score ascending (lower = stronger co-expression)
    coexpressed.sort(key=lambda x: x["mr_score"])
    coexpressed = coexpressed[:top_n]

    # Compute cluster membership
    cluster_count = sum(1 for c in coexpressed if c["mr_score"] <= mr_threshold)

    result = {
        "summary": (
            f"Found {len(coexpressed)} co-expression partner(s) for {gene} in {binomial} "
            f"(ATTED-II, top {top_n}, MR threshold {mr_threshold})."
        ),
        "gene": gene,
        "species": binomial,
        "taxon_id": taxon_id,
        "top_n": top_n,
        "mr_threshold": mr_threshold,
        "coexpressed_genes": coexpressed,
        "cluster_size": cluster_count,
        "data_source": "ATTED-II",
    }
    set_cached("atted_coexp", cache_key, result)
    return result
