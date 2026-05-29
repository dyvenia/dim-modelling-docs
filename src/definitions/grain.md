# Grain

The grain of a fact table is the precise meaning of a single row — the level of
detail it records.

**In practice:** Declare the grain in business terms *before* choosing dimensions
or facts ("one row per order line", "one row per daily account balance"). Every
dimension and measure on the table must be true at that grain; mixing grains in a
single table is the most common dimensional modelling mistake.

**Example:** `fact_sales` at the grain *one row per product per order line* — so
`quantity` and `extended_amount` are recorded per line, never per whole order.

**See also:** [Standard Cost](../reference/standard-cost.md) (declares its grain as an explicit key tuple)
