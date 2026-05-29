# Standard Cost

> **Type:** Measure (cost) · **Primary home:** `fact_standard_cost` (periodic
> snapshot) · **Also surfaced on:** `dim_product` (current value only)

## Summary

The **standard cost** is the predetermined, planned unit cost of a product —
materials + labour + allocated overhead — set during a periodic *cost roll*
(often annually or quarterly). It is used for inventory valuation, margin
reporting, and variance analysis against actual cost. It is **not** the price the
customer pays and **not** the actual cost incurred.

## Grain

`fact_standard_cost` — **one row per product per cost version (effective period)**.

```text
grain = (product_durable_key, cost_effective_from)
```

A new row is inserted each time a cost roll changes a product's standard cost; the
previous row is closed out with `cost_effective_to`.

## Schema

| Column | Type | Role | Notes |
|---|---|---|---|
| `standard_cost_sk` | BIGINT | surrogate PK | one per cost version |
| `product_sk` | BIGINT | FK → `dim_product` | the product *version* in effect |
| `product_durable_key` | BIGINT | durable key | groups all cost versions of a product |
| `cost_effective_from` | DATE | — | inclusive start of this cost version |
| `cost_effective_to` | DATE | — | exclusive end; `9999-12-31` while current |
| `is_current` | BOOLEAN | — | flag for the active version |
| `material_cost` | DECIMAL(18,4) | measure | additive component |
| `labour_cost` | DECIMAL(18,4) | measure | additive component |
| `overhead_cost` | DECIMAL(18,4) | measure | additive component |
| `standard_unit_cost` | DECIMAL(18,4) | measure | = material + labour + overhead |
| `currency_code` | CHAR(3) | — | ISO 4217; cost is *per this currency* |
| `uom_code` | VARCHAR | — | unit of measure the cost is expressed in |

## Source & lineage

```text
ERP.COST_MASTER  ──┐
ERP.BOM_ROLLUP   ──┼──> stg_standard_cost ──> fact_standard_cost
ERP.COST_PERIODS ──┘                              │
                                                  └──> dim_product.standard_cost (current only, Type 1)
```

The cost roll job lands a new effective period; the staging model derives
`standard_unit_cost` and closes the prior period's `cost_effective_to`.

## How to use it

### Current standard cost of a product

```sql
SELECT product_durable_key, standard_unit_cost, currency_code
FROM   fact_standard_cost
WHERE  is_current;
```

### Margin using the cost in effect *on the sale date* (point-in-time join)

This is the correct way to compute standard margin — match each sale to the cost
version that was active when the sale happened, **not** the current cost.

```sql
SELECT  s.order_number,
        s.sale_date,
        s.extended_revenue,
        s.quantity * c.standard_unit_cost          AS standard_cost_of_sale,
        s.extended_revenue
          - s.quantity * c.standard_unit_cost      AS standard_margin
FROM    fact_sales            s
JOIN    fact_standard_cost    c
  ON    c.product_durable_key = s.product_durable_key
 AND    s.sale_date >= c.cost_effective_from
 AND    s.sale_date <  c.cost_effective_to;        -- half-open interval
```

### Purchase price / cost variance (standard vs actual)

```sql
SELECT  p.product_durable_key,
        SUM(p.actual_unit_cost   * p.quantity)        AS actual_cost,
        SUM(c.standard_unit_cost * p.quantity)        AS standard_cost,
        SUM((p.actual_unit_cost - c.standard_unit_cost) * p.quantity) AS variance
FROM    fact_purchase_receipts p
JOIN    fact_standard_cost     c
  ON    c.product_durable_key = p.product_durable_key
 AND    p.receipt_date >= c.cost_effective_from
 AND    p.receipt_date <  c.cost_effective_to
GROUP BY p.product_durable_key;
```

## Common Pitfalls

- **Always join point-in-time, never to the current cost.** Using
  `dim_product.standard_cost` (the current value) to value historical sales
  silently restates past margins every time a cost roll runs. Use
  `fact_standard_cost` with the `sale_date BETWEEN from/to` join above.
- **Use a half-open interval** `[from, to)` (`>= from AND < to`). Closed
  intervals (`BETWEEN`) double-count on the boundary day when one version ends
  and the next begins.
- **`standard_cost` on `dim_product` is Type 1 (overwrite).** It exists only for
  convenience / current-state lookups. It carries no history — don't report
  trends from it.
- **Currency and UoM are part of the cost.** Don't sum or compare
  `standard_unit_cost` across rows with different `currency_code` or `uom_code`.
  Convert first.
- **Standard ≠ actual ≠ average ≠ list price.** Keep cost *types* in separate,
  clearly named measures. Mixing them is the single most common reporting error.
- **Cost-roll timing.** A roll dated the 1st but loaded on the 5th leaves a 4-day
  gap if effective dating isn't backfilled. Validate that
  `max(cost_effective_to)` for the prior version meets `min(cost_effective_from)`
  of the next with no gap or overlap.
- **Missing cost for a product.** New products may sell before a standard cost is
  rolled. Provide a `-1` "Unknown cost" member (see
  [Kimball Keys Definitions](../concepts/kimball-keys.md#special-dimension-members))
  and a data-quality check, rather than producing `NULL` margins.

## Related

- [Kimball Keys Definitions](../concepts/kimball-keys.md) — durable vs surrogate
  keys used in the point-in-time join above.
- `fact_sales`, `fact_purchase_receipts` — consumers of standard cost.
- `dim_product` — carries the current-value convenience copy.

## Change history / SCD

`fact_standard_cost` is a **periodic snapshot with effective dating** (a Type 2
style history on a fact). Each cost roll closes the current row
(`cost_effective_to`, `is_current = false`) and inserts a new current row. The
`dim_product.standard_cost` copy is **Type 1** (overwrite, no history).
