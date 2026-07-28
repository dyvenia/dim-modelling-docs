# Unknown Members in Dimensions

An unknown member is a predefined row in a dimension table used when a fact record cannot be linked to a valid dimension record.

Instead of leaving the dimension key in the fact table as `NULL`, the fact points to the unknown member.

For example:

| customer_sk                        | customer_number | customer_name    |
| ---------------------------------- | --------------- | ---------------- |
| `00000000000000000000000000000000` | UNKNOWN         | Unknown Customer |
| `a1b2c3...`                        | C10001          | Customer A       |
| `d4e5f6`                           | C10002          | Customer B       |

A fact record with no valid customer would use:

```text
customer_sk = '00000000000000000000000000000000'
```

## Why an unknown member is needed

A fact record may fail to match a dimension for several reasons:

* the source key is missing
* the source key is invalid
* the dimension record has not been loaded yet
* data arrives in a different order across pipelines
* the source system contains inconsistent or incomplete master data
* the relationship is not applicable for a specific record

Using an unknown member allows the fact record to remain in the model while clearly indicating that the dimensional relationship could not be resolved.

This is generally preferable to:

* dropping the fact record
* leaving the foreign key as `NULL`
* creating joins that require special `NULL` handling
* silently assigning the record to an incorrect dimension member

## Standard rule

Every dimension referenced by a fact table should contain an unknown member.

When a valid dimension member cannot be found, the fact table should use the surrogate key of the unknown member.

The unknown member should be added in the final dimension model as a predefined technical row, normally using `UNION ALL` with the regular dimension records. This ensures that the row is recreated consistently whenever the dimension is built or refreshed. Separate post-load inserts should be used only where the dimension loading strategy makes the union pattern impractical.

When surrogate keys are generated using `MD5`, the standard unknown surrogate key should be a fixed reserved value with the same data type and length:

```text
00000000000000000000000000000000
```

The reserved value must be used consistently in the dimension and in all fact lookups

For example:

```sql
WITH

dimension_data as (
    SELECT
        MD5(CONCAT_WS('||', customer_number, source_system)) as customer_sk,
        customer_number,
        customer_name,
        source_system
    FROM source_data
),

unknown_member as (
    SELECT
        '00000000000000000000000000000000' as customer_sk,
        'UNKNOWN' as customer_number,
        'Unknown Customer' as customer_name,
        'SYSTEM' as source_system
)

SELECT
    customer_sk, 
    customer_number, 
    customer_name, 
    source_system 
FROM unknown_member

UNION ALL

SELECT
    customer_sk, 
    customer_number, 
    customer_name, 
    source_system 
FROM dimension_data
;
```

## Example fact lookup

When building the fact table, the dimension lookup should use a `LEFT JOIN`.

If no matching dimension member is found, the unknown surrogate key is assigned using `COALESCE`.

```sql
SELECT
    MD5(CONCAT_WS('||', f.billing_document_number, f.billing_item_number)) as billing_sk,
    f.billing_document_number,
    f.billing_item_number,
    COALESCE(d.customer_key, '00000000000000000000000000000000') as customer_sk,
    f.net_amount
FROM staging.billing_items as f
LEFT JOIN dimensions.dim_customer as d
    ON f.customer_number = d.customer_number
    AND f.source_system = d.source_system
;
```

The `LEFT JOIN` keeps the fact record even when the dimension lookup fails.

The `COALESCE` replaces the missing surrogate key with the unknown member key.

## Do not use NULL foreign keys

Foreign keys from facts to dimensions should normally not be `NULL`.

For example, avoid:

```text
customer_sk = NULL
```

Use:

```text
customer_sk = '00000000000000000000000000000000'
```

This provides several benefits:

* fact-to-dimension joins remain simple
* unmatched records remain visible in reports
* aggregations do not silently lose records
* data quality issues can be measured
* BI tools handle the relationship consistently

Example query:

```sql
SELECT
    d.customer_name,
    sum(f.net_amount) as net_amount
FROM facts.fct_billing_item as f
JOIN dimensions.dim_customer as d
    ON f.customer_key = d.customer_key
GROUP BY
    d.customer_name;
```

Records without a resolved customer will be grouped under:

```text
Unknown Customer
```

Without an unknown member, an inner join could remove these fact records from the result entirely.

The use of an unknown member prevents record loss, but it does not remove the need to investigate unresolved dimension relationships. Monitoring and handling such cases should be covered by the data quality standards.

## Unknown members in SCD Type 2 dimensions

An unknown member in an SCD Type 2 dimension should normally be a permanent technical row.

Example:

| customer_sk                        | customer_number | valid_from | valid_to   | is_current |
| ---------------------------------- | --------------- | ---------- | ---------- | ---------- |
| `00000000000000000000000000000000` | UNKNOWN         | 1900-01-01 | 9999-12-31 | 1          |

The unknown member:

* should cover the full supported technical validity range
* should not expire
* should not receive new versions
* should not be changed by the normal SCD comparison logic
* should be excluded from standard source-driven inserts and updates
* should remain marked as the current version

The dates `1900-01-01` and `9999-12-31` are technical validity boundaries. They should not be interpreted as actual business dates.

When resolving an SCD Type 2 relationship, the fact load should first attempt to find the dimension version valid at the fact event date.

If no valid historical dimension version is found, the fact is assigned to the permanent unknown member.

The unknown row does not need to be matched through the effective-date conditions. Its surrogate key is assigned as the fallback after the regular historical lookup fails.

## Date dimensions

A date dimension may also contain an unknown member.

For example:

| date_sk  | calendar_date | date_label   |
| -------- | ------------- | ------------ |
| 0        | NULL          | Unknown Date |
| 20260713 | 2026-07-13    | 2026-07-13   |

If the source date is missing or invalid, the fact can use:

```text
date_key = 0
```

Do not replace an unknown date with an arbitrary real date such as:

```text
1900-01-01
```

unless that date is explicitly used as the documented unknown member.

Using a real calendar date without clearly identifying it as technical can lead users to interpret it as an actual business date.

