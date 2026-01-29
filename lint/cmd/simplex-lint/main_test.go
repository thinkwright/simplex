package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/brannn/simplex/lint/internal/result"
)

func TestNewLinter(t *testing.T) {
	config := LinterConfig{
		MaxRules:  20,
		MaxInputs: 8,
		NoLLM:     true,
		Verbose:   false,
	}

	linter := NewLinter(config)

	assert.NotNil(t, linter)
	assert.NotNil(t, linter.parser)
	assert.NotNil(t, linter.structuralChecker)
	assert.NotNil(t, linter.complexityChecker)
	assert.Equal(t, config, linter.config)
}

func TestNewLinter_DefaultConfig(t *testing.T) {
	linter := NewLinter(LinterConfig{})

	assert.NotNil(t, linter)
	// With zero config, defaults should be applied
}

func TestLinter_Lint_ValidSpec(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

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

	result := linter.Lint(input)

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
	assert.Equal(t, "valid.md", result.File)
	assert.Equal(t, 1, result.Stats.Functions)
	assert.Equal(t, 1, result.Stats.Examples)
}

func TestLinter_Lint_InvalidSpec_MissingFunction(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

	input := InputSource{
		Name:    "invalid.md",
		Content: `DATA: SomeType\n  field: string`,
	}

	result := linter.Lint(input)

	assert.False(t, result.Valid)
	require.Len(t, result.Errors, 1)
	assert.Equal(t, "E001", result.Errors[0].Code)
}

func TestLinter_Lint_InvalidSpec_MissingErrors(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

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

	result := linter.Lint(input)

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
	linter := NewLinter(LinterConfig{
		MaxRules:  3,
		MaxInputs: 2,
		NoLLM:     true,
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

	result := linter.Lint(input)

	assert.False(t, result.Valid)

	codes := make(map[string]bool)
	for _, e := range result.Errors {
		codes[e.Code] = true
	}
	assert.True(t, codes["E010"], "Expected E010 for too many rules")
	assert.True(t, codes["E011"], "Expected E011 for too many inputs")
}

func TestLinter_Lint_ParseWarnings(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

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

	result := linter.Lint(input)

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
	linter := NewLinter(LinterConfig{NoLLM: true})

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

	result := linter.Lint(input)

	assert.True(t, result.Valid)
	assert.Equal(t, 2, result.Stats.Functions)
	assert.Equal(t, 4, result.Stats.Examples) // 3 + 1
	assert.True(t, result.Stats.Branches > 0)
	assert.True(t, result.Stats.CoveragePercent > 0)
}

func TestLinter_Lint_CoveragePercent_Capped(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

	// More examples than branches should cap at 100%
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

	result := linter.Lint(input)

	assert.True(t, result.Valid)
	assert.Equal(t, 100.0, result.Stats.CoveragePercent)
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
	assert.Contains(t, output, "VALID")
}

func TestOutputSingle_JSON(t *testing.T) {
	r := result.NewLintResult("test.md")

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
	assert.Contains(t, output, "2/2 specs valid")
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

	linter := NewLinter(LinterConfig{NoLLM: true})
	result := linter.Lint(InputSource{
		Name:    "valid_minimal.md",
		Content: string(content),
	})

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
}

func TestIntegration_ValidComplex(t *testing.T) {
	content, err := os.ReadFile("../../testdata/valid_complex.md")
	require.NoError(t, err)

	linter := NewLinter(LinterConfig{NoLLM: true})
	result := linter.Lint(InputSource{
		Name:    "valid_complex.md",
		Content: string(content),
	})

	assert.True(t, result.Valid)
	assert.Empty(t, result.Errors)
	assert.Equal(t, 3, result.Stats.Functions)
}

func TestIntegration_InvalidMissingErrors(t *testing.T) {
	content, err := os.ReadFile("../../testdata/invalid_missing_errors.md")
	require.NoError(t, err)

	linter := NewLinter(LinterConfig{NoLLM: true})
	result := linter.Lint(InputSource{
		Name:    "invalid_missing_errors.md",
		Content: string(content),
	})

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

	linter := NewLinter(LinterConfig{NoLLM: true})
	result := linter.Lint(InputSource{
		Name:    "invalid_missing_function.md",
		Content: string(content),
	})

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

	linter := NewLinter(LinterConfig{NoLLM: true})
	result := linter.Lint(InputSource{
		Name:    "invalid_too_complex.md",
		Content: string(content),
	})

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

	linter := NewLinter(LinterConfig{NoLLM: true})

	for _, file := range files {
		t.Run(filepath.Base(file), func(t *testing.T) {
			content, err := os.ReadFile(file)
			require.NoError(t, err)

			// Should not panic
			result := linter.Lint(InputSource{
				Name:    filepath.Base(file),
				Content: string(content),
			})

			// Valid files should pass, invalid files should fail
			if strings.HasPrefix(filepath.Base(file), "valid_") {
				assert.True(t, result.Valid, "Expected %s to be valid", file)
			} else if strings.HasPrefix(filepath.Base(file), "invalid_") {
				assert.False(t, result.Valid, "Expected %s to be invalid", file)
			}
		})
	}
}

func TestLinter_Lint_VerboseMode(t *testing.T) {
	// Test with verbose mode enabled (covers the verbose branch in Lint)
	linter := NewLinter(LinterConfig{
		NoLLM:   false, // LLM enabled but not configured
		Verbose: true,
	})

	input := InputSource{
		Name: "verbose_test.md",
		Content: `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`,
	}

	// Capture stderr to verify verbose output
	// Note: This tests the branch but we don't verify stderr content
	result := linter.Lint(input)
	assert.True(t, result.Valid)
}

func TestLinter_Lint_ZeroBranches(t *testing.T) {
	// Test with a spec that has no identifiable branches
	linter := NewLinter(LinterConfig{NoLLM: true})

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

	result := linter.Lint(input)
	assert.True(t, result.Valid)
	// With 1 branch (minimum) and 1 example, coverage should be 100%
	assert.Equal(t, 1, result.Stats.Branches)
}

func TestLinter_Lint_EmptySpec(t *testing.T) {
	linter := NewLinter(LinterConfig{NoLLM: true})

	input := InputSource{
		Name:    "empty.md",
		Content: "",
	}

	result := linter.Lint(input)
	assert.False(t, result.Valid)
	assert.Equal(t, 0, result.Stats.Functions)
	assert.Equal(t, 0, result.Stats.Branches)
	assert.Equal(t, 0, result.Stats.Examples)
}
