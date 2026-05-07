# Tests

Test suite for Knowledge Base Platform.

## Structure

```
tests/
├── conftest.py           # Pytest configuration and fixtures
├── unit/                 # Unit tests (fast, isolated)
├── integration/          # Integration tests (database, API)
└── e2e/                  # End-to-end tests (full workflows)
```

## Running Tests

### All tests
```bash
pytest
```

### By category
```bash
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest tests/e2e/            # E2E tests only
```

### By marker
```bash
pytest -m unit               # Tests marked with @pytest.mark.unit
pytest -m integration        # Tests marked with @pytest.mark.integration
pytest -m "not slow"         # Skip slow tests
```

### With coverage
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Verbose output
```bash
pytest -v                    # Verbose
pytest -vv                   # Very verbose
pytest -s                    # Show print statements
```

### Specific test
```bash
pytest tests/unit/test_validators.py
pytest tests/unit/test_validators.py::TestValidateFileSize::test_valid_file_size
```

## Test Database

Integration and E2E tests use a separate test database: `knowledge_base_test`

The test database is:
- Created automatically before each test function
- Dropped automatically after each test function
- Isolated from development database

## Fixtures

Key fixtures available in all tests (defined in `conftest.py`):

### Database
- `test_db`: Async database session
- `sample_kb`: Pre-created knowledge base
- `sample_document`: Pre-created document

### API
- `test_client`: Async HTTP client for API testing

### Mock Data
- `mock_kb_data`: Dictionary with KB data
- `mock_document_data`: Dictionary with document data
- `sample_text`: Sample plain text
- `sample_markdown`: Sample markdown content

## Writing Tests

### Unit Test Example
```python
import pytest

@pytest.mark.unit
def test_something():
    """Test something in isolation."""
    result = my_function()
    assert result == expected
```

### Integration Test Example
```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_endpoint(test_client: AsyncClient):
    """Test API endpoint with database."""
    response = await test_client.get("/api/v1/endpoint")
    assert response.status_code == 200
```

### E2E Test Example
```python
import pytest

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_workflow(test_client, test_db):
    """Test complete user workflow."""
    # Create KB
    # Upload document
    # Query chat
    # Verify results
```

## Best Practices

1. **Use appropriate markers**: Mark tests with `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
2. **Test isolation**: Each test should be independent and not rely on other tests
3. **Use fixtures**: Leverage fixtures for common setup/teardown
4. **Clear assertions**: Use descriptive assertion messages
5. **Test edge cases**: Include tests for error conditions and edge cases
6. **Keep tests fast**: Unit tests should be < 1s, integration tests < 5s

## Coverage Goals

- Overall: 80%+
- Critical components (RAG, embeddings): 95%+
- Utilities: 90%+

## CI/CD

Tests are run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds

All tests must pass before merging.
