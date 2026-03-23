# TechWatch

> 🔍 **Agentic CLI tech purchase research assistant** — research tech products, track prices over time, get deal alerts.

TechWatch is a CLI-first, daemon-second application that helps you decide **what to buy**, **whether it's worth buying now**, and **whether it got better or worse since the last time you looked**.

## Why Agentic?

Tech buying involves ambiguous tradeoffs, changing source schemas, unstructured product pages, and context-sensitive decisions. TechWatch uses AI agents for what they're good at — **planning** and **explaining** — while keeping normalization, scoring, and ranking **deterministic and inspectable**.

| Deterministic (no LLM) | Agentic (LLM-powered) |
|------------------------|----------------------|
| Condition normalization | Intent → search plan |
| Price scoring | Buyer-facing explanations |
| Delivery scoring | Deal narrative generation |
| Ranking formula | Watch trigger summaries |

## Source Support

| Source | Type | Status |
|--------|------|--------|
| Best Buy Products API | Official API | ✅ Implemented |
| Best Buy Open Box API | Official API | ✅ Implemented |
| eBay Browse API | Official API | ✅ Implemented |
| eBay Taxonomy API | Official API | ✅ Implemented |
| Structured Data (JSON-LD) | Web extraction | ✅ Implemented |
| ECB Exchange Rates | Reference rates | ✅ Implemented |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Search for products
techwatch search "used thinkpad x1 carbon" --budget 900 --conditions used,refurbished

# Create a price watch
techwatch watch create "oled gaming monitor 27 240hz" \
  --budget 650 --schedule "0 9 * * *" \
  --email you@example.com \
  --trigger "price_drop_pct>=8"

# Manage watches
techwatch watch list
techwatch watch pause WATCH_ID

# Run daemon for background monitoring
techwatch run daemon
```

## Architecture

```
CLI → Command Handler → Search Orchestrator
  → Planner Agent (LLM)     → Intent to structured plan
  → Source Selector          → Choose adapters
  → Adapter Tools            → Fetch raw data (Best Buy, eBay, JSON-LD)
  → Normalization Engine     → Deterministic canonical mapping
  → Deterministic Scorer     → Weighted ranking (35% spec, 30% cost, 15% delivery, 10% condition, 10% trust)
  → Explanation Agent (LLM)  → Buyer-facing prose
  → Results Store            → SQLite persistence + price history
  → Digest Renderer          → Email alerts
```

### Deterministic Ranking

| Component | Weight | Description |
|-----------|--------|-------------|
| Spec Fit | 35% | How well specs match requirements |
| Total Landed Cost | 30% | Price + shipping + fees |
| Delivery | 15% | Speed and pickup availability |
| Condition Confidence | 10% | 3-axis condition assessment |
| Seller/Source Trust | 10% | Marketplace and seller reputation |

### Condition Normalization

Every condition is split into **three independent axes**, because marketplaces treat them differently:

- **Canonical condition** — `new`, `open_box`, `certified_refurbished`, `used_good`, etc.
- **Functional state** — `fully_functional`, `minor_issues`, `for_parts`, `unknown`
- **Cosmetic grade** — `pristine`, `excellent`, `good`, `fair`, `poor`, `unknown`

## Development

```bash
# Setup
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"

# Quality checks
ruff check .
mypy src/
pytest tests/
```

## Project Structure

```
src/techwatch/
├── cli/            # Typer commands
├── agents/         # LLM-powered planning & explanation
├── adapters/       # Source data fetchers (Best Buy, eBay, JSON-LD, ECB)
├── normalization/  # Deterministic condition/category/price mapping + trends
├── scoring/        # Deterministic ranking engine
├── taxonomy/       # Category resolution (Best Buy, eBay, canonical)
├── persistence/    # SQLAlchemy models and repositories
├── scheduling/     # APScheduler watch execution
├── email/          # SMTP adapter and digest rendering
├── evals/          # Golden fixtures and regression testing
└── config/         # Pydantic settings
```

## License

MIT
