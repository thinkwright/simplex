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

```bash
cd lint
make build
./bin/simplex-lint ../examples/minimal.simplex
```

## Documentation

- [README.md](README.md) - Full specification (v0.3)
- [1-pager.md](1-pager.md) - Executive summary
- [examples/](examples/) - Example specifications
- [docs/lint-design.md](docs/lint-design.md) - Linter architecture

## Status

Research spike exploring structured specification capture for AI agent development.
