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


# ---------------------------------------------------------------------------
# TestOrthologMap
# ---------------------------------------------------------------------------


class TestOrthologMap:
    """Tests for genomics.ortholog_map."""

    # ------------------------------------------------------------------
    # 1. Successful ortholog lookup
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon")
    def test_success(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        # First call: source species taxon; second call: target species taxon
        mock_taxon.side_effect = [3702, 4530]
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),  # gene lookup
            (
                {
                    "data": [
                        {
                            "homologies": [
                                {
                                    "type": "ortholog_one2one",
                                    "target": {
                                        "id": "Os06g0486700",
                                        "species": "oryza_sativa",
                                        "perc_id": 42.5,
                                        "perc_pos": 55.0,
                                    },
                                }
                            ]
                        }
                    ]
                },
                None,
            ),
        ]
        result = _genomics_module.ortholog_map(gene="FLC", species="Arabidopsis thaliana")

        assert result["ortholog_count"] == 1
        assert result["orthologs"][0]["gene_id"] == "Os06g0486700"
        assert result["orthologs"][0]["orthology_type"] == "ortholog_one2one"
        assert isinstance(result["orthologs"][0]["phylo_weight"], float)
        assert 0.0 <= result["orthologs"][0]["phylo_weight"] <= 1.0
        assert result["orthologs"][0]["percent_identity"] == 42.5

    # ------------------------------------------------------------------
    # 2. compara=plants is passed in Ensembl Compara API call
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon")
    def test_compara_plants_param(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_taxon.side_effect = [3702, 4530]
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),
            ({"data": [{"homologies": []}]}, None),
        ]
        _genomics_module.ortholog_map(gene="FLC", species="Arabidopsis thaliana")

        # Second request_json call is the Compara homology lookup
        second_call_kwargs = mock_request_json.call_args_list[1]
        # params may be passed as positional or keyword
        call_kwargs = second_call_kwargs[1] if second_call_kwargs[1] else {}
        call_args = second_call_kwargs[0] if second_call_kwargs[0] else ()
        # Extract params from call (passed as keyword arg)
        params_passed = call_kwargs.get("params", {})
        assert params_passed.get("compara") == "plants", (
            "compara=plants MUST be present in Ensembl Compara API call"
        )

    # ------------------------------------------------------------------
    # 3. Empty homology response
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_empty_response(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),
            ({"data": [{"homologies": []}]}, None),
        ]
        result = _genomics_module.ortholog_map(gene="FLC", species="Arabidopsis thaliana")

        assert result["ortholog_count"] == 0
        assert "No orthologs" in result["summary"]

    # ------------------------------------------------------------------
    # 4. target_species filter is passed to API
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_target_species_filter(
        self,
        mock_taxon,
        mock_binomial,
        mock_request_json,
        mock_get_cached,
        mock_set_cached,
    ):
        # First call: source species binomial; second call: target species binomial
        mock_binomial.side_effect = ["Arabidopsis thaliana", "Oryza sativa"]
        mock_request_json.side_effect = [
            ({"id": "AT5G10140"}, None),
            ({"data": [{"homologies": []}]}, None),
        ]
        _genomics_module.ortholog_map(
            gene="FLC", species="Arabidopsis thaliana", target_species="rice"
        )

        second_call_kwargs = mock_request_json.call_args_list[1][1]
        params_passed = second_call_kwargs.get("params", {})
        assert params_passed.get("target_species") == "oryza_sativa", (
            "target_species should be passed as lowercase underscore form"
        )

    # ------------------------------------------------------------------
    # 5. Unknown source species without force returns error
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        result = _genomics_module.ortholog_map(gene="FLC", species="martian_grass")

        assert "error" in result
        assert "Unknown species" in result["error"]

    # ------------------------------------------------------------------
    # 6. Cache hit skips API calls
    # ------------------------------------------------------------------
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._api_cache.get_cached", return_value={"summary": "cached", "ortholog_count": 0})
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_cache_hit(self, mock_taxon, mock_binomial, mock_get_cached, mock_request_json):
        result = _genomics_module.ortholog_map(gene="FLC", species="Arabidopsis thaliana")

        mock_request_json.assert_not_called()
        assert result == {"summary": "cached", "ortholog_count": 0}


# ---------------------------------------------------------------------------
# Standalone _phylo_weight tests
# ---------------------------------------------------------------------------


def test_phylo_weight_known_pair():
    """Verify distance matrix values and weight formula for known pairs."""
    from ct.tools.genomics import _phylo_weight

    # Arabidopsis-rice: 150 Mya → 1/(1+1.5) = 0.4
    arab_rice = _phylo_weight(3702, 4530)
    assert abs(arab_rice - 0.4) < 0.001, f"Expected ~0.4, got {arab_rice}"

    # Same species → 1.0
    assert _phylo_weight(3702, 3702) == 1.0

    # Maize-sorghum: 12 Mya → 1/(1+0.12) ≈ 0.893 (very close, > 0.8)
    maize_sorghum = _phylo_weight(4577, 4558)
    assert maize_sorghum > 0.8, f"Expected > 0.8, got {maize_sorghum}"


def test_phylo_weight_unknown_pair():
    """Unknown pair defaults to 200 Mya → weight ~0.333."""
    from ct.tools.genomics import _phylo_weight

    # Human (9606) vs Arabidopsis (3702) — not in matrix, defaults to 200 Mya
    # 1/(1+2.0) = 0.333...
    weight = _phylo_weight(9606, 3702)
    assert abs(weight - 0.333) < 0.001, f"Expected ~0.333, got {weight}"


# ---------------------------------------------------------------------------
# Registration check for ortholog_map
# ---------------------------------------------------------------------------


def test_ortholog_map_registered():
    """Verify genomics.ortholog_map is in the registry with correct category."""
    t = registry.get_tool("genomics.ortholog_map")
    assert t is not None, "genomics.ortholog_map not found in registry"
    assert t.category == "genomics"
