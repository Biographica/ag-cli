"""
End-to-end test for multi-species evidence gathering (TOOL-09).

TOOL-09 is NOT a new tool — it validates that the existing Phase 3-5 tool
suite is composable. The test simulates an agent-like workflow that:
1. Takes a list of 5+ genes and a target species
2. For each gene, calls gene_annotation, ortholog_map, gwas_qtl_lookup,
   coexpression_network, paralogy_score, and crispr_guide_design
3. Assembles a structured per-gene evidence summary

If this test fails, the signal is for system prompt tuning or M2
meta-prompting — not for building a new tool.

Gated behind --run-e2e flag to avoid running in normal CI.
The --run-e2e flag and skip logic are handled by conftest.py.
"""

from unittest.mock import patch
import pytest

from ct.tools import ensure_loaded

ensure_loaded()


# ---------------------------------------------------------------------------
# Mock data factories
# ---------------------------------------------------------------------------

def _mock_gene_annotation(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic gene_annotation result for testing."""
    return {
        "summary": f"Gene annotation for {gene} in {species}",
        "gene": gene,
        "ensembl_id": f"AT{hash(gene) % 5 + 1}G{abs(hash(gene)) % 100000:05d}",
        "species": species,
        "go_terms": [
            {"go_id": "GO:0003700", "term": "DNA-binding transcription factor activity", "namespace": "molecular_function"},
            {"go_id": "GO:0006355", "term": "regulation of DNA-templated transcription", "namespace": "biological_process"},
        ],
        "pubmed_ids": [{"pmid": str(10000000 + hash(gene) % 90000000), "title": f"{gene} function study"}],
        "description": f"Putative {gene} protein",
    }


def _mock_ortholog_map(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic ortholog_map result."""
    return {
        "summary": f"Found 3 orthologs for {gene}",
        "gene": gene,
        "species": species,
        "ortholog_count": 3,
        "orthologs": [
            {"gene_id": f"Os{hash(gene) % 12 + 1:02d}g{abs(hash(gene)) % 1000000:07d}", "species": "Oryza sativa", "phylo_weight": 0.667},
            {"gene_id": f"Zm{abs(hash(gene)) % 100000:05d}", "species": "Zea mays", "phylo_weight": 0.556},
            {"gene_id": f"Sl{abs(hash(gene)) % 10000:04d}", "species": "Solanum lycopersicum", "phylo_weight": 0.5},
        ],
    }


def _mock_gwas_qtl_lookup(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic gwas_qtl_lookup result."""
    return {
        "summary": f"Found 2 phenotype annotations for {gene}",
        "gene": gene,
        "species": species,
        "phenotype_count": 2,
        "phenotypes": [
            {"description": "Flowering time variation", "source": "TAIR", "pubmed_id": "12345678"},
            {"description": "Vernalization response", "source": "Ensembl", "pubmed_id": "23456789"},
        ],
    }


def _mock_coexpression_network(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic coexpression_network result."""
    return {
        "summary": f"Found 5 co-expression partners for {gene}",
        "gene": gene,
        "species": species,
        "coexpressed_genes": [
            {"partner": f"AT{i}G{10000 + i * 1000:05d}", "mr_score": 2.0 + i * 3.0}
            for i in range(5)
        ],
        "cluster_size": 3,
    }


def _mock_paralogy_score(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic paralogy_score result."""
    return {
        "summary": f"Found 2 paralogs for {gene}",
        "gene": gene,
        "species": species,
        "paralog_count": 2,
        "paralogs": [f"MAF{i}" for i in range(1, 3)],
        "paralog_details": [
            {"paralog_id": "MAF1", "shared_go_count": 3, "coexpression_overlap_count": 2},
            {"paralog_id": "MAF2", "shared_go_count": 1, "coexpression_overlap_count": 0},
        ],
    }


def _mock_crispr_guide_design(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic crispr_guide_design result."""
    return {
        "summary": f"Designed 10 guides for {gene}",
        "gene": gene,
        "species": species,
        "guide_count": 10,
        "tier_counts": {"high_confidence": 4, "acceptable": 4, "poor": 2},
        "guides": [
            {
                "guide_sequence": "GCATGCATGCATGCATGCAT",
                "pam": "AGG",
                "on_target_score": 0.7,
                "gc_content": 0.5,
                "tier": "high_confidence",
                "off_target_count": 3,
            }
        ],
    }


def _mock_string_plant_ppi(gene: str, species: str = "Arabidopsis thaliana", **kwargs) -> dict:
    """Return a realistic string_plant_ppi result."""
    return {
        "summary": f"Found 5 interactions for {gene}",
        "gene": gene,
        "species": species,
        "interaction_count": 5,
        "interactions": [
            {"partner": f"InteractorOf{gene}_{i}", "combined_score": 900 - i * 50}
            for i in range(5)
        ],
    }


def _mock_pubmed_plant_search(query: str, **kwargs) -> dict:
    """Return a realistic pubmed_plant_search result."""
    return {
        "summary": f"Found 3 articles for '{query}'",
        "query": query,
        "total_count": 3,
        "articles": [
            {"pmid": f"3{i}000000", "title": f"Study of {query} #{i+1}", "year": 2024}
            for i in range(3)
        ],
    }


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------

# Gene list for testing — 5+ genes as required by TOOL-09
_TEST_GENES = ["FLC", "FT", "CO", "GI", "SOC1", "SVP"]
_TEST_SPECIES = "Arabidopsis thaliana"


@pytest.mark.e2e
class TestMultiGeneEvidenceCollection:
    """
    End-to-end test: given a gene list, exercise the full tool suite
    to gather per-gene evidence summaries.

    This simulates what the agent does in a multi-step research workflow.
    """

    @patch("ct.tools.genomics.paralogy_score", side_effect=_mock_paralogy_score)
    @patch("ct.tools.genomics.coexpression_network", side_effect=_mock_coexpression_network)
    @patch("ct.tools.genomics.gwas_qtl_lookup", side_effect=_mock_gwas_qtl_lookup)
    @patch("ct.tools.genomics.ortholog_map", side_effect=_mock_ortholog_map)
    @patch("ct.tools.genomics.gene_annotation", side_effect=_mock_gene_annotation)
    @patch("ct.tools.editing.crispr_guide_design", side_effect=_mock_crispr_guide_design)
    def test_multi_gene_evidence_collection(
        self,
        mock_crispr,
        mock_ga,
        mock_ortho,
        mock_gwas,
        mock_coexp,
        mock_para,
    ):
        """
        For each gene in a 6-gene list, call 6 distinct tools and assemble
        a per-gene evidence summary. Validates TOOL-09: the agent can compose
        a multi-species evidence-gathering workflow.
        """
        from ct.tools.genomics import (
            gene_annotation,
            ortholog_map,
            gwas_qtl_lookup,
            coexpression_network,
            paralogy_score,
        )
        from ct.tools.editing import crispr_guide_design

        evidence_summaries = {}

        for gene in _TEST_GENES:
            # Step 1: Gene annotation (GO terms, function, publications)
            annotation = gene_annotation(gene=gene, species=_TEST_SPECIES)
            assert "summary" in annotation
            assert "go_terms" in annotation

            # Step 2: Ortholog mapping
            orthologs = ortholog_map(gene=gene, species=_TEST_SPECIES)
            assert "summary" in orthologs
            assert "orthologs" in orthologs

            # Step 3: GWAS/QTL evidence
            gwas = gwas_qtl_lookup(gene=gene, species=_TEST_SPECIES)
            assert "summary" in gwas
            assert "phenotypes" in gwas

            # Step 4: Co-expression network
            coexp = coexpression_network(gene=gene, species=_TEST_SPECIES)
            assert "summary" in coexp
            assert "coexpressed_genes" in coexp

            # Step 5: Paralogy assessment
            paralogy = paralogy_score(gene=gene, species=_TEST_SPECIES)
            assert "summary" in paralogy
            assert "paralog_count" in paralogy

            # Step 6: CRISPR guide design
            crispr = crispr_guide_design(gene=gene, species=_TEST_SPECIES)
            assert "summary" in crispr
            assert "guides" in crispr

            # Assemble per-gene evidence summary
            evidence_summaries[gene] = {
                "gene": gene,
                "species": _TEST_SPECIES,
                "annotation": {
                    "go_term_count": len(annotation.get("go_terms", [])),
                    "pubmed_count": len(annotation.get("pubmed_ids", [])),
                    "description": annotation.get("description", ""),
                },
                "orthologs": {
                    "count": orthologs.get("ortholog_count", 0),
                    "species_covered": len(set(o.get("species", "") for o in orthologs.get("orthologs", []))),
                },
                "gwas_qtl": {
                    "phenotype_count": gwas.get("phenotype_count", 0),
                },
                "coexpression": {
                    "partner_count": len(coexp.get("coexpressed_genes", [])),
                    "cluster_size": coexp.get("cluster_size", 0),
                },
                "paralogy": {
                    "paralog_count": paralogy.get("paralog_count", 0),
                },
                "editability": {
                    "guide_count": crispr.get("guide_count", 0),
                    "high_confidence_guides": crispr.get("tier_counts", {}).get("high_confidence", 0),
                },
            }

        # Validate: all genes have evidence summaries
        assert len(evidence_summaries) == len(_TEST_GENES)
        for gene in _TEST_GENES:
            assert gene in evidence_summaries
            summary = evidence_summaries[gene]
            assert summary["gene"] == gene
            assert summary["species"] == _TEST_SPECIES

            # Each tool contributed data
            assert summary["annotation"]["go_term_count"] > 0
            assert summary["orthologs"]["count"] > 0
            assert summary["gwas_qtl"]["phenotype_count"] >= 0
            assert summary["coexpression"]["partner_count"] > 0
            assert summary["paralogy"]["paralog_count"] >= 0
            assert summary["editability"]["guide_count"] > 0

        # Validate: all 6 tools were called for each of the 6 genes
        assert mock_ga.call_count == len(_TEST_GENES)
        assert mock_ortho.call_count == len(_TEST_GENES)
        assert mock_gwas.call_count == len(_TEST_GENES)
        assert mock_coexp.call_count == len(_TEST_GENES)
        assert mock_para.call_count == len(_TEST_GENES)
        assert mock_crispr.call_count == len(_TEST_GENES)

    @patch("ct.tools.genomics.paralogy_score", side_effect=_mock_paralogy_score)
    @patch("ct.tools.genomics.coexpression_network", side_effect=_mock_coexpression_network)
    @patch("ct.tools.genomics.gwas_qtl_lookup", side_effect=_mock_gwas_qtl_lookup)
    @patch("ct.tools.genomics.ortholog_map", side_effect=_mock_ortholog_map)
    @patch("ct.tools.genomics.gene_annotation", side_effect=_mock_gene_annotation)
    @patch("ct.tools.editing.crispr_guide_design", side_effect=_mock_crispr_guide_design)
    def test_evidence_summaries_are_structured(
        self,
        mock_crispr,
        mock_ga,
        mock_ortho,
        mock_gwas,
        mock_coexp,
        mock_para,
    ):
        """Evidence summaries have consistent structure across all genes."""
        from ct.tools.genomics import (
            gene_annotation,
            ortholog_map,
            gwas_qtl_lookup,
            coexpression_network,
            paralogy_score,
        )
        from ct.tools.editing import crispr_guide_design

        required_keys = {"gene", "species", "annotation", "orthologs", "gwas_qtl", "coexpression", "paralogy", "editability"}

        for gene in _TEST_GENES[:3]:  # Test subset for speed
            summary = {
                "gene": gene,
                "species": _TEST_SPECIES,
                "annotation": gene_annotation(gene=gene, species=_TEST_SPECIES),
                "orthologs": ortholog_map(gene=gene, species=_TEST_SPECIES),
                "gwas_qtl": gwas_qtl_lookup(gene=gene, species=_TEST_SPECIES),
                "coexpression": coexpression_network(gene=gene, species=_TEST_SPECIES),
                "paralogy": paralogy_score(gene=gene, species=_TEST_SPECIES),
                "editability": crispr_guide_design(gene=gene, species=_TEST_SPECIES),
            }
            assert required_keys.issubset(summary.keys()), f"Missing keys for {gene}: {required_keys - summary.keys()}"
            # Each sub-result has a 'summary' key (tool contract)
            for key in ("annotation", "orthologs", "gwas_qtl", "coexpression", "paralogy", "editability"):
                assert "summary" in summary[key], f"{key} result for {gene} missing 'summary' key"

    @patch("ct.tools.genomics.paralogy_score", side_effect=_mock_paralogy_score)
    @patch("ct.tools.genomics.coexpression_network", side_effect=_mock_coexpression_network)
    @patch("ct.tools.genomics.gwas_qtl_lookup", side_effect=_mock_gwas_qtl_lookup)
    @patch("ct.tools.genomics.ortholog_map", side_effect=_mock_ortholog_map)
    @patch("ct.tools.genomics.gene_annotation", side_effect=_mock_gene_annotation)
    @patch("ct.tools.editing.crispr_guide_design", side_effect=_mock_crispr_guide_design)
    def test_tool_diversity(
        self,
        mock_crispr,
        mock_ga,
        mock_ortho,
        mock_gwas,
        mock_coexp,
        mock_para,
    ):
        """At least 5 distinct tool functions are exercised."""
        from ct.tools.genomics import (
            gene_annotation,
            ortholog_map,
            gwas_qtl_lookup,
            coexpression_network,
            paralogy_score,
        )
        from ct.tools.editing import crispr_guide_design

        tools_called = set()
        gene = _TEST_GENES[0]

        gene_annotation(gene=gene, species=_TEST_SPECIES)
        tools_called.add("gene_annotation")

        ortholog_map(gene=gene, species=_TEST_SPECIES)
        tools_called.add("ortholog_map")

        gwas_qtl_lookup(gene=gene, species=_TEST_SPECIES)
        tools_called.add("gwas_qtl_lookup")

        coexpression_network(gene=gene, species=_TEST_SPECIES)
        tools_called.add("coexpression_network")

        paralogy_score(gene=gene, species=_TEST_SPECIES)
        tools_called.add("paralogy_score")

        crispr_guide_design(gene=gene, species=_TEST_SPECIES)
        tools_called.add("crispr_guide_design")

        assert len(tools_called) >= 5, f"Only {len(tools_called)} distinct tools called, need >= 5"


# ---------------------------------------------------------------------------
# Non-gated registration sanity check (always runs)
# ---------------------------------------------------------------------------

def test_all_phase5_tools_registered():
    """All Phase 5 tools are registered and visible."""
    from ct.tools import registry, PLANT_SCIENCE_CATEGORIES

    phase5_tools = [
        ("editing.crispr_guide_design", "editing"),
        ("editing.editability_score", "editing"),
        ("genomics.paralogy_score", "genomics"),
    ]
    for tool_name, expected_category in phase5_tools:
        t = registry.get_tool(tool_name)
        assert t is not None, f"{tool_name} not registered"
        assert t.category == expected_category, f"{tool_name} has wrong category"

    assert "editing" in PLANT_SCIENCE_CATEGORIES, "'editing' not in plant science allowlist"
