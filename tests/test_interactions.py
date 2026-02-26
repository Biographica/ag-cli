"""
Tests for the STRING plant PPI connector (interactions.string_plant_ppi).

All network calls are mocked — no real HTTP requests are made.
Because interactions.py uses lazy imports inside the function body, patches
must target the source modules where the names live, not the interactions
module namespace (which doesn't re-export them at module level).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ct.tools import PLANT_SCIENCE_CATEGORIES, ensure_loaded, registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARABIDOPSIS_TAXON = 3702

_MOCK_STRING_IDS = [
    {
        "stringId": "3702.AT5G10140.1",
        "preferredName": "FLC",
    }
]

_MOCK_PARTNERS = [
    {
        "preferredName_A": "FLC",
        "preferredName_B": "FRI",
        "stringId_A": "3702.AT5G10140.1",
        "stringId_B": "3702.AT4G00650.1",
        "score": 900,
    }
]

# Patch targets — source modules (lazy imports happen inside the function body)
_TAXON_TARGET = "ct.tools._species.resolve_species_taxon"
_BINOMIAL_TARGET = "ct.tools._species.resolve_species_binomial"
_REQUEST_JSON_TARGET = "ct.tools.http_client.request_json"
_GET_CACHED_TARGET = "ct.tools._api_cache.get_cached"
_SET_CACHED_TARGET = "ct.tools._api_cache.set_cached"


def _call_tool(**kwargs) -> dict:
    """Helper: call the registered tool by name."""
    ensure_loaded()
    tool = registry.get_tool("interactions.string_plant_ppi")
    return tool.run(**kwargs)


# ---------------------------------------------------------------------------
# Registration / category tests
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registered(self) -> None:
        """Tool is registered with the correct name and category."""
        ensure_loaded()
        t = registry.get_tool("interactions.string_plant_ppi")
        assert t is not None, "interactions.string_plant_ppi must be registered"
        assert t.category == "interactions"

    def test_interactions_in_plant_categories(self) -> None:
        """'interactions' category appears in the plant science allowlist."""
        assert "interactions" in PLANT_SCIENCE_CATEGORIES, (
            "'interactions' must be in PLANT_SCIENCE_CATEGORIES so the tool is "
            "exposed at the MCP layer for the plant science agent."
        )


# ---------------------------------------------------------------------------
# Species validation
# ---------------------------------------------------------------------------


class TestUnknownSpecies:
    def test_unknown_species_returns_error(self) -> None:
        """An unrecognised species returns a structured error without hitting the API."""
        with (
            patch(_TAXON_TARGET, return_value=0),
            patch(_REQUEST_JSON_TARGET) as mock_rj,
        ):
            result = _call_tool(gene="FLC", species="martian_grass")

        mock_rj.assert_not_called()
        assert "error" in result, "Result must contain 'error' key for unknown species"
        assert "not recognised" in result["summary"].lower(), (
            "Summary must mention that the species is not recognised"
        )
        assert result["interactions"] == []


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestSuccessPath:
    def test_success(self) -> None:
        """Full happy path: two API calls succeed and result is parsed correctly."""
        with (
            patch(_TAXON_TARGET, return_value=_ARABIDOPSIS_TAXON),
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_MOCK_STRING_IDS, None),   # get_string_ids
                (_MOCK_PARTNERS, None),     # interaction_partners
            ]),
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana")

        assert "summary" in result
        assert isinstance(result["interactions"], list)
        assert len(result["interactions"]) == 1

        partner = result["interactions"][0]
        assert partner["partner"] == "FRI"
        assert partner["score"] == pytest.approx(0.9, rel=1e-4)

    def test_empty_string_ids(self) -> None:
        """Empty get_string_ids response returns structured empty result."""
        with (
            patch(_TAXON_TARGET, return_value=_ARABIDOPSIS_TAXON),
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, return_value=([], None)),
        ):
            result = _call_tool(gene="FAKE_GENE", species="Arabidopsis thaliana")

        assert result["interactions"] == []
        assert "No STRING identifier found" in result["summary"]

    def test_empty_interactions(self) -> None:
        """Valid STRING ID but no partners above min_score returns empty list."""
        with (
            patch(_TAXON_TARGET, return_value=_ARABIDOPSIS_TAXON),
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_MOCK_STRING_IDS, None),   # get_string_ids succeeds
                ([], None),                 # interaction_partners returns nothing
            ]),
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana")

        assert result["interactions"] == []
        assert "No interaction partners found" in result["summary"]

    def test_limit_capped_at_50(self) -> None:
        """limit parameter is capped at 50 regardless of user input."""
        call_params = []

        def capture_request_json(method, url, *, params=None, **kw):
            call_params.append(params or {})
            if "get_string_ids" in url:
                return (_MOCK_STRING_IDS, None)
            return ([], None)

        with (
            patch(_TAXON_TARGET, return_value=_ARABIDOPSIS_TAXON),
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=capture_request_json),
        ):
            _call_tool(gene="FLC", species="Arabidopsis thaliana", limit=200)

        # Second call is interaction_partners — params captured at index 1
        assert len(call_params) >= 2, "Expected at least 2 API calls"
        assert call_params[1].get("limit") == 50, (
            f"limit must be capped at 50, got {call_params[1].get('limit')}"
        )


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


class TestCacheBehaviour:
    def test_cache_hit_skips_api(self) -> None:
        """When get_cached returns a pre-built result, request_json is not called."""
        cached_result = {
            "summary": "Cached result",
            "gene": "FLC",
            "resolved_name": "FLC",
            "string_id": "3702.AT5G10140.1",
            "species": "Arabidopsis thaliana",
            "taxon_id": _ARABIDOPSIS_TAXON,
            "min_score": 0.4,
            "interaction_count": 1,
            "interactions": [
                {"partner": "FRI", "string_id": "3702.AT4G00650.1", "score": 0.9}
            ],
        }

        with (
            patch(_TAXON_TARGET, return_value=_ARABIDOPSIS_TAXON),
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=cached_result),
            patch(_REQUEST_JSON_TARGET) as mock_rj,
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana")

        mock_rj.assert_not_called()
        assert result == cached_result
