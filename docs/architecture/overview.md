# Architecture Overview

## System Design

TechWatch is a CLI-first, daemon-second application for automated tech product research and deal tracking.

```
┌─────────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐    ┌──────────┐
│   CLI/User  │───▶│ Planner  │───▶│  Adapters  │───▶│  Scorer  │───▶│  Output  │
│  (Typer)    │    │  (LLM)   │    │ (API/Web)  │    │ (Determ) │    │ (Rich)   │
└─────────────┘    └──────────┘    └────────────┘    └──────────┘    └──────────┘
       │                                                  │
       │           ┌──────────┐    ┌────────────┐         │
       └──────────▶│  Watch   │───▶│ Scheduler  │─────────┘
                   │  System  │    │(APScheduler)│
                   └──────────┘    └────────────┘
                                        │
                                   ┌────────────┐
                                   │   Email    │
                                   │  (SMTP)    │
                                   └────────────┘
```

## Data Flow

### Search Pipeline

```
User Query ──▶ SearchQuery (Pydantic)
  │
  ├──▶ PlannerAgent (LLM) ──▶ SearchPlan
  │         │
  │         └──▶ SourceSelector (deterministic) ──▶ AdapterSelection[]
  │                     │
  │                     ├──▶ BestBuyProductsAdapter ──▶ raw JSON
  │                     ├──▶ BestBuyOpenBoxAdapter  ──▶ raw JSON
  │                     ├──▶ EbayBrowseAdapter      ──▶ raw JSON
  │                     └──▶ JsonLdExtractor        ──▶ raw JSON
  │                              │
  │                     NormalizationEngine (deterministic)
  │                              │
  │                     ┌────────▼────────┐
  │                     │  Product + Offer │ (canonical domain models)
  │                     └────────┬────────┘
  │                              │
  │                     ScoringEngine (deterministic, weighted 35/30/15/10/10)
  │                              │
  │                     ┌────────▼────────┐
  │                     │    Analysis     │ (score components + overall)
  │                     └────────┬────────┘
  │                              │
  │                     ExplainerAgent (LLM, explain-only)
  │                              │
  └─────────── SearchResponse ◀──┘
```

### Watch Pipeline

```
Watch (stored in SQLite) ──▶ APScheduler cron trigger
  │
  ├──▶ Execute SearchPipeline
  │         │
  │         └──▶ DealAnalyst (deterministic trigger evaluation)
  │                     │
  │                     ├──▶ price_drop_pct: compare vs 30-day median
  │                     ├──▶ price_below:    absolute threshold
  │                     └──▶ new_offer_rank: rank threshold
  │                              │
  │                     AlertDecision
  │                              │
  │         ┌────────────────────┤
  │         │ if should_alert:   │
  │         │                    ▼
  │         │           DigestRenderer ──▶ SMTP Adapter
  │         │           (Babel i18n)      (TLS + CAN-SPAM)
  │         │
  │         └──▶ WatchRunRow (logged in DB)
  └──────────────────────────────────────────
```

## Module Boundaries

| Module | Responsibility | LLM? |
|--------|---------------|------|
| `adapters/` | Fetch raw data from APIs and web | No |
| `normalization/` | Map raw data to canonical models | No |
| `scoring/` | Compute deterministic scores | No |
| `taxonomy/` | Category resolution and mapping | No |
| `agents/` | LLM planning and explanation | Yes (constrained) |
| `persistence/` | SQLite storage and history | No |
| `scheduling/` | Watch execution and cron | No |
| `email/` | SMTP delivery and rendering | No |
| `evals/` | Golden fixtures and regression testing | No |
| `cli/` | User-facing commands | No |

## Key Invariants

1. **Deterministic Core**: Normalization, scoring, and deal detection are pure Python functions with no LLM dependency
2. **3-Axis Condition**: Every offer has `CanonicalCondition` + `FunctionalState` + `CosmeticGrade`
3. **Atomic Persistence**: `OfferRepo.upsert` handles both the offer record and price history snapshot in one transaction
4. **Currency Lossless**: Original amounts are always preserved; conversions return `None` when unavailable
5. **Domain Allowlist**: All HTTP outbound goes through `check_domain_allowlist()` except the JSON-LD extractor
