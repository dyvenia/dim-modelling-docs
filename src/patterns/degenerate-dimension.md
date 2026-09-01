# Degenerate Dimensions

## Overview

A **degenerate dimension** is a business or transactional identifier that is stored directly in a fact table instead of in a separate dimension table.

Degenerate dimensions are typically document or transaction identifiers that are useful for filtering, grouping, drill-down, reconciliation, or tracing records back to the source system, but do not have meaningful descriptive attributes that justify creating a separate dimension.

Typical examples include:

* sales order number
* billing document number
* purchase order number
* shipment number
* claim number
* transaction number

Degenerate dimensions are a specific exception to the normal dimensional modeling approach where descriptive dimension attributes are stored in separate dimension tables.

They should not be treated as a general mechanism for placing descriptive attributes directly in fact tables.

## Recommended Approach

Business transaction and document identifiers should be stored directly in the fact table as degenerate dimensions when:

* they identify a meaningful business transaction or document,
* they are useful for filtering, grouping, reconciliation, drill-down, or source tracing,
* they do not have meaningful descriptive attributes that require a separate dimension.

A separate dimension should not be created solely to assign a surrogate key to such an identifier.

For example, a billing item fact may contain:

```text
billing_document_sk
billing_document_number
billing_document_item
customer_sk
material_sk
billing_date_sk
quantity
net_value
```

If a separate dimension were created only to represent the billing document and item identifiers:

```text
dim_billing_document

billing_document_sk
billing_document_number
billing_document_item
```

it would have essentially the same grain as the billing fact and, in many cases, a very similar row count.

The dimension would largely duplicate identifiers already available in the fact while adding no meaningful descriptive information. It would also introduce an additional table and join without providing additional dimensional context.

In this case, the transaction identifiers should remain directly in the fact.

## When to Use

A degenerate dimension is typically appropriate when the identifier:

* represents a business document or transaction,
* is meaningful to users or developers,
* may be used to group multiple fact rows belonging to the same transaction,
* is useful for validation and reconciliation,
* provides traceability back to the source system,
* does not have meaningful descriptive attributes of its own.

Common examples include:

```text
sales_order_number
billing_document_number
purchase_order_number
shipment_number
```

For example, an invoice number may span multiple invoice-item fact rows. Keeping the invoice number directly in the fact makes it possible to group or trace those rows without introducing a separate invoice dimension that contains only the identifier.

A degenerate dimension should generally not be used when the identified business object has meaningful descriptive attributes that need to be modeled.

For example, attributes such as:

```text
customer_name
material_group
sales_region
order_type
sales_channel
```

are normal descriptive dimension attributes and should be modeled in appropriate dimension tables.

The degenerate dimension pattern should therefore remain a narrow exception for transaction and document identifiers rather than a general way of storing dimensional information in facts.

## How It Works

A billing item fact may look as follows:

```text
facts.fct_billing

billing_document_sk
billing_document_number
billing_document_item
billing_date_sk
customer_sk
material_sk
currency_sk
quantity
net_value
```

The fact grain may be defined as:

> One row per billing document item.

Here:

* `billing_date_sk` references the date dimension.
* `customer_sk` references the customer dimension.
* `material_sk` references the material dimension.
* `currency_sk` references the currency dimension.
* `billing_document_number` is stored directly in the fact as a degenerate dimension.
* `billing_document_item` identifies the individual transaction line and forms part of the natural fact grain.

The document identifier can then be used directly for analysis:

```sql
SELECT
    billing_document_number,
    SUM(net_value) AS net_value
FROM facts.fct_billing
GROUP BY billing_document_number;
```

It can also be used for validation or troubleshooting:

```sql
SELECT *
FROM facts.fct_billing
WHERE billing_document_number = '0000123456';
```

This allows the dimensional model to retain a direct connection to the source transaction without requiring a separate dimension table.

## Implementation Considerations

### Technical Keys

A fact may still contain a standardized technical key for a degenerate dimension.

For example:

```text
billing_document_sk
billing_document_number
```

The `billing_document_sk` may be generated from the business identifier according to the modeling standard, for example using a stable hash or another standardized key-generation method.

In this case, the key does not necessarily represent a foreign key to a physical dimension table. It can instead act as a standardized technical identifier for the business transaction.

The presence of a `_sk` column therefore does not by itself mean that a corresponding dimension table must exist.

### Fact Grain

Document and transaction identifiers often form part of the natural grain of a fact.

For example:

```text
billing_document_number
billing_document_item
```

may together identify the source transaction line represented by a billing fact row.

The document number is a typical degenerate dimension.

The item number primarily represents part of the transaction grain, but it may still be retained directly in the fact because it is useful for identification, reconciliation, and source tracing.

### Avoid Overusing the Pattern

Degenerate dimensions should not be used as justification for moving normal descriptive attributes into fact tables.

Being useful for filtering, grouping, or reporting is not sufficient by itself to make an attribute a degenerate dimension.

The pattern is intended for identifiers where creating a separate dimension would not add meaningful dimensional context.

If meaningful attributes are later identified for a transaction or document, the model should be reviewed.

This does not automatically mean that a document-level dimension must be created. The attributes may belong in existing conformed dimensions, separate dimensions, or another appropriate modeling structure.

## Key Takeaways

* Degenerate dimensions are business or transaction identifiers stored directly in fact tables.
* They are most appropriate when the identifier is useful but has no meaningful descriptive attributes of its own.
* They are commonly used for document numbers such as invoices, orders, shipments, and purchase orders.
* A separate dimension should not be created solely to hold the identifier and assign it a surrogate key.
* A technical `_key` may still be retained even when no physical dimension table exists.
* Degenerate dimensions are a narrow exception and should not be used to place ordinary descriptive dimension attributes or measures directly in fact tables.
