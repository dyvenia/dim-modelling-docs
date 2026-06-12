# Summary

[Introduction](./introduction.md)

# Concepts

- [Dimension](./concepts/dimension.md)
- [Star Schema](./concepts/star-schema.md)
- [Kimball Keys Definitions](./concepts/kimball-keys.md)

# Transformations

- [Prepare](./transformations/prepare.md)
- [Join](./transformations/join.md)
- [Union](./transformations/union.md)
- [Keys](./transformations/keys.md)

- [References]()
    - [Dimensions]()
        - [Standard Cost](./references/dimensions/standard-cost.md)
        - [Sales Territory](./references/dimensions/sales-territory.md)
    - [Facts]()
        - [Invoice Lines](./references/facts/invoice_lines.md)


- [Definitions]()
  - [Degenerate Dimension](./definitions/degenerate-dimension.md)
  - [Grain](./definitions/grain.md)
  - [Slowly Changing Dimension](./definitions/slowly-changing-dimension.md)




# Introduction
   - Why this guide <!-- links to Playbook for process-->
   - Who is this for <!--junior → senior, analyst → business-->
   - How this fits with the Playbook & Templates <!--'map' of files -->

# Foundations
   - Why dimensional modeling <!--problem it solves -->
   - The big picture  <!--landing→staging→dims/facts→marts -->
   - Core principles at a glance

# Core Concepts
   - Dimension
   - Fact
   - Grain
   - Star Schema
   - Keys (surrogate, natural, foreign)

# Transformations (link do pipeline templates)
   - Prepare / standardise
   - Join
   - Union
   - Keys & Unknown member

# Patterns & Edge Cases <!--this probably will grow over time, we have to agree on some concepts here as, as I said yesterday, this impacting dim model design -->
   - Unknown member
   - Late-arriving members
   - Degenerate dimensions
   - Outrigger
   - Resolution engines (map_) <!-- tbd -->
   - Composite keys
   - Views for business (vw_) <!-- imo important for analysts -->

# Conventions <!-- we can use kimball/dyvenia standard -->
   - Naming (_sk, _code, _number, is_, vw_, map_)
   - Key strategy (hash hybrid, SCD2) <!-- hash hybrid = hasing key in dim and asigning to fact, not hashing in fact independently-->

# Reference
   - Dimensions catalogue <!--(link do templates)-->
   - Facts catalogue <!--(link do templates)-->

# Glossary
   - SCD, grain, degenerate dim, conformed dim, etc.