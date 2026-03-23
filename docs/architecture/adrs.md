# ADR-001: Deterministic Scoring with LLM Explanation

## Status
Accepted

## Context
Tech buying involves ambiguous tradeoffs that might seem ideal for LLM-based ranking. However, we need reproducible, inspectable rankings that don't shift with model updates, token sampling, or prompt drift.

## Decision
**Scoring is deterministic Python.** The scoring engine uses a fixed weighted formula (35% spec fit, 30% value, 15% delivery, 10% condition, 10% trust) with no LLM calls.

LLMs are constrained to two phases:
- **Planning**: Converting user intent into structured `SearchPlan` (structured output)
- **Explanation**: Generating buyer-facing narratives from pre-computed scores (never overriding them)

## Consequences
- ✅ Rankings are reproducible and auditable
- ✅ Golden fixtures catch regressions
- ✅ System works without API keys (fallback plan)
- ⚠️ Edge cases (e.g., "I trust eBay sellers with 99.9% feedback more than retailers") require weight customization rather than LLM judgment

---

# ADR-002: 3-Axis Condition Model

## Status
Accepted

## Context
Different marketplaces describe product condition differently: Best Buy uses "Excellent/Satisfactory/Fair", eBay uses numeric IDs (1000/3000/7000), Back Market uses "Fair to New/Excellent/Good/Stallion".

## Decision
Every offer carries a 3-axis condition:
1. `CanonicalCondition` — normalized tier (new, open_box, certified_refurbished, etc.)
2. `FunctionalState` — does it work? (fully_functional, minor_issues, for_parts)
3. `CosmeticGrade` — how does it look? (pristine, excellent, good, fair, poor)

## Consequences
- ✅ Accurate cross-marketplace comparison
- ✅ Condition scoring separates function from aesthetics
- ⚠️ Some mappings are best-effort (e.g., eBay "Used" → USED_LIKE_NEW is optimistic)

---

# ADR-003: File-Based Response Cache

## Status
Accepted

## Context
API calls are expensive (rate-limited) and responses are relatively stable within short windows.

## Decision
Use a file-based cache (`ResponseCache`) with configurable TTL per adapter. Cache keys are derived from URL + params hash. Cache is stored under the config directory.

## Consequences
- ✅ Survives process restarts (unlike in-memory)
- ✅ Inspectable (JSON files on disk)
- ✅ TTL prevents stale data
- ⚠️ No cross-machine sharing (acceptable for CLI tool)
