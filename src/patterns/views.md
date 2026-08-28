# Secured Views

A **secured view** is a governed database view that exposes an approved fact or dimension through a secured/access schema.

Its purpose is to provide controlled access to modeled data by selecting approved columns and, where needed, applying access filters such as region, entity, country, or business area.

A secured view does not replace dimensional modeling. It exposes fact and dimension structures from the internal modeling layer to approved consumers without giving them direct access to the physical `facts` and `dimensions` schemas.

A secured view may:

* select specific columns
* apply access-related filters
* provide stable object names for users and BI tools

A secured view should not contain additional modeling logic, calculations, complex transformations, deduplication logic, or joins. Those should be handled earlier in the modeling layer.

A secured view should not join facts and dimensions for enrichment. It should expose either a fact or a dimension, not create a flattened business object. The only exception is a join required purely for access filtering. If the security attribute, such as region or entity, sits on a dimension rather than on the fact, the secured view may join to that dimension only to apply the access filter. Columns from the joined dimension should not be exposed unless they are part of the approved secured view definition.

Separating the modeling layer from the publishing layer allows the physical model to evolve without breaking reports. Secured views become a stable contract between the warehouse and its consumers.

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
finance.fct_billing_cogs
finance.dim_calendar
finance_emea.fct_billing_cogs
sales.fct_bookings
sales_emea.fct_bookings
```

The access layer is responsible for:

* exposing approved columns
* applying access-related filters, for example, region or entity filters
* giving users stable, business-friendly entry points
* separating global and restricted access scopes where needed
* exposing approved fact and dimension views through secured/access schemas

The access layer should not become another modeling layer.

## View Design Principles

Secured views should be thin and predictable.

A secured view should only contain:

* explicit column selection
* simple column renaming where needed for user clarity
* filtering conditions required for access scope, for example, region, entity, country, or business area
* optional comments/documentation on exposed columns

A secured view shouldn’t contain:

* `SELECT *`
* undocumented business calculations
* joins between facts and dimensions, except when it’s necessary for access control
* joins between facts
* hidden transformation logic
* deduplication logic
* grain-changing logic
* complex `CASE` expressions, unless they are purely technical and approved as an exception.

Recommended pattern:

```sql
create view finance_emea.fct_billing_cogs as

SELECT
    f.billing_document_sk,
    f.billing_date_sk,
    f.sold_to_customer_sk,
    f.material_sk,
    f.sales_organization_sk,
    f.document_currency_sk,
    f.cogs_amount_doc,
    f.cogs_amount_lcy,
    f.cogs_amount_eur
FROM facts.fct_billing_cogs f
LEFT JOIN dimensions.dim_sales_organization o
    ON o.sales_organization_sk = f.sales_organization_sk
WHERE o.region_code = 'EMEA';
```

The view should make the access scope clear, but the calculation of `cogs_amount_doc`, `cogs_amount_lcy`, or `cogs_amount_eur` should already happen in the modeled fact table.

The selected columns should follow the agreed fact design. The fact structure itself is defined in the fact modeling documentation.

## Common Pitfalls

* Putting undocumented business logic into the access layer. Calculations, joins, and transformations belong in the modeling layer.
* Using `SELECT *`. Explicitly selecting columns prevents downstream reports from changing when the modeled table evolves.
* Joining facts and dimensions for enrichment inside secured views. A secured view should expose a fact or a dimension, not create a flattened business object. Joins are allowed only when required for access filtering.
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
finance.fct_billing_cogs
finance.fct_booking

finance_emea.fct_billing_cogs
finance_emea.fct_booking
```

In this approach:

* finance contains globally accessible finance views
* finance_emea contains finance views restricted to the EMEA region
* access can usually be granted at the schema level
* all views inside a schema should follow the same access rules.

This approach is easier for users to understand and easier to govern.

A user can clearly see that:

```text
finance.fct_billing_cogs
```

means global finance access, while:

```text
finance_emea.fct_billing_cogs
```

means finance data limited to EMEA.

It also reduces the risk of mixing global and restricted views in one schema.

## Dimension Views

Dimensions can also be exposed through secured views.

A secured dimension view should follow the same principles as a secured fact view:

* expose only approved columns
* apply access filters where required
* avoid additional modeling logic
* avoid exposing the physical `dimensions` schema directly to users.

If a dimension is broadly reusable and non-sensitive, it may be exposed through a shared or common access schema. If a dimension requires domain-specific or regional restrictions, it should be exposed through the relevant secured/access schema.

The naming and structure of shared dimension access schemas should follow the access schema strategy documentation.

## Naming

Secured views should generally keep the same object name as the approved fact or dimension they expose.

Example:

```text
facts.fct_billing_cogs
finance.fct_billing_cogs
finance_emea.fct_billing_cogs
```

If the access scope is already clear from the schema name, avoid repeating it in the view name.

Preferred:

```text
finance_emea.fct_billing_cogs
```

Less preferred:

```text
finance.fct_billing_cogs_emea
```

## Performance Considerations

Views do not physically duplicate data. A view is usually a stored query definition on top of an underlying table. This allows multiple secured views to expose different subsets of the same modeled object without creating additional physical copies of the data.

For example, a single modeled fact:

```text
facts.fct_billing_cogs
```

can be exposed through multiple secured views:

```text
finance.fct_billing_cogs
finance_emea.fct_billing_cogs
finance_apac.fct_billing_cogs
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

finance.fct_billing_cogs
finance_emea.fct_billing_cogs
finance.dim_calendar
```

This approach keeps the model reusable, reduces data duplication, supports governance, and remains understandable for both technical and business users.
