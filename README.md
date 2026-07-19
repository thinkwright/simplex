# Simplex

[![CI](https://github.com/thinkwright/simplex/actions/workflows/ci.yml/badge.svg)](https://github.com/thinkwright/simplex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Simplex is a semi-structured specification format for describing work assigned to autonomous agents. A Simplex document states required behavior, completion criteria, examples, and failure handling while leaving implementation choices to the agent.

The current specification version is **v0.6**. The normative source is [spec/simplex.md](spec/simplex.md).

## Status and scope

This repository contains:

- the normative Simplex specification;
- example specifications;
- a deterministic Go linter;
- design notes and proposal documents.

Agent interpretation does not require a formal grammar or compilation step. The linter uses a tolerant parser because tooling needs repeatable structure and diagnostics. The parser is an implementation aid, not a replacement for the normative specification.

The linter implements only the checks documented below. A passing lint result means those checks produced no errors. It does not prove that a specification is complete, semantically unambiguous, or sufficient for a particular agent.

## Repository layout

| Path | Purpose |
|---|---|
| [spec/simplex.md](spec/simplex.md) | Canonical v0.6 specification |
| [examples/](examples/) | Four example `.simplex` documents |
| [lint/](lint/) | Go linter module, CLI, tests, and fixtures |
| [QUICKSTART.md](QUICKSTART.md) | Short introduction and first example |
| [docs/lint-design.md](docs/lint-design.md) | Implemented linter architecture, diagnostics, result model, and explicit boundaries |
| [CHANGELOG.md](CHANGELOG.md) | Specification release history |
| [proposals/](proposals/) | Experimental or rejected proposals; not normative |

The public website is maintained in a separate repository. The `web/` directory and `fly.toml` still present in this checkout are legacy copies and are not the authoritative website source. This repository currently has no `gh-pages` branch or GitHub Pages deployment workflow.

## Writing a Simplex specification

A Simplex document has at least one `FUNCTION`. Every function requires `RULES`, `DONE_WHEN`, `EXAMPLES`, and `ERRORS`. The following minimal example passes the current deterministic linter checks:

```simplex
SIMPLEX: 0.6

FUNCTION: add(a, b) → sum

RULES:
  - [R1] return the sum of a and b

DONE_WHEN:
  - [D1] the returned value equals a + b

EXAMPLES:
  - [E1] value: (2, 3) → 5

ERRORS:
  - any unhandled condition → fail with descriptive message

COVERS:
  - E1 → R1, D1
```

`SIMPLEX`, stable identifiers, example kinds, and `COVERS` are optional. Removing them from this
example leaves a backward-compatible minimal document.

Simplex v0.6 defines eighteen landmarks:

- Structural: `SIMPLEX`, `DATA`, `CONSTRAINT`, `FUNCTION`, `BASELINE`, `EVAL`
- Function-level: `RULES`, `DONE_WHEN`, `EXAMPLES`, `COVERS`, `ERRORS`, `READS`, `WRITES`, `TRIGGERS`, `NOT_ALLOWED`, `HANDOFF`, `UNCERTAIN`, `DETERMINISM`

`FUNCTION`, `RULES`, `DONE_WHEN`, `EXAMPLES`, and `ERRORS` are always required. `EVAL` is required when a function contains `BASELINE`. All other landmarks are optional.

When authoring a specification:

1. Write the function signature and concrete examples first.
2. Describe observable behavior in `RULES`, not implementation steps.
3. Make each `DONE_WHEN` criterion externally checkable.
4. Include the expected response to known failures in `ERRORS`.
5. Add optional landmarks only when they clarify an actual requirement.
6. Split a document when a function or rule set becomes difficult to understand.

Examples are normative contracts in the specification. The current linter counts them for a complexity heuristic but does not execute them. `COVERS` records an author's example-to-contract mapping; the linter checks its references and reports gaps but does not prove the mapping semantically correct.

See [spec/simplex.md](spec/simplex.md) for landmark semantics, validation requirements, and the complete v0.6 definition.

## Using the linter

The linter requires Go 1.22 or newer.

From the repository root:

```bash
make test
make build
./build/simplex-lint examples/minimal.simplex
```

The CLI supports text and JSON output:

```bash
./build/simplex-lint --format text examples/minimal.simplex
./build/simplex-lint --format json examples/minimal.simplex
```

Complexity thresholds can be overridden with positive integers:

```bash
./build/simplex-lint --max-rules 20 --max-inputs 8 examples/complete.simplex
```

Exit status is:

- `0` when every input has no lint errors;
- `1` when at least one input has lint errors;
- `2` when the command cannot run, an input cannot be read, or an option is invalid.

Warnings do not change the exit status.

### Input modes

The CLI defaults to `--input-mode auto`.

| Mode | Behavior |
|---|---|
| `raw` | Parses the supplied document as Simplex while treating fenced blocks as literal content |
| `markdown` | Parses only fenced blocks whose first info word is `simplex` |
| `extracted` | Parses text already selected as a Simplex block by the caller |
| `auto` | Uses extracted mode for stdin, raw mode for `.simplex`, Markdown mode for a `.md` or `.markdown` file containing a live `simplex` fence, and raw compatibility mode with a warning for unmarked Markdown |

In auto mode, other filename extensions use raw mode.

Examples:

```bash
./build/simplex-lint --input-mode raw contract.simplex
./build/simplex-lint --input-mode markdown design-notes.md
cat contract.simplex | ./build/simplex-lint -
```

In Markdown mode, prose and unlabeled fences are not linted. Multiple `simplex` fences form one logical specification in source order.

### Implemented checks

The current Go linter performs these deterministic checks:

| Area | Diagnostics | Behavior |
|---|---|---|
| Structure | `E001`–`E009` | Requires functions and non-empty required landmarks; rejects duplicate landmarks, malformed signatures, and duplicate function names |
| Return-type reference | `W006` | When the document defines `DATA` blocks, warns if a return type may reference an undefined one |
| Complexity | `E010`, `E011`, `W010`, `W011` | Checks rule count, input count, individual rule length, and total function count |
| Example/branch count | `E012` | Compares the number of examples with a regex-based branch-count estimate |
| `BASELINE` | `E050`–`E054` | Checks required fields and non-empty preserve/evolve lists |
| `EVAL` | `E060`–`E065` | Checks its relationship to `BASELINE`, threshold syntax, and grading value |
| `DETERMINISM` | `E070` | Requires a valid `level`: `strict`, `structural`, or `semantic` |
| Language version | `E090`–`E093`, `W090` | Validates optional `SIMPLEX` declarations and relates `COVERS` to v0.6 semantics |
| Declared traceability | `E100`–`E105`, `W100`–`W102` | Checks identifier syntax and uniqueness, COVERS shape/scope/reference integrity, and declared coverage gaps |
| Parser/input warnings | `W001` | Reports unknown landmarks and input-selection issues |

`E012` is a count comparison. It does not determine which example covers which rule branch.

The linter also reports:

- function, branch, and example counts;
- `examples_per_branch`, which is a ratio rather than a coverage percentage.
- the declared and supported specification versions;
- identifier, link, example-kind, covered-item, and gap counts when traceability metadata is present.

### Checks not implemented

The current linter does not:

- execute examples;
- prove branch-to-example coverage or the semantic truth of `COVERS` links;
- detect conflicting interpretations;
- determine whether `DONE_WHEN` is observable;
- classify rules as behavioral or procedural;
- validate example outputs against `DATA` schemas;
- execute `EVAL` trials or grading;
- validate `DETERMINISM.seed`, `vary`, or `stable`;
- infer preservation/evolution example coverage when explicit COVERS links are absent;
- perform LLM-backed review;
- cache results or modify files automatically.

These may be normative requirements or design ideas, but they are not current linter capabilities.

## Go API

The `lint` module can be used without the CLI:

```go
package main

import (
	"fmt"
	"os"

	"github.com/thinkwright/simplex/lint"
)

func main() {
	content, err := os.ReadFile("contract.simplex")
	if err != nil {
		panic(err)
	}

	linter := lint.New(lint.Config{
		InputMode: lint.InputModeAuto,
	})

	result := linter.Lint("contract.simplex", string(content))
	fmt.Printf("passed=%t errors=%d warnings=%d\n",
		result.Valid, len(result.Errors), len(result.Warnings))
}
```

`lint.Config{}` and `lint.DefaultLinter()` use raw input mode for library compatibility. The CLI explicitly selects auto mode.

The result field `valid` means that implemented checks produced no errors. It is retained as an API field name and should not be interpreted as proof of full semantic validity.

## Development

Run the linter module checks from `lint/`:

```bash
go test ./...
go vet ./...
```

The test suite covers parser input modes, structural checks, complexity heuristics, evolution metadata, determinism levels, version declarations, declared traceability, output formatting, and CLI behavior.

The repository CI workflow:

- runs Go tests with coverage;
- builds and vets the linter;
- lints every file in `examples/`;
- lints the canonical specification and requires zero errors.

The linter is deterministic and does not require network access or API credentials.

## Versioning and proposals

Specification releases are recorded in [CHANGELOG.md](CHANGELOG.md). Tooling, parser, test, and documentation maintenance do not by themselves create a new Simplex specification version.

Files under [proposals/](proposals/) are exploratory and are not part of the current specification.

## License

Simplex is available under the [MIT License](LICENSE).
