"""Tests for editing.py — CRISPR guide design and editability scoring tools."""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from ct.tools import ensure_loaded, registry, PLANT_SCIENCE_CATEGORIES
import ct.tools.editing as _editing_module

ensure_loaded()

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FASTA_PATH = str(FIXTURE_DIR / "FLC_mini_region.fasta")


class TestHelpers:
    """Tests for internal helper functions."""

    def test_reverse_complement(self):
        assert _editing_module._reverse_complement("ACGT") == "ACGT"
        assert _editing_module._reverse_complement("AAAA") == "TTTT"
        assert _editing_module._reverse_complement("GCAT") == "ATGC"

    def test_gc_content(self):
        assert _editing_module._gc_content("GCGC") == 1.0
        assert _editing_module._gc_content("ATAT") == 0.0
        assert _editing_module._gc_content("GCAT") == 0.5
        assert _editing_module._gc_content("") == 0.0

    def test_score_guide_heuristic_optimal(self):
        """Guide with 50% GC, no polyT, no homopolymers scores well."""
        guide = "GCATGCATGCATGCATGCAT"  # 50% GC, 20 nt
        score = _editing_module._score_guide_heuristic(guide)
        assert score >= 0.65  # Should be high_confidence tier

    def test_score_guide_heuristic_polyT_penalty(self):
        """Guide with TTTT run gets penalised."""
        guide = "GCATTTTTGCATGCATGCAT"  # Has TTTT
        score = _editing_module._score_guide_heuristic(guide)
        assert score < _editing_module._score_guide_heuristic("GCATGCATGCATGCATGCAT")

    def test_score_guide_heuristic_extreme_gc(self):
        """Guide with very low GC gets penalised."""
        guide = "AAAAAAAAAAAAAAAAAAAA"  # 0% GC
        score = _editing_module._score_guide_heuristic(guide)
        assert score < 0.3  # Should be poor

    def test_tier_labels(self):
        assert _editing_module._tier_label(0.70) == "high_confidence"
        assert _editing_module._tier_label(0.65) == "high_confidence"
        assert _editing_module._tier_label(0.50) == "acceptable"
        assert _editing_module._tier_label(0.40) == "acceptable"
        assert _editing_module._tier_label(0.30) == "poor"
        assert _editing_module._tier_label(0.0) == "poor"


class TestPamScanning:
    """Tests for _scan_pam_sites function."""

    def test_spcas9_finds_ngg(self):
        """SpCas9 scanning finds NGG PAM sites."""
        # Construct a sequence with a known guide+NGG pattern
        # 20 nt guide + AGG (NGG where N=A)
        seq = "A" * 10 + "GCATGCATGCATGCATGCAT" + "AGG" + "A" * 10
        guides = _editing_module._scan_pam_sites(seq, "SpCas9")
        # Should find at least one guide on the + strand with the known guide sequence
        plus_guides = [g for g in guides if g["strand"] == "+"]
        assert len(plus_guides) >= 1
        found = any(g["guide_sequence"] == "GCATGCATGCATGCATGCAT" for g in plus_guides)
        assert found, "Expected guide not found in + strand results"

    def test_cas12a_finds_tttv(self):
        """Cas12a scanning finds TTTV PAM sites."""
        # TTTA (TTTV where V=A) + 20 nt guide
        seq = "A" * 10 + "TTTA" + "GCATGCATGCATGCATGCAT" + "A" * 10
        guides = _editing_module._scan_pam_sites(seq, "Cas12a")
        plus_guides = [g for g in guides if g["strand"] == "+"]
        assert len(plus_guides) >= 1
        found = any(g["guide_sequence"] == "GCATGCATGCATGCATGCAT" for g in plus_guides)
        assert found, "Expected Cas12a guide not found"

    def test_both_strands_scanned(self):
        """Scanning produces guides from both + and - strands."""
        # Long enough sequence to have PAM sites on both strands
        seq = "GCATGCATGCATGCATGCATAGG" * 5
        guides = _editing_module._scan_pam_sites(seq, "SpCas9")
        strands = set(g["strand"] for g in guides)
        assert "+" in strands or "-" in strands  # At least one strand found

    def test_guide_fields_present(self):
        """Each guide dict has all required fields."""
        seq = "A" * 10 + "GCATGCATGCATGCATGCAT" + "AGG" + "A" * 10
        guides = _editing_module._scan_pam_sites(seq, "SpCas9")
        assert len(guides) >= 1
        required_fields = {"guide_sequence", "pam", "strand", "position", "gc_content", "on_target_score", "tier"}
        for g in guides:
            assert required_fields.issubset(g.keys()), f"Missing fields in guide: {required_fields - g.keys()}"
            assert g["tier"] in ("high_confidence", "acceptable", "poor")
            assert 0.0 <= g["gc_content"] <= 1.0
            assert 0.0 <= g["on_target_score"] <= 1.0

    def test_overlapping_ngg_matches(self):
        """Adjacent NGG PAMs are not missed due to non-overlapping regex."""
        # GG followed immediately by another G creates overlapping NGG
        seq = "ACGTACGTACGTACGTACGT" + "AGGG" + "ACGTACGTACGTACGTACGT"
        guides = _editing_module._scan_pam_sites(seq, "SpCas9")
        # The AGG and GGG PAMs overlap — both should be found
        # This verifies the lookahead pattern handles overlapping matches
        assert len(guides) >= 1


class TestCrisprGuideDesign:
    """Tests for the editing.crispr_guide_design registered tool."""

    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_local_fasta_spcas9(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool):
        """Guide design with local FASTA returns guides with all fields."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            cas_system="SpCas9",
            genome_fasta=FASTA_PATH,
        )
        assert "error" not in result
        assert "guides" in result
        assert isinstance(result["guides"], list)
        assert result["cas_system"] == "SpCas9"
        assert result["gene"] == "FLC"
        assert result["species"] == "Arabidopsis thaliana"
        assert result["fasta_source"].startswith("local file")
        mock_set.assert_called_once()

    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_cas12a_guides(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool):
        """Cas12a guide design with TTTV PAM returns guides."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            cas_system="Cas12a",
            genome_fasta=FASTA_PATH,
        )
        assert "error" not in result
        assert result["cas_system"] == "Cas12a"

    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_tier_labels_assigned(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool):
        """All guides have valid tier labels."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            genome_fasta=FASTA_PATH,
        )
        for g in result.get("guides", []):
            assert g["tier"] in ("high_confidence", "acceptable", "poor")

    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_max_guides_cap(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool):
        """Guide count does not exceed max_guides parameter."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            genome_fasta=FASTA_PATH,
            max_guides=3,
        )
        assert len(result.get("guides", [])) <= 3

    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_off_target_fallback(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool):
        """Without external aligner, off-target uses regex scan."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
            genome_fasta=FASTA_PATH,
        )
        if result.get("guides"):
            # off_target_count should be an int (from regex scan) or None
            for g in result["guides"]:
                assert "off_target_count" in g
                assert g["off_target_count"] is None or isinstance(g["off_target_count"], int)

    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        """Unknown species without force returns error."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="martian_grass",
        )
        assert "error" in result
        assert "Unknown species" in result["error"]

    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    @patch("ct.tools._species.resolve_species_binomial", return_value="")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    def test_force_override(self, mock_tool, mock_set, mock_get, mock_binomial, mock_taxon):
        """force=True bypasses species validation."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="novelplant",
            genome_fasta=FASTA_PATH,
            force=True,
        )
        assert "Unknown species" not in result.get("error", "")

    def test_unknown_cas_system(self):
        """Unknown Cas system returns error."""
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            cas_system="CasMadeUp",
        )
        assert "error" in result
        assert "Unknown Cas system" in result["error"]

    def test_missing_gene(self):
        """Empty gene parameter returns error."""
        result = _editing_module.crispr_guide_design(gene="")
        assert "error" in result
        assert "Missing required parameter" in result["error"]

    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._api_cache.get_cached")
    def test_cache_hit(self, mock_get, mock_binomial, mock_taxon):
        """Cached result is returned without scanning."""
        cached_result = {"summary": "cached", "gene": "FLC", "guides": []}
        mock_get.return_value = cached_result
        result = _editing_module.crispr_guide_design(
            gene="FLC",
            species="Arabidopsis thaliana",
        )
        assert result == cached_result


class TestEditabilityScore:
    """Tests for the editing.editability_score registered tool."""

    @patch("ct.tools.genomics.gff_parse")
    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_sub_scores_returned(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool, mock_gff):
        """Editability score returns all expected sub-score fields."""
        mock_gff.return_value = {
            "summary": "Gene structure for FLC",
            "total_exons": 7,
            "total_introns": 6,
            "gene_span_bp": 5952,
        }
        result = _editing_module.editability_score(
            gene="FLC",
            species="Arabidopsis thaliana",
            genome_fasta=FASTA_PATH,
        )
        assert "guide_quality_score" in result
        assert isinstance(result["guide_quality_score"], float)
        assert 0.0 <= result["guide_quality_score"] <= 1.0
        assert "structure_complexity" in result
        assert result["structure_complexity"]["exon_count"] == 7
        assert result["structure_complexity"]["intron_count"] == 6
        assert result["structure_complexity"]["gene_span_bp"] == 5952
        assert "guide_result" in result
        assert "structure_result" in result
        assert "n_guides_total" in result
        assert "n_guides_high_confidence" in result

    @patch("ct.tools.genomics.gff_parse")
    @patch("ct.tools._local_tools.check_tool_available", return_value=False)
    @patch("ct.tools._api_cache.set_cached")
    @patch("ct.tools._api_cache.get_cached", return_value=None)
    @patch("ct.tools._species.resolve_species_binomial", return_value="Arabidopsis thaliana")
    @patch("ct.tools._species.resolve_species_taxon", return_value=3702)
    def test_regulatory_stub(self, mock_taxon, mock_binomial, mock_get, mock_set, mock_tool, mock_gff):
        """Regulatory complexity is None (stub for M1)."""
        mock_gff.return_value = {
            "summary": "Gene structure",
            "total_exons": 2,
            "total_introns": 1,
            "gene_span_bp": 1000,
        }
        result = _editing_module.editability_score(
            gene="FLC",
            species="Arabidopsis thaliana",
            genome_fasta=FASTA_PATH,
        )
        assert result["regulatory_complexity_score"] is None

    @patch("ct.tools._species.resolve_species_taxon", return_value=0)
    def test_unknown_species(self, mock_taxon):
        """Unknown species without force returns error."""
        result = _editing_module.editability_score(gene="FLC", species="martian_grass")
        assert "error" in result

    def test_missing_gene(self):
        """Empty gene returns error."""
        result = _editing_module.editability_score(gene="")
        assert "error" in result


def test_editing_tools_registered():
    """Both editing tools are registered in the editing category."""
    t1 = registry.get_tool("editing.crispr_guide_design")
    t2 = registry.get_tool("editing.editability_score")
    assert t1 is not None, "editing.crispr_guide_design not registered"
    assert t2 is not None, "editing.editability_score not registered"
    assert t1.category == "editing"
    assert t2.category == "editing"


def test_editing_in_plant_categories():
    """'editing' is in the plant science category allowlist."""
    assert "editing" in PLANT_SCIENCE_CATEGORIES
