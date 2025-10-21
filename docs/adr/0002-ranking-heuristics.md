# ADR 0002: Ranking heuristics and category boosts

## Context
- The ranking-service blends embedding similarity with social-mode and intensity adjustments. The heuristics were implicit in code and not documented, making it hard to justify weighting choices or evolve them coherently.
- Upcoming analytics require predictable behaviour across social modes so that marketing copy (e.g. "friends" favour bars, "family" prefers parks) stays true to the algorithm.

## Decision
- Keep cosine similarity as the primary scoring function to preserve alignment between the user's embedding vector and POI embeddings.
- Apply multiplicative boosts from curated dictionaries (`SOCIAL_MODE_WEIGHTS`, `INTENSITY_WEIGHTS`) to nudge categories without overpowering similarity. The weights remain ≤1.4 to avoid drowning the base signal.
- Surface the heuristics in this ADR so product and data teams can iterate on category weight tables without reverse-engineering the service.

## Consequences
- Category adjustments remain explainable: changing a weight requires updating a single dictionary entry and re-running the service.
- Cosine similarity continues to dominate, ensuring new embeddings integrate seamlessly while the boosts provide tasteful steering.
- The documentation enables future experimentation (e.g. weight tuning from analytics) without compromising traceability.
