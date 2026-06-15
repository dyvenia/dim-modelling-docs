# Degenerate Dimension

> **Also known as:** DD

A business identifier stored directly on a fact table that has no attributes of
its own, and therefore no separate dimension table.

**In practice:** It usually identifies the operational transaction or document a
fact row came from — an invoice number, order number, or ticket id. Keeping it on
the fact lets you group the line items of a single document without a join.

**Examples:** 

* `fact_invoice_lines.invoice_number = "INV-2026-008812"` — one invoice
spans many line-item fact rows but needs no `dim_invoice`.
* `standard_cost_amount = 3,4` - standard cost can be used as a degenerate dimension.

**Common pitfalls:**

- Don't build a dimension table for it just to "be consistent" — with no
  descriptive attributes, it stays on the fact.
- If you later discover real attributes (status, channel), promote it to a proper
  dimension and replace the degenerate key with a surrogate-key foreign key.

**See also:** [Kimball Keys Definitions](../concepts/kimball-keys.md#degenerate-dimension)
