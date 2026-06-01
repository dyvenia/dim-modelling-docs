# Invoice Lines

> **Type:** Fact — transaction · **Grain:** one row per invoice line ·
> **Primary home:** `fact_invoice_lines`

## Summary

`fact_invoice_lines` records the billed detail of customer invoices — one row for
each product line on each invoice. It is the backbone for revenue, discount, tax,
and margin reporting, sliced by customer, product, date, and sales territory.

It is **not** an invoice-*header* fact: whole-invoice charges (freight,
invoice-level discounts) are not repeated on every line — keep those in a separate
header fact or allocate them down to the line, or you will double-count.

## Grain

One row per **invoice line** — a single product line item on a single invoice.

```text
grain = (invoice_number, invoice_line_number)
```

`invoice_number` and `invoice_line_number` are degenerate dimensions (identifiers
with no dimension table of their own); together they uniquely identify a row.

## Schema

| Column | Type | Role | Notes |
|---|---|---|---|
| `invoice_number` | VARCHAR | degenerate dimension | the operational invoice id |
| `invoice_line_number` | INT | degenerate dimension | line position within the invoice |
| `invoice_date_sk` | BIGINT | FK → `dim_date` | date the invoice was issued |
| `customer_sk` | BIGINT | FK → `dim_customer` | bill-to customer (version at invoice date) |
| `product_sk` | BIGINT | FK → `dim_product` | product sold |
| `sales_territory_sk` | BIGINT | FK → `dim_sales_territory` | rep / territory in effect at invoice date |
| `standard_cost_sk` | BIGINT | FK → `dim_standard_cost` | standard-cost version in effect at invoice date |
| `currency_code` | CHAR(3) | attribute | document currency (ISO 4217) |
| `quantity` | DECIMAL(18,4) | measure | units invoiced; **additive** |
| `gross_amount` | DECIMAL(18,4) | measure | list value before discount; **additive** |
| `discount_amount` | DECIMAL(18,4) | measure | **additive** |
| `net_amount` | DECIMAL(18,4) | measure | = gross − discount; **additive** |
| `tax_amount` | DECIMAL(18,4) | measure | **additive** |
| `standard_cost_of_sale` | DECIMAL(18,4) | measure | = `quantity × standard_unit_cost`; **additive** |
| `unit_price` | DECIMAL(18,4) | measure | net per unit; **non-additive** (a rate) |
| `load_ts` | TIMESTAMP | audit | warehouse load timestamp |

## Measures & additivity

| Measure | Additivity | Notes |
|---|---|---|
| `quantity` | additive | sums across all dimensions |
| `gross_amount`, `discount_amount`, `net_amount`, `tax_amount` | additive | the money measures; sum freely |
| `standard_cost_of_sale` | additive | pairs with `net_amount` to give margin |
| `unit_price` | **non-additive** | a per-unit rate — never `SUM`; for an average use `SUM(net_amount) / SUM(quantity)` |

Margin is **derived, not stored**: `net_amount − standard_cost_of_sale`. Because
both inputs are additive, margin can be summed at any level.

## Source & lineage

```text
ERP.INVOICE_HEADER ──┐
ERP.INVOICE_LINE   ──┼──> stg_invoice_lines ──> fact_invoice_lines
ERP.FX_RATES       ──┘
```

The staging model joins header to line, then resolves each foreign key. The SCD
Type 2 keys (`customer_sk`, `sales_territory_sk`, `standard_cost_sk`) are looked
up **as of the invoice date**, so every line carries the dimension version that
was in effect when it was billed — point-in-time correct (see the pitfalls).

## How to use it

### Net sales by month and sales area

```sql
SELECT  d.year_month,
        st.territory_l2_name          AS area,
        SUM(f.net_amount)             AS net_sales
FROM    fact_invoice_lines   f
JOIN    dim_date             d  ON d.date_sk            = f.invoice_date_sk
JOIN    dim_sales_territory  st ON st.sales_territory_sk = f.sales_territory_sk
GROUP BY d.year_month, st.territory_l2_name;
```

### Standard margin by product category

```sql
SELECT  p.product_category,
        SUM(f.net_amount)                            AS net_sales,
        SUM(f.standard_cost_of_sale)                 AS standard_cost,
        SUM(f.net_amount - f.standard_cost_of_sale)  AS standard_margin
FROM    fact_invoice_lines f
JOIN    dim_product        p ON p.product_sk = f.product_sk
GROUP BY p.product_category;
```

### Average selling price (the non-additive measure, done right)

```sql
-- weighted average, NOT AVG(unit_price)
SELECT  product_sk,
        SUM(net_amount) / NULLIF(SUM(quantity), 0) AS avg_unit_price
FROM    fact_invoice_lines
GROUP BY product_sk;
```

## Common Pitfalls

- **Never `SUM(unit_price)`** (or `AVG` it). It is a per-unit rate — non-additive.
  Compute an average as `SUM(net_amount) / SUM(quantity)`.
- **Header vs line grain.** Whole-invoice charges (freight, invoice-level
  discounts) belong to the header, not each line. Repeating them per line
  double-counts — allocate them to lines or keep a separate header fact.
- **Dimension fan-out.** Joining to a dimension at a coarser grain or through a
  multi-valued bridge multiplies rows and inflates the measures. Join on the
  line's own surrogate keys, and pre-aggregate the fact before any 1-to-many join.
- **Point-in-time keys.** `customer_sk`, `sales_territory_sk`, and
  `standard_cost_sk` are the versions in effect *at the invoice date*. Don't
  re-derive them from the current dimension row, or history is restated on every
  reorg / cost roll.
- **Returns & credit notes.** Credits arrive as negative `quantity` / amounts.
  Keep the sign convention consistent so `SUM` nets correctly; don't silently
  filter them out of margin.
- **Currency.** Amounts are in `currency_code` (document currency). Convert to a
  single reporting currency before summing across currencies.
- **Unknown members.** A line that can't resolve a dimension points at the `-1`
  "Unknown" member (see
  [Kimball Keys Definitions](../../concepts/kimball-keys.md#special-dimension-members)),
  never a `NULL` FK.

## Related

- [Standard Cost](../dimensions/standard-cost.md) — supplies `standard_cost_sk`
  / `standard_unit_cost` behind `standard_cost_of_sale`.
- [Sales Territory](../dimensions/sales-territory.md) — supplies
  `sales_territory_sk` for territory rollups.
- [Grain](../../definitions/grain.md) and
  [Kimball Keys Definitions](../../concepts/kimball-keys.md) — the concepts this fact
  builds on.
- `dim_date`, `dim_customer`, `dim_product` — the remaining conformed dimensions.

## Change history / load pattern

`fact_invoice_lines` is a **transaction-grain fact**, loaded **insert-only**: each
invoice line is written once and never updated. Corrections and returns flow in as
new (often negative) lines rather than edits, preserving an auditable history.
Late-arriving invoices are appended with their historical `invoice_date_sk`, and
their SCD Type 2 keys resolve to the version that was current then (or the `-1`
Unknown member until the dimension member appears).
