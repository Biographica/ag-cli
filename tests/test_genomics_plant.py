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
    """All 5 Phase 4 tools are registered under the genomics category in the plant allowlist."""
    from ct.tools import PLANT_SCIENCE_CATEGORIES

    t1 = registry.get_tool("genomics.gene_annotation")
    t2 = registry.get_tool("genomics.gwas_qtl_lookup")
    t3 = registry.get_tool("genomics.ortholog_map")
    t4 = registry.get_tool("genomics.gff_parse")
    t5 = registry.get_tool("genomics.coexpression_network")

    assert t1 is not None, "genomics.gene_annotation not found in registry"
    assert t1.category == "genomics"
    assert t2 is not None, "genomics.gwas_qtl_lookup not found in registry"
    assert t2.category == "genomics"
    assert t3 is not None, "genomics.ortholog_map not found in registry"
    assert t3.category == "genomics"
    assert t4 is not None, "genomics.gff_parse not found in registry"
    assert t4.category == "genomics"
    assert t5 is not None, "genomics.coexpression_network not found in registry"
    assert t5.category == "genomics"
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


# ---------------------------------------------------------------------------
# TestGffParse
# ---------------------------------------------------------------------------


class TestGffParse:
    """Tests for genomics.gff_parse."""

    # ------------------------------------------------------------------
    # 1. Local file success — 2-exon gene, UTRs, intron
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_local_file_success(self, mock_taxon, mock_binomial):
        from pathlib import Path

        fixture = str(Path(__file__).parent / "fixtures" / "FLC_mini.gff3")
        result = _genomics_module.gff_parse(
            gene="FLC",
            species="Arabidopsis thaliana",
            gff_path=fixture,
        )
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["total_exons"] == 2
        assert isinstance(result["exons"], list) and len(result["exons"]) == 2
        for exon in result["exons"]:
            assert "start" in exon and "end" in exon and "length" in exon
        assert result["total_introns"] == 1
        assert "start" in result["introns"][0]
        assert "end" in result["introns"][0]
        assert "length" in result["introns"][0]
        assert result["introns"][0]["length"] > 0
        assert result["chromosome"] == "5"
        assert result["strand"] == "-"
        assert "exon" in result["summary"]

    # ------------------------------------------------------------------
    # 2. Intron computation — start/end values match exon gap
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_intron_computation(self, mock_taxon, mock_binomial):
        from pathlib import Path

        fixture = str(Path(__file__).parent / "fixtures" / "FLC_mini.gff3")
        result = _genomics_module.gff_parse(
            gene="FLC",
            species="Arabidopsis thaliana",
            gff_path=fixture,
        )
        assert result["total_introns"] == 1
        exons = result["exons"]
        intron = result["introns"][0]
        # Intron is the gap between the two sorted exons
        # exon[0] is the lower-coordinate exon, exon[1] is the higher
        exon_ends = sorted([e["end"] for e in exons])
        exon_starts = sorted([e["start"] for e in exons])
        # The intron start = end of lower exon + 1, intron end = start of upper exon - 1
        assert intron["start"] == exon_ends[0] + 1
        assert intron["end"] == exon_starts[1] - 1

    # ------------------------------------------------------------------
    # 3. Name attribute fallback — FLC looked up by Name not ID
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_name_fallback(self, mock_taxon, mock_binomial):
        from pathlib import Path

        fixture = str(Path(__file__).parent / "fixtures" / "FLC_mini.gff3")
        # "FLC" is the Name attribute, not the ID (which is "gene:AT5G10140")
        # The tool should find the gene via Name attribute fallback
        result = _genomics_module.gff_parse(
            gene="FLC",
            species="Arabidopsis thaliana",
            gff_path=fixture,
        )
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["total_exons"] >= 1

    # ------------------------------------------------------------------
    # 4. Gene not found returns error dict
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_gene_not_found(self, mock_taxon, mock_binomial):
        from pathlib import Path

        fixture = str(Path(__file__).parent / "fixtures" / "FLC_mini.gff3")
        result = _genomics_module.gff_parse(
            gene="NONEXISTENT_GENE",
            species="Arabidopsis thaliana",
            gff_path=fixture,
        )
        assert "error" in result
        assert "not found" in result["error"].lower() or "not found" in result["summary"].lower()

    # ------------------------------------------------------------------
    # 5. Auto-download — request called with Ensembl Plants URL
    # ------------------------------------------------------------------
    @patch("ct.tools.http_client.request")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_auto_download(self, mock_taxon, mock_binomial, mock_request, tmp_path):
        import gzip
        from pathlib import Path
        from unittest.mock import MagicMock

        # Read the real fixture content and compress it
        fixture = Path(__file__).parent / "fixtures" / "FLC_mini.gff3"
        with open(fixture, "rb") as fh:
            gff_bytes = fh.read()
        compressed = gzip.compress(gff_bytes)

        # Mock the HTTP response
        mock_resp = MagicMock()
        mock_resp.content = compressed
        mock_resp.status_code = 200
        mock_request.return_value = (mock_resp, None)

        # Patch _CACHE_BASE to use tmp_path so no real files are written
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.gff_parse(
                gene="FLC",
                species="Arabidopsis thaliana",
                # No gff_path — auto-download path
            )

        # Verify request was called with an Ensembl URL
        assert mock_request.called
        call_url = mock_request.call_args[0][1]
        assert "ensemblgenomes.ebi.ac.uk" in call_url
        # Verify we got gene structure from the decompressed file
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["total_exons"] >= 1

    # ------------------------------------------------------------------
    # 6. Unknown species without force returns error
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        from pathlib import Path

        fixture = str(Path(__file__).parent / "fixtures" / "FLC_mini.gff3")
        result = _genomics_module.gff_parse(
            gene="FLC",
            species="martian_grass",
            gff_path=fixture,
        )
        assert "error" in result
        assert "Unknown species" in result["error"]


# ---------------------------------------------------------------------------
# TestCoexpressionNetwork
# ---------------------------------------------------------------------------

_ATTED_SAMPLE_TSV = b"""AT5G10140\tAT3G24440\t2.5
AT5G10140\tAT1G65480\t8.3
AT5G10140\tAT2G45660\t15.0
AT5G10140\tAT4G00650\t45.0
AT1G01010\tAT1G01020\t3.0
"""


class TestCoexpressionNetwork:
    """Tests for genomics.coexpression_network."""

    def _write_atted_file(self, tmp_path, content: bytes = _ATTED_SAMPLE_TSV):
        """Create a mock ATTED-II file in tmp_path/atted/."""
        atted_dir = tmp_path / "atted"
        atted_dir.mkdir(parents=True, exist_ok=True)
        atted_file = atted_dir / "arabidopsis_thaliana_coexp.tsv"
        atted_file.write_bytes(content)
        return atted_file

    # ------------------------------------------------------------------
    # 1. Arabidopsis success — correct partners, cluster membership
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_arabidopsis_success(
        self, mock_taxon, mock_binomial, mock_get_cached, mock_set_cached, tmp_path
    ):
        self._write_atted_file(tmp_path)
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.coexpression_network(
                gene="AT5G10140",
                species="Arabidopsis thaliana",
                top_n=20,
                mr_threshold=30.0,
            )
        assert "error" not in result
        # 4 rows involve AT5G10140 (last row AT1G01010 is excluded)
        assert len(result["coexpressed_genes"]) == 4
        # First entry has lowest MR score (strongest co-expression)
        assert result["coexpressed_genes"][0]["mr_score"] == 2.5
        # cluster_size = entries with MR <= 30.0: 2.5, 8.3, 15.0 (45.0 excluded)
        assert result["cluster_size"] == 3

    # ------------------------------------------------------------------
    # 2. Download fallback — request failure returns fallback dict
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request", return_value=(None, "Connection error"))
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_download_fallback(
        self, mock_taxon, mock_binomial, mock_request, mock_get_cached, tmp_path
    ):
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.coexpression_network(
                gene="AT5G10140",
                species="Arabidopsis thaliana",
            )
        assert result.get("fallback") is True
        assert result["coexpressed_genes"] == []

    # ------------------------------------------------------------------
    # 3. MR threshold filtering — only genes below threshold in cluster
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_mr_threshold(
        self, mock_taxon, mock_binomial, mock_get_cached, mock_set_cached, tmp_path
    ):
        self._write_atted_file(tmp_path)
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.coexpression_network(
                gene="AT5G10140",
                species="Arabidopsis thaliana",
                mr_threshold=10.0,
            )
        # Only 2.5 and 8.3 are <= 10.0
        assert result["cluster_size"] == 2

    # ------------------------------------------------------------------
    # 4. Gene not in data — empty coexpressed_genes, informative summary
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_gene_not_found_in_data(
        self, mock_taxon, mock_binomial, mock_get_cached, mock_set_cached, tmp_path
    ):
        self._write_atted_file(tmp_path)
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.coexpression_network(
                gene="AT9G99999",
                species="Arabidopsis thaliana",
            )
        assert result["coexpressed_genes"] == []
        assert "No co-expression data found" in result["summary"]

    # ------------------------------------------------------------------
    # 5. top_n limit — returns at most top_n entries
    # ------------------------------------------------------------------
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_top_n_limit(
        self, mock_taxon, mock_binomial, mock_get_cached, mock_set_cached, tmp_path
    ):
        # 10 rows for the query gene
        rows = "\n".join(
            f"AT5G10140\tAT1G{i:05d}\t{float(i)}" for i in range(1, 11)
        ).encode()
        self._write_atted_file(tmp_path, content=rows)
        with patch("ct.tools._api_cache._CACHE_BASE", tmp_path):
            result = _genomics_module.coexpression_network(
                gene="AT5G10140",
                species="Arabidopsis thaliana",
                top_n=3,
            )
        assert len(result["coexpressed_genes"]) == 3

    # ------------------------------------------------------------------
    # 6. Unknown species without force returns error
    # ------------------------------------------------------------------
    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        result = _genomics_module.coexpression_network(
            gene="AT5G10140",
            species="martian_grass",
        )
        assert "error" in result
        assert "Unknown species" in result["error"]
