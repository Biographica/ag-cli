"""
Tests for literature.pubmed_plant_search.

All network calls are mocked — no real HTTP requests are made.
Because literature.py uses lazy imports inside the function body, patches
must target the source modules where the names live, not the literature
module namespace. Exception: _normalize_pubmed_query is a module-level
function in literature.py and is imported directly by the tool body, so
it does not need to be patched.

Patch targets:
  ct.tools._species.resolve_species_binomial
  ct.tools.http_client.request_json
  ct.tools.http_client.request
  ct.tools._api_cache.get_cached
  ct.tools._api_cache.set_cached
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

import ct.tools.literature as _lit_module
from ct.tools import ensure_loaded, registry


# ---------------------------------------------------------------------------
# Patch targets — source modules (lazy imports inside function body)
# ---------------------------------------------------------------------------

_BINOMIAL_TARGET = "ct.tools._species.resolve_species_binomial"
_REQUEST_JSON_TARGET = "ct.tools.http_client.request_json"
_REQUEST_TARGET = "ct.tools.http_client.request"
_GET_CACHED_TARGET = "ct.tools._api_cache.get_cached"
_SET_CACHED_TARGET = "ct.tools._api_cache.set_cached"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_session(ncbi_key: str | None = None) -> MagicMock:
    """Build a minimal mock session whose config.get returns ncbi_key."""
    session = MagicMock()

    def _config_get(key, default=None):
        if key == "api.ncbi_key":
            return ncbi_key
        return default

    session.config.get.side_effect = _config_get
    return session


_ESEARCH_ONE = {
    "esearchresult": {
        "idlist": ["12345678"],
        "count": "1",
    }
}

_ESUMMARY_ONE = {
    "result": {
        "12345678": {
            "title": "Flowering time control by FLC",
            "authors": [{"name": "Smith J"}],
            "fulljournalname": "Plant Cell",
            "pubdate": "2023 Jan 15",
            "elocationid": "10.1234/pc.2023.001",
            "articleids": [],
        }
    }
}

_ABSTRACT_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <Abstract>
          <AbstractText>My abstract text about FLC flowering time.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _make_fetch_response(xml_text: str) -> MagicMock:
    """Create a mock HTTP response object with the given XML text."""
    resp = MagicMock()
    resp.text = xml_text
    return resp


def _call_tool(**kwargs) -> dict:
    ensure_loaded()
    tool = registry.get_tool("literature.pubmed_plant_search")
    return tool.run(**kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQueryConstruction:
    def setup_method(self):
        # Reset module-level rate limit flag before each test.
        _lit_module._pubmed_rate_limit_warned = False

    def test_query_construction_known_species(self):
        """Known species produces organism-scoped PubMed query."""
        session = _make_session(ncbi_key="fake-key")  # suppress rate note

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
            ]),
            patch(_REQUEST_TARGET, return_value=(_make_fetch_response(_ABSTRACT_XML), None)),
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana", _session=session)

        assert "error" not in result
        assert "FLC" in result["query_used"]
        assert "[Title/Abstract]" in result["query_used"]
        assert "Arabidopsis thaliana" in result["query_used"]
        assert "[Organism]" in result["query_used"]

    def test_query_construction_unknown_species(self):
        """Unknown species falls back to plant[MeSH Terms] in the query."""
        session = _make_session(ncbi_key="fake-key")

        with (
            patch(_BINOMIAL_TARGET, return_value=""),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
            ]),
            patch(_REQUEST_TARGET, return_value=(_make_fetch_response(_ABSTRACT_XML), None)),
        ):
            result = _call_tool(gene="FLC", species="unknown_plant", _session=session)

        assert "error" not in result
        assert "plant[MeSH Terms]" in result["query_used"]
        assert "[Organism]" not in result["query_used"]

    def test_extra_terms_added(self):
        """extra_terms are ANDed into the query string."""
        session = _make_session(ncbi_key="fake-key")

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
            ]),
            patch(_REQUEST_TARGET, return_value=(_make_fetch_response(_ABSTRACT_XML), None)),
        ):
            result = _call_tool(
                gene="FLC",
                species="Arabidopsis thaliana",
                extra_terms="drought",
                _session=session,
            )

        assert "error" not in result
        assert "drought" in result["query_used"]
        assert "AND" in result["query_used"]


class TestEmptyResults:
    def setup_method(self):
        _lit_module._pubmed_rate_limit_warned = False

    def test_empty_results_returns_structured_response(self):
        """Zero PMIDs returns structured response with correct fields."""
        session = _make_session(ncbi_key="fake-key")
        empty_esearch = {"esearchresult": {"idlist": [], "count": "0"}}

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, return_value=(empty_esearch, None)),
        ):
            result = _call_tool(gene="NOTEXIST", species="Arabidopsis thaliana", _session=session)

        assert result["total_count"] == 0
        assert result["articles"] == []
        assert "query_used" in result
        assert "NOTEXIST" in result["query_used"]


class TestAbstractFetching:
    def setup_method(self):
        _lit_module._pubmed_rate_limit_warned = False

    def test_abstract_fetched_and_included(self):
        """EFetch XML is parsed and abstract text appears in the article entry."""
        session = _make_session(ncbi_key="fake-key")

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
            ]),
            patch(_REQUEST_TARGET, return_value=(
                _make_fetch_response(_ABSTRACT_XML), None
            )),
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana", _session=session)

        assert len(result["articles"]) >= 1
        assert result["articles"][0]["abstract"] != "", (
            "Abstract should be non-empty when EFetch succeeds"
        )
        assert "FLC" in result["articles"][0]["abstract"] or "abstract" in result["articles"][0]["abstract"].lower()


class TestRateLimitWarning:
    def setup_method(self):
        _lit_module._pubmed_rate_limit_warned = False

    def teardown_method(self):
        _lit_module._pubmed_rate_limit_warned = False

    def test_rate_limit_warning_emitted_once(self):
        """Rate limit warning appears in summary on first call but not second."""
        session = _make_session(ncbi_key=None)  # No key — triggers warning

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=None),
            patch(_SET_CACHED_TARGET),
            patch(_REQUEST_JSON_TARGET, side_effect=[
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
                (_ESEARCH_ONE, None),
                (_ESUMMARY_ONE, None),
            ]),
            patch(_REQUEST_TARGET, return_value=(_make_fetch_response(_ABSTRACT_XML), None)),
        ):
            result1 = _call_tool(gene="FLC", species="Arabidopsis thaliana", _session=session)
            # Flag should now be True.
            assert _lit_module._pubmed_rate_limit_warned is True, (
                "_pubmed_rate_limit_warned must be set after first call with no key"
            )

            result2 = _call_tool(gene="FLC", species="Arabidopsis thaliana", _session=session)

        assert "NCBI API key" in result1["summary"], (
            "Rate limit note should appear in first call summary"
        )
        assert "NCBI API key" not in result2["summary"], (
            "Rate limit note must NOT appear in second call summary"
        )


class TestCacheBehaviour:
    def setup_method(self):
        _lit_module._pubmed_rate_limit_warned = False

    def test_cache_hit_skips_network(self):
        """When get_cached returns a value, request_json is not called."""
        session = _make_session(ncbi_key="fake-key")
        cached_result = {
            "summary": "Cached PubMed result",
            "query_used": "FLC[Title/Abstract] AND Arabidopsis thaliana[Organism]",
            "total_count": 5,
            "articles": [{"pmid": "99999"}],
            "species": "Arabidopsis thaliana",
            "gene": "FLC",
        }

        with (
            patch(_BINOMIAL_TARGET, return_value="Arabidopsis thaliana"),
            patch(_GET_CACHED_TARGET, return_value=cached_result),
            patch(_REQUEST_JSON_TARGET) as mock_rj,
        ):
            result = _call_tool(gene="FLC", species="Arabidopsis thaliana", _session=session)

        mock_rj.assert_not_called()
        assert result == cached_result
