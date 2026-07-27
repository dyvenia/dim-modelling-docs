# Views (Business Views)

A business view is a user-facing database view built on top of an approved fact, dimension, or curated mart. It forms part of the access layer of the dimensional model, exposing only approved data while keeping the underlying modeling schemas internal.

In practice, business views are the approved access-layer representations of modeled facts, dimensions, or approved marts.

They do not replace dimensional modeling. BI tools such as Power BI may still consume fact and dimension structures and build semantic models on top of them. The difference is that users and BI tools should query the curated views exposed through access-layer schemas rather than the physical tables stored in the internal facts and dimensions schemas.

Business views provide a stable and governed interface to the modeled data while keeping the physical modeling schemas internal.

Business views should not introduce undocumented or independently defined business logic. Their main role is to present approved modeled data in a stable, governed, and user-friendly way by selecting approved columns and, where required, applying access restrictions.

Simple aggregations or calculations may be allowed when they are based on already modeled measures, are approved, and are clearly documented. More complex, reusable, or grain-changing logic should usually be handled earlier in the modeling layer, for example, as a derived fact or other approved modeled object.

A business view may:

* select specific columns
* apply access-related filters
* provide stable object names for users and BI tools
* expose simple approved calculations or aggregations based on already modeled measures

A business view should not contain additional modeling logic, calculations, complex transformations, deduplication logic, or joins. Those should be handled earlier in the modeling layer.

Separating the modeling layer from the publishing layer allows the physical model to evolve without breaking reports. Business views become a stable contract between the warehouse and its consumers.

The main assumption is that modeled facts and dimensions are stored as physical tables in dedicated modeling schemas, for example:

```text
facts
dimensions
```

End users should not query these schemas directly. Instead, users should access curated views created on top of these tables in user-facing schemas.

The goal is to:

* keep business logic centralized in modeled fact and dimension tables
* expose only approved columns to users
* support different access scopes, for example, global vs regional access
* avoid unnecessary table duplication
* keep naming simple and understandable for business and technical users
* prevent the access layer from becoming another modeling layer.

## Layer Definitions

### Modeling Layer

The modeling layer contains physical tables created as part of the dimensional model.

Examples:

```text
facts.fct_billing_cogs
facts.fct_bookings
dimensions.dim_calendar
dimensions.dim_customer
dimensions.dim_material
```

This layer should contain the actual business logic, calculations, joins, transformations, surrogate keys, conformed dimensions, and reusable fact definitions.

End users should generally not have direct access to this layer.

### Access Layer / Publishing Layer

The access layer contains views that expose approved modeled data to users.

Examples:

```text
finance.fct_billing_cogs_v
finance.fct_margin_v
finance_emea.fct_billing_cogs_v
sales.fct_bookings_v
sales_emea.fct_bookings_v
```

The access layer is responsible for:

* exposing approved columns
* applying access-related filters, for example, region or entity filters
* giving users stable, business-friendly entry points
* separating global and restricted access scopes where needed
* exposing approved derived or aggregated views where there is a documented use case

The access layer should not become another modeling layer.

## View Design Principles

Business views should be thin and predictable.

A business view should only contain:

* explicit column selection
* simple column renaming where needed for user clarity
* filtering conditions required for access scope, for example, region, entity, country, or business area
* optional comments/documentation on exposed columns

A business view should never contain:

* SELECT *
* undocumented business calculations
* joins between facts and dimensions
* joins between facts
* hidden transformation logic
* deduplication logic
* grain-changing logic
* complex CASE expressions, unless they are purely technical and approved as an exception.

Recommended pattern:

```sql
CREATE view finance_emea.fct_billing_cogs_v AS

SELECT
    billing_document_sk,
    billing_document_id,
    billing_item_id,
    billing_date_key,
    sold_to_customer_sk,
    material_sk,
    sales_organization_code,
    document_currency_code,
    cogs_amount_doc,
    cogs_amount_lcy,
    cogs_amount_eur
FROM facts.fct_billing_cogs
WHERE region_code = 'EMEA';
```

The view should make the access scope clear, but the calculation of cogs_amount_doc, cogs_amount_lcy, or cogs_amount_eur should already happen in the modeled fact table.

## Common Pitfalls

* Putting undocumented business logic into the access layer. Calculations, joins, and transformations belong in the modeling layer.
* Using SELECT *. Explicitly selecting columns prevents downstream reports from changing when the modeled table evolves.
* Joining facts and dimensions inside business views. This effectively creates another semantic layer and duplicates business logic.
* Materializing filtered copies of fact tables before measuring whether views actually present a performance issue.
* Exposing physical modeling schemas directly to users instead of publishing curated views.

## Access Pattern

### Schema-Level Access by Domain and Scope

The recommended default is to create separate access-layer schemas by business domain and access scope.

Examples:

```text
finance
finance_emea
sales
sales_emea
operations
operations_emea
```

Example views:

```text
finance.fct_billing_cogs_v
finance.fct_margin_v

finance_emea.fct_billing_cogs_v
finance_emea.fct_margin_v
```

In this approach:

* finance contains globally accessible finance views
* finance_emea contains finance views restricted to the EMEA region
* access can usually be granted at the schema level
* all views inside a schema should follow the same access rules.

This approach is easier for users to understand and easier to govern.

A user can clearly see that:

```text
finance.fct_billing_cogs_v
```

means global finance access, while:

```text
finance_emea.fct_billing_cogs_v
```

means finance data limited to EMEA.

It also reduces the risk of mixing global and restricted views in one schema.

## Dimension Views

Dimensions are reusable objects and may be consumed by multiple business areas.

The recommended starting point is a hybrid approach.

Use a shared dimension access schema for broadly reusable, non-sensitive dimensions.

Example:

```text
common.dim_calendar_v
common.dim_currency_v
common.dim_country_v
```

Use domain/access-specific dimension views when the dimension must follow the same access scope as the facts.

Example:

```text
finance.dim_customer_v
finance_emea.dim_customer_v
sales.dim_customer_v
sales_emea.dim_customer_v
```

This keeps common dimensions simple while still allowing restricted dimensions where needed.

Recommendation

* expose safe, conformed dimensions once in a shared access schema
* expose restricted or domain-specific dimensions inside the relevant access schema
* avoid exposing the physical dimensions schema directly to users.

## Naming Recommendations

### Physical Modeling Schemas

Recommended:

```text
facts
dimensions
```

These names are simple, aligned with dimensional modeling, and easy to understand.

### Access Layer Schemas

Recommended pattern:

```text
<business_domain>
<business_domain>_<access_scope>
```

Examples:

```text
finance
finance_emea
sales
sales_emea
operations
operations_apac
```

This naming makes the purpose of access clear.

### View Names

Recommended pattern:

```text
<object_name>_v
```

Examples:

```text
fct_billing_cogs_v
fct_margin_v
fct_bookings_v
dim_customer_v
dim_calendar_v
```

If the access scope is already clear from the schema name, avoid repeating it in the view name:

```text
finance_emea.fct_billing_cogs_v
```

vs

```text
finance.fct_billing_cogs_emea_v
```

The first option keeps the object name stable and puts the access scope at the schema level.

For aggregation views, the name should clearly describe the grain or purpose.

Examples:

```text
finance.fct_margin_by_global_customer_v
sales.fct_bookings_by_month_v
```

## Performance Considerations

Views do not physically duplicate data. A view is usually a stored query definition on top of an underlying table. This allows multiple business views to expose different subsets of the same modeled object without creating additional physical copies of the data.

For example, a single modeled fact:

```text
facts.fct_billing_cogs
```

can be exposed through multiple business views:

```text
finance.fct_billing_cogs_v
finance_emea.fct_billing_cogs_v
finance_apac.fct_billing_cogs_v
```

without physically duplicating the full fact table.

This approach is preferable to creating separate filtered tables, such as:

```text
facts.fct_billing_cogs_global
facts.fct_billing_cogs_emea
facts.fct_billing_cogs_apac
```

unless there is a clear performance- or platform-specific reason to materialize them.

### Important Performance Notes

The actual performance depends on the database engine and optimizer.

In most modern SQL engines, simple views with column selection and filters can perform well because the optimizer can push filters down to the underlying table.

However, performance should still be tested for large fact tables, especially when:

* the underlying table is very large
* many users query the same views concurrently
* BI tools generate inefficient SQL
* access filters are complex
* the underlying table is not partitioned or clustered appropriately
* the database platform charges heavily for scanned data.

### Recommended Practice

Do not duplicate tables by default.

Start with thin access-layer views on top of modeled tables.

Materialize filtered tables only when there is evidence that:

* view performance is not acceptable
* the platform cannot optimize the view properly
* concurrency creates a real bottleneck
* storage cost is lower than the repeated query cost
* the filtered object is reused heavily by many consumers.

Materialized copies should be treated as an exception and documented.

## Summary

The preferred architecture is to model once and publish through controlled, thin views.

Facts and dimensions should remain in dedicated modeling schemas. Users should access data through business-friendly access-layer schemas.

The access layer should be organized by business domain and, where needed, by access scope.

Recommended example:

```text
facts.fct_billing_cogs
dimensions.dim_calendar

finance.fct_billing_cogs_v
finance_emea.fct_billing_cogs_v
common.dim_calendar_v
```

This approach keeps the model reusable, reduces data duplication, supports governance, and remains understandable for both technical and business users.

