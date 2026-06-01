# Standard Cost

> **Type:** Dimension (per-unit cost rate) · **Primary home:** `dim_standard_cost`
> (SCD Type 2) · **Also surfaced on:** `dim_product` (current value only, Type 1)

## Summary

The **standard cost** is the predetermined, planned unit cost of a product, it typically includes these costs:

 * materials
 * labour
 * allocated overhead

Standard costs are calculated per material, typically during a periodic *cost roll* (often annually or quarterly). It is used for inventory valuation, margin reporting, and variance analysis against actual cost.

Standard Cost is **not** the price the customer pays and **not** the actual cost incurred.

## Natural Key

Standard Cost is per unit of product, the natural key tends to be:

* Plant ID
* Material Number
* Effective Date (period in which the cost is valid)

In the warehouse this natural key maps to a `cost_durable_key` (stable per
plant + material across every cost version) and a per-version `standard_cost_sk`
surrogate key.

## Schema

**One row per:** `plant_id` + `material_number` + cost version (effective period).

| Column | Type | Role | Notes |
|---|---|---|---|
| `standard_cost_sk` | BIGINT | surrogate PK | one row per plant + material + cost version |
| `plant_id` | VARCHAR | natural key | ERP plant / costing location |
| `material_number` | VARCHAR | natural key | ERP material (≈ product) |
| `cost_durable_key` | BIGINT | durable key | stable per (plant, material) across all versions |
| `cost_effective_from` | DATE | natural key · validity | inclusive start of this cost version |
| `cost_effective_to` | DATE | validity | exclusive end; `9999-12-31` while current |
| `is_current` | BOOLEAN | validity | flag for the active version |
| `material_cost` | DECIMAL(18,4) | attribute (rate) | per-unit component; **non-additive** |
| `labour_cost` | DECIMAL(18,4) | attribute (rate) | per-unit component; **non-additive** |
| `overhead_cost` | DECIMAL(18,4) | attribute (rate) | per-unit component; **non-additive** |
| `standard_unit_cost` | DECIMAL(18,4) | attribute (rate) | = material + labour + overhead; **non-additive** |
| `currency_code` | CHAR(3) | attribute | ISO 4217; cost is *per this currency* |
| `uom_code` | VARCHAR | attribute | unit of measure the cost is expressed in |

## Source & lineage

```text
ERP.COST_MASTER  ──┐
ERP.BOM_ROLLUP   ──┼──> stg_standard_cost ──> dim_standard_cost
ERP.COST_PERIODS ──┘                              │
                                                  └──> dim_product.standard_cost (current only, Type 1)
```

The cost roll job lands a new effective period; the staging model derives
`standard_unit_cost`, closes the prior period's `cost_effective_to`, and assigns
the new `standard_cost_sk`.

## How to use it

### Current standard cost of a product

```sql
SELECT plant_id, material_number, standard_unit_cost, currency_code
FROM   dim_standard_cost
WHERE  is_current;
```

### Margin — the dimensional way (fact carries the cost surrogate key)

The ETL stamps each fact row with the `standard_cost_sk` for the version in
effect on the transaction date, so this is a plain equi-join that is *already*
point-in-time correct — no date logic needed at query time.

```sql
SELECT  s.order_number,
        s.sale_date,
        s.extended_revenue,
        s.quantity * sc.standard_unit_cost            AS standard_cost_of_sale,
        s.extended_revenue
          - s.quantity * sc.standard_unit_cost        AS standard_margin
FROM    fact_sales         s
JOIN    dim_standard_cost  sc
  ON    sc.standard_cost_sk = s.standard_cost_sk;     -- point-in-time resolved at load
```

### If the fact has no cost SK — point-in-time range join

When a fact only carries the natural key, match each row to the cost version that
was active when it happened — **never** to the current cost:

```sql
SELECT  s.order_number,
        s.quantity * sc.standard_unit_cost AS standard_cost_of_sale
FROM    fact_sales        s
JOIN    dim_standard_cost sc
  ON    sc.plant_id        = s.plant_id
 AND    sc.material_number = s.material_number
 AND    s.sale_date >= sc.cost_effective_from
 AND    s.sale_date <  sc.cost_effective_to;          -- half-open interval
```

### Purchase price / cost variance (standard vs actual)

```sql
SELECT  p.plant_id,
        p.material_number,
        SUM(p.actual_unit_cost   * p.quantity)        AS actual_cost,
        SUM(sc.standard_unit_cost * p.quantity)       AS standard_cost,
        SUM((p.actual_unit_cost - sc.standard_unit_cost) * p.quantity) AS variance
FROM    fact_purchase_receipts p
JOIN    dim_standard_cost      sc
  ON    sc.standard_cost_sk = p.standard_cost_sk
GROUP BY p.plant_id, p.material_number;
```

## Common Pitfalls

- **Standard cost is a dimension, not a fact — because its amounts are
  non-additive.** `standard_unit_cost` is a *per-unit rate*: summing it across
  products, plants, or periods is meaningless (`SUM(standard_unit_cost)` answers
  no real question). You **look it up and multiply** by a fact quantity
  (`quantity × standard_unit_cost`) to get an *additive* measure — the cost of
  sale — which belongs in the fact/query, not here. Modelling these rates as a
  fact table is what tempts that erroneous `SUM`.
- **Always join point-in-time, never to the current cost.** Resolve the version
  at ETL into `standard_cost_sk`, or range-join on the natural key + date (above).
  Using `dim_product.standard_cost` (the current value) to value historical sales
  silently restates past margins every time a cost roll runs.
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
  clearly named attributes. Mixing them is the single most common reporting error.
- **Cost-roll timing.** A roll dated the 1st but loaded on the 5th leaves a 4-day
  gap if effective dating isn't backfilled. Validate that
  `max(cost_effective_to)` for the prior version meets `min(cost_effective_from)`
  of the next with no gap or overlap.
- **Missing cost for a product.** New materials may sell before a standard cost is
  rolled. Provide a `-1` "Unknown cost" member (see
  [Kimball Keys Definitions](../../concepts/kimball-keys.md#special-dimension-members))
  and a data-quality check, rather than producing `NULL` margins.

## Related

- [Kimball Keys Definitions](../../concepts/kimball-keys.md) — natural, durable, and
  surrogate keys used above.
- `fact_sales`, `fact_purchase_receipts` — consumers; carry `standard_cost_sk`.
- `dim_product` — carries the current-value convenience copy (Type 1).

## Change history / SCD

`dim_standard_cost` is an **SCD Type 2 dimension** with effective dating. Each
cost roll closes the current row (`cost_effective_to`, `is_current = false`) and
inserts a new current row with a fresh `standard_cost_sk`. Facts reference the
version in effect at their transaction date via that `standard_cost_sk`. The
`dim_product.standard_cost` convenience copy is **Type 1** (overwrite, no history).
