package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/thinkwright/simplex/lint"
	"github.com/thinkwright/simplex/lint/internal/result"
)

func lintIssueCodes(issues []result.LintError) []string {
	codes := make([]string, 0, len(issues))
	for _, issue := range issues {
		codes = append(codes, issue.Code)
	}
	return codes
}

func TestPublicLinterWithConfig(t *testing.T) {
	config := lint.Config{
		MaxRules:  20,
		MaxInputs: 8,
	}

	linter := lint.New(config)

	assert.NotNil(t, linter)
}

func TestPublicLinterDefaultConfig(t *testing.T) {
	linter := lint.DefaultLinter()

	assert.NotNil(t, linter)
}

func TestLinter_Lint_ValidSpec(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name: "valid.md",
		Content: `FUNCTION: add(a, b) → sum

RULES:
  - return the sum of a and b

DONE_WHEN:
  - result equals a + b

EXAMPLES:
  (2, 3) → 5

ERRORS:
  - any error → fail`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
	assert.Equal(t, "valid.md", result.File)
	assert.Equal(t, 1, result.Stats.Functions)
	assert.Equal(t, 1, result.Stats.Examples)
}

func TestLinter_Lint_InvalidSpec_MissingFunction(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name:    "invalid.md",
		Content: `DATA: SomeType\n  field: string`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.False(t, result.Valid)
	require.Len(t, result.Errors, 1)
	assert.Equal(t, "E001", result.Errors[0].Code)
}

func TestLinter_Lint_InvalidSpec_MissingErrors(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name: "missing_errors.md",
		Content: `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.False(t, result.Valid)
	hasE005 := false
	for _, e := range result.Errors {
		if e.Code == "E005" {
			hasE005 = true
		}
	}
	assert.True(t, hasE005, "Expected E005 for missing ERRORS")
}

func TestLinter_Lint_ComplexityViolations(t *testing.T) {
	linter := lint.New(lint.Config{
		MaxRules:  3,
		MaxInputs: 2,
	})

	input := InputSource{
		Name: "complex.md",
		Content: `FUNCTION: complex(a, b, c, d) → result

RULES:
  - rule 1
  - rule 2
  - rule 3
  - rule 4
  - rule 5

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2, 3, 4) → ok

ERRORS:
  - fail`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.False(t, result.Valid)

	codes := make(map[string]bool)
	for _, e := range result.Errors {
		codes[e.Code] = true
	}
	assert.True(t, codes["E010"], "Expected E010 for too many rules")
	assert.True(t, codes["E011"], "Expected E011 for too many inputs")
}

func TestLinter_Lint_ParseWarnings(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name: "warnings.md",
		Content: `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail

CUSTOM_UNKNOWN_LANDMARK:
  - this is unrecognized`,
	}

	result := linter.Lint(input.Name, input.Content)

	// Should still be valid (unrecognized landmarks are warnings)
	assert.True(t, result.Valid)
	assert.NotEmpty(t, result.Warnings)

	hasW001 := false
	for _, w := range result.Warnings {
		if w.Code == "W001" {
			hasW001 = true
		}
	}
	assert.True(t, hasW001, "Expected W001 for unrecognized landmark")
}

func TestLinter_Lint_Stats(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name: "stats.md",
		Content: `FUNCTION: fn1() → result

RULES:
  - if A, do X
  - if B, do Y

DONE_WHEN:
  - done

EXAMPLES:
  (A) → X
  (B) → Y
  (C) → Z

ERRORS:
  - fail

FUNCTION: fn2() → result

RULES:
  - simple rule

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.True(t, result.Valid)
	assert.Equal(t, 2, result.Stats.Functions)
	assert.Equal(t, 4, result.Stats.Examples) // 3 + 1
	assert.True(t, result.Stats.Branches > 0)
	assert.True(t, result.Stats.ExamplesPerBranch > 0)
}

func TestLinter_Lint_ExamplesPerBranch(t *testing.T) {
	linter := lint.DefaultLinter()

	// More examples than counted branches produce a ratio greater than one.
	input := InputSource{
		Name: "overcovered.md",
		Content: `FUNCTION: test() → result

RULES:
  - simple rule with no branches

DONE_WHEN:
  - done

EXAMPLES:
  (1) → a
  (2) → b
  (3) → c
  (4) → d
  (5) → e

ERRORS:
  - fail`,
	}

	result := linter.Lint(input.Name, input.Content)

	assert.True(t, result.Valid)
	assert.Equal(t, 5.0, result.Stats.ExamplesPerBranch)
}

func TestOutputSingle_Text(t *testing.T) {
	r := result.NewLintResult("test.md")

	// Capture stdout
	old := os.Stdout
	r2, w, _ := os.Pipe()
	os.Stdout = w

	outputSingle(*r, "text")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r2)
	output := buf.String()

	assert.Contains(t, output, "simplex-lint: test.md")
	assert.Contains(t, output, "Checks PASSED")
}

func TestOutputSingle_JSON(t *testing.T) {
	r := result.NewLintResult("test.md")
	r.SpecificationVersion = "0.6"
	r.SupportedVersion = "0.6"
	r.Stats.Traceability = &result.TraceabilityStats{
		Declared:       true,
		Links:          2,
		CoverableItems: 2,
		CoveredItems:   2,
		Complete:       true,
	}

	// Capture stdout
	old := os.Stdout
	r2, w, _ := os.Pipe()
	os.Stdout = w

	outputSingle(*r, "json")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r2)
	output := buf.String()

	assert.Contains(t, output, `"file": "test.md"`)
	assert.Contains(t, output, `"specification_version": "0.6"`)
	assert.Contains(t, output, `"supported_specification_version": "0.6"`)
	assert.Contains(t, output, `"traceability": {`)
	assert.Contains(t, output, `"complete": true`)
	assert.Contains(t, output, `"valid": true`)
}

func TestOutputMultiple_Text(t *testing.T) {
	results := []result.LintResult{
		*result.NewLintResult("test1.md"),
		*result.NewLintResult("test2.md"),
	}

	// Capture stdout
	old := os.Stdout
	r2, w, _ := os.Pipe()
	os.Stdout = w

	outputMultiple(results, "text")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r2)
	output := buf.String()

	assert.Contains(t, output, "test1.md")
	assert.Contains(t, output, "test2.md")
	assert.Contains(t, output, "OVERALL:")
	assert.Contains(t, output, "2/2 files passed")
}

func TestOutputMultiple_JSON(t *testing.T) {
	results := []result.LintResult{
		*result.NewLintResult("test1.md"),
		*result.NewLintResult("test2.md"),
	}

	// Capture stdout
	old := os.Stdout
	r2, w, _ := os.Pipe()
	os.Stdout = w

	outputMultiple(results, "json")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r2)
	output := buf.String()

	assert.Contains(t, output, `"total_files": 2`)
	assert.Contains(t, output, `"total_valid": 2`)
}

// Integration tests using actual test fixtures
func TestIntegration_ValidMinimal(t *testing.T) {
	content, err := os.ReadFile("../../testdata/valid_minimal.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	result := linter.Lint("valid_minimal.md", string(content))

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
}

func TestIntegration_ValidComplex(t *testing.T) {
	content, err := os.ReadFile("../../testdata/valid_complex.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	result := linter.Lint("valid_complex.md", string(content))

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
	assert.Equal(t, 3, result.Stats.Functions)
}

func TestIntegration_ValidTraceability(t *testing.T) {
	content, err := os.ReadFile("../../testdata/valid_traceability.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	lintResult := linter.Lint("valid_traceability.md", string(content))

	assert.True(t, lintResult.Valid)
	assert.Empty(t, lintResult.Errors)
	assert.Empty(t, lintResult.Warnings)
	assert.Equal(t, "0.6", lintResult.SpecificationVersion)
	assert.Equal(t, lint.SupportedSpecVersion, lintResult.SupportedVersion)
	require.NotNil(t, lintResult.Stats.Traceability)
	assert.True(t, lintResult.Stats.Traceability.Declared)
	assert.True(t, lintResult.Stats.Traceability.Complete)
	assert.Equal(t, 3, lintResult.Stats.Traceability.CoverableItems)
	assert.Equal(t, 3, lintResult.Stats.Traceability.CoveredItems)
}

func TestIntegration_InvalidTraceability(t *testing.T) {
	content, err := os.ReadFile("../../testdata/invalid_traceability.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	lintResult := linter.Lint("invalid_traceability.md", string(content))

	assert.False(t, lintResult.Valid)
	assert.Contains(t, lintIssueCodes(lintResult.Errors), "E103")
	require.NotNil(t, lintResult.Stats.Traceability)
	assert.False(t, lintResult.Stats.Traceability.Complete)
}

func TestIntegration_InvalidMissingErrors(t *testing.T) {
	content, err := os.ReadFile("../../testdata/invalid_missing_errors.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	result := linter.Lint("invalid_missing_errors.md", string(content))

	assert.False(t, result.Valid)
	hasE005 := false
	for _, e := range result.Errors {
		if e.Code == "E005" {
			hasE005 = true
		}
	}
	assert.True(t, hasE005)
}

func TestIntegration_InvalidMissingFunction(t *testing.T) {
	content, err := os.ReadFile("../../testdata/invalid_missing_function.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	result := linter.Lint("invalid_missing_function.md", string(content))

	assert.False(t, result.Valid)
	hasE001 := false
	for _, e := range result.Errors {
		if e.Code == "E001" {
			hasE001 = true
		}
	}
	assert.True(t, hasE001)
}

func TestIntegration_InvalidTooComplex(t *testing.T) {
	content, err := os.ReadFile("../../testdata/invalid_too_complex.md")
	require.NoError(t, err)

	linter := lint.DefaultLinter()
	result := linter.Lint("invalid_too_complex.md", string(content))

	assert.False(t, result.Valid)

	codes := make(map[string]bool)
	for _, e := range result.Errors {
		codes[e.Code] = true
	}
	assert.True(t, codes["E010"], "Expected E010")
	assert.True(t, codes["E011"], "Expected E011")
}

func TestIntegration_AllTestdata(t *testing.T) {
	// Test that all testdata files can be processed without panics
	files, err := filepath.Glob("../../testdata/*.md")
	require.NoError(t, err)
	require.NotEmpty(t, files)

	linter := lint.DefaultLinter()

	for _, file := range files {
		t.Run(filepath.Base(file), func(t *testing.T) {
			content, err := os.ReadFile(file)
			require.NoError(t, err)

			// Should not panic
			result := linter.Lint(filepath.Base(file), string(content))

			// Valid files should pass, invalid files should fail
			if strings.HasPrefix(filepath.Base(file), "valid_") {
				assert.True(t, result.Valid, "Expected %s to be valid", file)
			} else if strings.HasPrefix(filepath.Base(file), "invalid_") {
				assert.False(t, result.Valid, "Expected %s to be invalid", file)
			}
		})
	}
}

func TestCLIExposesOnlyImplementedFlags(t *testing.T) {
	for _, name := range []string{"format", "input-mode", "max-rules", "max-inputs"} {
		assert.NotNil(t, rootCmd.Flags().Lookup(name), "expected supported flag --%s", name)
	}

	for _, name := range []string{
		"fix", "no-llm", "provider", "model", "api-key", "api-base",
		"cache", "no-cache", "verbose",
	} {
		assert.Nil(t, rootCmd.Flags().Lookup(name), "unsupported flag --%s should not be exposed", name)
	}
}

func TestParseInputMode(t *testing.T) {
	for _, value := range []string{"auto", "raw", "markdown", "extracted"} {
		mode, err := parseInputMode(value)
		require.NoError(t, err)
		assert.Equal(t, lint.InputMode(value), mode)
	}

	_, err := parseInputMode("guess")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "invalid --input-mode")
}

func TestValidateCLIOptions(t *testing.T) {
	originalFormat := flagFormat
	originalMaxRules := flagMaxRules
	originalMaxInputs := flagMaxInputs
	t.Cleanup(func() {
		flagFormat = originalFormat
		flagMaxRules = originalMaxRules
		flagMaxInputs = originalMaxInputs
	})

	flagFormat = "text"
	flagMaxRules = 15
	flagMaxInputs = 6
	require.NoError(t, validateCLIOptions())

	flagFormat = "yaml"
	assert.EqualError(t, validateCLIOptions(), `invalid --format "yaml": expected text or json`)

	flagFormat = "json"
	flagMaxRules = 0
	assert.EqualError(t, validateCLIOptions(), "invalid --max-rules 0: expected a positive integer")

	flagMaxRules = 15
	flagMaxInputs = -1
	assert.EqualError(t, validateCLIOptions(), "invalid --max-inputs -1: expected a positive integer")
}

func TestLinter_Lint_ZeroBranches(t *testing.T) {
	// Test with a spec that has no identifiable branches
	linter := lint.DefaultLinter()

	input := InputSource{
		Name: "no_branches.md",
		Content: `FUNCTION: simple() → result

RULES:
  - just do it

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`,
	}

	result := linter.Lint(input.Name, input.Content)
	assert.True(t, result.Valid)
	// With 1 counted branch and 1 example, the ratio should be 1.
	assert.Equal(t, 1, result.Stats.Branches)
	assert.Equal(t, 1.0, result.Stats.ExamplesPerBranch)
}

func TestLinter_Lint_EmptySpec(t *testing.T) {
	linter := lint.DefaultLinter()

	input := InputSource{
		Name:    "empty.md",
		Content: "",
	}

	result := linter.Lint(input.Name, input.Content)
	assert.False(t, result.Valid)
	assert.Equal(t, 0, result.Stats.Functions)
	assert.Equal(t, 0, result.Stats.Branches)
	assert.Equal(t, 0, result.Stats.Examples)
}
