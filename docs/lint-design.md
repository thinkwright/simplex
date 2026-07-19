# Simplex Lint — Design and Implementation

Document revision 0.3

This document describes the Go linter included in this repository for Simplex v0.6. It records
implemented behavior and explicit boundaries. The language definition remains
[`spec/simplex.md`](../spec/simplex.md).

## Purpose and boundaries

`simplex-lint` is an offline, deterministic static checker for Simplex documents. It uses a
tolerant landmark parser and reports errors, warnings, and summary statistics.

A result with `valid: true` means that no implemented check produced an error. It does not mean
that the specification is complete in every semantic sense or that an implementation conforms to
the specification.

The linter currently checks:

- input selection and landmark extraction;
- required structure and function signatures;
- configurable rule and input limits;
- a count-based branch/example heuristic;
- selected `BASELINE`, `EVAL`, and `DETERMINISM` fields;
- optional Simplex language-version declarations; and
- stable identifiers and author-declared `COVERS` traceability.

It does not execute examples, grade `EVAL` trials, validate outputs against `DATA` schemas, prove
branch coverage, prove `COVERS` assertions, assess observability or ambiguity, call an LLM, cache
model results, or modify source files.

## Architecture

```text
source files or stdin
        |
        v
input-mode selection
        |
        v
tolerant landmark parser
        |
        v
version -> structure -> complexity -> evolution -> determinism -> traceability
        |
        v
result aggregation and text or JSON formatting
```

The public pipeline is assembled in `lint.go`. The CLI in `cmd/simplex-lint/main.go` reads input,
constructs the linter configuration, and formats one or more results.

## Input interpretation

The parser supports four input modes:

| Mode | Behavior |
|---|---|
| `raw` | Parses the whole source while masking content inside fenced literal blocks |
| `markdown` | Parses only fenced blocks whose first info word is `simplex` |
| `extracted` | Parses the caller-provided text as an already extracted Simplex region |
| `auto` | Uses `extracted` for stdin, `raw` for `.simplex` and other non-Markdown files, and live `simplex` fences for Markdown when present |

In `auto` mode, a Markdown file without a live `simplex` fence falls back to raw parsing and emits
`W001`. An unterminated live fence is parsed through the end of input and also emits `W001`.

The CLI supplies `auto` by default. The Go library's zero-value `Config.InputMode`, including
`DefaultLinter`, is interpreted as `raw`; callers that want filename-sensitive selection must set
`InputModeAuto` explicitly.

Raw mode masks fenced content so examples that contain literal code with words such as `RULES:` do
not create landmarks. Markdown mode ignores prose and non-Simplex fences.

## Parser model

The parser recognizes a landmark with this line-oriented pattern:

```text
^[ \t]*([A-Z][A-Z_]+):[ \t]*(.*)$
```

`[ \t]*` is intentional. It accepts horizontal spacing without allowing an empty landmark to
consume the next line as same-line content.

The principal internal structures are:

```go
type Landmark struct {
    Name       string
    Content    string
    LineNumber int
}

type FunctionBlock struct {
    Signature          string
    SignatureParsed    bool
    Name               string
    Inputs             []string
    ReturnType         string
    Landmarks          map[string]Landmark
    DuplicateLandmarks []Landmark
    LineNumber         int
}

type ParsedSpec struct {
    SimplexDeclarations []Landmark
    Functions           []FunctionBlock
    DataBlocks          []Landmark
    Constraints         []Landmark
    RawText             string
    InputMode           InputMode
    ParseWarnings       []string
}
```

The parser associates function landmarks with the most recent `FUNCTION` until another function
or a top-level structural landmark ends that context. For a repeated function-level landmark it
retains the first block in `Landmarks` and records later blocks in `DuplicateLandmarks`; this lets
the structural checker report the duplicate without silently changing which content later checks
inspect.

Unknown landmarks and function landmarks outside a function become parse warnings. The parser is
not a formal grammar and does not attempt to interpret the full meaning of prose.

## Check pipeline

Checks run in a fixed order after parsing:

1. Convert parser and input warnings to `W001`.
2. Validate the optional language version.
3. Validate required structure, signatures, duplicate names, and duplicate landmarks.
4. Apply complexity thresholds and the branch/example count heuristic.
5. Validate selected `BASELINE` and `EVAL` fields.
6. Validate the `DETERMINISM.level` field.
7. Validate stable identifiers and `COVERS` mappings.
8. Populate function, example, branch, and ratio statistics.

Errors set `valid` to `false`. Warnings do not affect `valid`.

### Parser and structural diagnostics

| Code | Severity | Condition |
|---|---|---|
| `W001` | Warning | Parser or input-selection warning |
| `E001` | Error | No `FUNCTION` block |
| `E002` | Error | Function missing `RULES` |
| `E003` | Error | Function missing `DONE_WHEN` |
| `E004` | Error | Function missing `EXAMPLES` |
| `E005` | Error | Function missing `ERRORS` |
| `E006` | Error | A required function landmark is present but empty |
| `E007` | Error | Duplicate function-level landmark |
| `E008` | Error | Function signature does not match `name(inputs) -> return type` or the Unicode-arrow equivalent |
| `E009` | Error | Duplicate parsed function name in one document |
| `W006` | Warning | A return type may reference an undefined `DATA` type when the document uses `DATA` blocks |

The undefined-type check is deliberately conservative. It recognizes common primitive and generic
types and only warns when at least one `DATA` block exists.

### Complexity diagnostics

| Code | Severity | Default condition |
|---|---|---|
| `E010` | Error | More than 15 list items in a `RULES` block |
| `E011` | Error | More than 6 parsed function inputs |
| `E012` | Error | Counted examples are fewer than heuristically counted branches |
| `W010` | Warning | A rule item exceeds 200 characters |
| `W011` | Warning | A document has more than 10 functions |

`--max-rules` and `--max-inputs` configure the first two thresholds. The rule-length and function
count thresholds are fixed in the current public configuration.

Branch counting uses lexical indicators such as `if`, `when`, `optionally`, and `either ... or`.
It assigns at least one branch to a non-empty rule block. Example counting recognizes lines that
start with `(` or contain `->` or `→`. `E012` is a numerical consistency check; it does not match a
particular example to a particular branch.

### Evolution and determinism diagnostics

| Code | Severity | Condition |
|---|---|---|
| `E050` | Error | `BASELINE` missing `reference` |
| `E051` | Error | `BASELINE` missing `preserve` |
| `E052` | Error | `BASELINE` missing `evolve` |
| `E053` | Error | `BASELINE.preserve` has no list item |
| `E054` | Error | `BASELINE.evolve` has no list item |
| `E060` | Error | `BASELINE` present without `EVAL` |
| `E061` | Error | `EVAL` missing `preserve` while `BASELINE` is present |
| `E062` | Error | `EVAL` missing `evolve` while `BASELINE` is present |
| `E063` | Error | `EVAL.preserve` does not use `pass^k` syntax |
| `E064` | Error | `EVAL.evolve` does not use `pass@k` syntax |
| `E065` | Error | `EVAL.grading` is not `code`, `model`, or `outcome` |
| `E070` | Error | `DETERMINISM` lacks a valid `strict`, `structural`, or `semantic` level |

The current determinism checker does not validate `seed`, `vary`, or `stable`. The evolution
checker validates notation; it does not run trials or graders.

### Language-version diagnostics

`SIMPLEX` is optional. Unversioned documents and documents declaring `SIMPLEX: 0.5` remain
accepted by the v0.6 linter when they do not use an incompatible landmark. The language version is
separate from the CLI binary version.

| Code | Severity | Condition |
|---|---|---|
| `E090` | Error | The declaration is missing a single `major.minor` value or contains extra non-comment content |
| `E091` | Error | The declared version is neither `0.5` nor the supported `0.6` version |
| `E092` | Error | More than one `SIMPLEX` declaration |
| `E093` | Error | `COVERS` is used while the document declares `SIMPLEX: 0.5` |
| `W090` | Warning | `COVERS` is used without a language declaration |

An unsupported declaration produces an error rather than being silently treated as the newest
known semantics. Other deterministic checks still run so one invocation can report additional
local defects.

### Declared traceability diagnostics

Stable identifiers use `[ID]` prefixes. A valid identifier starts with an ASCII letter and then
uses ASCII letters, digits, `.`, `_`, or `-`. The linter inventories identifiers in:

- document-level `CONSTRAINT` list items;
- `RULES`, `DONE_WHEN`, `EXAMPLES`, `ERRORS`, `NOT_ALLOWED`, `READS`, `WRITES`, `TRIGGERS`,
  `HANDOFF`, and `UNCERTAIN` items;
- list items under `BASELINE.preserve` and `BASELINE.evolve`; and
- list items under `DETERMINISM.stable` and `DETERMINISM.vary`.

Identifiers must be document-wide unique even when `COVERS` is absent. When identifiers are
present without `COVERS`, the linter reports inventory and example-kind counts but does not issue
coverage-gap warnings.

A `COVERS` row has one source example ID and one or more comma-separated target IDs. Square
brackets around references are accepted but not required. The source must belong to the same
function's `EXAMPLES`. A target may belong to the same function's contract or to a document-level
`CONSTRAINT`; another function's local item is out of scope.

| Code | Severity | Condition |
|---|---|---|
| `E100` | Error | Duplicate stable identifier |
| `E101` | Error | Empty or malformed `COVERS` content or malformed reference syntax |
| `E102` | Error | Source does not resolve to an example in the same function |
| `E103` | Error | Target is unknown or belongs to another function |
| `E104` | Error | Target resolves to an example rather than a contract item |
| `E105` | Error | Invalid stable identifier syntax |
| `W100` | Warning | An identified expected contract item has no declared link |
| `W101` | Warning | An identified example has no declared link |
| `W102` | Warning | A traceable item lacks an identifier in a function that declares `COVERS` |

The catch-all `ERRORS` item containing `any unhandled` is not treated as an expected coverage
obligation. Identified document-level constraints may be linked, but they are not automatically
counted as obligations for every function.

Repeated identical links are counted once. `traceability.complete` means that the implemented
inventory has no malformed references, uncovered expected items, unlinked examples, or unlabelled
traceable items in functions that declare `COVERS`. It is a statement about the declared map, not
proof that the examples exercise the meaning of their targets.

## Result model

The single-file JSON result has this shape:

```json
{
  "file": "example.simplex",
  "specification_version": "0.6",
  "supported_specification_version": "0.6",
  "valid": true,
  "errors": [],
  "warnings": [],
  "stats": {
    "functions": 1,
    "branches": 1,
    "examples": 1,
    "examples_per_branch": 1,
    "traceability": {
      "declared": true,
      "identifiers": 3,
      "example_identifiers": 1,
      "links": 2,
      "coverable_items": 2,
      "covered_items": 2,
      "uncovered_items": 0,
      "unlabelled_items": 0,
      "unlinked_examples": 0,
      "complete": true,
      "example_kinds": {"value": 1}
    }
  }
}
```

`specification_version` is omitted from JSON for an unversioned document.
`supported_specification_version` reports the newest language version understood by the linter.
`stats.traceability` is omitted when the document contains neither recognized stable identifiers
nor `COVERS`.

`branches`, `examples`, and `examples_per_branch` are heuristic counts. They are not coverage
measurements. Traceability fields report author-declared links and mechanically detected gaps.

Multiple input files produce a `MultiResult` with the individual results, `total_valid`, and
`total_files`.

## CLI contract

```text
simplex-lint [OPTIONS] <files...>

Options:
  --format text|json
  --input-mode auto|raw|markdown|extracted
  --max-rules <positive integer>
  --max-inputs <positive integer>
  --version
  --help
```

With no file argument, or with `-`, the CLI reads stdin. It accepts multiple file paths. `NO_COLOR`
disables colored text output.

Exit codes are:

| Code | Meaning |
|---|---|
| `0` | Every input has no lint errors |
| `1` | At least one input has a lint error |
| `2` | The CLI could not read input, parse an option, or otherwise complete the invocation |

The CLI has no provider, model, API-key, cache, semantic-review, or auto-fix flags.

## Public Go API

The `lint` package exposes `New`, `DefaultLinter`, and `LintString`, plus aliases for results,
issues, general statistics, and traceability statistics. `SupportedSpecVersion` exposes the newest
language version known to the package.

`Config` currently accepts `MaxRules`, `MaxInputs`, and `InputMode`. A non-positive rule or input
value supplied through the Go API leaves the corresponding default in place; the CLI rejects
non-positive flag values.

## Testing and verification

Tests are organized by behavior:

```text
internal/parser/                 input selection and tolerant parsing
internal/checks/structural_test.go
internal/checks/complexity_test.go
internal/checks/evolution_test.go
internal/checks/determinism_test.go
internal/checks/version_test.go
internal/checks/traceability_test.go
internal/result/result_test.go
lint_test.go                     public pipeline integration
cmd/simplex-lint/main_test.go    CLI helpers, output, and fixtures
testdata/                        valid and invalid documents
```

From `lint/`:

```bash
go test ./...
go test -race ./...
go vet ./...
go build ./cmd/simplex-lint
```

The module Makefile also defines strict local coverage targets: 98 percent for internal packages
and 90 percent overall. The GitHub Actions workflow currently enforces 85 percent internal and 75
percent overall. These thresholds are tooling quality controls, not properties of the Simplex
language.

## Distribution

The linter can be built from `lint/` or installed with:

```bash
go install github.com/thinkwright/simplex/lint/cmd/simplex-lint@latest
```

This repository does not currently document prebuilt release binaries, a package-manager formula,
an LSP, or release automation as available features.
