# Introduction

Welcome to the **Dimensional Modelling Docs** — a shared, practical source of
truth for building dimensional (Kimball-style) data warehouses and marts. It
collects the concepts, definitions, and reference models we rely on when
designing facts and dimensions, written to be useful both to the analytics
engineers on the team and to the LLMs that assist them.

## Why this guide

There are many excellent Kimball books and tutorials, but we kept hitting the
same gaps. They were:

* **Not written for LLMs** — hard to feed to an assistant as ground truth.
* **Light on concrete examples** — strong on theory, thin on the exact SQL and
  edge cases you actually meet in production.

So this guide is deliberately pragmatic: short explanations backed by real
examples we have encountered while developing facts and dimensions in production.

## Concepts

The [Concepts](./concepts/dimension.md) section covers the foundational building
blocks of dimensional modelling — the ideas you compose into a model. Start with
the [Dimension](./concepts/dimension.md), see how dimensions and facts fit
together in a [Star Schema](./concepts/star-schema.md), then learn how rows are
identified and linked in [Kimball Keys Definitions](./concepts/kimball-keys.md).

## Definitions

The [Kimball Group](https://www.kimballgroup.com/) website already offers
excellent, concise definitions. Here the focus is narrower: collect the terms
that come up most often during development, each as a short, self-contained
definition with an example where it helps. See
[Degenerate Dimension](./definitions/degenerate-dimension.md) or
[Slowly Changing Dimension](./definitions/slowly-changing-dimension.md) for the
shape these take.

## Reference

The Reference section is a growing catalogue of the facts and dimensions you meet
in real-life scenarios. Each page documents one entity — its grain, schema,
worked SQL, and common pitfalls — so you have a standard to design and build from
(and one an LLM can quote). [Standard Cost](./references/dimensions/standard-cost.md) is the
first worked example.
