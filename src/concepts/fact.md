# Fact 

A **fact** table is the center table of the [star schema](./star-schema.md) in Kimball methodology. This table consists of the quantitative measurements of business value such as the sales, orders, backlogs, etc. 

## What is a fact?
A fact table represents a business process at a defined grain and records the measurements, events, or states associated with that process. It connects to dimensions that provide descriptive context. Reporting, semantic models, and business views are typically built on top of fact tables, rather than the fact table itself being the end deliverable.

They store the measurable, quantitative data associated with a business process or event  while the surrounding dimension tables provide the descriptive context. A fact table is typically narrow but very long, growing continuously as new business events occur, and it connects to dimensions through foreign keys. 


## Structure and grain
The grain of a fact table — the precise definition of what a single row represents — must be declared before any other design decision is made, and every column in the table must be true to that grain. Once the grain is set, the table should contain:

- **Foreign keys** to the relevant conformed dimensions
- **Measures (facts)** that are numeric and, wherever possible, additive

This is guidance rather than a rigid template: the exact set of dimensions, the type of fact table, and the handling of edge cases will vary by business process. What should not vary is the discipline of declaring the grain explicitly and keeping every row and column consistent with it.

## Business usage of fact tables
Fact table modelling is the right approach whenever you need to analyze a measurable business process — sales, orders, shipments, support tickets, inventory levels, and similar events or states. Which type of fact table to use depends on the nature of the process:

- **Transaction fact tables** — when you need the finest-grained record of individual events (e.g., each sales transaction). This is the most common and most granular pattern, and the default choice unless there's a specific reason to aggregate further.
- **Periodic snapshot fact tables** — when you need to track status or balances at regular intervals, regardless of whether activity occurred (e.g., monthly account balances, daily inventory levels).
- **Accumulating snapshot fact tables** — when you're tracking an entity through a workflow with defined milestones, and the row needs to be updated as the entity progresses (e.g., an order moving through placed → shipped → delivered).
- **Factless fact tables** — when the goal is to record that an event or association occurred, without any associated numeric measure (e.g., student attendance, coverage tables).

A different approach may be more appropriate when the data doesn't represent a measurable business process at all — purely descriptive or reference data belongs in a dimension table, not a fact table. Similarly, if the "measure" you want to report on is a ratio or percentage rather than an additive quantity, it typically shouldn't be stored directly as a fact column — see Implementation Considerations below.


## Steps of designing a fact table

1. **Declare the grain.** Write a single, unambiguous sentence describing what one row represents (e.g., "one row = one product line item on one customer sales order"). This statement should be documented, not just implied by the design.
2. **Identify the dimensions.** Determine which conformed dimensions apply at that grain (date, customer, product, store, etc.) and add them as foreign keys, using consistent surrogate key naming across all fact tables (e.g., `customer_key` always refers to `dim_customer.customer_key`).
3. **Identify the facts.** Add the numeric measures relevant to the process, favoring additive measures (quantities, amounts) over derived or non-additive ones (percentages, ratios, averages).
4. **Classify additivity.** For each fact, determine whether it is additive, semi-additive, or non-additive, and document this — it determines how the fact can safely be aggregated.
5. **Handle special cases explicitly.** Use surrogate "not applicable" dimension rows instead of NULLs where the absence of a value carries business meaning (e.g., a `promotion_key = -1` row for "no promotion applied," rather than a NULL foreign key).
6. **Assign Surrogate Keys** The assignment of surrogate key is important to identify each row. Even though it is warehouse-generated, it gives business information about each transaction.

**Example:** A retail sales line-item fact table might look like this:

| order_number | order_line_number | order_date_key | customer_key | product_key | quantity_sold_units | net_sales_amount_usd | cost_amount_usd |
|---|---|---|---|---|---|---|---|
| 100234 | 1 | 20260115 | 4821 | 9931 | 2 | 59.98 | 32.00 |
| 100234 | 2 | 20260115 | 4821 | 9931 | 4 | 119.96 | 64.00 |
| 1002378 | 2 | 20261005 | 6758 | 3427 | 4 | 210.89 | 75.80 |


Here, the grain is "one row per product line item per sales order." `quantity_sold_units`, `net_sales_amount_usd`, and `cost_amount_usd` are all additive facts that can be safely summed across any combination of dimensions — by customer, by product, by date, or all three.

 ## Implementation Considerations

 - **Additivity discipline.** Store base additive measures (quantity, gross amount, discount amount, cost) rather than pre-computed ratios (margin %, average discount rate). Derived ratios should be calculated at query time or defined once in a semantic/metrics layer, not stored as fact columns — this avoids the common error of summing or averaging a percentage across rows.
 - **Conformed keys.** Foreign key columns should use consistent names and types across every fact table that references the same dimension. This keeps join logic predictable, whether written by an analyst or generated by a query tool.
 - **Slowly changing dimensions.** Fact tables referencing Type 2 SCD dimensions will reflect the dimension's attributes as of the event date — this needs to be understood by anyone (or anything) querying historical trends.
 - **NULL handling.** Avoid NULLs that carry implicit business meaning. Use surrogate "not applicable" or "unknown" dimension rows instead, so the meaning is explicit and queryable.
 - **Naming clarity.** Self-descriptive, unambiguous column names (including units, e.g., `net_sales_amount_usd` rather than `amt`) reduce misinterpretation — by human analysts, and especially by AI-driven query tools that infer meaning primarily from names and metadata rather than institutional knowledge.
 - **Documentation and metadata.** The grain, additivity classification, and business definitions should be captured as table/column-level metadata (e.g., in a data dictionary, dbt `schema.yml`, or semantic layer) rather than left as tribal knowledge. This is increasingly important as more tools — including AI agents — consume the schema directly.
 - **Performance and volume.** Fact tables grow continuously and can become very large; partitioning (typically by date), appropriate indexing, and periodic archiving strategies should be considered as part of the physical design, separate from the logical grain decision. 

## Designing a fact table
A fact table is the foundation for reliable, consistent reporting and analytics. A poorly defined fact table typically shows one or more of these issues:

1. Ambiguous grain — the grain isn't documented, or isn't the same for every row, so it's unclear what a single row actually represents. This makes it easy to double-count or under-aggregate without realizing it.

2. Mixed level of detail — some rows represent individual events while others are pre-summarized (e.g. daily totals mixed with individual transactions) within the same table. Aggregating across these rows produces incorrect results, since the same measure means different things at different levels.

3. Non-additive measures stored and treated as additive — ratios, percentages, or averages (e.g. a tax rate or margin percentage) are summed or averaged directly across rows, rather than being recalculated from their underlying additive components. This produces numbers that look plausible but are mathematically wrong.

A poorly defined fact table can lead to duplicates, incorrect aggregations and inconsistent answers to the same question depending on the tools used by different teams. AI-drive tools and agents lack the intuition to catch mistakes which makes it more important to have a well and correctly designed fact table. 

## Key Takeaways
- Declare the grain before choosing dimensions or measures, and keep every row consistent with it.
Use additive measures where possible; derive ratios from additive components rather than storing or aggregating them directly.
- Avoid ambiguous grain, mixed levels of detail, and treating non-additive measures as additive.
<!-- - Use the _sk convention consistently for surrogate keys across fact tables. -->
- Clear naming and documented metadata reduce ambiguity for both analysts and AI query tools.





