# Simplex Lint — Design Document

Version 0.2

**Status:** Partially implemented design document. The current Go linter is deterministic and implements the parser, result model, structural checks, complexity heuristics, BASELINE/EVAL checks, and DETERMINISM-level checks. Sections explicitly marked **planned** describe unimplemented ideas, not available capabilities.

---

## Overview

Simplex Lint is a deterministic linter for Simplex specification files. It performs structural checks, configurable complexity checks, count-based example/branch heuristics, and validation of selected evolution and determinism fields.

The linter enforces a documented subset of the "enforced simplicity" pillar through concrete, configurable limits. It does not execute examples or perform semantic/LLM validation.

**Implementation Language:** Go

---

## Goals

1. **Check Simplex structure** before specifications are used by autonomous agents
2. **Catch deterministic errors early** — missing landmarks, complexity violations, and malformed evolution metadata
3. **Remain offline and reproducible** — current checks require no model or network access
4. **Integrate with workflows** — human-readable output for interactive use, JSON for CI/CD
5. **Distribute as one binary** — no runtime dependencies

LLM-backed semantic review was considered for a later phase but is not implemented or exposed by the CLI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                         (cmd/simplex-lint/main.go)               │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Soft Parser                                │
│                       (internal/parser/)                         │
│                                                                  │
│  Input: source text, source name, and input mode                 │
│  Output: ParsedSpec (landmarks, content, structure)              │
│                                                                  │
│  - Identifies landmarks via pattern matching                     │
│  - Extracts content blocks                                       │
│  - Associates nested landmarks with parent FUNCTION              │
│  - Tolerates formatting variation                                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Check Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Structural    │  │   Complexity    │  │ Evolution/Det.  │  │
│  │ (internal/      │  │ (internal/      │  │ (internal/      │  │
│  │  checks/struct) │  │  checks/complx) │  │  checks/evol,det│  │
│  │                 │  │                 │  │                 │  │
│  │  E001: missing  │  │  E010: rules    │  │ E050+: metadata │  │
│  │  landmarks      │  │  too complex    │  │ E070: det. level│  │
│  │                 │  │  E011: too many │  │                 │  │
│  │                 │  │  inputs         │  │                 │  │
│  │  [Deterministic]│  │  [Deterministic]│  │  [Deterministic]│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Result Aggregation                         │
│                       (internal/result/)                         │
│                                                                  │
│  - Collects errors and warnings from all checks                  │
│  - Determines whether implemented checks passed                  │
│  - Formats output (human-readable or JSON)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Multi-file | Yes, `simplex-lint *.md` works | Practical for batch validation |
| Auto-fix | Not implemented or exposed | Suggestions are reported but files are never modified |
| Config file | No; use threshold flags | Keep the implemented surface small |
| IDE/LSP | Post-MVP | Nice to have, not essential |
| Caching | Not implemented | Deterministic local checks are inexpensive |

---

## Components

### 1. CLI Interface (`cmd/simplex-lint/main.go`)

Entry point for the linter. Built with [Cobra](https://github.com/spf13/cobra).

```
simplex-lint [OPTIONS] <files...>

Arguments:
  <files...>          One or more Simplex spec files (or - for stdin)

Options:
  --format <fmt>      Output format: text (default), json
  --input-mode <mode> Input interpretation: auto (default), raw, markdown, extracted
  --max-rules <n>     Override max RULES items (default: 15)
  --max-inputs <n>    Override max inputs (default: 6)
  --version           Show version and exit
  --help              Show this help and exit

Environment Variables:
  NO_COLOR            Disable colored text output

Exit Codes:
  0   All files pass implemented checks (no errors)
  1   One or more specs invalid (has errors)
  2   Linter error (could not complete checks)
```

#### Example Usage

```bash
# Basic usage
simplex-lint my-spec.md

# Multiple files
simplex-lint specs/*.md

# JSON output for CI
simplex-lint --format json my-spec.md

# Parse only fenced blocks labeled simplex
simplex-lint --input-mode markdown guide.md

# Override complexity limits
simplex-lint --max-rules 20 --max-inputs 8 my-spec.md

# Pipe from stdin
cat my-spec.md | simplex-lint -
```

### 2. Soft Parser (`internal/parser/`)

Extracts structure from spec text without enforcing strict grammar.

#### Data Structures

```go
// Landmark represents a parsed landmark block
type Landmark struct {
    Name       string // e.g., "FUNCTION", "RULES"
    Content    string // raw content after landmark
    LineNumber int    // for error reporting
}

// FunctionBlock represents a parsed FUNCTION with its nested landmarks
type FunctionBlock struct {
    Signature  string              // e.g., "filter_policies(policies, ids, tags) → filtered list"
    Name       string              // e.g., "filter_policies"
    Inputs     []string            // e.g., ["policies", "ids", "tags"]
    ReturnType string              // e.g., "filtered list"
    Landmarks  map[string]Landmark // nested landmarks (RULES, DONE_WHEN, etc.)
    LineNumber int
}

// ParsedSpec represents the fully parsed specification
type ParsedSpec struct {
    Functions     []FunctionBlock
    DataBlocks    []Landmark
    Constraints   []Landmark
    RawText       string
    InputMode     InputMode
    ParseWarnings []string // non-fatal parse issues
}
```

#### Parsing Strategy

1. **Input selection**:
   - `raw`: parse the whole source while shielding fenced literal blocks
   - `markdown`: parse only fences whose first info word is `simplex`
   - `extracted`: parse a caller-provided Simplex block
   - `auto`: use extracted mode for stdin, raw mode for `.simplex`, and labeled-fence Markdown mode when a `.md` file contains a live `simplex` fence; unmarked Markdown falls back to raw mode with a warning
2. **Landmark detection**: Regex pattern `^[ \t]*([A-Z][A-Z_]+):\s*(.*)$` with multiline flag
3. **Content extraction**: Everything from a landmark to the next landmark in the same live input region
4. **Nesting**: Landmarks after FUNCTION are associated with that function until the next FUNCTION or structural landmark; function context can continue across consecutive live Markdown regions
5. **Tolerance**:
   - Accept minor spacing variations
   - Accept indented landmarks
   - Accept landmarks with trailing whitespace
   - Accept content with inconsistent indentation
   - Warn but don't fail on unrecognized landmarks

### 3. Structural Checks (`internal/checks/structural.go`)

Deterministic checks for required landmarks.

| Code | Check | Severity |
|------|-------|----------|
| E001 | No FUNCTION block found | Error |
| E002 | FUNCTION missing RULES | Error |
| E003 | FUNCTION missing DONE_WHEN | Error |
| E004 | FUNCTION missing EXAMPLES | Error |
| E005 | FUNCTION missing ERRORS | Error |
| W006 | Return type may reference an undefined DATA type | Warning |
| W001 | Parser/input warning, including unrecognized landmarks | Warning |

### 4. Complexity Checks (`internal/checks/complexity.go`)

Deterministic checks for enforced simplicity.

| Code | Check | Default Threshold | Severity |
|------|-------|-------------------|----------|
| E010 | RULES block has too many items | 15 | Error |
| E011 | FUNCTION has too many inputs | 6 | Error |
| E012 | EXAMPLES fewer than branch count | varies | Error |
| W010 | Single RULES item too long | 200 chars | Warning |
| W011 | Spec has many FUNCTION blocks | 10 | Warning |

#### Branch Counting Heuristics

To check E012, we need to count conditional branches in RULES:

```go
// CountBranches performs heuristic branch counting on RULES content.
//
// Patterns that introduce branches:
//   - "if X" → 1 branch (implicit else is no-op)
//   - "if X or Y" → 2 branches
//   - "if X, otherwise Y" / "if X, else Y" → 2 branches
//   - "when X" → 1 branch
//   - "optionally" → 2 branches (with/without)
//   - "either X or Y" → 2 branches
//
// This is a count-based heuristic, not a semantic coverage proof.
func CountBranches(rulesContent string) int {
    // Implementation uses regex patterns to identify branch indicators
}
```

### 5. Planned Semantic Checks (Not Implemented)

The following LLM-based checks were considered in the original design. There is no `internal/checks/semantic/` package, provider integration, or CLI support for these checks. No diagnostic codes are reserved for these ideas.

| Code | Check | Description |
|------|-------|-------------|
| — | Branch coverage | Every conditional path in RULES has an example |
| — | Cannot identify branches | RULES structure too ambiguous to analyze |
| — | Non-observable DONE_WHEN | Completion criteria reference internal state |
| — | Ambiguous observability | Unclear if criterion is externally checkable |
| — | Procedural RULES | Rules describe steps instead of outcomes |
| — | Mixed behavioral/procedural | Some rules behavioral, some procedural |
| — | Ambiguous interpretation | Examples satisfiable by conflicting implementations |

#### LLM Prompt Design

Each semantic check uses a structured prompt:

```go
const CoverageCheckPrompt = `You are validating a Simplex specification for branch coverage.

RULES:
%s

EXAMPLES:
%s

Task:
1. Identify all conditional branches in the RULES
2. For each branch, determine if at least one EXAMPLE exercises it
3. Report any uncovered branches

Respond in JSON:
{
  "branches": [
    {"description": "...", "covered": true/false, "covering_example": "..." or null}
  ],
  "uncovered_count": <int>,
  "analysis": "brief explanation"
}`
```

#### Provider Abstraction

```go
// Provider defines the interface for LLM backends
type Provider interface {
    Complete(ctx context.Context, prompt string) (string, error)
    Name() string
}

// AnthropicProvider implements Provider for Claude models
type AnthropicProvider struct {
    apiKey string
    model  string // default: "claude-sonnet-4-20250514"
    client *http.Client
}

// OpenAICompatibleProvider implements Provider for OpenAI-compatible APIs
// Works with OpenAI, GLM, MiniMax, Ollama, and other compatible endpoints
type OpenAICompatibleProvider struct {
    apiBase string
    apiKey  string
    model   string
    client  *http.Client
}
```

### 6. Result Models (`internal/result/`)

```go
// LintError represents a single linting issue
type LintError struct {
    Code       string  `json:"code"`       // e.g., "E001"
    Message    string  `json:"message"`    // human-readable
    Location   string  `json:"location"`   // e.g., "FUNCTION filter_policies" or "line 42"
    Severity   string  `json:"severity"`   // "error" or "warning"
    Suggestion *string `json:"suggestion,omitempty"` // optional fix suggestion
    Fixable    bool    `json:"fixable"`    // suggestion metadata; CLI does not apply fixes
}

// LintStats provides summary statistics
type LintStats struct {
    Functions         int     `json:"functions"`
    Branches          int     `json:"branches"`
    Examples          int     `json:"examples"`
    ExamplesPerBranch float64 `json:"examples_per_branch,omitempty"`
}

// LintResult represents the complete linting output for a single file
type LintResult struct {
    File     string      `json:"file"`
    Valid    bool        `json:"valid"` // true when implemented checks have no errors
    Errors   []LintError `json:"errors"`
    Warnings []LintError `json:"warnings"`
    Stats    LintStats   `json:"stats"`
}

// MultiResult aggregates results from multiple files
type MultiResult struct {
    Results    []LintResult `json:"results"`
    TotalValid int          `json:"total_valid"`
    TotalFiles int          `json:"total_files"`
}

func (r *LintResult) ToJSON() ([]byte, error)
func (r *LintResult) ToText() string
func (r *MultiResult) ToJSON() ([]byte, error)
func (r *MultiResult) ToText() string
```

#### Output Formats

**Text (human-readable):**

```
simplex-lint: my-spec.md

ERRORS:
  E005 [FUNCTION validate_input] Missing required ERRORS landmark
  E010 [FUNCTION filter_policies] RULES block has 18 items (max 15)
  E060 [FUNCTION modernize_auth] EVAL required when BASELINE present

WARNINGS:
  W010 [FUNCTION validate_input, RULES item 2] Rule exceeds 200 characters

SUMMARY:
  3 errors, 1 warning
  Checks FAILED
```

**JSON (CI/CD):**

```json
{
  "valid": false,
  "errors": [
    {
      "code": "E005",
      "message": "Missing required ERRORS landmark",
      "location": "FUNCTION validate_input",
      "severity": "error",
      "suggestion": "Add ERRORS: block with at least default error handling"
    }
  ],
  "warnings": [...],
  "stats": {
    "functions": 2,
    "branches": 8,
    "examples": 5,
    "examples_per_branch": 0.625
  }
}
```

---

## Planned Caching (Not Implemented)

The original design proposed caching for semantic checks. No cache is implemented because the current checks are deterministic and local. The following structure is retained only as historical design context.

```
~/.cache/simplex-lint/
├── v1/                   # cache version (invalidates on breaking changes)
│   ├── a1b2c3d4e5f6.json # SHA-256 of spec content + model name
│   └── ...
└── metadata.json         # cache stats
```

**Cache key**: SHA-256 of `(normalized_spec_content + provider + model)`

**Cache invalidation**:
- Different linter version (cache version bump)
- Different LLM model
- Manual invalidation control (proposed)
- Cache entry older than 30 days

```go
// Cache provides semantic check result caching
type Cache struct {
    dir     string
    version string
}

func (c *Cache) Get(spec string, provider string, model string) (*SemanticResult, bool)
func (c *Cache) Set(spec string, provider string, model string, result *SemanticResult) error
func (c *Cache) Clear() error
```

---

## Testing Strategy

### Unit Tests

```
internal/parser/parser_test.go      — landmark extraction, nesting, tolerance
internal/checks/structural_test.go  — each E00x error code
internal/checks/complexity_test.go  — each E01x/W01x error code, threshold overrides
internal/checks/evolution_test.go   — BASELINE and EVAL validation
internal/result/result_test.go      — output formatting
```

Semantic-check tests do not exist because semantic checks are not implemented.

### Integration Tests

```
cmd/simplex-lint/main_test.go — public linter pipeline with real fixtures
```

Fixture specs in `testdata/`:
- `valid_minimal.md` — passes all checks
- `valid_complex.md` — passes implemented checks
- `invalid_missing_errors.md` — E005
- `invalid_too_complex.md` — deterministic complexity errors
- etc.

### Planned LLM Tests (Not Implemented)

The original design called for mock providers, optional live tests, and golden model outputs. None currently exists.

---

## Project Structure

```
simplex-lint/
├── lint.go                    # public linter API and canonical check pipeline
├── cmd/
│   └── simplex-lint/
│       ├── main.go           # thin CLI entry point
│       └── main_test.go
├── internal/
│   ├── parser/
│   │   ├── input.go          # raw, Markdown, extracted, and auto selection
│   │   ├── input_test.go
│   │   ├── parser.go         # landmark extraction and organization
│   │   └── parser_test.go
│   ├── checks/
│   │   ├── structural.go     # required landmarks and type-reference warning
│   │   ├── structural_test.go
│   │   ├── complexity.go     # limits and branch/example count heuristic
│   │   ├── complexity_test.go
│   │   ├── evolution.go      # BASELINE and EVAL checks
│   │   ├── evolution_test.go
│   │   └── determinism.go    # DETERMINISM level check
│   ├── result/
│   │   ├── result.go         # LintResult, LintError
│   │   └── result_test.go
├── testdata/
│   ├── valid_*.md
│   └── invalid_*.md
├── go.mod
├── go.sum
├── Makefile
├── README.md
└── LICENSE
```

---

## Dependencies

```go
// go.mod
module github.com/thinkwright/simplex/lint

go 1.22

require (
    github.com/spf13/cobra v1.8.0      // CLI framework
    github.com/fatih/color v1.16.0     // colored output
    github.com/stretchr/testify v1.9.0 // testing assertions
)
```

No external dependencies for HTTP or JSON—using standard library.

### Build & Install

```makefile
# Makefile
VERSION := $(shell git describe --tags --always --dirty)
LDFLAGS := -ldflags "-X main.version=$(VERSION)"

.PHONY: build install test lint clean

build:
	go build $(LDFLAGS) -o bin/simplex-lint ./cmd/simplex-lint

install:
	go install $(LDFLAGS) ./cmd/simplex-lint

test:
	go test ./...

lint:
	golangci-lint run

clean:
	rm -rf bin/
```

### Distribution

- **Current:** Build from source or run `go install github.com/thinkwright/simplex/lint/cmd/simplex-lint@latest`.
- **Not implemented:** Pre-built release binaries and a Homebrew tap.

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [x] Project setup (go.mod, structure, Makefile)
- [x] CLI with Cobra
- [x] Soft parser implementation
- [x] Result models and output formatting (text + JSON)
- [x] Unit tests for parser

### Phase 2: Deterministic Checks
- [x] Structural checks (E001-E005, W006)
- [x] Complexity checks (E010-E012, W010-W011)
- [x] Branch counting heuristics
- [x] BASELINE/EVAL checks (E050-E065)
- [x] DETERMINISM level check (E070)
- [x] Unit tests for implemented deterministic checks
- [x] Test fixtures (valid and invalid specs)

### Phase 3: LLM Integration (Not Implemented)
- [ ] Provider interface
- [ ] Anthropic provider
- [ ] OpenAI-compatible provider (for GLM, MiniMax, Ollama)
- [ ] Mock provider for testing
- [ ] Caching layer

### Phase 4: Semantic Checks (Not Implemented)
- [ ] Coverage check
- [ ] Observability check
- [ ] Behavioral check
- [ ] Ambiguity check
- [ ] Integration tests with mock provider
- [ ] Optional live tests with real providers

### Phase 5: Auto-fix (Not Implemented)
- [ ] Fixer infrastructure
- [ ] Fix E005 (add minimal ERRORS block)
- [ ] Fix W010 (suggest rule splitting)
- [ ] Dry-run mode (show what would be fixed)

### Phase 6: Polish
- [x] Error messages and suggestions
- [x] README and usage documentation
- [x] CI/CD setup (GitHub Actions)
- [ ] Release automation (goreleaser)
- [ ] Homebrew formula (optional)

---

## Future Considerations

These are explicitly out of scope for MVP but worth noting:

1. **IDE/LSP integration** — Real-time linting in VSCode, GoLand, etc. Would require implementing Language Server Protocol.

2. **Configuration file** — If threshold flags become unwieldy in practice, consider `.simplex-lint.yaml`.

3. **Watch mode** — `simplex-lint --watch specs/` for continuous validation during authoring.

4. **Spec generation** — Scaffolding tool to generate spec templates.

---

## Appendix: Error Code Reference

| Code | Category | Description |
|------|----------|-------------|
| E001 | Structural | No FUNCTION block found |
| E002 | Structural | FUNCTION missing RULES |
| E003 | Structural | FUNCTION missing DONE_WHEN |
| E004 | Structural | FUNCTION missing EXAMPLES |
| E005 | Structural | FUNCTION missing ERRORS |
| E010 | Complexity | RULES block exceeds max items |
| E011 | Complexity | FUNCTION has too many inputs |
| E012 | Complexity | EXAMPLES fewer than branch count |
| E050 | Evolution | BASELINE missing reference |
| E051 | Evolution | BASELINE missing preserve field |
| E052 | Evolution | BASELINE missing evolve field |
| E053 | Evolution | BASELINE preserve list is empty |
| E054 | Evolution | BASELINE evolve list is empty |
| E060 | Evolution | EVAL required when BASELINE is present |
| E061 | Evolution | EVAL missing preserve threshold |
| E062 | Evolution | EVAL missing evolve threshold |
| E063 | Evolution | Invalid preserve threshold notation |
| E064 | Evolution | Invalid evolve threshold notation |
| E065 | Evolution | Invalid grading value |
| E070 | Determinism | Missing or invalid DETERMINISM level |
| W001 | Parser | Parse warning or unrecognized landmark |
| W006 | Structural | Return type may reference undefined DATA |
| W010 | Complexity | Single RULES item too long |
| W011 | Complexity | Many FUNCTION blocks in spec |
