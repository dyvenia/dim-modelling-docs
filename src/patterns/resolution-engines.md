# Resolution engines (map_)

A **resolution engine** — named with the `map_` prefix — is an ETL object that turns a messy code from a source system into the clean key a dimension uses, before the fact links to that dimension.

Most facts don't need a `map_` at all. They already carry a clean natural key and join the dimension directly — that is the normal case. A `map_` is only for the exceptions, where the source code isn't clean: one field might hold two different kinds of code, or a code that only makes sense with extra context, or a value buried inside a parent-child tree. A `map_` handles those cases — it does the untangling once, in one place, so every fact that needs the same resolution gets the same answer.

## Not a dimension, not a fact

A `map_` is a third kind of object, and knowing what it *isn't* tells you where it belongs.

- **Not a fact** — it records no business event and holds no measures. It resolves a code, it doesn't measure anything.
- **Not a dimension** — it is never filtered, grouped, or shown on a report. Users don't see it; only the load uses it.
- **A back-room tool** — it lives in the ETL layer, before facts are loaded. Nothing downstream joins to it; only its *output* — a clean key — flows on.

If you ever want to show a `map_` on a report, that's the sign you actually needed a dimension, and the attributes belong there instead.

## Why it exists

Without a `map_`, the same untangling has to be rewritten inside every fact that needs it. The copies slowly drift apart, the logic is buried where no one can test or reuse it, and if the source format changes you have to fix every fact instead of one object.

A `map_` keeps that rule in one place, as the single source of truth. Think of it as a translator between the source system and the warehouse: the fact no longer has to understand the source's messy codes — it just receives clean keys.

## The three shapes

Almost every `map_` is one of three patterns:

- **Code-type resolution** — one field holds two kinds of code, told apart by something you can detect, like length or prefix. The engine spots the type and resolves each to the same key. *Example: an outlet field holding either a single store code or a regional cluster code.*
- **Context-dependent resolution** — the code isn't unique on its own; it becomes unique only when combined with another field. That field can be a simple piece of context or a second full-fledged code — either way, the engine combines them into one clean key. *Example: a product code that repeats across catalogues and is unique only within one; or a code that only means something once paired with the customer it belongs to.*
- **Hierarchy walk-up** — the source is a parent-child tree of uneven depth, and you need a leaf resolved up to a set level. The engine climbs the tree and stops at that level. *Example: any node in an org tree resolved up to its department.*

## The golden rule: resolve before the key, never in the fact

The fact never untangles source codes and never builds its own keys. It receives a clean natural key from the `map_`, then joins the dimension on that key and takes the surrogate key from it — nothing more.

```
flowchart LR
    src[Source code] --> map[map_ resolution engine]
    map --> nk[Clean natural key]
    nk --> join[Fact joins the dimension on the natural key]
    join --> fk[Fact foreign key]
```

The surrogate key is created once, in the dimension; the fact only ever takes a copy. Keeping resolution and key assignment as separate steps is what lets you check a resolution on its own, reuse it across many facts, and re-run the load without surprises. A fact that resolves codes inline puts these jobs back together and brings back every problem the `map_` was built to remove.

## Two properties that matter

- **Persisted, not inline.** A `map_` is a view or table, not a throwaway step hidden inside one model — so you can inspect and reuse the resolution. Rule of thumb: if two or more models need the resolution, it earns its own object.
- **Deterministic.** The same code must always resolve to the same key. A `map_` depends only on its inputs, never on when it ran. That's what keeps loads reproducible — a rule that could give a different answer on re-run is a bug, not a resolution engine.

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