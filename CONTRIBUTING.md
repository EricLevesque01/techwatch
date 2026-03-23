# Contributing to TechWatch

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Development Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
techwatch --help
```

## Quality Checks

All checks must pass before opening a PR:

```bash
ruff check .           # Lint (identifies issues)
ruff format .          # Format (auto-fixes style)
mypy src/              # Type check (strict mode)
pytest tests/ -x       # Run full test suite (stop on first failure)
```

## Architecture Rules

These are **non-negotiable**. Do not violate them without explicit approval.

1. **Adapters only fetch** — no normalization, scoring, or LLM calls in adapter code
2. **Normalization is deterministic** — no LLM calls in `src/techwatch/normalization/`
3. **Scoring is deterministic** — no LLM calls in `src/techwatch/scoring/`
4. **LLMs plan and explain** — agent outputs go through strict Pydantic validation; they never mutate normalized facts
5. **Condition is always 3-axis** — `canonical_condition`, `functional_state`, `cosmetic_grade`. Never collapse to a single enum
6. **Currency is lossless** — always preserve original amount + currency alongside converted values
7. **Times are UTC internally** — use `zoneinfo` for IANA timezone display, not `pytz`

## Testing Requirements

| Change Type | Required Tests |
|:--|:--|
| New feature | Unit tests in `tests/unit/` |
| Ranking change | Golden fixture updates in `tests/golden/` |
| LLM schema change | Contract tests in `tests/contracts/` |
| Normalization change | Parametrized tests covering all marketplace variants |
| New adapter | Integration test + mock fixture |

## Code Style

- **Formatter/Linter:** Ruff (`ruff check .` and `ruff format .`)
- **Type checker:** mypy strict mode (`mypy src/`)
- **Imports:** sorted by isort (integrated in Ruff)
- **Line length:** 100 characters
- **Docstrings:** Google style

## Protected Paths

These require explicit code-owner approval to modify:

- `.github/workflows/*`
- `docs/architecture/*`
- `src/techwatch/normalization/*`
- `src/techwatch/scoring/*`
- `AGENTS.md`
- `CODEOWNERS`

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with corresponding tests
3. Run all quality checks locally
4. Open a PR using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
5. Wait for review from code owners (required for protected paths)
6. Squash-merge when approved

## Source Compliance

When adding a new data source:

1. **Prefer official APIs** over scraping
2. **Prefer structured data (JSON-LD)** when APIs are unavailable
3. **Check `robots.txt`** and legal guidance before any scraping
4. **Do not add authenticated scraping** (no retailer account login in v1)
5. **Respect per-source rate limits** — every adapter must define `max_qps`, `burst`, `cache_ttl`
6. **All HTTP fetches** must go through the domain allowlist in `src/techwatch/adapters/base.py`
