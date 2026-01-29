# Valid Evolution Spec with Model Grading

A valid Simplex specification using model grading for subjective outputs.

FUNCTION: improve_documentation(docs) → ImprovedDocs

BASELINE:
  reference: "current documentation state"
  preserve:
    - all existing pages remain accessible
    - links continue to work
  evolve:
    - improve clarity of explanations
    - add more code examples

RULES:
  - maintain all existing content
  - enhance explanations for clarity
  - add working code examples where missing

DONE_WHEN:
  - all pages accessible
  - explanations improved
  - examples added to key sections

EXAMPLES:
  # Preserved behaviors
  (existing_page) → page remains accessible
  (existing_links) → links still work

  # Evolved capabilities - subjective, needs model grading
  (confusing_section) → "clearer explanation"
  (section_without_examples) → "section with working examples"

ERRORS:
  - any unhandled condition → fail with descriptive message

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: model
