"""
Unit tests for genomics.gene_annotation and genomics.gwas_qtl_lookup.

All external dependencies are mocked at the source module level (Phase 3
convention) — no network calls are made.  Mock targets follow the pattern
established in Phase 3:

    @patch("ct.tools._species.resolve_species_taxon")   # correct
    @patch("ct.tools.genomics.request_json")            # WRONG — lazy import
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

# Import the module and functions directly so tests call them with mocks in place.
import ct.tools.genomics as _genomics_module
from ct.tools import ensure_loaded, registry


# Ensure module is loaded once — registers all tools.
ensure_loaded()


# ---------------------------------------------------------------------------
# Helpers — pre-built mock API responses
# ---------------------------------------------------------------------------

_ENSEMBL_GENE_RESPONSE = (
    {
        "id": "AT5G10140",
        "display_name": "FLC",
        "description": "MADS-box protein FLOWERING LOCUS C",
        "biotype": "protein_coding",
        "seq_region_name": "5",
        "start": 3173498,
        "end": 3179449,
        "strand": -1,
    },
    None,  # no error
)

_ENSEMBL_GO_RESPONSE = (
    [
        {
            "primary_id": "GO:0003700",
            "description": "DNA-binding transcription factor activity",
            "info_type": "DEPENDENT",
        }
    ],
    None,
)

_UNIPROT_RESPONSE = (
    {
        "results": [
            {
                "uniProtKBCrossReferences": [
                    {
                        "database": "GO",
                        "id": "GO:0003700",
                        "properties": [
                            {
                                "key": "GoTerm",
                                "value": "F:DNA-binding transcription factor activity",
                            }
                        ],
                    }
                ],
                "references": [
                    {
                        "citation": {
                            "title": "FLC function",
                            "citationCrossReferences": [
                                {"database": "PubMed", "id": "12345678"}
                            ],
                        }
                    }
                ],
                "comments": [
                    {
                        "commentType": "FUNCTION",
                        "texts": [{"value": "Transcription factor controlling flowering time"}],
                    }
                ],
            }
        ]
    },
    None,
)


# ---------------------------------------------------------------------------
# TestGeneAnnotation
# ---------------------------------------------------------------------------


class TestGeneAnnotation:
    """Tests for genomics.gene_annotation."""

    # ------------------------------------------------------------------
    # 1. Arabidopsis success path
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_arabidopsis_success(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            _ENSEMBL_GENE_RESPONSE,
            _ENSEMBL_GO_RESPONSE,
            _UNIPROT_RESPONSE,
        ]
        result = _genomics_module.gene_annotation(gene="FLC", species="Arabidopsis thaliana")

        assert "GO terms" in result["summary"]
        assert result["ensembl_id"] == "AT5G10140"
        assert isinstance(result["go_terms"], list)
        assert len(result["go_terms"]) > 0
        assert any(t["go_id"] == "GO:0003700" for t in result["go_terms"])
        assert isinstance(result["pubmed_ids"], list)
        assert len(result["pubmed_ids"]) > 0
        mock_set_cached.assert_called_once()

    # ------------------------------------------------------------------
    # 2. Unknown species without force
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        result = _genomics_module.gene_annotation(gene="FLC", species="martian_grass")

        assert "error" in result
        assert "Unknown species" in result["error"]

    # ------------------------------------------------------------------
    # 3. force=True overrides unknown species
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="")
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_force_override(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            _ENSEMBL_GENE_RESPONSE,
            _ENSEMBL_GO_RESPONSE,
            _UNIPROT_RESPONSE,
        ]
        result = _genomics_module.gene_annotation(gene="FLC", species="novelplant", force=True)

        assert "error" not in result
        assert mock_request_json.called

    # ------------------------------------------------------------------
    # 4. PubMed IDs present in result
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_pubmed_ids_present(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            _ENSEMBL_GENE_RESPONSE,
            _ENSEMBL_GO_RESPONSE,
            _UNIPROT_RESPONSE,
        ]
        result = _genomics_module.gene_annotation(gene="FLC", species="Arabidopsis thaliana")

        pmids = result["pubmed_ids"]
        assert any(p["pmid"] == "12345678" for p in pmids)
        assert any(p.get("title") == "FLC function" for p in pmids)

    # ------------------------------------------------------------------
    # 5. Cache hit skips API calls
    # ------------------------------------------------------------------
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._api_cache.get_cached", return_value={"summary": "cached", "gene": "FLC"})
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_cache_hit(self, mock_taxon, mock_binomial, mock_get_cached, mock_request_json):
        result = _genomics_module.gene_annotation(gene="FLC", species="Arabidopsis thaliana")

        mock_request_json.assert_not_called()
        assert result == {"summary": "cached", "gene": "FLC"}

    # ------------------------------------------------------------------
    # 6. Ensembl lookup failure returns error
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json", return_value=(None, "404 Not Found"))
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_ensembl_lookup_failure(
        self, mock_taxon, mock_binomial, mock_request_json, mock_get_cached, mock_set_cached
    ):
        result = _genomics_module.gene_annotation(gene="UNKNOWNGENE", species="Arabidopsis thaliana")

        assert "error" in result
        assert "not found" in result["summary"].lower() or "Not found" in result.get("error", "")


# ---------------------------------------------------------------------------
# TestGwasQtlLookup
# ---------------------------------------------------------------------------


class TestGwasQtlLookup:
    """Tests for genomics.gwas_qtl_lookup."""

    # ------------------------------------------------------------------
    # 1. Successful lookup
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_success(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),  # gene lookup
            (
                [{"description": "Flowering time", "source": "TAIR", "pubmed_id": "98765432", "attributes": {}}],
                None,
            ),  # phenotype/gene
        ]
        result = _genomics_module.gwas_qtl_lookup(gene="FLC", species="Arabidopsis thaliana")

        assert result["phenotype_count"] == 1
        assert result["phenotypes"][0]["description"] == "Flowering time"
        assert "error" not in result

    # ------------------------------------------------------------------
    # 2. Trait keyword filtering
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_trait_filter(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),
            (
                [
                    {"description": "Flowering time", "source": "TAIR", "pubmed_id": "111", "attributes": {}},
                    {"description": "Root length", "source": "TAIR", "pubmed_id": "", "attributes": {}},
                ],
                None,
            ),
        ]
        result = _genomics_module.gwas_qtl_lookup(gene="FLC", species="Arabidopsis thaliana", trait="flowering")

        assert result["phenotype_count"] == 1
        assert "Flowering" in result["phenotypes"][0]["description"]

    # ------------------------------------------------------------------
    # 3. Empty result for non-Arabidopsis species — cross-species suggestion
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Oryza sativa")
    @patch("ct.tools._species.resolve_species_taxon", return_value=4530)
    def test_empty_with_suggestion(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            ({"id": "Os01g0979200"}, None),
            ([], None),  # empty phenotype list
        ]
        result = _genomics_module.gwas_qtl_lookup(gene="GW5", species="Oryza sativa")

        assert result["phenotype_count"] == 0
        assert "Arabidopsis" in result["suggestion"]

    # ------------------------------------------------------------------
    # 4. Empty result for Arabidopsis — sparser-than-human suggestion
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_empty_arabidopsis(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),
            ([], None),
        ]
        result = _genomics_module.gwas_qtl_lookup(gene="FLC", species="Arabidopsis thaliana")

        assert result["phenotype_count"] == 0
        assert "sparser than for human diseases" in result["suggestion"]

    # ------------------------------------------------------------------
    # 5. Unknown species without force
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        result = _genomics_module.gwas_qtl_lookup(gene="GW5", species="martian_grass")

        assert "error" in result

    # ------------------------------------------------------------------
    # 6. Cache hit skips API calls
    # ------------------------------------------------------------------
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._api_cache.get_cached", return_value={"summary": "cached", "phenotype_count": 0})
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_cache_hit(self, mock_taxon, mock_binomial, mock_get_cached, mock_request_json):
        result = _genomics_module.gwas_qtl_lookup(gene="FLC", species="Arabidopsis thaliana")

        mock_request_json.assert_not_called()
        assert result["phenotype_count"] == 0


# ---------------------------------------------------------------------------
# Standalone registration test
# ---------------------------------------------------------------------------


def test_all_tools_registered():
    """Both tools are registered under the genomics category in the plant allowlist."""
    from ct.tools import PLANT_SCIENCE_CATEGORIES

    t1 = registry.get_tool("genomics.gene_annotation")
    t2 = registry.get_tool("genomics.gwas_qtl_lookup")

    assert t1 is not None, "genomics.gene_annotation not found in registry"
    assert t1.category == "genomics"
    assert t2 is not None, "genomics.gwas_qtl_lookup not found in registry"
    assert t2.category == "genomics"
    assert "genomics" in PLANT_SCIENCE_CATEGORIES
