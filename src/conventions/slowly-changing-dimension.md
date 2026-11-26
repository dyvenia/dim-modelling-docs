# Slowly Changing Dimension

> **Also known as:** SCD

A dimension whose attribute values change occasionally over time, together with
the technique chosen for whether to keep or overwrite the prior values.

**In practice:** Pick a strategy per *attribute*, not per table:

- **Type 1** — overwrite the value; no history kept.
- **Type 2** — add a new row with a new surrogate key and an effective-date range
  (`valid_from` / `valid_to` / `is_current`); full history preserved.
- **Type 3** — keep a "previous value" column alongside the current one; limited
  history.

**Validity columns:** every Type 2 dimension uses the same three columns:

- `valid_from` — the first date the version is valid, **inclusive**.
- `valid_to` — the date the version stops being valid, **exclusive**. It equals
  the `valid_from` of the next version, and is `9999-12-31` while the version is
  open.
- `is_current` — true for the open version, false for the closed ones.

A version applies to a date when `valid_from <= date AND date < valid_to`.

**Example:** A customer moves city. Type 1 overwrites the city; Type 2 closes the
old row (`valid_to`) and inserts a new current row, so historical facts still join
to the address that was true at the time.

**See also:** [Kimball Keys Definitions](../concepts/kimball-keys.md#surrogate-key) · [Standard Cost](../references/dimensions/standard-cost.md)
