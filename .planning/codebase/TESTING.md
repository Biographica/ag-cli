# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Runner:**
- pytest 8.0+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
- Testpaths configured: `tests/`

**Assertion Library:**
- pytest built-in assertions (`assert`)
- No external assertion library; standard Python `assert` statements used throughout

**Run Commands:**
```bash
pytest tests/ -v                    # Run all tests
pytest tests/ -k test_name          # Run specific test
pytest tests/ --run-e2e             # Run end-to-end tests (hit real APIs)
pytest tests/ --cov=src/ct          # Run with coverage
pytest tests/ -x                    # Stop on first failure
```

**Markers defined in `pyproject.toml`:**
- `e2e`: end-to-end tests hitting real APIs (skip by default, run with `--run-e2e`)
- `docker`: tests requiring Docker (skip by default, run with `--run-e2e`)
- `e2e_matrix`: optional live multi-prompt end-to-end matrix (set `CT_RUN_E2E_MATRIX=1`)
- `api_smoke`: optional live API smoke tests (set `CT_RUN_API_SMOKE=1`)

## Test File Organization

**Location:**
- Colocated in `tests/` directory at repository root
- Pattern: one test file per major module or domain
- Examples: `tests/test_target.py`, `tests/test_registry.py`, `tests/test_repurposing.py`, `tests/test_engine.py`, `tests/test_knowledge.py`

**Naming:**
- Test files: `test_*.py` prefix
- Test classes: `Test{Module}` (e.g., `TestNeosubstrateScore`, `TestRepurposingCmapQuery`, `TestToolRegistry`)
- Test methods: `test_*` prefix (e.g., `test_returns_top_targets`, `test_scoring_fields_present`, `test_register_decorator`)

**Structure:**
```
tests/
├── conftest.py              # Shared pytest fixtures and configuration
├── test_registry.py         # Tool registry tests
├── test_target.py           # Target discovery tool tests
├── test_repurposing.py      # Repurposing tool tests
├── test_engine.py           # Query engine tests (DuckDB)
├── test_knowledge.py        # Knowledge primer consistency tests
├── test_structure.py        # Structure/docking tool tests
└── ... (60+ test files)
```

## Test Structure

**Suite Organization:**
```python
class TestNeosubstrateScore:
    def _make_proteomics(self, n_proteins=100, n_compounds=20):
        """Helper: Generate mock proteomics data."""
        np.random.seed(42)
        proteins = [f"PROT_{i}" for i in range(n_proteins)]
        compounds = [f"COMP_{i}" for i in range(n_compounds)]
        data = np.random.randn(n_proteins, n_compounds) * 0.3
        data[0, :3] = -1.5  # Make some proteins strongly degraded
        return pd.DataFrame(data, index=proteins, columns=compounds)

    @patch("ct.data.loaders.load_proteomics")
    def test_returns_top_targets(self, mock_load):
        """Test that tool returns top_targets key."""
        from ct.tools.target import neosubstrate_score
        mock_load.return_value = self._make_proteomics()

        result = neosubstrate_score(top_n=10)

        assert "summary" in result
        assert "top_targets" in result
        assert len(result["top_targets"]) <= 10
```

**Patterns:**
- Setup methods named `_make_*` (e.g., `_make_proteomics()`, `_mock_uniprot_response()`)
- No explicit setUp/tearDown; use fixtures or inline setup in test methods
- Mocking via `@patch()` decorator or context manager
- Fixtures defined in `conftest.py` (e.g., `captured_console`)

## Mocking

**Framework:** `unittest.mock` (part of Python standard library)

**Patterns:**
```python
from unittest.mock import patch, MagicMock

@patch("ct.data.loaders.load_proteomics")
def test_returns_top_targets(self, mock_load):
    mock_load.return_value = self._make_proteomics()
    result = neosubstrate_score(top_n=10)
    assert "summary" in result
```

**Multiple mocks stacked:**
```python
@patch("ct.data.loaders.load_l1000", side_effect=FileNotFoundError("missing"))
@patch("ct.tools.repurposing.request_json")
def test_no_remote_call_when_allow_remote_false(self, mock_request_json, _mock_l1000):
    mock_request_json.assert_not_called()
    assert result["data_unavailable"] is True
```

**What to Mock:**
- Data loaders: `@patch("ct.data.loaders.load_X")`
- HTTP requests: `@patch("ct.tools.repurposing.request_json")`
- External API responses with side effects for conditional behavior
- Don't mock core business logic; test actual computation

**What NOT to Mock:**
- Core domain algorithms (e.g., scoring formulas should run)
- Data structures (e.g., allow pandas DataFrames to process normally)
- Return dict construction (test the full tool output)

## Fixtures and Factories

**Test Data:**
```python
def _make_proteomics(self, n_proteins=100, n_compounds=20):
    """Factory helper for proteomics DataFrame."""
    np.random.seed(42)
    proteins = [f"PROT_{i}" for i in range(n_proteins)]
    compounds = [f"COMP_{i}" for i in range(n_compounds)]
    data = np.random.randn(n_proteins, n_compounds) * 0.3
    # Make a few proteins strongly degraded by few compounds (selective)
    data[0, :3] = -1.5  # PROT_0: degraded by 3 compounds
    data[1, :1] = -2.0  # PROT_1: strongly degraded by 1 compound
    return pd.DataFrame(data, index=proteins, columns=compounds)
```

**Fixture example from `conftest.py`:**
```python
@pytest.fixture
def captured_console():
    """Yield a (console, buffer) tuple for capturing Rich output."""
    from io import StringIO
    from rich.console import Console
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    return console, buf
```

**Location:**
- Test class helpers: defined as `_make_*` methods in test class
- Shared fixtures: in `tests/conftest.py`
- No separate factories directory; factories are methods or functions within test modules

## Coverage

**Requirements:** No explicit coverage targets enforced

**View Coverage:**
```bash
pytest tests/ --cov=src/ct --cov-report=html
```

**Coverage behavior:**
- Optional pytest-cov plugin installed in dev extras
- HTML report generated to `htmlcov/` (not committed)
- No minimum coverage threshold enforced in CI

## Test Types

**Unit Tests:**
- Scope: Individual tool functions with mocked data loaders
- Approach: Mock external dependencies, test algorithm logic
- Location: `tests/test_*.py` for each tool module
- Example: `test_neosubstrate_score()` tests scoring formula with synthetic data

**Integration Tests:**
- Scope: Tool-to-tool interactions and multi-step workflows
- Approach: May use temp files or in-memory data
- Location: Marked with `@pytest.mark.integration` (not commonly used)
- Example: `test_query_parquet_file()` integrates QueryEngine with file I/O

**E2E Tests:**
- Framework: Not a separate test framework; marked with `@pytest.mark.e2e` or `e2e` in test name
- Approach: Hit real APIs, require `--run-e2e` flag or environment variables
- Marked to skip by default in `conftest.py`: `pytest_collection_modifyitems()` skips tests with `e2e` in nodeid or keywords
- Environmental controls: `CT_RUN_E2E_MATRIX=1`, `CT_RUN_API_SMOKE=1` enable optional suites

## Common Patterns

**Async Testing:**
```python
# Not commonly used; most tests are synchronous
# For SDK-related async tests, pytest-asyncio would be needed (not configured)
```

**Error Testing:**
```python
def test_no_degradation(self, mock_load):
    """Test when no proteins meet degradation threshold."""
    from ct.tools.target import neosubstrate_score
    # All values above -0.5 threshold → no degradation detected
    data = pd.DataFrame(
        np.ones((10, 5)) * 0.1,
        index=[f"P{i}" for i in range(10)],
        columns=[f"C{i}" for i in range(5)],
    )
    mock_load.return_value = data

    result = neosubstrate_score()

    assert result["n_proteins_scored"] == 0
    assert result["top_targets"] == []
```

**Parametrized Testing:**
```python
@pytest.mark.parametrize("assay_type", list(ASSAY_TEMPLATES.keys()))
def test_assay_template_loading(self, assay_type):
    """Test each assay template."""
    # Test logic here
```

**FileSystem Testing:**
```python
def test_custom_proteomics_path(self, tmp_path):
    """Test loading custom CSV file."""
    from ct.tools.target import neosubstrate_score
    csv_path = tmp_path / "prot.csv"
    data = pd.DataFrame(...)
    data.to_csv(csv_path)

    result = neosubstrate_score(proteomics_path=str(csv_path), top_n=5)

    assert result["n_proteins_scored"] >= 1
```

**Skipif Decorators:**
```python
@pytest.mark.skipif(not _rdkit_available(), reason="RDKit not installed")
def test_valid_smiles(self, tmp_path):
    """Test SMILES processing requires RDKit."""
```

## Special Patterns

**Module-level conftest helpers:**
- `has_api_key()`: Check if `ANTHROPIC_API_KEY` set
- `_has_cellxgene()`: Try import `cellxgene_census`
- `pytest_addoption()`: Register custom flags like `--run-e2e`
- `pytest_collection_modifyitems()`: Skip tests based on markers/flags

**Example from `conftest.py`:**
```python
def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e", action="store_true", default=False,
        help="Run end-to-end tests that hit real APIs",
    )

def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-e2e"):
        return  # Run all tests
    # Skip e2e tests by default
    skip_e2e = pytest.mark.skip(reason="Need --run-e2e to run")
    for item in items:
        if "test_e2e" in item.nodeid or "e2e" in item.keywords:
            item.add_marker(skip_e2e)
```

---

*Testing analysis: 2026-02-25*
