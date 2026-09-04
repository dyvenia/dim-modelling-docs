# Late-Arriving Members

## Overview

A late-arriving member is a dimension member whose details arrive **after** a fact that already references it.

For example, an order fact arrives with `customer_id = 12345`, but the matching customer row hasn't reached the warehouse yet. The fact has a customer to point to, but the dimension member isn't there.

This is common when facts and dimensions come through separate pipelines, source systems run on different schedules, or data arrives out of order.

## General Rule

Don't block the fact load just because the dimension member is missing. Load the fact, let it rest on the reserved **Unknown** member, and let it resolve once the dimension catches up.

One part of this is not a matter of preference: **the fact does not build its own keys.** It takes the key from the dimension. Where the member does not exist yet, there is simply nothing to take, and the fact points at Unknown until there is.

> Load the fact now, leave it unresolved, and let the next run resolve it once the member exists.

Nothing is created to bridge the gap. No placeholder row is written, so a mistyped or invalid key leaves nothing behind to clean up, and one mechanism covers every unresolved case whatever the reason for it.

## How It Works

```
flowchart LR
    f[Fact arrives with business key] --> chk{Member exists?}
    chk -- yes --> res[Resolve to the dimension key]
    chk -- no --> unk[Point at the Unknown member]
    later[Dimension catches up] --> re[Next run resolves the fact normally]
```

1. A fact arrives with a business key (`customer_id = 12345`).
2. The member doesn't exist yet, so the fact resolves to the Unknown member and loads.
3. The real customer data arrives in the dimension.
4. The next run reprocesses that fact row, the join now succeeds, and the fact resolves to the real member.

## What This Relies On

The pattern is deliberately simple, and it stands on two things being in place.

**Facts are reprocessed over a window.** Step 4 is what does the work: a nightly run that reprocesses, say, the last thirty or forty days will pick the row up again once the dimension has caught up. The window has to be longer than the longest expected lag in dimension delivery — a member arriving after the fact has aged out will leave that fact unresolved for good. Treat the window as a dependency of this pattern, not as a tuning parameter.

**Unresolved rows are tested daily.** Referential tests over the fact's dimension keys tell you what landed on Unknown and whether it cleared. This is part of the pattern rather than an add-on: it is what turns "unresolved" from a blind spot into a tracked, expected state. A row that resolves on the next run is normal; one that stays unresolved while the dimension clearly holds the member is a signal to look at.

Where both hold, nothing else is needed — no placeholder rows, no enrichment step, no second mechanism to maintain.

## Adjusting the Pattern

A few situations call for something slightly different.

**Facts are never reprocessed.** Nothing resolves the row on its own, so the correction has to be deliberate. The tests still surface it, and the fix is **targeted re-resolution**: find the rows still on Unknown, check whether the dimension now holds their member, and update the key column on the ones that resolve. It writes nothing to the dimension, and running it again changes nothing the second time.

That needs the original business key to be reachable, and it usually already is — a fact carries its document or line identifier as a degenerate dimension, and staging holds the full source row behind it. Where staging doesn't reach back far enough, keep the business key on the fact as a degenerate column, for the few dimensions that actually arrive late. Only where it cannot be reached at all does the classic **inferred member** apply: a stub row in the dimension carrying the business key, keyed with exactly the same rule as a real row, and enriched once the details arrive.

**The fact shouldn't load at all.** Where a fact is invalid without its member — regulatory reporting that requires an approved legal entity, for instance — hold it in staging until the dimension arrives.

**The dimension is seconds behind.** If it follows almost immediately and nobody needs the fact instantly, a short buffer is simpler than anything else.

**The business key can't be trusted.** Resolving later is still the safer choice, because it commits to nothing — but an unstable identifier is a problem to fix at the source, not in the load.

## Late-Arriving Is Not Unknown

A missing member isn't always a late-arriving one. If a fact has no customer information and never will, it belongs on the Unknown member permanently — that is its final state, not a waiting room.

The catch is that on day one both look identical: a fact resting on Unknown because its member is still in transit looks exactly like a fact whose member will never exist. Late-arriving means *coming later*; unknown means *never coming* — and it is the daily tests, not the load, that tell them apart.

## Common Pitfalls

- **A reload window shorter than the delivery lag.** A member arriving after the fact has aged out of the window leaves that fact unresolved for good. Check the window against how late dimensions realistically arrive.
- **No test on unresolved rows.** Without a daily count, a permanent gap looks the same as a temporary one, and nobody notices the difference until a report is questioned.
- **Assuming everything on Unknown is late-arriving.** Some of it is invalid data that will never resolve. The tests are what separate the two.
- **Losing the business key.** Where facts are not reprocessed, a row on Unknown can only be corrected if its original business key is still reachable — from staging, or from a degenerate column on the fact. Without it there is nothing to re-resolve against.

## Key Takeaways

- Don't block the fact because a dimension member is missing — load it, and let it rest on Unknown.
- The key comes from the dimension, never from the fact.
- Resolution happens on the next run, so the reload window has to be longer than the expected dimension lag.
- Test unresolved rows daily. A row that clears is normal; one that doesn't is a signal.
- Where facts are never reprocessed, correct them with targeted re-resolution, using the business key from staging or a degenerate column. An inferred member is the established fallback where that key cannot be reached.

## Related

- [Keys & Unknown member](https://dimensional-modelling.dyvenia.com/transformations/keys-assignments.html) — where the key comes from, and the member unresolved rows land on
- [Resolution engines (map_)](https://dimensional-modelling.dyvenia.com/patterns/resolution-engines.html) — resolving a messy source code before the key is assigned