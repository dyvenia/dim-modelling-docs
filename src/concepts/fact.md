# Fact 

A **fact** table is the center table of the star schema in Kimball methodology. This table consists of the quantitative measurements of business value such as the sales, orders, backlogs, etc. 

**What is a fact table?**
A fact table is the final answer of analytics containing numeric measures produced by operational measurements and dimensional modeling.  They store the measurable, quantitative data associated with a business process or event  while the surrounding dimension tables provide the descriptive context. A fact table is typically narrow but very long, growing continuously as new business events occur, and it connects to dimensions through foreign keys. 

**Designing a fact table**
A fact table is the foundation for reliable, consistent reporting and analytics. A poorly defined fact table consists of these:
1. Ambiguous grain
2. mixed level of detail
3. non-additive measures stored like an additive measure. 

A poorly defined fact table can lead to duplicates, incorrect aggregations and inconsistent answers to the same question depending on the tools used by different teams. AI-drive tools and agents lack the intuition to catch mistakes which makes it more important to have a well and correctly designed fact table. 

**Business usage of fact tables**
Fact table modelling is the right approach whenever you need to analyze a measurable business process — sales, orders, shipments, support tickets, inventory levels, and similar events or states. Which type of fact table to use depends on the nature of the process:

- **Transaction fact tables** — when you need the finest-grained record of individual events (e.g., each sales transaction). This is the most common and most granular pattern, and the default choice unless there's a specific reason to aggregate further.
- **Periodic snapshot fact tables** — when you need to track status or balances at regular intervals, regardless of whether activity occurred (e.g., monthly account balances, daily inventory levels).
- **Accumulating snapshot fact tables** — when you're tracking an entity through a workflow with defined milestones, and the row needs to be updated as the entity progresses (e.g., an order moving through placed → shipped → delivered).
- **Factless fact tables** — when the goal is to record that an event or association occurred, without any associated numeric measure (e.g., student attendance, coverage tables).

A different approach may be more appropriate when the data doesn't represent a measurable business process at all — purely descriptive or reference data belongs in a dimension table, not a fact table. Similarly, if the "measure" you want to report on is a ratio or percentage rather than an additive quantity, it typically shouldn't be stored directly as a fact column — see Implementation Considerations below.


**Structure and grain**
The grain of a fact table — the precise definition of what a single row represents — must be declared before any other design decision is made, and every column in the table must be true to that grain. Once the grain is set, the table should contain:

- **Foreign keys** to the relevant conformed dimensions
- **Measures (facts)** that are numeric and, wherever possible, additive

This is guidance rather than a rigid template: the exact set of dimensions, the type of fact table, and the handling of edge cases will vary by business process. What should not vary is the discipline of declaring the grain explicitly and keeping every row and column consistent with it.

**Steps of designing a fact table**

1. **Declare the grain.** Write a single, unambiguous sentence describing what one row represents (e.g., "one row = one product line item on one customer sales order"). This statement should be documented, not just implied by the design.
2. **Identify the dimensions.** Determine which conformed dimensions apply at that grain (date, customer, product, store, etc.) and add them as foreign keys, using consistent surrogate key naming across all fact tables (e.g., `customer_key` always refers to `dim_customer.customer_key`).
3. **Identify the facts.** Add the numeric measures relevant to the process, favoring additive measures (quantities, amounts) over derived or non-additive ones (percentages, ratios, averages).
4. **Classify additivity.** For each fact, determine whether it is additive, semi-additive, or non-additive, and document this — it determines how the fact can safely be aggregated.
5. **Handle special cases explicitly.** Use surrogate "not applicable" dimension rows instead of NULLs where the absence of a value carries business meaning (e.g., a `promotion_key = -1` row for "no promotion applied," rather than a NULL foreign key).

**Example:** A retail sales line-item fact table might look like this:

| order_number | order_line_number | order_date_key | customer_key | product_key | quantity_sold_units | net_sales_amount_usd | cost_amount_usd |
|---|---|---|---|---|---|---|---|
| 100234 | 1 | 20260115 | 4821 | 9931 | 2 | 59.98 | 32.00 |

Here, the grain is "one row per product line item per sales order." `quantity_sold_units`, `net_sales_amount_usd`, and `cost_amount_usd` are all additive facts that can be safely summed across any combination of dimensions — by customer, by product, by date, or all three.

## Implementation Considerations

## - **Additivity discipline.** Store base additive measures (quantity, gross amount, discount amount, cost) rather than pre-computed ratios (margin %, average discount rate). Derived ratios should be calculated at query time or defined once in a semantic/metrics layer, not stored as fact columns — this avoids the common error of summing or averaging a percentage across rows.
## - **Conformed keys.** Foreign key columns should use consistent names and types across every fact table that references the same dimension. This keeps join logic predictable, whether written by an analyst or generated by a query tool.
## - **Slowly changing dimensions.** Fact tables referencing Type 2 SCD dimensions will reflect the dimension's attributes as of the event date — this needs to be understood by anyone (or anything) querying historical trends.
## - **NULL handling.** Avoid NULLs that carry implicit business meaning. Use surrogate "not applicable" or "unknown" dimension rows instead, so the meaning is explicit and queryable.
## - **Naming clarity.** Self-descriptive, unambiguous column names (including units, e.g., `net_sales_amount_usd` rather than `amt`) reduce misinterpretation — by human analysts, and especially by AI-driven query tools that infer meaning primarily from names and metadata rather than institutional knowledge.
## - **Documentation and metadata.** The grain, additivity classification, and business definitions should be captured as table/column-level metadata (e.g., in a data dictionary, dbt `schema.yml`, or semantic layer) rather than left as tribal knowledge. This is increasingly important as more tools — including AI agents — consume the schema directly.
## - **Performance and volume.** Fact tables grow continuously and can become very large; partitioning (typically by date), appropriate indexing, and periodic archiving strategies should be considered as part of the physical design, separate from the logical grain decision.


