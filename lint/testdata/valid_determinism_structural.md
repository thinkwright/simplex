# Valid Determinism - Structural Level

A valid Simplex specification demonstrating DETERMINISM with structural level
and vary/stable fields for fine-grained variance control.

DATA: SearchResult
  items: list of Item, required
  total_count: positive integer, required
  query: string, required

DATA: Item
  id: string, required
  score: number, required
  title: string, required

FUNCTION: search(query, limit) → SearchResult

DETERMINISM:
  level: structural
  vary: ordering of items with equal scores, whitespace in titles
  stable: all item IDs, all scores, total_count, query echo

RULES:
  - search index for items matching query
  - return up to limit items sorted by relevance score
  - items with equal scores may appear in any order
  - always echo the original query in response

DONE_WHEN:
  - results contain only matching items
  - results are sorted by score (ties may vary)
  - total_count reflects actual matches

EXAMPLES:
  ("test", 10) → { items: [...], total_count: 42, query: "test" }
  ("nonexistent", 10) → { items: [], total_count: 0, query: "nonexistent" }
  ("", 10) → Error: empty query

ERRORS:
  - empty query → fail with "query cannot be empty"
  - negative limit → fail with "limit must be positive"
  - any unhandled condition → fail with descriptive message
