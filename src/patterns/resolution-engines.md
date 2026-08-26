# Resolution engines (map_)

A **resolution engine** — named with the `map_` prefix — is an ETL object that turns a messy code from a source system into the clean key a dimension uses, before the fact links to that dimension.

Most facts don't need a `map_` at all. They already carry a clean natural key and join the dimension directly — that is the normal case. A `map_` is only for the exceptions, where the source code isn't clean: one field might hold two different kinds of code, or a code that only makes sense with extra context, or a value buried inside a parent-child tree. A `map_` handles those cases — it does the untangling once, in one place, so every fact that needs the same resolution gets the same answer.

## Not a dimension, not a fact

A `map_` is a supporting ETL object rather than a part of the dimensional model itself. Facts and dimensions are what the model is made of; a `map_` is machinery that helps build them. Knowing that tells you where it belongs.

- **Not a fact** — it records no business event and holds no measures. It resolves a code, it doesn't measure anything.
- **Not a dimension** — it is never filtered, grouped, or shown on a report. Users don't see it; only the load uses it.
- **A back-room tool** — it lives in the ETL layer, before facts are loaded. Nothing downstream joins to it; only its *output* — a clean key — flows on.

If you ever want to show a `map_` on a report, that's the sign you actually needed a dimension, and the attributes belong there instead.

## Why it exists

Without a `map_`, the same untangling has to be rewritten inside every fact that needs it. The copies slowly drift apart, the logic is buried where no one can test or reuse it, and if the source format changes you have to fix every fact instead of one object.

A `map_` keeps that rule in one place, as the single source of truth. Think of it as a translator between the source system and the warehouse: the fact no longer has to understand the source's messy codes — it just receives clean keys.

## The three shapes

Almost every `map_` is one of three patterns.

### Code-type resolution

One field holds two kinds of code, told apart by something you can detect, like length or prefix. The engine spots the type and resolves each to the same key.

*Example: an outlet field holding either a 5-digit store code or a 2-digit cluster code.*

```sql
-- map_outlet
SELECT
    o.outlet_code,
    CASE WHEN LENGTH(o.outlet_code) = 5
         THEN o.outlet_code            -- store: use as-is
         ELSE lead.cluster_store_nk    -- cluster: its lead store
    END AS store_nk
FROM stg_outlets o
LEFT JOIN map_cluster_lead lead
    ON lead.outlet_code = o.outlet_code;
```

One row per operational input, one clean key out:

| outlet_code | store_nk |
|-------------|----------|
| 10432       | 10432    |
| 10433       | 10433    |
| 22          | 10500    |
| 10510       | 10510    |
| 07          | 10600    |
| 10611       | 10611    |

### Context-dependent resolution

The code isn't unique on its own; it becomes unique only when combined with another field. That field can be a simple piece of context or a second full-fledged code — either way, the engine combines them into one clean key.

*Example: a product code that repeats across catalogues and is unique only within one.*

```sql
-- map_product
SELECT c.catalogue_id, c.product_code, x.global_product_nk
FROM stg_catalogue_lines c
JOIN map_catalogue_crossref x
    ON  x.catalogue_id = c.catalogue_id
    AND x.product_code = c.product_code;
```

### Hierarchy walk-up

The source is a parent-child tree of uneven depth, and you need a leaf resolved up to a set level. The engine climbs the tree and stops at that level.

*Example: any node in an org tree resolved up to its department.*

```sql
-- map_department: climb until the ancestor is a department
WITH RECURSIVE walk (node, ancestor) AS (
    SELECT node, node FROM stg_org_edges
    UNION ALL
    SELECT w.node, e.parent
    FROM walk w
    JOIN stg_org_edges e ON e.child = w.ancestor
)
SELECT node, ancestor AS department_nk
FROM walk
WHERE ancestor IN (SELECT dept_code FROM stg_departments);
```

## Resolve before the key, never in the fact

Resolution that is complex or reused should be handled before the fact, rather than repeated inside each one. The fact should normally consume a clean natural key instead of untangling source codes itself.

One part of this is not a matter of preference: **the fact does not build its own keys.** It joins the dimension on the natural key and takes the surrogate key from there. The key is created once, in the dimension, and the fact only ever takes a copy.

```
flowchart LR
    src[Source code] --> map[map_ resolution engine]
    map --> nk[Clean natural key]
    nk --> join[Fact joins the dimension on the natural key]
    join --> fk[Fact foreign key]
```

In the fact load, that is one step — read the resolved key, join the dimension, fall back to Unknown when nothing resolves:

```sql
SELECT
    s.*,
    COALESCE(d.store_sk, unk.store_sk) AS store_sk
FROM stg_sales s
LEFT JOIN map_outlet m ON m.outlet_code = s.outlet_code
LEFT JOIN dim_store d  ON d.store_nk    = m.store_nk
CROSS JOIN (SELECT store_sk FROM dim_store WHERE store_nk = 'UNKNOWN') unk;
```

Keeping resolution and key assignment as separate steps is what lets you check a resolution on its own, reuse it across many facts, and re-run the load without surprises. A fact that resolves codes inline puts these jobs back together and brings back every problem the `map_` was built to remove.

## Two things to get right

- **Persisted where it is shared.** A `map_` is normally a view or table rather than a step hidden inside one model, so the resolution can be inspected and reused. For simple logic used in a single place, keeping it inline can be reasonable — once two or more models need it, or the logic gets complex, it earns its own object.
- **Deterministic.** The same inputs must always produce the same key. Those inputs are not only the code — a resolution may also depend on source system, company, effective date, or other context. What matters is that the full set of inputs always resolves the same way, whenever it runs. A rule that could give a different answer on re-run is a bug, not a resolution engine.

## Common Pitfalls

- **Fan-out.** If a resolution returns more than one row per input code, the join multiplies fact rows and silently inflates every measure. Guarantee one output per input.
- **Resolving downstream.** Pushing the logic into a view or the BI tool lets every consumer redo it, and the answers drift. Resolve once, in the ETL.
- **No unknown handling.** An unresolved code must land on a reserved **Unknown** member, so the row survives and the gap is visible — never a `NULL` an inner join can drop.
- **Copying per fact.** The same logic pasted into several facts is the exact drift a `map_` prevents. One object, many consumers.
- **Building one where none is needed.** If a fact already carries a clean natural key, it joins the dimension directly — wrapping that in a `map_` adds a layer that resolves nothing. Reach for a `map_` only when the source code actually needs untangling.

## Related

- [Keys & Unknown member](https://dimensional-modelling.dyvenia.com/transformations/keys-assignments.html) — the surrogate-key step a `map_` feeds
- [Prepare](https://dimensional-modelling.dyvenia.com/transformations/prepare.html) · [Join](https://dimensional-modelling.dyvenia.com/transformations/join.html) · [Union](https://dimensional-modelling.dyvenia.com/transformations/union.html) — the staging steps before resolution
- [Naming conventions](https://dimensional-modelling.dyvenia.com/conventions/naming.html) — the `map_`, `vw_`, `_sk`, `_nk` prefixes