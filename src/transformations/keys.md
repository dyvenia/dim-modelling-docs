# Keys

**Keys** is the final transformation. After sources are
[prepared](./prepare.md), [joined](./join.md), and [unioned](./union.md), we add
the **surrogate keys** that make each row uniquely addressable and that fact
tables join on. See [Kimball Keys Definitions](../concepts/kimball-keys.md) for
the full set of key types.

```mermaid
flowchart LR
    raw[Raw application tables] --> prepare[Prepare → staging]
    prepare --> join[Join per source]
    join --> union[Union all sources]
    union --> keys[Keys → surrogate keys]
    style keys fill:#ffd54f,stroke:#f57f17,stroke-width:2px
```

## Rules

### Hash the natural key

The recommended way to generate a surrogate key is to **hash the natural key** of
the table — whether it is a fact or a dimension.

- Hashing produces a stable, deterministic value: the same natural key always
  yields the same surrogate key, so re-runs are reproducible and idempotent.
- It is easy to explain and audit — the key is a direct function of the business
  identifier rather than an opaque sequence number.
- For composite natural keys, concatenate the parts (with a separator) before
  hashing so the combination stays unique.

```text
customer_sk = hash(customer_id)
invoice_line_sk = hash(invoice_number || '|' || line_number)
```

> **Convention:** name surrogate keys `<entity>_sk` and the source identifier
> they are built from `<entity>_nk` (natural key).

### Where keys live

- On a **dimension**, the surrogate key is the **primary key** — one per row,
  including each historical version (see [Slowly Changing Dimension](../definitions/slowly-changing-dimension.md)).
- On a **fact**, store the surrogate keys of the related dimensions as **foreign
  keys**, plus the fact's own key built from its natural key.

## See also

- [Kimball Keys Definitions](../concepts/kimball-keys.md) — natural, surrogate, durable, and foreign keys
- [Dimension](../concepts/dimension.md) — how surrogate keys serve as the dimension primary key
- [Union](./union.md) — the step that feeds this transformation
