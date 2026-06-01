# Sales Territory

> **Type:** Dimension · **Primary home:** `dim_sales_territory` (SCD Type 2) ·
> **Also surfaced on:** `fact_invoice_lines` (FK `sales_territory_sk`)

## Summary

`dim_sales_territory` maps each **salesperson** (also called a *sales rep* or
*sales district*) to the nested chain of **sales territories** they roll up
through, flattened into one row per salesperson. It lets you aggregate sales,
quota, and commission at *any* level of the territory tree — from a single rep up
to global sales — with a plain `GROUP BY`.

It is **not** a geography dimension: the levels are an internal *sales*
hierarchy, not postal/administrative geography (a rep's territory need not match
where customers live). The salesperson is the **leaf** of this dimension, not a
full employee/HR dimension.

## Natural Key

One row represents one salesperson for an assignment period (SCD Type 2); there
is exactly one **current** row per salesperson. The natural key is the source
salesperson identifier, made unique per version by the effective date:

**Natural Key Fields:**

* Sales Person Id

The territory tree is **balanced and fixed at 6 levels**, flattened onto each
salesperson row — the standard Kimball treatment for a fixed-depth hierarchy
(no bridge table needed). Level 1 is the root (Global Sales); level 5 is the most
granular territory; the salesperson is the leaf below level 5:

```text
L1  Global Sales
└── L2  EMEA
    └── L3  Italy
        └── L4  Northern Italy
            └── L5  District 512 – Milan
                └── Salesperson  Maria Rossi (REP-00417)
```

## Schema

| Column | Type | Role | Notes |
|---|---|---|---|
| `sales_territory_sk` | BIGINT | surrogate PK | one row per salesperson version |
| `salesperson_id` | VARCHAR | natural key | source sales rep / district code |
| `salesperson_name` | VARCHAR | attribute | leaf of the hierarchy |
| `territory_l5_code` | VARCHAR | attribute | **level 5** — most granular territory (e.g. district) |
| `territory_l5_name` | VARCHAR | attribute | |
| `territory_l4_code` | VARCHAR | attribute | level 4 |
| `territory_l4_name` | VARCHAR | attribute | |
| `territory_l3_code` | VARCHAR | attribute | level 3 |
| `territory_l3_name` | VARCHAR | attribute | |
| `territory_l2_code` | VARCHAR | attribute | level 2 |
| `territory_l2_name` | VARCHAR | attribute | |
| `territory_l1_code` | VARCHAR | attribute | **level 1** — root; constant |
| `territory_l1_name` | VARCHAR | attribute | always `Global Sales` |
| `valid_from` | DATE | validity | inclusive start of this assignment |
| `valid_to` | DATE | validity | exclusive end; `9999-12-31` while current |
| `is_current` | BOOLEAN | validity | active-version flag |

A worked row for the example above:

| Column | Value |
|---|---|
| `salesperson_name` | Maria Rossi |
| `territory_l5_name` | District 512 – Milan |
| `territory_l4_name` | Northern Italy |
| `territory_l3_name` | Italy |
| `territory_l2_name` | EMEA |
| `territory_l1_name` | Global Sales |

## Source & lineage

```text
CRM.SALES_REP        ──┐
CRM.TERRITORY_TREE   ──┼──> stg_sales_territory ──> dim_sales_territory
HR.REP_ASSIGNMENTS   ──┘                                │
                                                        └──> fact_invoice_lines.sales_territory_sk (FK, resolved at load)
```

`TERRITORY_TREE` is a parent→child recursive table. The staging model walks it,
flattens the five territory levels onto each salesperson, and — on a reassignment
(reorg, rep moves district) — closes the prior row's `valid_to` and inserts a new
current row with a fresh `sales_territory_sk`.

## How to use it

### Sales rolled up to any territory level

Because the hierarchy is flattened, grouping at any level is a plain `GROUP BY` —
no bridge, no recursion:

```sql
SELECT  st.territory_l2_name        AS area,
        SUM(s.net_amount)           AS net_sales
FROM    fact_invoice_lines            s
JOIN    dim_sales_territory   st ON st.sales_territory_sk = s.sales_territory_sk
GROUP BY st.territory_l2_name
ORDER BY net_sales DESC;
```

### The full territory chain for one salesperson

```sql
SELECT  salesperson_name,
        territory_l5_name, territory_l4_name, territory_l3_name,
        territory_l2_name, territory_l1_name
FROM    dim_sales_territory
WHERE   is_current
  AND   salesperson_id = 'REP-00417';
```

### Point-in-time: attribute each sale to the territory in effect *then*

The ETL stamps each `fact_invoice_lines` row with the `sales_territory_sk` that was active
on the sale date, so this equi-join is automatically point-in-time correct — a
sale stays with the rep's territory *at the time*, even after a later reorg:

```sql
SELECT  st.territory_l3_name        AS country,
        DATE_TRUNC('quarter', s.sale_date) AS qtr,
        SUM(s.net_amount)           AS net_sales
FROM    fact_invoice_lines            s
JOIN    dim_sales_territory   st ON st.sales_territory_sk = s.sales_territory_sk
GROUP BY st.territory_l3_name, DATE_TRUNC('quarter', s.sale_date);
```

## Common Pitfalls

- **Mind the level direction.** Level 1 = Global (root), level 5 = most granular.
- **Salesperson ≠ person.** The leaf is a sales role/district. One human may cover
  several districts, and a district may pass between people over time. Keep this
  dimension at the territory-assignment grain; model the individual separately if
  HR attributes are needed.
- **Unassigned reps.** New reps may book sales before territory setup. Point the
  fact FK at a `-1` "Unknown territory" member (see
  [Kimball Keys Definitions](../../concepts/kimball-keys.md#special-dimension-members))
  rather than leaving the FK `NULL`.

## Related

- [Kimball Keys Definitions](../../concepts/kimball-keys.md) — surrogate, durable,
  and natural keys plus the special "Unknown" member used above.
- [Slowly Changing Dimension](../../definitions/slowly-changing-dimension.md) — the
  SCD Type 2 pattern this dimension uses for reassignments.
- `fact_invoice_lines` — primary consumer; carries `sales_territory_sk`.

## Change history / SCD

`dim_sales_territory` is an **SCD Type 2 dimension**. Each territory reassignment
closes the current row (`valid_to`, `is_current = false`) and inserts a new
current row with a fresh `sales_territory_sk`; the `salesperson_id` natural key
stays constant so all of a rep's history can be grouped together. Facts reference the
version in effect at their transaction date via `sales_territory_sk`.
