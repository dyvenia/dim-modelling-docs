# Introduction

Welcome to the **Dimensional Modelling Docs** — a shared, practical source of
truth for building dimensional (Kimball-style) data warehouses and marts. It
collects the concepts, definitions, and reference models we rely on when
designing facts and dimensions, written to be useful both to the analytics
engineers on the team and to the LLMs that assist them.

## Why dimensional modeling

Source systems like SAP are built to *run* the business — thousands of
normalised tables optimised for fast, safe transactions. They are not built to
*analyse* the business. Asking "what did we sell, to whom, by product line, this
quarter?" against raw source tables means joining dozens of tables, decoding
cryptic keys, and reconciling inconsistent values — slow to write, slow to run,
and easy to get wrong.

Dimensional modeling reorganises that same data around how the business actually
asks questions. Facts hold the measurements (amounts, quantities); dimensions
hold the descriptive context (customer, product, date) you slice and group by.
The result is a model that is:

* **Understandable** — business users recognise the structure without a data dictionary.
* **Fast** — star schemas are optimised for the read-heavy, aggregate queries that reporting needs.
* **Consistent** — conformed dimensions mean "revenue by business unit" reconciles across every report.

In short: we do dimensional modeling so the business can answer its own questions
quickly, correctly, and in the same language everywhere.

## Why this guide

There are many excellent Kimball books and tutorials, but we kept hitting the
same gaps. They were:

* **Not written for LLMs** — hard to feed to an assistant as ground truth.
* **Light on concrete examples** — strong on theory, thin on the exact SQL and
  edge cases you actually meet in production.

So this guide is deliberately pragmatic: short explanations backed by real
examples we have encountered while developing facts and dimensions in production.

## Who is this for

This documentation is designed to be accessible and valuable across different roles and experience levels:

*   **Data & Analytics Engineers (Junior to Senior):** To learn the technical standards, transformation patterns, and key strategies (such as hash hybrids and SCD2) required to build robust pipelines.
*   **Data Analysts:** To understand how our data marts are structured, how to query facts and dimensions correctly, and how to utilize business-facing views.
*   **Business Stakeholders:** To grasp the core concepts of our data models and align on shared terminology (like grain, dimensions, and facts) when defining data requirements.


## How this fits with the Playbook & Templates

This guide does not exist in isolation. It acts as the conceptual bridge between our high-level processes and our low-level code templates. Here is how you can navigate the ecosystem:

*   **The Playbook:** Covers the "how-to" of our delivery process, CI/CD, and overall architecture.
*   **This Guide:** Covers the "what" and "why" of our dimensional models (Core Concepts, Transformations, Patterns, and Conventions).
*   **Templates & Reference Catalogues:** For practical, everyday implementation, refer to our [Dimensions Template](./references/dimensions/dimension_template.md) and [Facts Template](./references/dimensions/fact_template.md). They provide concrete examples based directly on the rules defined in this guide.