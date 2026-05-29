# Page Template

Copy this file when documenting a dimension, fact, or measure. Delete the
guidance in _italics_ as you fill each section. Keep the section order — it makes
every reference page scannable. See [Standard Cost](./standard-cost.md) for a
worked example.

---

# Entity Name

> **Type:** _Dimension | Fact | Measure_ · **Primary home:** _table_ ·
> **Also surfaced on:** _other tables, if any_

## Summary

_One or two sentences: what it is, who uses it, and — just as important — what it
is NOT (the thing people confuse it with)._

## Grain

_For a fact: "one row per ___". For a dimension: what one row represents. State
the grain as an explicit key tuple._

```text
grain = (..., ...)
```

## Schema

| Column | Type | Role | Notes |
|---|---|---|---|
| `..._sk` | BIGINT | surrogate PK | |
| `..._sk` | BIGINT | FK → `dim_...` | |
| ... | ... | measure / attribute / degenerate | |

## Source & lineage

_Source system/table → staging model → this object. A small ASCII diagram helps._

## How to use it

_Copy-pasteable SQL for the 1–3 most common questions. Show the correct
point-in-time join if history matters._

```sql
SELECT ...
```

## Common Pitfalls

_The traps: point-in-time vs current joins, additive vs semi-/non-additive
measures, double-counting, currency/UoM, NULL handling, grain mismatches. Be
specific — this is the highest-value section._

## Related

_Links to neighbouring dimensions/facts and relevant [Concepts](../concepts/)._

## Change history / SCD

_How history is tracked: SCD Type 1/2/3, snapshot cadence, effective dating._
