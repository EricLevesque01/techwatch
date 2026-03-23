# Contributing to TechWatch

Thank you for your interest in contributing!

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

## Quality Checks

Before submitting a PR, ensure all checks pass:

```bash
ruff check .           # Lint
ruff format .          # Format
mypy src/              # Type check
pytest tests/ -x       # Tests
```

## Architecture Rules

1. **Adapters only fetch** — no normalization, scoring, or LLM calls
2. **Normalization is deterministic** — no LLM calls in `normalization/`
3. **Scoring is deterministic** — no LLM calls in `scoring/`
4. **LLMs plan and explain** — never mutate normalized facts

## Testing Requirements

- Every feature needs unit tests
- Scoring changes need golden fixture updates
- LLM schema changes need contract tests
- Normalization changes need parametrized tests for all marketplace variants

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Run all quality checks
4. Open a PR using the template
5. Wait for review from code owners (required for protected paths)
