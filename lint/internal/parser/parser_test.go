package parser

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParser_Parse_MinimalSpec(t *testing.T) {
	input := `FUNCTION: add(a, b) → sum

RULES:
  - return the sum of a and b

DONE_WHEN:
  - result equals a + b

EXAMPLES:
  (2, 3) → 5
  (0, 0) → 0

ERRORS:
  - any unhandled condition → fail with descriptive message
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	assert.Equal(t, "add", fn.Name)
	assert.Equal(t, []string{"a", "b"}, fn.Inputs)
	assert.Equal(t, "sum", fn.ReturnType)

	assert.True(t, fn.HasLandmark(LandmarkRULES))
	assert.True(t, fn.HasLandmark(LandmarkDONE_WHEN))
	assert.True(t, fn.HasLandmark(LandmarkEXAMPLES))
	assert.True(t, fn.HasLandmark(LandmarkERRORS))

	assert.Contains(t, fn.GetRules(), "return the sum of a and b")
	assert.Contains(t, fn.GetExamples(), "(2, 3) → 5")
}

func TestParser_Parse_MultipleFunctions(t *testing.T) {
	input := `FUNCTION: foo(x) → result

RULES:
  - do foo

DONE_WHEN:
  - foo done

EXAMPLES:
  (1) → 2

ERRORS:
  - fail on error

FUNCTION: bar(y) → output

RULES:
  - do bar

DONE_WHEN:
  - bar done

EXAMPLES:
  (3) → 6

ERRORS:
  - fail on error
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 2)

	assert.Equal(t, "foo", spec.Functions[0].Name)
	assert.Equal(t, "bar", spec.Functions[1].Name)

	assert.Contains(t, spec.Functions[0].GetRules(), "do foo")
	assert.Contains(t, spec.Functions[1].GetRules(), "do bar")
}

func TestParser_Parse_WithDataBlocks(t *testing.T) {
	input := `DATA: User
  id: string
  name: string
  email: string

FUNCTION: create_user(data) → User

RULES:
  - create a new user

DONE_WHEN:
  - user created

EXAMPLES:
  (valid data) → User

ERRORS:
  - invalid data → fail
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.DataBlocks, 1)
	assert.Equal(t, "DATA", spec.DataBlocks[0].Name)
	assert.Contains(t, spec.DataBlocks[0].Content, "id: string")

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, "create_user", spec.Functions[0].Name)
}

func TestParser_Parse_WithConstraints(t *testing.T) {
	input := `CONSTRAINT: unique_ids
  all IDs must be unique across the system

FUNCTION: generate_id() → id

RULES:
  - generate unique ID

DONE_WHEN:
  - ID is unique

EXAMPLES:
  () → "abc123"

ERRORS:
  - collision → retry
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Constraints, 1)
	assert.Contains(t, spec.Constraints[0].Content, "all IDs must be unique")

	require.Len(t, spec.Functions, 1)
}

func TestParser_Parse_OptionalLandmarks(t *testing.T) {
	input := `FUNCTION: complex_fn(input) → output

RULES:
  - process input

DONE_WHEN:
  - processing complete

EXAMPLES:
  (x) → y

ERRORS:
  - error → fail

READS:
  - SharedMemory.config

WRITES:
  - SharedMemory.result

TRIGGERS:
  - SharedMemory.ready == true

NOT_ALLOWED:
  - modify source files

HANDOFF:
  - on success: pass to next stage

UNCERTAIN:
  - if format unknown → log warning
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	// Check all landmarks are present
	assert.True(t, fn.HasLandmark(LandmarkRULES))
	assert.True(t, fn.HasLandmark(LandmarkDONE_WHEN))
	assert.True(t, fn.HasLandmark(LandmarkEXAMPLES))
	assert.True(t, fn.HasLandmark(LandmarkERRORS))
	assert.True(t, fn.HasLandmark(LandmarkREADS))
	assert.True(t, fn.HasLandmark(LandmarkWRITES))
	assert.True(t, fn.HasLandmark(LandmarkTRIGGERS))
	assert.True(t, fn.HasLandmark(LandmarkNOT_ALLOWED))
	assert.True(t, fn.HasLandmark(LandmarkHANDOFF))
	assert.True(t, fn.HasLandmark(LandmarkUNCERTAIN))

	// Check content
	reads := fn.GetLandmark(LandmarkREADS)
	require.NotNil(t, reads)
	assert.Contains(t, reads.Content, "SharedMemory.config")
}

func TestParser_Parse_AlternateArrowSyntax(t *testing.T) {
	// Test with ASCII arrow (->)
	input := `FUNCTION: convert(x) -> string

RULES:
  - convert to string

DONE_WHEN:
  - converted

EXAMPLES:
  (1) -> "1"

ERRORS:
  - fail on error
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, "convert", spec.Functions[0].Name)
	assert.Equal(t, "string", spec.Functions[0].ReturnType)
}

func TestParser_Parse_FunctionNoInputs(t *testing.T) {
	input := `FUNCTION: get_timestamp() → timestamp

RULES:
  - return current timestamp

DONE_WHEN:
  - timestamp returned

EXAMPLES:
  () → 1234567890

ERRORS:
  - fail on error
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	assert.Equal(t, "get_timestamp", fn.Name)
	assert.Empty(t, fn.Inputs)
	assert.Equal(t, "timestamp", fn.ReturnType)
}

func TestParser_Parse_ToleratesFormatting(t *testing.T) {
	// Test with inconsistent spacing and indentation
	input := `FUNCTION:   spaced_fn( a,  b , c )  →  result

RULES:
- item without leading space
  - item with leading space
    - deeply indented item

DONE_WHEN:
  - done

EXAMPLES:
  (1,2,3) → 6

ERRORS:
  - fail
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	assert.Equal(t, "spaced_fn", fn.Name)
	assert.Equal(t, []string{"a", "b", "c"}, fn.Inputs)

	// Rules should contain all items regardless of indentation
	rules := fn.GetRules()
	assert.Contains(t, rules, "item without leading space")
	assert.Contains(t, rules, "item with leading space")
	assert.Contains(t, rules, "deeply indented item")
}

func TestParser_Parse_UnrecognizedLandmark(t *testing.T) {
	input := `FUNCTION: test() → result

RULES:
  - test

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail

CUSTOM_LANDMARK:
  - this is custom
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	// Should have a warning about unrecognized landmark
	assert.NotEmpty(t, spec.ParseWarnings)
}

func TestParser_Parse_EmptyInput(t *testing.T) {
	p := NewParser()
	spec := p.Parse("")

	assert.Empty(t, spec.Functions)
	assert.Empty(t, spec.DataBlocks)
	assert.Empty(t, spec.Constraints)
}

func TestParser_Parse_NoLandmarks(t *testing.T) {
	input := `This is just some text
without any landmarks.

It should parse but find nothing.
`

	p := NewParser()
	spec := p.Parse(input)

	assert.Empty(t, spec.Functions)
	assert.Empty(t, spec.DataBlocks)
	assert.Empty(t, spec.Constraints)
}

func TestParser_Parse_LineNumbers(t *testing.T) {
	input := `DATA: Type1
  field: value

FUNCTION: fn1() → result

RULES:
  - rule 1

DONE_WHEN:
  - done

EXAMPLES:
  () → x

ERRORS:
  - fail
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.DataBlocks, 1)
	assert.Equal(t, 1, spec.DataBlocks[0].LineNumber)

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, 4, spec.Functions[0].LineNumber)

	rules := spec.Functions[0].GetLandmark(LandmarkRULES)
	require.NotNil(t, rules)
	assert.Equal(t, 6, rules.LineNumber)
}

func TestParser_GetFunctionByName(t *testing.T) {
	input := `FUNCTION: alpha() → a

RULES:
  - alpha rules

DONE_WHEN:
  - done

EXAMPLES:
  () → a

ERRORS:
  - fail

FUNCTION: beta() → b

RULES:
  - beta rules

DONE_WHEN:
  - done

EXAMPLES:
  () → b

ERRORS:
  - fail
`

	p := NewParser()
	spec := p.Parse(input)

	alpha := spec.GetFunctionByName("alpha")
	require.NotNil(t, alpha)
	assert.Contains(t, alpha.GetRules(), "alpha rules")

	beta := spec.GetFunctionByName("beta")
	require.NotNil(t, beta)
	assert.Contains(t, beta.GetRules(), "beta rules")

	gamma := spec.GetFunctionByName("gamma")
	assert.Nil(t, gamma)
}

func TestParser_Parse_CodeBlockContent(t *testing.T) {
	// Test that code blocks in content are preserved
	input := `FUNCTION: parse(text) → ast

RULES:
  - parse the input text
  - handle code like:
    ` + "```" + `
    if x > 0:
        return x
    ` + "```" + `

DONE_WHEN:
  - AST generated

EXAMPLES:
  ("x = 1") → AST node

ERRORS:
  - syntax error → fail with details
`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	rules := spec.Functions[0].GetRules()
	assert.Contains(t, rules, "if x > 0")
	assert.Contains(t, rules, "return x")
}

func TestParser_Parse_MultipleDataAndConstraints(t *testing.T) {
	input := `DATA: TypeA
  field_a: string

DATA: TypeB
  field_b: int

CONSTRAINT: rule_1
  types must be valid

CONSTRAINT: rule_2
  references must exist

FUNCTION: process(a, b) → result

RULES:
  - process types

DONE_WHEN:
  - processed

EXAMPLES:
  (a, b) → result

ERRORS:
  - fail
`

	p := NewParser()
	spec := p.Parse(input)

	assert.Len(t, spec.DataBlocks, 2)
	assert.Len(t, spec.Constraints, 2)
	assert.Len(t, spec.Functions, 1)

	assert.Contains(t, spec.DataBlocks[0].Content, "field_a")
	assert.Contains(t, spec.DataBlocks[1].Content, "field_b")
	assert.Contains(t, spec.Constraints[0].Content, "types must be valid")
	assert.Contains(t, spec.Constraints[1].Content, "references must exist")
}

func TestFunctionBlock_GetDoneWhen(t *testing.T) {
	input := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - task completed
  - output verified

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	doneWhen := fn.GetDoneWhen()
	assert.Contains(t, doneWhen, "task completed")
	assert.Contains(t, doneWhen, "output verified")
}

func TestFunctionBlock_GetErrors(t *testing.T) {
	input := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - invalid input → fail with message
  - timeout → retry`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	errors := fn.GetErrors()
	assert.Contains(t, errors, "invalid input")
	assert.Contains(t, errors, "timeout")
}

func TestFunctionBlock_GetLandmark_NotFound(t *testing.T) {
	input := `FUNCTION: test() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	// READS landmark doesn't exist
	reads := fn.GetLandmark(LandmarkREADS)
	assert.Nil(t, reads)
}

func TestParser_Parse_FunctionLandmarkOutsideFunction(t *testing.T) {
	// RULES appearing before any FUNCTION should trigger a warning
	input := `RULES:
  - orphan rules

FUNCTION: test() → result

RULES:
  - proper rules

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	// Should have a parse warning about orphan RULES
	assert.NotEmpty(t, spec.ParseWarnings)
}

func TestParser_Parse_MalformedFunctionSignature(t *testing.T) {
	input := `FUNCTION: not_a_proper_signature

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	// Name should be the whole content since signature parsing failed
	assert.Equal(t, "not_a_proper_signature", fn.Name)
	assert.Empty(t, fn.Inputs)
	assert.Empty(t, fn.ReturnType)
}

func TestParser_Parse_FunctionSignatureOnSeparateLine(t *testing.T) {
	// When FUNCTION: has the signature on the next line
	input := `FUNCTION:
test(x, y) → result

RULES:
  - process

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2) → 3

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	assert.Equal(t, "test", fn.Name)
	assert.Equal(t, []string{"x", "y"}, fn.Inputs)
	assert.Equal(t, "result", fn.ReturnType)
}

func TestParser_Parse_LandmarkRegexEdgeCases(t *testing.T) {
	// Test that we don't match things that look like landmarks but aren't
	input := `FUNCTION: test() → result

RULES:
  - check if DATA: is in string
  - verify FUNCTION: references work

DONE_WHEN:
  - done

EXAMPLES:
  ("DATA: test") → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	// Should only find one FUNCTION, not match the text inside rules
	assert.Len(t, spec.Functions, 1)
	assert.Empty(t, spec.DataBlocks)
}

func TestParsedSpec_GetFunctionByName_Empty(t *testing.T) {
	spec := &ParsedSpec{
		Functions: []FunctionBlock{},
	}

	fn := spec.GetFunctionByName("nonexistent")
	assert.Nil(t, fn)
}

func TestFunctionBlock_HasLandmark_Missing(t *testing.T) {
	fn := FunctionBlock{
		Landmarks: map[string]Landmark{
			LandmarkRULES: {Name: LandmarkRULES, Content: "rules"},
		},
	}

	assert.True(t, fn.HasLandmark(LandmarkRULES))
	assert.False(t, fn.HasLandmark(LandmarkREADS))
	assert.False(t, fn.HasLandmark(LandmarkWRITES))
}

func TestFunctionBlock_GetRules_Empty(t *testing.T) {
	fn := FunctionBlock{
		Landmarks: map[string]Landmark{},
	}

	assert.Equal(t, "", fn.GetRules())
}

func TestFunctionBlock_GetExamples_Empty(t *testing.T) {
	fn := FunctionBlock{
		Landmarks: map[string]Landmark{},
	}

	assert.Equal(t, "", fn.GetExamples())
}

func TestFunctionBlock_GetDoneWhen_Empty(t *testing.T) {
	fn := FunctionBlock{
		Landmarks: map[string]Landmark{},
	}

	assert.Equal(t, "", fn.GetDoneWhen())
}

func TestFunctionBlock_GetErrors_Empty(t *testing.T) {
	fn := FunctionBlock{
		Landmarks: map[string]Landmark{},
	}

	assert.Equal(t, "", fn.GetErrors())
}

func TestParser_Parse_FunctionWithMultilineSignature(t *testing.T) {
	// Test a function where the FUNCTION: content spans multiple lines
	// This ensures the sigLine extraction handles newlines properly
	input := `FUNCTION: complex_fn(a, b, c) → result
  extra content after signature that shouldn't affect parsing

RULES:
  - process inputs

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2, 3) → 6

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]

	assert.Equal(t, "complex_fn", fn.Name)
	assert.Equal(t, []string{"a", "b", "c"}, fn.Inputs)
	assert.Equal(t, "result", fn.ReturnType)
}

func TestParser_Parse_FunctionWithInlineContent(t *testing.T) {
	// Edge case: FUNCTION block where content immediately follows signature
	input := `FUNCTION: inline() → out
some inline content

RULES:
  - rule

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := NewParser()
	spec := p.Parse(input)

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]
	assert.Equal(t, "inline", fn.Name)
}
