# Test Suite

**Parent:** `./AGENTS.md`

## OVERVIEW

Pytest-based test suite with unit, API, and integration tests.

## STRUCTURE

```
tests/
├── unit/                  # Unit tests
│   ├── test_provider_validator.py
│   ├── test_google_embedder.py
│   └── test_all_embedders.py
├── api/                   # API tests
│   └── test_api.py
└── integration/           # Integration tests
    └── test_full_integration.py
```

## CONVENTIONS

- pytest configuration in `pytest.ini`
- Tests use `if __name__ == "__main__"` for direct execution
- No conftest.py (simple setup)

## COMMANDS

```bash
pytest                    # Run all tests
pytest tests/unit/        # Unit only
pytest tests/api/        # API only
pytest tests/integration/ # Integration only
```
