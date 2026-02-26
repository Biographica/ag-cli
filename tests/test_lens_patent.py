"""
Tests for literature.lens_patent_search and MCP-layer hiding.

All network calls are mocked — no real HTTP requests are made.
Because literature.py uses lazy imports inside the function body, patches
must target the source modules where the names live.

Patch targets:
  ct.tools._species.resolve_species_binomial
  ct.tools.http_client.request
  ct.tools._api_cache.get_cached
  ct.tools._api_cache.set_cached
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ct.tools import ensure_loaded, registry


# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_BINOMIAL_TARGET = "ct.tools._species.resolve_species_binomial"
_REQUEST_TARGET = "ct.tools.http_client.request"
_GET_CACHED_TARGET = "ct.tools._api_cache.get_cached"
_SET_CACHED_TARGET = "ct.tools._api_cache.set_cached"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(lens_key: str | None = None) -> MagicMock:
    """Create a mock session whose config.get returns lens_key."""
    session = MagicMock()

    def _config_get(key, default=None):
        if key == "api.lens_key":
            return lens_key
        return default

    session.config.get.side_effect = _config_get
    return session


_MOCK_PATENT = {
    "lens_id": "001-234-567-890",
    "title": [{"text": "Patent Title About FLC Gene"}],
    "abstract": [{"text": "This patent claims methods using FLC gene."}],
    "claim": [
        {"text": "Claim 1: A method comprising..."},
        {"text": "Claim 2: The method of claim 1..."},
    ],
    "applicant": [{"name": "AgroCorp Ltd"}],
    "publication_date": "2024-01-15",
    "doc_number": "US123456",
    "jurisdiction": "US",
    "kind": "B2",
}

_LENS_RESPONSE_ONE = {
    "total": 1,
    "data": [_MOCK_PATENT],
}


def _make_lens_response(status_code: int = 200, data: dict | None = None) -> MagicMock:
    """Create a mock HTTP response for the Lens.org API."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data or _LENS_RESPONSE_ONE
    resp.text = str(data or _LENS_RESPONSE_ONE)[:200]
    return resp


def _call_tool(**kwargs) -> dict:
    ensure_loaded()
    tool = registry.get_tool("literature.lens_patent_search")
    return tool.run(**kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGeneMode:
    def test_gene_mode_query_construction(self):
        """Gene mode builds a query containing gene name AND binomial species."""
        session = _make_session(lens_key="test-key")

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_TARGET, return_value=(_make_lens_response(), None)),
        ):
            result = _call_tool(
                query_text="FLC",
                mode="gene",
                species="Arabidopsis thaliana",
                _session=session,
            )

        assert "error" not in result
        assert "FLC" in result["query_used"]
        assert "Arabidopsis thaliana" in result["query_used"]

    def test_gene_mode_returns_patents(self):
        """Gene mode result includes patents list with expected fields."""
        session = _make_session(lens_key="test-key")

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_TARGET, return_value=(_make_lens_response(), None)),
        ):
            result = _call_tool(
                query_text="FLC",
                mode="gene",
                species="Arabidopsis thaliana",
                _session=session,
            )

        assert result["total_count"] == 1
        assert len(result["patents"]) == 1
        patent = result["patents"][0]
        assert patent["lens_id"] == "001-234-567-890"
        assert "FLC" in patent["title"] or patent["title"]  # title extracted
        assert patent["abstract"]  # non-empty abstract
        assert isinstance(patent["claims"], list)
        assert len(patent["claims"]) > 0


class TestLandscapeMode:
    def test_landscape_mode_query_construction(self):
        """Landscape mode builds a query containing crop AND trait."""
        session = _make_session(lens_key="test-key")

        with (
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_TARGET, return_value=(_make_lens_response(), None)),
        ):
            result = _call_tool(
                query_text="rice",
                mode="landscape",
                trait="drought tolerance",
                _session=session,
            )

        assert "error" not in result
        assert "rice" in result["query_used"]
        assert "drought tolerance" in result["query_used"]

    def test_landscape_missing_trait_returns_error(self):
        """Landscape mode without trait returns error dict."""
        session = _make_session(lens_key="test-key")

        with (
            patch(_GET_CACHED_TARGET, return_value=None),
        ):
            result = _call_tool(
                query_text="rice",
                mode="landscape",
                trait="",
                _session=session,
            )

        assert "error" in result
        assert "trait" in result["error"].lower()


class TestNoApiKey:
    def test_no_api_key_returns_error(self):
        """Tool returns a structured error when no Lens.org key is configured."""
        session = _make_session(lens_key=None)

        result = _call_tool(
            query_text="FLC",
            mode="gene",
            species="Arabidopsis thaliana",
            _session=session,
        )

        assert "error" in result
        assert "api.lens_key" in result["error"] or "Lens.org" in result["error"]


class TestMCPHiding:
    def test_mcp_hiding_when_no_lens_key(self):
        """create_ct_mcp_server excludes lens_patent_search when api.lens_key is absent."""
        from ct.agent.mcp_server import create_ct_mcp_server

        # Build a session where config.get('api.lens_key') returns None.
        session = MagicMock()
        session.config.get.return_value = None

        # We only need to verify the tool hiding logic. Mock out the registry
        # iteration and the SDK server creation to avoid real I/O.
        from ct.tools import ensure_loaded

        ensure_loaded()

        with (
            patch("ct.agent.mcp_server.create_sdk_mcp_server") as mock_sdk,
            patch("ct.agent.mcp_server._make_run_python_handler") as mock_rp,
        ):
            mock_sdk.return_value = MagicMock()
            # _make_run_python_handler returns (handler, sandbox)
            mock_rp.return_value = (MagicMock(), None)

            _, _, tool_names, _ = create_ct_mcp_server(
                session,
                include_run_python=False,
            )

        assert "literature.lens_patent_search" not in tool_names, (
            "literature.lens_patent_search must be excluded from MCP when api.lens_key is None"
        )

    def test_mcp_exposes_lens_when_key_present(self):
        """create_ct_mcp_server includes lens_patent_search when api.lens_key is set."""
        from ct.agent.mcp_server import create_ct_mcp_server

        session = MagicMock()

        def _cfg_get(key, default=None):
            if key == "api.lens_key":
                return "test-lens-key"
            return default

        session.config.get.side_effect = _cfg_get

        from ct.tools import ensure_loaded
        ensure_loaded()

        with (
            patch("ct.agent.mcp_server.create_sdk_mcp_server") as mock_sdk,
            patch("ct.agent.mcp_server._make_run_python_handler") as mock_rp,
        ):
            mock_sdk.return_value = MagicMock()
            mock_rp.return_value = (MagicMock(), None)

            _, _, tool_names, _ = create_ct_mcp_server(
                session,
                include_run_python=False,
            )

        assert "literature.lens_patent_search" in tool_names, (
            "literature.lens_patent_search must be exposed when api.lens_key is configured"
        )


class TestResponseParsing:
    def test_response_includes_claims(self):
        """Patent entry includes claims list with text content."""
        session = _make_session(lens_key="test-key")

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_TARGET, return_value=(_make_lens_response(), None)),
        ):
            result = _call_tool(
                query_text="FLC",
                mode="gene",
                species="Arabidopsis thaliana",
                _session=session,
            )

        assert len(result["patents"]) == 1
        patent = result["patents"][0]
        assert "claims" in patent
        assert isinstance(patent["claims"], list)
        assert len(patent["claims"]) >= 1
        # Claims should have text content (list of strings).
        assert all(isinstance(c, str) for c in patent["claims"])
        assert any("Claim" in c for c in patent["claims"])

    def test_no_results_returns_structured_response(self):
        """Zero results returns structured response without error."""
        session = _make_session(lens_key="test-key")
        empty_response = {"total": 0, "data": []}

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_TARGET, return_value=(
                _make_lens_response(status_code=200, data=empty_response), None
            )),
        ):
            result = _call_tool(
                query_text="FAKEGENE999",
                mode="gene",
                species="Arabidopsis thaliana",
                _session=session,
            )

        assert "error" not in result
        assert result["total_count"] == 0
        assert result["patents"] == []
        assert "No patents found" in result["summary"]


class TestCacheBehaviour:
    def test_cache_hit_skips_network(self):
        """When get_cached returns a value, request is not called."""
        session = _make_session(lens_key="test-key")
        cached_result = {
            "summary": "Cached Lens result",
            "query_used": '"FLC" AND "Arabidopsis thaliana"',
            "mode": "gene",
            "total_count": 3,
            "patents": [{"lens_id": "AAA", "title": "Old patent"}],
        }

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=cached_result),
            patch(_REQUEST_TARGET) as mock_req,
        ):
            result = _call_tool(
                query_text="FLC",
                mode="gene",
                species="Arabidopsis thaliana",
                _session=session,
            )

        mock_req.assert_not_called()
        assert result == cached_result
