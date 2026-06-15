# Summary
[Introduction](./introduction.md)

# Foundations
   - [Why dimensional modeling](./foundations/big-picture.md)
   - [The big picture](./foundations/core-principles.md)
   - [Core principles at a glance](./foundations/why-dimensional-modeling.md)

# Core Concepts
   - [Dimension](./concepts/dimension.md)
   - [Fact](./concepts/fact.md)
   - [Grain](./concepts/grain.md)
   - [Star Schema](./concepts/star-schema.md)
   - [Keys (surrogate, natural, foreign)](./concepts/kimball-keys.md)

# Transformations
   - [Prepare / standardise](./transformations/prepare.md)
   - [Join](./transformations/join.md)
   - [Union](./transformations/union.md)
   - [Keys & Unknown member](./transformations/keys-assignments.md)

# Patterns & Edge Cases
   - [Unknown member](./patterns/unknown.md)
   - [Late-arriving members](./patterns/late-arriving.md)
   - [Degenerate dimensions](./patterns/degenerate-dimension.md)
   - [Outrigger](./patterns/outtrigger.md)
   - [Resolution engines (map_)](./patterns/resolution-engines.md)
   - [Composite keys](./patterns/composite-keys.md)
   - [Views for business (vw_)](./patterns/views.md)

# Conventions
   - [Naming (_sk, _code, _number, is_, vw_, map_)](./conventions/naming.md)
   - [Key strategy (hash hybrid, SCD2)](./conventions/slowly-changing-dimension.md)

# [Reference]()
   - [Dimensions catalogue]()
      - [Standard Cost](./references/dimensions/standard-cost.md)
      - [Sales Territory](./references/dimensions/sales-territory.md)
   - [Facts catalogue]()
      - [Invoice Lines](./references/facts/invoice_lines.md)
      
# Glossary
   - [SCD, grain, degenerate dim, conformed dim, etc.](./glossary.md)