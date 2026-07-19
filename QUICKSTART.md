# Simplex

A minimal specification language for autonomous AI agents.

## What is Simplex?

See [README.md](README.md) for the full specification.

## Quick Start

A Simplex specification describes what a function should do using landmarks:

```
FUNCTION: add(a, b) → sum

RULES:
  - return the sum of a and b

DONE_WHEN:
  - result equals a + b

EXAMPLES:
  (2, 3) → 5
  (0, 0) → 0

ERRORS:
  - non-numeric input → "Inputs must be numbers"
```

### Required Landmarks

Every function needs these five sections:
- **FUNCTION** - signature and return type
- **RULES** - what the function does
- **DONE_WHEN** - success criteria
- **EXAMPLES** - input/output pairs
- **ERRORS** - failure cases

### Validate with the Linter

The bundled linter performs deterministic structural, complexity, evolution-metadata, and determinism-declaration checks. It does not execute examples or perform semantic/LLM validation.

```bash
cd lint
make build
./bin/simplex-lint ../examples/minimal.simplex
```

The CLI uses `--input-mode auto` by default. It treats `.simplex` files as raw specifications, reads stdin as an already extracted specification, and lints only `simplex`-labeled fences in Markdown files that contain them. An unmarked Markdown file falls back to raw mode with a warning. Use `--input-mode raw`, `markdown`, or `extracted` to override that selection.

## Documentation

- [README.md](README.md) - Project overview
- [spec/simplex.md](spec/simplex.md) - Full specification (v0.5)
- [examples/](examples/) - Example specifications
- [docs/lint-design.md](docs/lint-design.md) - Linter architecture and unimplemented design notes

## Status

Research spike exploring structured specification capture for AI agent development.
