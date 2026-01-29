# Simplex Lint — Design Document

Version 0.2

---

## Overview

Simplex Lint is a hybrid linter for Simplex specification files. It combines deterministic pattern matching for structural and complexity checks with LLM-based reasoning for semantic validation.

The linter enforces the "enforced simplicity" pillar of the Simplex language through concrete, configurable limits and checks.

**Implementation Language:** Go

---

## Goals

1. **Validate Simplex specifications** before they are used by autonomous agents
2. **Catch errors early** — missing landmarks, complexity violations, ambiguous specs
3. **Support multiple LLM backends** — Anthropic (Opus, Sonnet), internal models (GLM 4.7, MiniMax M2)
4. **Work offline** — structural/complexity checks run without LLM; semantic checks skippable
5. **Integrate with workflows** — human-readable output for interactive use, JSON for CI/CD
6. **Single binary distribution** — no runtime dependencies, easy installation

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
│  Input: raw spec text                                            │
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
│  │   Structural    │  │   Complexity    │  │    Semantic     │  │
│  │ (internal/      │  │ (internal/      │  │ (internal/      │  │
│  │  checks/struct) │  │  checks/complx) │  │  checks/semant) │  │
│  │                 │  │                 │  │                 │  │
│  │  E001: missing  │  │  E010: rules    │  │  E020: coverage │  │
│  │  landmarks      │  │  too complex    │  │  E030: observe  │  │
│  │                 │  │  E011: too many │  │  E040: behavior │  │
│  │                 │  │  inputs         │  │                 │  │
│  │  [Deterministic]│  │  [Deterministic]│  │  [LLM-based]    │  │
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
│  - Determines overall validity                                   │
│  - Formats output (human-readable or JSON)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Multi-file | Yes, `simplex-lint *.md` works | Practical for batch validation |
| Auto-fix | Available via `--fix`, disabled by default | Explicit is better than implicit |
| Config file | No, use CLI flags and env vars | Avoid over-engineering; aliases and env vars suffice |
| IDE/LSP | Post-MVP | Nice to have, not essential |
| Cache granularity | Per-spec (whole file hash) | Specs are small (<200 lines typically); simpler implementation |

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
  --fix               Auto-fix simple issues (disabled by default)
  --no-llm            Skip semantic checks (offline mode)
  --provider <name>   LLM provider: anthropic, openai, glm, minimax, ollama
  --model <name>      Model identifier (provider-specific)
  --api-key <key>     API key (or use environment variable)
  --api-base <url>    Base URL for self-hosted models
  --max-rules <n>     Override max RULES items (default: 15)
  --max-inputs <n>    Override max inputs (default: 6)
  --cache             Enable result caching (default: on)
  --no-cache          Disable result caching
  --verbose           Show detailed check progress
  --version           Show version and exit
  --help              Show this help and exit

Environment Variables:
  ANTHROPIC_API_KEY       API key for Anthropic
  OPENAI_API_KEY          API key for OpenAI
  SIMPLEX_LINT_PROVIDER   Default provider
  SIMPLEX_LINT_MODEL      Default model
  SIMPLEX_LINT_CACHE_DIR  Cache directory (default: ~/.cache/simplex-lint)

Exit Codes:
  0   All specs valid (no errors)
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

# Offline mode (structural/complexity only)
simplex-lint --no-llm my-spec.md

# Using internal GLM model
simplex-lint --provider glm --api-base http://internal-llm:8080 my-spec.md

# Override complexity limits
simplex-lint --max-rules 20 --max-inputs 8 my-spec.md

# Auto-fix simple issues
simplex-lint --fix my-spec.md

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
    ParseWarnings []string // non-fatal parse issues
}
```

#### Parsing Strategy

1. **Landmark detection**: Regex pattern `^([A-Z_]+):\s*(.*)$` with multiline flag
2. **Content extraction**: Everything from landmark to next landmark or EOF
3. **Nesting**: Landmarks after FUNCTION are associated with that function until next FUNCTION or structural landmark
4. **Tolerance**:
   - Accept minor spacing variations
   - Accept landmarks with trailing whitespace
   - Accept content with inconsistent indentation
   - Warn but don't fail on unrecognized landmarks

### 3. Structural Checks (`structural.py`)

Deterministic checks for required landmarks.

| Code | Check | Severity |
|------|-------|----------|
| E001 | No FUNCTION block found | Error |
| E002 | FUNCTION missing RULES | Error |
| E003 | FUNCTION missing DONE_WHEN | Error |
| E004 | FUNCTION missing EXAMPLES | Error |
| E005 | FUNCTION missing ERRORS | Error |
| E006 | DATA type referenced but not defined | Error |
| W001 | Unrecognized landmark (ignored) | Warning |

### 4. Complexity Checks (`complexity.py`)

Deterministic checks for enforced simplicity.

| Code | Check | Default Threshold | Severity |
|------|-------|-------------------|----------|
| E010 | RULES block has too many items | 15 | Error |
| E011 | FUNCTION has too many inputs | 6 | Error |
| E012 | EXAMPLES fewer than branch count | varies | Error |
| W010 | Single RULES item too long | 200 chars | Warning |
| W011 | Spec has many FUNCTION blocks | 10 | Warning |
| W012 | FUNCTION has no inputs | 0 | Warning |

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
// This is heuristic, not perfect. LLM semantic check provides deeper analysis.
func CountBranches(rulesContent string) int {
    // Implementation uses regex patterns to identify branch indicators
}
```

### 5. Semantic Checks (`internal/checks/semantic/`)

LLM-based checks for meaning and coverage.

| Code | Check | Description |
|------|-------|-------------|
| E020 | Branch coverage | Every conditional path in RULES has an example |
| E021 | Cannot identify branches | RULES structure too ambiguous to analyze |
| E030 | Non-observable DONE_WHEN | Completion criteria reference internal state |
| E031 | Ambiguous observability | Unclear if criterion is externally checkable |
| E040 | Procedural RULES | Rules describe steps instead of outcomes |
| E041 | Mixed behavioral/procedural | Some rules behavioral, some procedural |
| E050 | Ambiguous interpretation | Examples satisfiable by conflicting implementations |

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
    Suggestion *string `json:"suggestion"` // optional fix suggestion
    Fixable    bool    `json:"fixable"`    // can --fix resolve this?
}

// LintStats provides summary statistics
type LintStats struct {
    Functions       int     `json:"functions"`
    Branches        int     `json:"branches"`
    Examples        int     `json:"examples"`
    CoveragePercent float64 `json:"coverage_percent"`
}

// LintResult represents the complete linting output for a single file
type LintResult struct {
    File     string      `json:"file"`
    Valid    bool        `json:"valid"`
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
  E020 [FUNCTION filter_policies] Branch "only tags provided" not covered by examples
  E040 [FUNCTION process_items, RULES item 3] Procedural language: "loop through each item"

WARNINGS:
  W010 [FUNCTION validate_input, RULES item 2] Rule exceeds 200 characters

SUMMARY:
  3 errors, 1 warning
  Spec is INVALID
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
    "coverage_percent": 62.5
  }
}
```

---

## Caching

Semantic checks are expensive. We cache results by content hash at the spec level.

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
- Manual `--no-cache` flag
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
internal/checks/semantic_test.go    — mock LLM responses, prompt construction
internal/result/result_test.go      — output formatting
```

### Integration Tests

```
integration_test.go — full pipeline with real specs
```

Fixture specs in `testdata/`:
- `valid_minimal.md` — passes all checks
- `valid_complex.md` — passes with warnings
- `invalid_missing_errors.md` — E005
- `invalid_uncovered_branch.md` — E020
- `invalid_procedural.md` — E040
- etc.

### LLM Tests

- Mock provider for deterministic unit tests
- Optional live tests against real providers (skipped in CI by default, enabled with `-tags=live`)
- Golden files for expected LLM outputs in `testdata/golden/`

---

## Project Structure

```
simplex-lint/
├── cmd/
│   └── simplex-lint/
│       └── main.go           # CLI entry point
├── internal/
│   ├── parser/
│   │   ├── parser.go         # soft parser implementation
│   │   └── parser_test.go
│   ├── checks/
│   │   ├── structural.go     # E001-E006
│   │   ├── structural_test.go
│   │   ├── complexity.go     # E010-E012, W010-W012
│   │   ├── complexity_test.go
│   │   ├── semantic.go       # E020-E050 (LLM-based)
│   │   └── semantic_test.go
│   ├── provider/
│   │   ├── provider.go       # Provider interface
│   │   ├── anthropic.go      # Anthropic implementation
│   │   ├── openai.go         # OpenAI-compatible implementation
│   │   └── mock.go           # Mock for testing
│   ├── result/
│   │   ├── result.go         # LintResult, LintError
│   │   └── result_test.go
│   ├── cache/
│   │   ├── cache.go
│   │   └── cache_test.go
│   └── fixer/
│       ├── fixer.go          # Auto-fix logic
│       └── fixer_test.go
├── testdata/
│   ├── valid_minimal.md
│   ├── valid_complex.md
│   ├── invalid_missing_errors.md
│   ├── invalid_uncovered_branch.md
│   ├── invalid_procedural.md
│   └── golden/               # expected LLM outputs
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
module github.com/yourorg/simplex-lint

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

test-live:
	go test -tags=live ./...

lint:
	golangci-lint run

clean:
	rm -rf bin/
```

### Distribution

- **go install**: `go install github.com/yourorg/simplex-lint/cmd/simplex-lint@latest`
- **GitHub Releases**: Pre-built binaries for linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64
- **Homebrew**: Optional tap for macOS users

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Project setup (go.mod, structure, Makefile)
- [ ] CLI skeleton with Cobra
- [ ] Soft parser implementation
- [ ] Result models and output formatting (text + JSON)
- [ ] Unit tests for parser

### Phase 2: Deterministic Checks
- [ ] Structural checks (E001-E006)
- [ ] Complexity checks (E010-E012, W010-W012)
- [ ] Branch counting heuristics
- [ ] Unit tests for all deterministic checks
- [ ] Test fixtures (valid and invalid specs)

### Phase 3: LLM Integration
- [ ] Provider interface
- [ ] Anthropic provider
- [ ] OpenAI-compatible provider (for GLM, MiniMax, Ollama)
- [ ] Mock provider for testing
- [ ] Caching layer

### Phase 4: Semantic Checks
- [ ] Coverage check (E020-E021)
- [ ] Observability check (E030-E031)
- [ ] Behavioral check (E040-E041)
- [ ] Ambiguity check (E050)
- [ ] Integration tests with mock provider
- [ ] Optional live tests with real providers

### Phase 5: Auto-fix
- [ ] Fixer infrastructure
- [ ] Fix E005 (add minimal ERRORS block)
- [ ] Fix W010 (suggest rule splitting)
- [ ] Dry-run mode (show what would be fixed)

### Phase 6: Polish
- [ ] Error messages and suggestions
- [ ] README and usage documentation
- [ ] CI/CD setup (GitHub Actions)
- [ ] Release automation (goreleaser)
- [ ] Homebrew formula (optional)

---

## Future Considerations

These are explicitly out of scope for MVP but worth noting:

1. **IDE/LSP integration** — Real-time linting in VSCode, GoLand, etc. Would require implementing Language Server Protocol.

2. **Configuration file** — If CLI flags become unwieldy in practice, consider `.simplex-lint.yaml`. Currently, env vars and shell aliases suffice.

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
| E006 | Structural | DATA type referenced but not defined |
| E010 | Complexity | RULES block exceeds max items |
| E011 | Complexity | FUNCTION has too many inputs |
| E012 | Complexity | EXAMPLES fewer than branch count |
| E020 | Semantic | Branch not covered by examples |
| E021 | Semantic | Cannot identify branches in RULES |
| E030 | Semantic | DONE_WHEN criterion not observable |
| E031 | Semantic | Ambiguous observability |
| E040 | Semantic | RULES contains procedural language |
| E041 | Semantic | Mixed behavioral/procedural RULES |
| E050 | Semantic | Ambiguous specification |
| W001 | Structural | Unrecognized landmark |
| W010 | Complexity | Single RULES item too long |
| W011 | Complexity | Many FUNCTION blocks in spec |
| W012 | Complexity | FUNCTION has no inputs |
