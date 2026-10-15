# Key Generation

## Overview

Each table generates **its own** surrogate key. A dimension owns its keys; facts
resolve them by lookup (see [Key Assignment](../transformations/key-assignment.md)).
Key types are defined in [Kimball Keys Definitions](../concepts/kimball-keys.md).

## Sequence or hash

Kimball recommends surrogate keys as **simple integers assigned in sequence**.
This is a well-established approach, but it requires state: something has to
remember the last value issued and which natural key received which number.

An alternative is the **hash hybrid**: the key is a deterministic hash of the
row's identifying columns, generated in the table that owns it. This is the
recommended approach for pipelines that are rebuilt rather than updated in place.

| Aspect               | Sequence / identity                        | Hash (recommended)                      |
| -------------------- | ------------------------------------------ | --------------------------------------- |
| Same input, same key | Only if the mapping is persisted           | Always                                  |
| Full rebuild         | Keys may change unless the mapping is kept | Keys stay the same                      |
| State to maintain    | Sequence and key map                       | None                                    |
| Key type             | Integer                                    | `VARCHAR`                               |
| Risk                 | Lost or reset sequence                     | Changing the inputs changes every key   |

## Rules

### Hash the columns that identify the row

The input to the hash is whatever makes one row of the table unique — its
**grain** — not necessarily the natural key alone.

- **Dimension without history (SCD Type 0 / 1):** hash the natural key.
- **SCD Type 2 dimension:** hash the natural key **and** a **version identifier**
  (e.g. `valid_from`), so each version gets its own key. The natural key alone
  would give all versions the same key.
- **Fact (optional):** a fact does not require its own surrogate key. If one is
  needed, for example for incremental loads or updates, hash the fact's grain
  (e.g. document number and line number). The foreign keys to dimensions are
  not generated here; they are looked up (see
  [Key Assignment](../transformations/key-assignment.md)).
- **Composite keys:** include every part of the key. See
  [Composite keys](../patterns/composite-keys.md).

```text
customer_sk     = HASH(customer_id)                     -- no history
company_sk      = HASH(company_code, valid_from)        -- SCD Type 2, one key per version
invoice_line_sk = HASH(invoice_number, line_number)     -- fact's own key (optional)
```

### Keep the inputs stable

A hash key is only as stable as its inputs. For the same row to always get the
same key:

- use **one shared hash function** for all keys;
- keep the **same columns in the same order**, separated by a delimiter, with
  `NULL` replaced by a fixed placeholder;
- **standardise values before hashing** (data types, trimming, casing) in the
  [Prepare](../transformations/prepare.md) step, not inside the key expression;
- treat a change to the inputs as a breaking change: every key of that table
  changes, so the dimension and all facts that use it must be rebuilt.

### Keys of special members

Unknown and Not applicable members are ordinary dimension rows. With sequence
keys, they usually get fixed values such as `-1`. With hash keys, each of them
gets a reserved **natural key value**, hashed the same way as any other row.

```text
customer_sk (Unknown) = HASH('UNKNOWN')
company_sk  (Unknown) = HASH('000')
```

See [Unknown member](../patterns/unknown.md) for how these rows are defined.

## Key Takeaways

- Each table generates its own surrogate key; facts resolve dimension keys by
  lookup (see [Key Assignment](../transformations/key-assignment.md)).
- Kimball recommends sequential integers; a deterministic hash is the recommended
  alternative because it needs no state and survives full rebuilds.
- The hash input is the row's **grain**: the natural key for dimensions without
  history, the natural key plus a version identifier for SCD Type 2.
- With hash keys, special members get their keys from a hashed reserved natural
  key.

## See also

- [Key Assignment](../transformations/key-assignment.md) — how facts obtain dimension keys
- [Kimball Keys Definitions](../concepts/kimball-keys.md) — natural, surrogate, durable, and foreign keys
- [Slowly Changing Dimensions](slowly-changing-dimension.md) — why SCD Type 2 keys are version-specific
- [Unknown member](../patterns/unknown.md) — the reserved dimension row
- [Naming](naming.md) — the `_sk` and `_nk` suffixes
