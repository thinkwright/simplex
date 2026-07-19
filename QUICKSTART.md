# Simplex

A semi-structured specification format for work assigned to autonomous agents.

## What is Simplex?

See [README.md](README.md) for the project overview and [spec/simplex.md](spec/simplex.md) for the
normative specification.

## Quick Start

A Simplex specification describes what a function should do using landmarks:

```simplex
SIMPLEX: 0.6

FUNCTION: add(a, b) → sum

RULES:
  - [R1] return the sum of a and b

DONE_WHEN:
  - [D1] result equals a + b

EXAMPLES:
  - [E1] value: (2, 3) → 5
  - [E2] value: (0, 0) → 0
  - [E3] error: ("x", 2) → "Inputs must be numbers"

ERRORS:
  - [X1] non-numeric input → "Inputs must be numbers"
  - any unhandled condition → fail with descriptive message

COVERS:
  - E1 → R1, D1
  - E2 → R1, D1
  - E3 → X1
```

`SIMPLEX`, bracketed identifiers, example-kind prefixes, and `COVERS` are optional v0.6
features. `COVERS` lets tooling check the integrity and completeness of the author's declared
evidence links; it does not prove that an example semantically covers a requirement.

### Required Landmarks

A valid specification requires `FUNCTION`; every function requires the other four landmarks:
- **FUNCTION** - signature and return type
- **RULES** - what the function does
- **DONE_WHEN** - success criteria
- **EXAMPLES** - input/output pairs
- **ERRORS** - failure cases

### Validate with the Linter

The bundled linter performs deterministic structural, complexity, evolution-metadata, determinism-declaration, language-version, and declared-traceability checks. It does not execute examples or perform semantic/LLM validation.

```bash
cd lint
make build
./bin/simplex-lint ../examples/minimal.simplex
```

The CLI uses `--input-mode auto` by default. It treats `.simplex` files as raw specifications, reads stdin as an already extracted specification, and lints only `simplex`-labeled fences in Markdown files that contain them. An unmarked Markdown file falls back to raw mode with a warning. Use `--input-mode raw`, `markdown`, or `extracted` to override that selection.

## Documentation

- [README.md](README.md) - Project overview
- [spec/simplex.md](spec/simplex.md) - Full specification (v0.6)
- [examples/](examples/) - Example specifications
- [docs/lint-design.md](docs/lint-design.md) - Linter architecture, checks, and boundaries

## Status

The specification and deterministic linter are experimental. Their behavior and limitations are documented in the repository.
