# Introduction

Welcome to the **Dimensional Modelling Docs**.

This site collects reference material, conventions, and definitions for building
dimensional (Kimball-style) data warehouses and marts. It is meant as a shared
source of truth for analytics engineers and data modellers on the team.

## How this is organised

- **Concepts** — foundational definitions and patterns (start with
  [Kimball Keys Definitions](./concepts/kimball-keys.md)).

## Building these docs

This site is built with [mdBook](https://rust-lang.github.io/mdBook/). From the
project root:

```bash
mdbook serve --open   # live-reload preview at http://localhost:3000
mdbook build          # render static HTML into ./book
```
