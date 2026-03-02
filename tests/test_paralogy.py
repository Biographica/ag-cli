"""Tests for genomics.paralogy_score tool."""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from ct.tools import ensure_loaded, registry
import ct.tools.genomics as _genomics_module

ensure_loaded()


class TestParseOrthofinderParalogs:
    """Tests for _parse_orthofinder_paralogs helper."""

    def test_finds_paralogs_in_same_column(self, tmp_path):
        """Genes in the same species column and row are paralogs."""
        tsv = tmp_path / "Orthogroups.tsv"
        tsv.write_text(
            "Orthogroup\tArabidopsis thaliana\tOryza sativa\n"
            "OG0000001\tAT5G10140, AT3G24440, AT1G77080\tOs01g0100100\n"
            "OG0000002\tAT1G01010\tOs02g0200200\n"
        )
        result = _genomics_module._parse_orthofinder_paralogs(
            gene="AT5G10140",
            species_col="Arabidopsis thaliana",
            orthogroups_tsv=str(tsv),
        )
        assert "AT3G24440" in result
        assert "AT1G77080" in result
        assert "AT5G10140" not in result  # Query gene excluded
        assert len(result) == 2

    def test_gene_not_found(self, tmp_path):
        """Gene not in any row returns empty list."""
        tsv = tmp_path / "Orthogroups.tsv"
        tsv.write_text(
            "Orthogroup\tArabidopsis thaliana\n"
            "OG0000001\tAT1G01010, AT1G01020\n"
        )
        result = _genomics_module._parse_orthofinder_paralogs(
            gene="AT9G99999",
            species_col="Arabidopsis thaliana",
            orthogroups_tsv=str(tsv),
        )
        assert result == []

    def test_single_gene_no_paralogs(self, tmp_path):
        """Gene alone in its species column has no paralogs."""
        tsv = tmp_path / "Orthogroups.tsv"
        tsv.write_text(
            "Orthogroup\tArabidopsis thaliana\n"
            "OG0000001\tAT5G10140\n"
        )
        result = _genomics_module._parse_orthofinder_paralogs(
            gene="AT5G10140",
            species_col="Arabidopsis thaliana",
            orthogroups_tsv=str(tsv),
        )
        assert result == []

    def test_file_not_found(self):
        """Non-existent file returns empty list."""
        result = _genomics_module._parse_orthofinder_paralogs(
            gene="AT5G10140",
            species_col="Arabidopsis thaliana",
            orthogroups_tsv="/nonexistent/path/Orthogroups.tsv",
        )
        assert result == []


class TestParalogyScore:
    """Tests for the genomics.paralogy_score registered tool."""

    @patch("ct.tools.genomics.coexpression_network")
    @patch("ct.tools.genomics.gene_annotation")
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_ensembl_compara_success(self, mock_taxon, mock_binomial, mock_rj, mock_get, mock_set, mock_ga, mock_coexp):
        """Ensembl Compara returns paralogs with details computed."""
        # Mock gene lookup and homology API calls
        mock_rj.side_effect = [
            # First call: gene lookup
            ({"id": "AT5G10140", "display_name": "FLC"}, None),
            # Second call: homology/paralogues
            ({"data": [{"homologies": [
                {"target": {"id": "AT3G24440", "perc_id": 65}, "type": "within_species_paralog"},
                {"target": {"id": "AT1G77080", "perc_id": 45}, "type": "within_species_paralog"},
            ]}]}, None),
        ]
        # Mock gene_annotation for query + 2 paralogs
        mock_ga.side_effect = [
            {"go_terms": [{"go_id": "GO:0003700"}, {"go_id": "GO:0006355"}]},  # query
            {"go_terms": [{"go_id": "GO:0003700"}, {"go_id": "GO:0009908"}]},  # paralog 1
            {"go_terms": [{"go_id": "GO:0006355"}, {"go_id": "GO:0009909"}]},  # paralog 2
        ]
        # Mock coexpression_network for query + 2 paralogs
        mock_coexp.side_effect = [
            {"coexpressed_genes": [{"partner": "AT2G01010"}, {"partner": "AT4G00650"}]},  # query
            {"coexpressed_genes": [{"partner": "AT2G01010"}, {"partner": "AT5G55555"}]},  # paralog 1
            {"coexpressed_genes": [{"partner": "AT4G00650"}, {"partner": "AT1G11111"}]},  # paralog 2
        ]

        result = _genomics_module.paralogy_score(
            gene="FLC",
            species="Arabidopsis thaliana",
        )

        assert "error" not in result
        assert result["paralog_count"] == 2
        assert "AT3G24440" in result["paralogs"]
        assert "AT1G77080" in result["paralogs"]
        assert result["data_source"] == "Ensembl Compara"
        assert len(result["paralog_details"]) == 2

        # Check shared GO annotations
        detail_1 = result["paralog_details"][0]
        assert detail_1["paralog_id"] == "AT3G24440"
        assert detail_1["shared_go_count"] == 1  # GO:0003700 shared
        assert "GO:0003700" in detail_1["shared_go_ids"]

        # Check co-expression overlap
        assert detail_1["coexpression_overlap_count"] == 1  # AT2G01010 shared

        mock_set.assert_called_once()

    @patch("ct.tools.genomics.coexpression_network")
    @patch("ct.tools.genomics.gene_annotation")
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_local_orthofinder_priority(self, mock_taxon, mock_binomial, mock_rj, mock_get, mock_set, mock_ga, mock_coexp, tmp_path):
        """OrthoFinder local data is used before Ensembl Compara API."""
        # Set up mock OrthoFinder directory using orthofinder_dir parameter
        of_dir = tmp_path / "orthofinder_results"
        of_orthogroups_dir = of_dir / "Orthogroups"
        of_orthogroups_dir.mkdir(parents=True)
        tsv = of_orthogroups_dir / "Orthogroups.tsv"
        tsv.write_text(
            "Orthogroup\tArabidopsis thaliana\tOryza sativa\n"
            "OG0000001\tFLC, MAF1, MAF2\tOs01g0100\n"
        )
        # Mock sub-calls for GO/co-expression overlap (for FLC + 2 paralogs)
        mock_ga.return_value = {"go_terms": []}
        mock_coexp.return_value = {"coexpressed_genes": []}

        result = _genomics_module.paralogy_score(
            gene="FLC",
            species="Arabidopsis thaliana",
            orthofinder_dir=str(of_dir),
        )

        # Ensembl Compara should NOT have been called (local data used first)
        mock_rj.assert_not_called()
        assert result["paralog_count"] == 2
        assert "MAF1" in result["paralogs"]
        assert "MAF2" in result["paralogs"]
        assert "OrthoFinder" in result["data_source"]

    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_compara_paralogues_param(self, mock_taxon, mock_binomial, mock_rj, mock_get, mock_set):
        """Ensembl API is called with type=paralogues and compara=plants."""
        mock_rj.side_effect = [
            ({"id": "AT5G10140"}, None),      # gene lookup
            ({"data": [{"homologies": []}]}, None),  # empty paralogues
        ]

        _genomics_module.paralogy_score(gene="FLC", species="Arabidopsis thaliana")

        # Check the second call (homology API) has correct params
        assert mock_rj.call_count >= 2
        second_call = mock_rj.call_args_list[1]
        call_params = second_call.kwargs.get("params", {}) if second_call.kwargs else second_call[1].get("params", {})
        assert call_params.get("type") == "paralogues"
        assert call_params.get("compara") == "plants"

    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools.http_client.request_json")
    @patch("ct.tools._species.resolve_species_binomial", return_value="Oryza sativa")
    @patch("ct.tools._species.resolve_species_taxon", return_value=4530)
    def test_empty_response(self, mock_taxon, mock_binomial, mock_rj, mock_get, mock_set):
        """Empty paralog list returns informative sparse-result summary."""
        mock_rj.side_effect = [
            ({"id": "Os01g0100100"}, None),
            ({"data": [{"homologies": []}]}, None),
        ]

        result = _genomics_module.paralogy_score(gene="GW5", species="Oryza sativa")

        assert result["paralog_count"] == 0
        assert result["paralogs"] == []
        assert "data coverage is limited" in result["summary"]
        assert "error" not in result

    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        """Unknown species without force returns error."""
        result = _genomics_module.paralogy_score(gene="FLC", species="martian_grass")
        assert "error" in result
        assert "Unknown species" in result["error"]

    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._api_cache.get_cached")
    def test_cache_hit(self, mock_get, mock_binomial, mock_taxon):
        """Cached result is returned without API calls."""
        cached = {"summary": "cached", "gene": "FLC", "paralogs": ["MAF1"]}
        mock_get.return_value = cached
        result = _genomics_module.paralogy_score(gene="FLC", species="Arabidopsis thaliana")
        assert result == cached

    def test_missing_gene(self):
        """Empty gene parameter returns error."""
        result = _genomics_module.paralogy_score(gene="")
        assert "error" in result
        assert "Missing required parameter" in result["error"]


def test_paralogy_tool_registered():
    """genomics.paralogy_score is registered in the genomics category."""
    t = registry.get_tool("genomics.paralogy_score")
    assert t is not None, "genomics.paralogy_score not registered"
    assert t.category == "genomics"
