---
name: build-fact-sql
description: Generate the fact_invoice_lines SQL from its markdown spec via a structured CTE workflow grounded in the live SQLite staging.db schema. Use this skill when the user asks to build, regenerate, or update the fact-invoice-lines SQL file.
---

# Build Fact SQL

Generate a SQL CTE pipeline that builds `fact_invoice_lines` from the staging source tables, following an 18-stage workflow. The output **must be valid SQLite SQL** that runs cleanly against `staging.db`.

## Inputs you have

| Source | How to access |
|---|---|
| Markdown spec | `Read` the file `fact_invoice_lines_spec.md` |
| Live DB schema | Call the `mcp__db_meta__fetch_db_meta` tool — pass `table=""` for the full schema, or `table=<name>` for one table |
| Existing DDL files | `sql/<table>.sql` (reference only — the live DB is the source of truth) |
| Output target | Write the final SQL to `sql/fact_invoice_lines.sql` |

## Hard rules

1. **Grounding** — every column reference in every CTE must come from the `fetch_db_meta` output (or from a CTE you defined earlier in the same file). Never invent column names.
2. **SQLite dialect**:
   - Use `||` for string concatenation. **Never** `CONCAT()`.
   - Use `CURRENT_TIMESTAMP` (no parens). **Never** `CURRENT_TIMESTAMP()`.
   - **No** `MD5()`, `SHA2()`, `HASHBYTES()`, or any hash function — SQLite has none.
   - Identifiers are case-insensitive but stick to the casing in the live schema.
3. **No phantom tables** — every `FROM`/`JOIN` target must be either a CTE you defined above or a table that exists in `fetch_db_meta`. There are no `dim_*` tables in this database; you must stub dimension lookups (see Step 11).
4. **Schema-identical UNION** — every per-source `<source>_conformed` CTE must produce the exact same column list, in the exact same order, with the same types. Use `NULL` for any column a source can't supply.

## Workflow (18 stages)

### Stage 0 — Ground the work
Call `mcp__db_meta__fetch_db_meta` with `table=""` once. Keep the result handy — you'll reference it in every later stage. If you're unsure about a single table, call it again with that table name.

### Stage 1 — Read the spec, build a plan
`Read` `fact_invoice_lines_spec.md`. From it, identify:
- **Grain** — one row per invoice line.
- **Sources** — SAP and Infor M3, with which staging tables belong to each (use the `sap_` / `infor_` prefix).
- **Target columns** — every fact column with its SAP and Infor derivation.
- **Natural key columns** — `source_system_code, invoice_number, invoice_line_number, legal_entity` (and `timestamp` for change tracking).
- **Dimension keys** — every column ending in `_key` whose group is `dimension_key`.
- **Date keys** — every column ending in `_key` whose group is `date_key`.
- **Measures** — quantity, prices, amounts.
- **Degenerate dimensions** — e.g. `accounting_document_number`.
- **Technical columns** — `row_insert_timestamp`, `row_updated_timestamp`, `is_deleted`.

You don't need to write the plan to disk — keep it in your head and proceed.

### Stages 2-6 — Per source table (5 CTEs each)
For **every** source table that contributes to the fact, generate a chain of 5 CTEs. Each references the previous one in the chain:

| # | CTE name | Purpose | Notes |
|---|---|---|---|
| 2 | `<table>_base` | Raw select | `SELECT <real columns> FROM <table>` |
| 3 | `<table>_agg` | Bring to fact grain | Pass-through for line tables; `GROUP BY` header key for header tables; pass-through for config tables |
| 4 | `<table>_sel` | Project required columns | Only the columns the fact actually needs |
| 5 | `<table>_std` | Rename + cast | Rename source columns to the canonical fact names. **Drop the `_key` suffix** from dimension FK columns (e.g. `KUNAG → sold_to_customer`, NOT `sold_to_customer_key`) — the `_key` suffix is added in Stage 11. Cast types to match the spec. |
| 6 | `<table>_flt` | Filter to in-scope rows | Exclude cancelled/reversed (`FKSTO = 'X'`, `IVST IN ('90','99')`); require non-null primary keys |

**Canonical naming convention** for the std stage (use these exact names so the join stage works):

- Natural keys: `invoice_number`, `invoice_line_number`, `source_system_code`, `legal_entity`, `timestamp`
- Dimension natural-ids (no `_key` suffix): `sold_to_customer`, `ship_to_customer`, `bill_to_customer`, `material_number`, `uom`, `profit_center`, `document_currency`, `local_currency`, `group_currency`, `distribution_channel`, `billing_type`
- Date keys (keep `_key` suffix; they're date values, not surrogates): `invoice_date_key`, `posting_date_key`, `baseline_date_key`, `due_date_key`, `clearing_date_key`
- Measures: `billed_quantity`, `unit_price_doc_curr`, `sales_amount_doc_curr`, `sales_amount_loc_curr`, `sales_amount_group_curr`
- Exchange rates: `exchange_rate_loc_curr`, `exchange_rate_group_curr`
- Degenerate: `accounting_document_number`
- Raw flags: `cancellation_flag` (will become `is_deleted` in Stage 10)

### Stages 7-8 — Per source (2 CTEs each)

| # | CTE name | Purpose |
|---|---|---|
| 7 | `<source>_joined` | LEFT JOIN every `<table>_flt` from this source on its natural key. Use the line table as the driver. |
| 8 | `<source>_conformed` | Project EXACTLY the conformed schema (see below) plus `'<SOURCE>' AS source_system_code`. Use `NULL` for columns this source can't supply. |

**Conformed schema** (every `_conformed` CTE outputs these columns in this exact order):

```
source_system_code, invoice_number, invoice_line_number, legal_entity, timestamp,
sold_to_customer, ship_to_customer, bill_to_customer,
material_number, uom, profit_center,
document_currency, local_currency, group_currency,
distribution_channel, billing_type,
invoice_date_key, posting_date_key, baseline_date_key, due_date_key, clearing_date_key,
accounting_document_number,
billed_quantity, unit_price_doc_curr,
sales_amount_doc_curr, sales_amount_loc_curr, sales_amount_group_curr,
exchange_rate_loc_curr, exchange_rate_group_curr,
cancellation_flag
```

### Stage 9 — Union
9. `unioned` — `SELECT * FROM <sap_conformed> UNION ALL SELECT * FROM <infor_conformed>`

### Stage 10 — Business rules
10. `business_rules` — pass through every column from `unioned`, then add or replace:
- `is_return = CASE WHEN billed_quantity < 0 THEN 1 ELSE 0 END`
- `is_deleted = COALESCE(cancellation_flag, 0)` (or convert `'X' → 1`)

### Stage 11 — Dimension lookups (SQLite stub)
For **each** dimension role (sold_to_customer, ship_to_customer, bill_to_customer, material_number, uom, profit_center, document_currency, local_currency, group_currency, distribution_channel, billing_type), generate ONE CTE:

```sql
dim_lookup_<role> AS (
    SELECT *, <role> AS <role>_key
    FROM business_rules
)
```

**SQLite stub mode**: there are no `dim_<role>` tables in this database. The lookup is just a passthrough that promotes the natural-id column to a `<role>_key` column. Do **not** JOIN any external table.

### Stage 12 — Dimension assignment
12. `dim_assigned` — chain the dim_lookup CTEs together, OR more simply: pick the last `dim_lookup_*` and `SELECT *` from it. If you chain, each `dim_lookup_<role>` should select from the previous one rather than from `business_rules`, so the final CTE has every `<role>_key` column.

### Stage 13 — Degenerate dimensions
13. `with_degenerate` — passthrough. `accounting_document_number` is already in `business_rules` from the conformance step.

```sql
with_degenerate AS (SELECT * FROM dim_assigned)
```

### Stage 14 — Natural key
14. `with_natural_key` — concatenate the natural key columns:

```sql
with_natural_key AS (
    SELECT *,
           source_system_code || '|' || legal_entity || '|' || invoice_number || '|' || invoice_line_number AS natural_key
    FROM with_degenerate
)
```

### Stage 15 — Surrogate key (SQLite stub)
15. `with_surrogate_key` — `fact_key = natural_key`. SQLite has no `MD5`/`SHA2`, so we use the natural key directly as the surrogate.

```sql
with_surrogate_key AS (SELECT *, natural_key AS fact_key FROM with_natural_key)
```

### Stage 16 — Technical columns
16. `with_technical` — add timestamps:

```sql
with_technical AS (
    SELECT *,
           CURRENT_TIMESTAMP AS row_insert_timestamp,
           CURRENT_TIMESTAMP AS row_updated_timestamp
    FROM with_surrogate_key
)
```

### Stage 17 — Final projection
17. `final_projection` — select **only** the target schema columns from the spec, in the order the spec defines them.

### Stage 18 — Emit
Stitch all the CTEs together into one SQL statement of the form:

```sql
WITH
  <cte1>,
  <cte2>,
  ...
  final_projection
SELECT * FROM final_projection;
```

`Write` the result to `sql/fact_invoice_lines.sql`.

## Validation

After writing the file, validate it with the `Bash` tool. **Always run sqlite3 non-interactively** — never call `sqlite3 staging.db` on its own (that opens an interactive REPL and hangs). Use input redirection or `-batch`:

```bash
sqlite3 -batch staging.db < sql/fact_invoice_lines.sql > /tmp/fact_test.out 2>&1
echo "exit_code=$?"
head -20 /tmp/fact_test.out
```

If `exit_code=0` and there's no error in the output, you're done. Stop and report success.

If SQLite reports an error:
1. Read the error message — the LAST CTE in the chain is usually misleading; the real bug is **upstream**.
2. Re-call `fetch_db_meta` for any table whose columns you're unsure about.
3. Use the `Edit` tool to fix the specific CTE in `sql/fact_invoice_lines.sql`.
4. Re-run the validation command above.
5. **Maximum 5 fix-and-retry iterations.** If the SQL still doesn't parse after 5 retries, stop and report what's still failing — do NOT keep looping.
