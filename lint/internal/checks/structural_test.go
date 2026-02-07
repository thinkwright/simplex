package checks

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

func TestStructuralChecker_E001_NoFunction(t *testing.T) {
	spec := `DATA: SomeType
  field: string

CONSTRAINT: some_rule
  must be valid`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)
	require.Len(t, r.Errors, 1)
	assert.Equal(t, "E001", r.Errors[0].Code)
	assert.Contains(t, r.Errors[0].Message, "No FUNCTION block found")
}

func TestStructuralChecker_E002_MissingRules(t *testing.T) {
	spec := `FUNCTION: test() → result

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)
	hasE002 := false
	for _, e := range r.Errors {
		if e.Code == "E002" {
			hasE002 = true
			assert.Contains(t, e.Message, "RULES")
		}
	}
	assert.True(t, hasE002, "Expected E002 error for missing RULES")
}

func TestStructuralChecker_E003_MissingDoneWhen(t *testing.T) {
	spec := `FUNCTION: test() → result

RULES:
  - do something

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)
	hasE003 := false
	for _, e := range r.Errors {
		if e.Code == "E003" {
			hasE003 = true
			assert.Contains(t, e.Message, "DONE_WHEN")
		}
	}
	assert.True(t, hasE003, "Expected E003 error for missing DONE_WHEN")
}

func TestStructuralChecker_E004_MissingExamples(t *testing.T) {
	spec := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)
	hasE004 := false
	for _, e := range r.Errors {
		if e.Code == "E004" {
			hasE004 = true
			assert.Contains(t, e.Message, "EXAMPLES")
		}
	}
	assert.True(t, hasE004, "Expected E004 error for missing EXAMPLES")
}

func TestStructuralChecker_E005_MissingErrors(t *testing.T) {
	spec := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)
	hasE005 := false
	for _, e := range r.Errors {
		if e.Code == "E005" {
			hasE005 = true
			assert.Contains(t, e.Message, "ERRORS")
			assert.NotNil(t, e.Suggestion)
			assert.True(t, e.Fixable)
		}
	}
	assert.True(t, hasE005, "Expected E005 error for missing ERRORS")
}

func TestStructuralChecker_AllRequired_Valid(t *testing.T) {
	spec := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.True(t, r.Valid)
	assert.Empty(t, r.Errors)
}

func TestStructuralChecker_MultipleFunctions_MixedValidity(t *testing.T) {
	spec := `FUNCTION: valid_fn() → result

RULES:
  - valid rules

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail

FUNCTION: invalid_fn() → result

RULES:
  - has rules

DONE_WHEN:
  - has done_when`
	// invalid_fn missing EXAMPLES and ERRORS

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	assert.False(t, r.Valid)

	// Should have E004 and E005 for invalid_fn
	codes := make(map[string]bool)
	for _, e := range r.Errors {
		codes[e.Code] = true
		// Verify errors are for the right function
		if e.Code == "E004" || e.Code == "E005" {
			assert.Contains(t, e.Location, "invalid_fn")
		}
	}
	assert.True(t, codes["E004"])
	assert.True(t, codes["E005"])
}

func TestStructuralChecker_W006_UndefinedDataType(t *testing.T) {
	spec := `DATA: User
  id: string
  name: string

FUNCTION: get_user(id) → Customer

RULES:
  - find user by id

DONE_WHEN:
  - user found

EXAMPLES:
  ("123") → Customer

ERRORS:
  - not found → fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	// Should have warning about Customer type not being defined
	hasW006 := false
	for _, w := range r.Warnings {
		if w.Code == "W006" {
			hasW006 = true
			assert.Contains(t, w.Message, "Customer")
		}
	}
	assert.True(t, hasW006, "Expected W006 warning for undefined DATA type")
}

func TestStructuralChecker_W006_DefinedDataType(t *testing.T) {
	spec := `DATA: User
  id: string
  name: string

FUNCTION: get_user(id) → User

RULES:
  - find user by id

DONE_WHEN:
  - user found

EXAMPLES:
  ("123") → User

ERRORS:
  - not found → fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	// No warning because User is defined
	for _, w := range r.Warnings {
		assert.NotEqual(t, "W006", w.Code, "Should not warn about defined type")
	}
}

func TestStructuralChecker_W006_BuiltinTypes(t *testing.T) {
	spec := `DATA: Custom
  field: string

FUNCTION: fn1() → string

RULES:
  - return string

DONE_WHEN:
  - done

EXAMPLES:
  () → "test"

ERRORS:
  - fail

FUNCTION: fn2() → list

RULES:
  - return list

DONE_WHEN:
  - done

EXAMPLES:
  () → []

ERRORS:
  - fail

FUNCTION: fn3() → int

RULES:
  - return int

DONE_WHEN:
  - done

EXAMPLES:
  () → 42

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	// No warnings for built-in types
	for _, w := range r.Warnings {
		if w.Code == "W006" {
			t.Errorf("Should not warn about built-in type: %s", w.Message)
		}
	}
}

func TestStructuralChecker_NoDataBlocks_NoW006(t *testing.T) {
	// When there are no DATA blocks, we don't warn about undefined types
	// because the user isn't using typed specs
	spec := `FUNCTION: process(input) → CustomResult

RULES:
  - process input

DONE_WHEN:
  - done

EXAMPLES:
  (x) → y

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewStructuralChecker()
	checker.Check(parsed, r)

	// No W006 warnings when no DATA blocks exist
	for _, w := range r.Warnings {
		assert.NotEqual(t, "W006", w.Code)
	}
}

func TestExtractTypeName(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		expected string
	}{
		{"with newline", "User\n  id: string", "User"},
		{"policy rule", "PolicyRule\n  field: value", "PolicyRule"},
		{"simple type", "SimpleType", "SimpleType"},
		{"type with space", "Type ", "Type"},
		{"type with tab", "Type\tfield", "Type"},
		{"empty", "", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractTypeName(tt.content)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestNormalizeTypeName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"User", "user"},
		{"PolicyRule", "policyrule"},
		{"list of User", "user"},
		{"listofItem", "item"},
		{"LIST_OF_THINGS", "things"},
		{"ArrayOfUser", "user"},
		{"setofItem", "item"},
		{"simple", "simple"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			result := normalizeTypeName(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestFormatFunctionLocation(t *testing.T) {
	assert.Equal(t, "FUNCTION test", formatFunctionLocation("test"))
	assert.Equal(t, "FUNCTION my_func", formatFunctionLocation("my_func"))
	assert.Equal(t, "FUNCTION (unnamed)", formatFunctionLocation(""))
}
