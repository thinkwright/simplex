# Simplex fidelity pilot review record

Status: author-side review complete; independent review pending

Reviewer: Codex, construction review (not independent)

Review date: 2026-07-19

Artifact-manifest SHA-256: `ec1c6b135ba82be11fde68ea1078d8c6d2cc8b2d28f6547af28f0212609c55d9`

## Mechanical gates

- [x] Generated prompts match family sources.
- [x] All prompts lint with zero diagnostics under Simplex v0.6.
- [x] All reference implementations pass their matching graders.
- [x] Cross-variant references fail only the declared mutation target.
- [x] Every requirement has held-out evidence.
- [x] Every declared example-requirement pair has a direct visible check.
- [x] ThinkBench resolves exactly 18 tasks and one selected condition.
- [x] The frozen matrix contains exactly 162 expected cells.

## Semantic review

For each family, confirm that the base and two mutation prompts differ semantically only in the
declared target requirement and its necessary examples. Confirm that graders test observable
behavior without requiring an undisclosed implementation choice.

| family | decision | notes |
|---|---|---|
| `cursorvault` | author-reviewed | Only cursor interpretation and its direct examples differ; terminal-page checks are cursor-neutral outside `R4`. |
| `configweave` | author-reviewed | Only list merge policy and its direct example differ; recursive mapping, deletion, copying, and validation remain fixed. |
| `idledger` | author-reviewed | Only successful-ID conflict handling differs; identical replay, insufficient funds, validation, and concurrency remain fixed. |
| `tokenquota` | author-reviewed | Only post-refill fractional handling differs; elapsed-time, capacity, availability, validation, and locking remain fixed. |
| `wirecodec` | author-reviewed | Only unknown-field handling differs; validation, version compatibility, checksum, and canonical encoding remain fixed. |
| `detreport` | author-reviewed | Only group ordering differs; event ordering, aggregation, JSON form, validation, and CLI behavior remain fixed. |

The semantic decisions above are an author-side check, not an independent assessment. They are
adequate for the declared engineering pilot boundary and should not be represented as independent
validation in a publication.
