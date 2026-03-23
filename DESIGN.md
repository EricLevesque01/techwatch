# Technical Design: Agentic CLI Tech Purchase Research Assistant

> **TechWatch** — A CLI-first, daemon-second application that researches technology products across online sources, tracks prices over time, and emails updates when the market changes in ways a buyer would care about.

---

## 1. Vision & Motivation

The core reason to build this as an **agentic system** is that tech buying involves ambiguous tradeoffs, changing source schemas, unstructured product pages, exceptions in used-item condition, and context-sensitive decisions around delivery, total cost, and trustworthiness.

The recommended product is a **CLI-first, daemon-second application**: the user runs searches and manages alerts through commands, while a local scheduler performs background refreshes and email digests.

### Ingestion Strategy

| Priority | Source Type | Examples |
|----------|------------|---------|
| 1st | Official APIs | Best Buy (Products, Categories, Recommendations, Open Box), eBay (Browse, Taxonomy, Metadata) |
| 2nd | Structured Data | Google merchant listing conventions, Schema.org Product/Offer markup (JSON-LD) |
| 3rd | HTML Scraping | Last resort, after robots.txt and legal review |

### Architectural Philosophy

- Use **OpenAI tool calling** and **structured outputs** for reliable JSON at every model boundary
- Add **tracing** for debugging
- Keep **orchestration in application code** so the project stays understandable

| Framework | Relationship | Why |
|-----------|-------------|-----|
| **LangGraph** | Borrow patterns | Durable execution, pause/resume, memory |
| **CrewAI** | Design reference | "Crew + flow" separation |
| **AutoGen** | Conceptual only | Currently in maintenance mode |

---

## 2. Product & Requirements

### 2.1 Core User Job

> *Help me decide what to buy, whether it is worth buying now, and whether it got better or worse since the last time I looked.*

The system needs a canonical category and facet model that borrows from retailer taxonomies:

- **Best Buy Categories API** — hierarchical paths and category/subcategory traversal
- **Best Buy Products API** — generic spec pairs via `details.name` / `details.value`
- **eBay Taxonomy API** — recursive category subtrees and leaf nodes
- **Google / Schema.org** — portable minimum shape for Product + Offer extraction

### 2.2 Functional Requirements

#### FR-1: Intent-Driven Search
Support queries like "best used ultrabook under $700," "new OLED monitor with USB-C," or "deal watch for M3 MacBook Air." The planner converts intent into category, facets, and source strategy using retailer taxonomy signals and structured outputs.

#### FR-2: Location as First-Class Input
Every saved search includes at minimum `country`, and preferably `postal_code`. eBay's delivery accuracy depends on `contextualLocation`; Best Buy Open Box fulfillment depends on nearest store.

#### FR-3: Multi-Condition Support
Support new, open-box, certified refurbished, refurbished, and used offers in the same result set. Keep source-specific truth alongside canonical labels.

| Source | Condition Details |
|--------|------------------|
| Best Buy Open Box | Excellent, Certified |
| eBay | Category-specific condition IDs and policies |
| Swappa | Appearance grades + functionality requirements |
| Back Market | Fair, Good, Excellent, Premium (100% functional guarantee) |

#### FR-4: Price & Availability History
Persist price, shipping, and availability history. Best Buy exposes `regularPrice`, `salePrice`, `savings`, `priceUpdateDate`; eBay sorts by total cost and exposes converted amounts; Google merchant guidance treats price, shipping, handling time, transit time as buyer-visible fields.

#### FR-5: Scheduled Watches & Email Digests
Watches with query, filters, schedule, max result count, alert thresholds, destination email, timezone. Cron-like and interval triggers. Jobs survive restarts through persistent storage.

#### FR-6: Buyer-Facing Explanations
Explain why a result ranked highly: spec fit, total cost, delivery timing, condition confidence, seller trust, trend vs. recent price history. LLM writes explanations, but ranking inputs must be **deterministic and inspectable**.

#### FR-7: Research-Only in v1
No auto-purchase, auto-bid, or retailer account login. Human approval mandatory for any future action that changes state outside the user's local environment.

### 2.3 Non-Goals (v1)

Full checkout automation, seller account automation, authenticated browser automation, review summarization at internet scale, hosted multi-user backend.

---

## 3. Data & Decision Model

### 3.1 Canonical Domain Model

Vendor-neutral, but visibly traceable back to the source:

```json
{
  "product": {
    "canonical_product_id": "source:marketplace:item_id",
    "title": "string",
    "brand": "string|null",
    "model": "string|null",
    "upc_gtin": "string|null",
    "canonical_category": "laptop",
    "source_category_path": ["Electronics", "Computers & Tablets", "Laptops"],
    "specs": {
      "cpu": "Apple M3",
      "ram_gb": 16,
      "storage_gb": 512,
      "screen_in": 13.6,
      "gpu": null
    }
  },
  "offer": {
    "offer_id": "string",
    "source": "bestbuy|ebay|structured_web",
    "condition": {
      "canonical": "used_good",
      "source_label": "Good",
      "functional_state": "fully_functional|unknown",
      "cosmetic_grade": "fair|good|excellent|premium|unknown"
    },
    "pricing": {
      "list_amount": 999.99,
      "sale_amount": 899.99,
      "currency": "USD",
      "converted_amount": 899.99,
      "converted_currency": "USD",
      "shipping_amount": 0.0,
      "known_tax_included": false,
      "price_updated_at": "2026-05-03T12:00:00Z"
    },
    "delivery": {
      "service_level": "Standard",
      "earliest_delivery_at": "2026-05-06T00:00:00Z",
      "latest_delivery_at": "2026-05-08T00:00:00Z",
      "pickup_available": true
    },
    "merchant": {
      "seller_name": "string|null",
      "marketplace": "Best Buy",
      "seller_type": "retailer|marketplace_seller|unknown"
    },
    "raw_source_ref": "adapter-specific pointer"
  },
  "analysis": {
    "fit_score": 0.0,
    "value_score": 0.0,
    "delivery_score": 0.0,
    "condition_score": 0.0,
    "overall_score": 0.0,
    "explanation": "string"
  }
}
```

### 3.2 Condition Normalization

Split condition into three fields: `canonical_condition`, `functional_state`, and `cosmetic_grade`. This is required to represent current marketplace behavior correctly:

| Marketplace | Functionality Model | Appearance Model |
|-------------|-------------------|-----------------|
| Back Market | 100% functional guarantee | Fair / Good / Excellent / Premium |
| Swappa | Must be fully functional, not activation-locked | Appearance grades |
| eBay | Category-specific condition policies and IDs | Includes "Certified Refurbished" |
| Best Buy Open Box | Implied functional | Excellent / Certified |

### 3.3 Deterministic Ranking Formula

| Component | Weight | Description |
|-----------|--------|-------------|
| Spec Fit | 35% | How well item matches requirements |
| Total Landed Cost | 30% | Item price + shipping + mandatory charges |
| Delivery | 15% | Speed and reliability |
| Condition Confidence | 10% | Trustworthiness of condition assessment |
| Seller/Source Trust | 10% | Marketplace and seller reputation |

On top of deterministic scores, the agent generates:
- Plain-language explanation of ranking
- Watch trigger reason (e.g., "price dropped 11% vs 30-day median")

### 3.4 Currency & Time Handling

**Currency:** Preserve original amount/currency from source. Store converted display amount from ECB reference rates. Mark `converted_amount` as `null` when unavailable. Never fabricate precision.

**Time:** UTC for run times. IANA timezone strings for user preferences. `zoneinfo` for rendering. `Babel` for locale-aware formatting.

---

## 4. Agentic System Architecture

### 4.1 Design Philosophy

A **thin orchestrator with specialist tools**, not a heavyweight autonomous swarm. OpenAI tool-calling provides the multi-step loop; structured outputs constrain JSON; tracing provides audit.

### 4.2 Runtime Layout

```
CLI command
  → Command handler
    → Search orchestrator
      → Planner agent
      → Source selector
      → Adapter tools
           - bestbuy_products, bestbuy_categories, bestbuy_open_box
           - ebay_browse, ebay_taxonomy
           - generic_product_jsonld
           - fx_rates, email_sender
      → Normalization engine
      → Deterministic scorer
      → Explanation agent
      → Results store / watch store
      → Digest renderer / scheduler
```

### 4.3 Specialist Definitions

| Specialist | Responsibility | Type |
|-----------|---------------|------|
| **Planner Agent** | Intent → category, facets, budget, source preference | LLM + structured output |
| **Source Selector** | Choose adapters and ordering | Deterministic |
| **Adapter Tools** | Fetch raw source data only | HTTP clients |
| **Normalization Engine** | Raw → canonical model | Deterministic Python |
| **Deal Analyst** | Thresholds + optional LLM explanation | Hybrid |
| **Digest Writer** | Ranked deltas → email prose | LLM for prose |

> **Invariant:** Adapters only fetch. Normalization is deterministic. Scoring is deterministic. LLMs may plan and explain, never mutate normalized facts.

### 4.4 Structured Output Contracts

| Agent | Output Schema | Validation |
|-------|--------------|------------|
| Planner | `SearchPlan` | Strict Pydantic |
| Explanation | `OfferNarrative` | Strict Pydantic |
| Watch Analyzer | `AlertDecision` | Strict Pydantic |

### 4.5 Guardrails

1. **Domain allowlist** — Restrict fetchers to trusted marketplaces/retailer domains
2. **Human approval** — Required for any action beyond data retrieval and local email
3. **Failure thresholds** — Watch jobs exit cleanly when a source breaks
4. **OWASP baseline** — Domain and protocol restrictions for URL following

---

## 5. CLI & Operations Specification

### 5.1 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| CLI | Typer | Type hints, clean subcommands |
| Persistence | SQLAlchemy | Transaction boundaries, ORM |
| Scheduling | APScheduler | Persistent schedules, background jobs |
| HTTP | HTTPX | Sync/async, default timeouts |
| Browser | Playwright | Only for adapters requiring rendering |
| Email | smtplib + EmailMessage | Standard library |
| Timezones | zoneinfo | stdlib, IANA-based |
| Currency | Babel | Locale-aware formatting |
| Validation | Pydantic | Strict schema validation |
| Packaging | pyproject.toml + console_scripts | Standard Python packaging |
| Lint/Format | Ruff | Fast, comprehensive |
| Types | mypy | Static typing |

### 5.2 CLI Interface

```bash
# Search
techwatch search "used thinkpad x1 carbon" \
  --budget 900 --country US --postal-code 10001 \
  --currency USD --conditions used,refurbished,open_box --top 15

# Compare & Explain
techwatch compare OFFER_ID_1 OFFER_ID_2
techwatch explain OFFER_ID

# Watch Management
techwatch watch create "oled gaming monitor 27 240hz" \
  --budget 650 --country US --postal-code 10001 \
  --schedule "0 9 * * *" --timezone "America/New_York" \
  --email "user@example.com" \
  --trigger "price_drop_pct>=8 OR new_offer_rank<=3"

techwatch watch list
techwatch watch pause WATCH_ID
techwatch watch resume WATCH_ID
techwatch watch delete WATCH_ID

# Execution
techwatch run once WATCH_ID
techwatch run daemon

# Utilities
techwatch source test bestbuy
techwatch source test ebay
techwatch email test
techwatch export WATCH_ID --format csv
```

### 5.3 Scheduling & Email

Daemon mode: load due watches → execute → persist snapshots → send digests. Email via `EmailMessage` with replaceable SMTP adapter. Model `subscription_status`, `digest_frequency`, `last_opt_out_at` from day one.

### 5.4 Adapter Compliance

Every adapter implements: rate limiting (`max_qps`, `burst`, `quota_scope`), retry with jittered exponential backoff, local caching (`cache_ttl`), budget awareness, structured logging. Priority: API first → structured data → HTML/browser.

---

## 6. Test & Quality Strategy

### 6.1 Testing Framework

pytest, heavy parametrization, monkeypatch for secrets, HTTPX transports for in-process testing, Playwright network mocking, Pydantic strict validation, GitHub Actions CI.

### 6.2 Required Automated Tests

| Category | Coverage |
|----------|----------|
| Canonical Taxonomy | Map retailer categories → internal taxonomy |
| Condition Normalization | BB Open Box, eBay Certified Refurb, Swappa, Back Market → canonical fields |
| Currency | Preserve original; verify conversion/fallback |
| Delivery | Shipping-level, min/max windows, local pickup |
| Deal Detection | Sale-vs-regular and historical trend logic |
| Ranking | Golden fixtures for top-N with score components |
| CLI Integration | Watch CRUD, run-once, email-test under temp DB |
| Digest Rendering | Golden markdown/plaintext by locale and timezone |
| Failure Paths | Timeout, malformed JSON-LD, stale FX, rate-limit exhaustion |
| LLM Contracts | Every agent output validates strict schema or fails closed |

### 6.3 Evaluation Corpus

Build ~hundreds of stored search intents with expected outcomes. Establish baseline with strongest model first, then optimize for cost/latency.

### 6.4 CI Gates

Lint/format (Ruff) → Type check (mypy) → Unit/integration (pytest) → Eval smoke tests. Browser tests in nightly matrix. Code-owner review for workflows. Branch protection with passing checks.

---

## 7. Repository Structure

```
techwatch/
├── AGENTS.md
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CODEOWNERS
├── pyproject.toml
├── .env.example
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── nightly-browser-adapters.yml
│   │   └── release.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   ├── feature_request.yml
│   │   └── source_adapter_request.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
├── docs/
│   ├── product/ (vision.md, user-stories.md, roadmap.md)
│   ├── architecture/ (system-overview.md, data-model.md, adapter-contract.md, scoring-model.md, scheduling-and-email.md, security.md)
│   ├── adr/ (adr-cli-first.md, adr-api-first-ingestion.md, adr-condition-normalization.md, adr-deterministic-ranking.md)
│   └── operations/ (runbook.md, rate-limits.md, incident-response.md)
├── src/techwatch/
│   ├── cli/
│   ├── agents/
│   ├── adapters/
│   ├── taxonomy/
│   ├── normalization/
│   ├── scoring/
│   ├── scheduling/
│   ├── email/
│   ├── persistence/
│   ├── evals/
│   └── config/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contracts/
│   ├── browser/
│   ├── golden/
│   └── fixtures/
└── scripts/
    ├── bootstrap.sh
    ├── export-fixtures.py
    └── seed-dev-db.py
```

---

## 8. Open Questions & Limitations

1. **API Access** — Verify Best Buy API key access level, rate limits, and commercial restrictions before broad deployment
2. **Delivery Precision** — eBay delivery accuracy improves with buyer `contextualLocation`; some item types return no dates. CLI must say "delivery unknown" when appropriate
3. **FX Normalization** — ECB doesn't cover all currencies (e.g., EUR/RUB suspended). Compare in original currency first, converted value second, mark unavailable/stale clearly
4. **Structured Data Coverage** — Not every retailer exposes quality Product/Offer markup. Some adapters may remain unsupported until compliant source surfaces exist
5. **Multi-User Evolution** — Separate privacy/compliance pass needed for email subscriptions, secrets management, account isolation, remote fetch security
