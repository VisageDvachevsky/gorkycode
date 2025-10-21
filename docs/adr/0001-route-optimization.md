# ADR 0001: Route optimisation strategy

## Context
- The route-planner service previously relied on a greedy nearest-neighbour heuristic. It tended to overfit to the first few POIs, ignored buffer time, and could not reason about intensity as "number of places" per user expectation.
- We now expose `/healthz`, `/readyz`, and `/metrics` from the service and must support accurate liveness/readiness probes. The optimisation algorithm therefore has to provide stable timing estimates that back these probes.
- NetworkX is already a dependency in the broader stack and provides robust approximations for the travelling salesman problem (TSP) without us having to maintain bespoke graph algorithms.

## Decision
- Use `networkx.approximation.greedy_tsp` on a complete graph built from the pedestrian distance matrix (start node + candidate POIs). This gives a reproducible visiting order while remaining inexpensive for ≤8 nodes.
- Generate candidate subsets by enumerating combinations of the top-ranked POIs, capped at eight to keep the solver fast. The subset size is determined by the user-provided time and the intensity profile's target POIs per hour.
- Enforce intensity-aware visit budgets via structured profiles (target_per_hour, visit duration bounds, transition padding, safety buffer). Each candidate route is evaluated against the reduced budget (available time − safety buffer) and includes visit time plus a transition padding to match user comfort.

## Consequences
- Route timing now aligns with the marketing definition of intensity (number of POIs per hour) and leaves explicit slack for orientation/coffee inserts.
- The algorithm gracefully scales down when time is tight (fewer POIs) and still returns the "least bad" route if the budget is unattainable.
- NetworkX becomes a direct dependency of the route-planner service; the added path dependency is documented and version-pinned in `pyproject.toml`.
