# Composite Keys

## Overview

A **composite key** is a natural key made of more than one column: no single field identifies the entity on its own, only the *combination* does. A standard cost is unique per plant *and* material *and* effective period; a product code repeats across plants and is unique only *within* a plant; an invoice line is identified by document number *and* line number together.

Composite keys are not a special case to design around — they are the normal shape of source data. The pattern is about one thing: **collapsing that multi-column natural key into a single surrogate key**, deterministically, so that facts and dimensions still join on one clean column.

## Recommended Approach

A dimension's primary key is always a single surrogate key, and a fact always joins on a single foreign key — even when the underlying natural key spans several columns. We never propagate a multi-column key into the fact and join on three or four columns at once.

[Keys](https://dimensional-modelling.dyvenia.com/transformations/keys-assignments.html) already sets the rule: concatenate the components with a separator, then hash the result. For a composite key the rule is the same — the `_sk` is generated from the full tuple:

```sql
WITH

with_natural_key as (
    SELECT
        plant_id,
        material_number,
        cost_effective_from,
        cost_effective_to,
        standard_unit_cost,
        plant_id || '|' || material_number || '|' || cost_effective_from as natural_key
    FROM staging.standard_cost
)

SELECT
    HASH(natural_key) as standard_cost_sk,
    plant_id,
    material_number,
    cost_effective_from,
    cost_effective_to,
    standard_unit_cost
FROM with_natural_key
;
```

Build the concatenation once, in a CTE, instead of repeating the expression. That is what keeps the separator and the component order in a single place.

**Whether `natural_key` stays in the output is a choice**, not part of the rule:

* Keeping it makes debugging direct — you read `1000|M-4471|2026-01-01` instead of decoding a hash to find out why a key did not match.
* Dropping it is one less column and loses nothing: the components are already on the row as dimension attributes or degenerate dimensions, and the join works on `_sk` either way.

**The serialisation has to be canonical.** Without a separator, `('AB','C')` and `('A','BC')` collapse to the same string and collide. A character that cannot occur in the data is the usual answer, but that is hard to guarantee, so where one could appear, escape it or reject the row rather than assume. The separator is only part of it: the concatenation also needs a fixed component order, one documented representation for `NULL`, and one agreed format per data type. The formatting rules are under [Normalising Before Hashing](#normalising-before-hashing).

The dimension owns the key. It is generated once, when the dimension row is built, and a fact never rebuilds it: the fact resolves the dimension row on the natural-key columns and takes the `_sk` from there, so key generation lives in exactly one model. That is the dimensional modelling principle, and it holds whatever the key is made of.

How the key is made is our own convention. Kimball's canonical recommendation is a sequentially assigned integer; we hash the natural key instead, because it needs no central sequence generator and it is reproducible. Hashing does not mathematically guarantee uniqueness, so what the convention actually buys is determinism: the dimension produces the same key on every rebuild, and the foreign keys already written into facts stay valid.

## Where Composite Keys Appear

### Dimensions With No Single Unique Identifier

Many source entities are unique only across a tuple of columns. [Standard Cost](https://dimensional-modelling.dyvenia.com/references/dimensions/standard-cost.html) is the worked example in this guide — its natural key is `plant_id` + `material_number` + cost version, resolved to a single `standard_cost_sk`. Consumers join on that one column and never need to know it was built from three.

**Hashing the components does not mean discarding them.** Kimball notes that operational natural keys are often built from meaningful parts — a line of business, a country of origin, a plant — which should be exposed as dimension attributes in their own right. Keeping `plant_id` and `material_number` on the row is not redundancy: they are the natural key for traceability *and* attributes people group by.

What must not happen is the reverse: **pushing the intelligence of the key onto its consumers.** Parsing a multipart code to filter the fact without joining the dimension bakes in assumptions — a length, a prefix, an embedded segment — that are business rules owned by someone else, and they will eventually be invalidated.

### Facts Whose Grain Is a Tuple

A fact's grain is itself usually a composite key. [Invoice Lines](https://dimensional-modelling.dyvenia.com/references/facts/invoice_lines.html) declares it directly:

```text
grain = (invoice_number, invoice_line_number)
```

Those two columns are [degenerate dimensions](https://dimensional-modelling.dyvenia.com/patterns/degenerate-dimension.html), and together they already identify the row. The fact needs nothing further to be uniquely addressable.

Hashing that tuple into one column is therefore a **technical convenience, not a dimensional modelling requirement**. The resulting key never joins to a dimension; it exists so the load has a single column to merge, deduplicate and reconcile on, and so that re-running produces the same values. `fact_invoice_lines` does not keep one.

Where a load does want one, it is built from the same tuple:

```sql
SELECT
    HASH(invoice_number || '|' || invoice_line_number) as invoice_line_sk,
    invoice_number,
    invoice_line_number,
    plant_id,
    material_number,
    invoice_date,
    sales_amount
FROM staging.invoice_lines
;
```

One case does rule out trusting a single column: a transaction number that is **not unique across locations**, or that gets recycled when the source counter wraps. A till receipt number unique only within a store is the classic example — the real identifier is `(store, receipt_number)`, so the identifier is the tuple, not the number alone.

### Multi-Source Warehouses

When two source systems can issue the same code for different entities, the source becomes part of the key:

```text
customer_sk = HASH(source_system || '|' || customer_number)
```

Omitting `source_system` is the most common way to have unrelated source records resolve to the same key once a second source is onboarded. Nothing is wrong with the hash in that case: two different entities were handed identical input, so they correctly produce identical output. Kimball treats this as a first-class ETL responsibility, to be caught during key lookup rather than discovered downstream.

## How It Works

The composite is standardised, concatenated into a natural key, hashed once, and from then on carried as a single column on both sides:

```mermaid
flowchart LR
    parts[Composite natural key columns] --> std[Prepare → standardise]
    std --> nk[natural_key joined with a separator]
    nk --> sk[HASH → surrogate key]
    sk --> join[Single-column fact-to-dimension join]
```

In the fact load, the lookup joins on the natural-key columns and takes the resolved key from the dimension — a fact never builds its own dimension keys (see [Resolution engines](https://dimensional-modelling.dyvenia.com/patterns/resolution-engines.html)). Because `dim_standard_cost` keeps one row per cost version, the event date resolves which version applies:

```sql
WITH

unknown_member as (
    SELECT standard_cost_sk
    FROM dimensions.dim_standard_cost
    WHERE material_number = 'UNKNOWN'
)

SELECT
    f.invoice_number,
    f.invoice_line_number,
    COALESCE(d.standard_cost_sk, unk.standard_cost_sk) as standard_cost_sk,
    f.sales_amount
FROM staging.invoice_lines as f
LEFT JOIN dimensions.dim_standard_cost as d
    ON f.plant_id = d.plant_id
    AND f.material_number = d.material_number
    AND f.invoice_date >= d.cost_effective_from
    AND f.invoice_date < d.cost_effective_to
CROSS JOIN unknown_member as unk
;
```

The `LEFT JOIN` and `COALESCE` are the standard [Unknown member](https://dimensional-modelling.dyvenia.com/patterns/unknown.html) treatment. The fallback is the Unknown member's own surrogate key: the dimension generates it like any other key, and the fact resolves and uses it rather than building one. See that page for the reserved code and how the row is added. Once assigned, the fact carries only `standard_cost_sk`.

This substitution is the **surrogate key assignment step**, and it has one ordering consequence worth stating: dimensions load before facts. The dimension is the only legitimate source of the key, and a composite has more columns that can be stale, so the ordering is less forgiving than with a single-column key.

## Implementation Considerations

### Validity Dates in the Key

Where a version discriminator such as `cost_effective_from` is part of the natural key, it must be resolved during the load and never left to consumers. Kimball warns against gluing a natural key to a timestamp and then expecting consumers to match an event date against a validity range at query time; his term for the result is a *double-barreled join*.

The join above does that resolution once and writes a single foreign key, so nothing downstream knows a validity range was involved. [Standard Cost](https://dimensional-modelling.dyvenia.com/references/dimensions/standard-cost.html) covers the mechanics of the range join itself, including why the interval must be half-open.

### Durable Keys When a Component Changes

A composite natural key has more moving parts than a single-column one, so it has more ways to change: a business rule change, a reorganisation, de-duplication, or the same entity arriving from a new system. When any component changes the hash changes, and the historical versions end up with unrelated surrogate keys and nothing tying them together.

That is what a [durable key](https://dimensional-modelling.dyvenia.com/concepts/kimball-keys.html) is for, and it matters more here than for a simple key: the more components a natural key has, the more likely one of them is eventually reformatted or merged away. `dim_standard_cost` carries `cost_durable_key` alongside its per-version `standard_cost_sk` for exactly this reason.

### Normalising Before Hashing

A hash is byte-sensitive: `'0012'` and `'12'`, or `'ES'` and `'es '`, produce different keys. The fact does not rebuild the key, but it does join on the natural-key columns. If the dimension and the fact standardise them even slightly differently, the lookup silently fails and the affected fact rows land on Unknown.

The cleaning itself belongs in [Prepare / standardise](https://dimensional-modelling.dyvenia.com/transformations/prepare.html). What composite keys add is a stricter requirement on it:

* every component must be standardised **identically on both sides**, and before the concatenation — not per-model,
* date components need one agreed representation, since a `DATE` and its text form hash differently,
* `NULL` components need one documented sentinel, since hash functions treat `NULL` inconsistently and a single `NULL` can void the whole key.

## Common Pitfalls

Failure modes that the sections above do not spell out:

* **Component set or order drift.** The dimension hashes `(plant, material)` and the fact hashes `(material, plant)`. No error is raised, the keys differ, nothing matches — and it stays invisible until someone notices everything is on Unknown. Define the concatenation once and reuse it.
* **Dropping a date condition on a versioned dimension.** The fact row matches every version — [fan-out](https://dimensional-modelling.dyvenia.com/patterns/resolution-engines.html), with the measures silently multiplied.
* **Leaking the composite into the fact.** Carrying every component as the foreign key and joining on the tuple defeats the purpose. Resolve to one `_sk`; keep components only where they are also degenerate dimensions.
* **Loading facts before dimensions.** A composite lookup against a stale dimension sends good rows to Unknown, and they stay there until the fact is reprocessed.

## Related

* [Keys](https://dimensional-modelling.dyvenia.com/transformations/keys-assignments.html) — the concatenate-and-hash rule this page applies
* [Keys (surrogate, natural, foreign)](https://dimensional-modelling.dyvenia.com/concepts/kimball-keys.html) — key types and durable keys
* [Standard Cost](https://dimensional-modelling.dyvenia.com/references/dimensions/standard-cost.html) — dimension with a multi-part natural key and a durable key
* [Invoice Lines](https://dimensional-modelling.dyvenia.com/references/facts/invoice_lines.html) — fact whose grain is a tuple
* [Prepare / standardise](https://dimensional-modelling.dyvenia.com/transformations/prepare.html) — where components are cleaned
* [Unknown member](https://dimensional-modelling.dyvenia.com/patterns/unknown.html) — the fallback when a lookup does not resolve

## References

* [Dimension surrogate keys](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/dimension-surrogate-key/) — Kimball Group
* [Natural, durable and supernatural keys](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/natural-durable-supernatural-key/) — Kimball Group, and Design Tip #147
* *The Data Warehouse Toolkit*, 3rd ed. — Chapter 3, "Dimension and Fact Table Keys"; Chapter 19 (surrogate key pipeline)
