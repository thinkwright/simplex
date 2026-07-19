package parser

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseWithOptionsRawShieldsLandmarksInsideFences(t *testing.T) {
	input := `FUNCTION: render_docs() → text

RULES:
  - include this literal example:
    ` + "```" + `simplex
FUNCTION: illustrative() → ignored
RULES:
  - this is documentation, not another live function
    ` + "```" + `

DONE_WHEN:
  - documentation is returned

EXAMPLES:
  () → "documentation"

ERRORS:
  - any unhandled condition → fail with descriptive message
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{Mode: InputModeRaw})

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, "render_docs", spec.Functions[0].Name)
	assert.Contains(t, spec.Functions[0].GetRules(), "FUNCTION: illustrative")
	assert.True(t, spec.Functions[0].HasLandmark(LandmarkDONE_WHEN))
}

func TestParseWithOptionsRawAcceptsIndentedLandmarks(t *testing.T) {
	input := `  FUNCTION: indented(value) → value

    RULES:
      - return value

    DONE_WHEN:
      - value is returned

    EXAMPLES:
      (1) → 1

    ERRORS:
      - any unhandled condition → fail with descriptive message
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{Mode: InputModeRaw})

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]
	assert.Equal(t, "indented", fn.Name)
	assert.True(t, fn.HasLandmark(LandmarkRULES))
	assert.True(t, fn.HasLandmark(LandmarkDONE_WHEN))
	assert.True(t, fn.HasLandmark(LandmarkEXAMPLES))
	assert.True(t, fn.HasLandmark(LandmarkERRORS))
}

func TestParseWithOptionsMarkdownParsesOnlySimplexFences(t *testing.T) {
	input := `# Parser guide

FUNCTION: prose_example() → ignored

` + "```" + `
FUNCTION: unlabeled_example() → ignored
RULES:
  - ignored
` + "```" + `

` + "```" + `simplex
FUNCTION: live(value) → value

RULES:
  - return value

DONE_WHEN:
  - value is returned

EXAMPLES:
  (1) → 1

ERRORS:
  - any unhandled condition → fail with descriptive message
` + "```" + `
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{Mode: InputModeMarkdown})

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, "live", spec.Functions[0].Name)
	assert.Equal(t, InputModeMarkdown, spec.InputMode)
	assert.Empty(t, spec.ParseWarnings)
}

func TestParseWithOptionsMarkdownCombinesLiveRegionsInSourceOrder(t *testing.T) {
	input := `# Split contract

` + "```" + `simplex
FUNCTION: split(value) → value

RULES:
  - return value
` + "```" + `

Explanatory prose between live regions.

` + "```" + `simplex
DONE_WHEN:
  - value is returned

EXAMPLES:
  (1) → 1

ERRORS:
  - any unhandled condition → fail with descriptive message
` + "```" + `
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{Mode: InputModeMarkdown})

	require.Len(t, spec.Functions, 1)
	fn := spec.Functions[0]
	assert.Equal(t, "split", fn.Name)
	assert.True(t, fn.HasLandmark(LandmarkRULES))
	assert.NotContains(t, fn.GetRules(), "Explanatory prose")
	assert.True(t, fn.HasLandmark(LandmarkDONE_WHEN))
	assert.True(t, fn.HasLandmark(LandmarkEXAMPLES))
	assert.True(t, fn.HasLandmark(LandmarkERRORS))
}

func TestParseWithOptionsExtractedRetainsCallerLineOffset(t *testing.T) {
	input := `FUNCTION: extracted() → result

RULES:
  - return result

DONE_WHEN:
  - result is returned

EXAMPLES:
  () → result

ERRORS:
  - any unhandled condition → fail with descriptive message
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{
		Mode:      InputModeExtracted,
		StartLine: 40,
	})

	require.Len(t, spec.Functions, 1)
	assert.Equal(t, 40, spec.Functions[0].LineNumber)
	rules := spec.Functions[0].GetLandmark(LandmarkRULES)
	require.NotNil(t, rules)
	assert.Equal(t, 42, rules.LineNumber)
}

func TestParseWithOptionsAutoSelectsMode(t *testing.T) {
	minimal := `FUNCTION: raw() → result

RULES:
  - return result

DONE_WHEN:
  - result is returned

EXAMPLES:
  () → result

ERRORS:
  - any unhandled condition → fail with descriptive message
`

	t.Run("simplex extension selects raw", func(t *testing.T) {
		spec := NewParser().ParseWithOptions(minimal, ParseOptions{
			Mode:       InputModeAuto,
			SourceName: "contract.simplex",
		})

		assert.Equal(t, InputModeRaw, spec.InputMode)
		require.Len(t, spec.Functions, 1)
		assert.Empty(t, spec.ParseWarnings)
	})

	t.Run("labeled Markdown selects Markdown", func(t *testing.T) {
		input := "FUNCTION: ignored() → result\n\n```simplex\n" + minimal + "```\n"
		spec := NewParser().ParseWithOptions(input, ParseOptions{
			Mode:       InputModeAuto,
			SourceName: "guide.md",
		})

		assert.Equal(t, InputModeMarkdown, spec.InputMode)
		require.Len(t, spec.Functions, 1)
		assert.Equal(t, "raw", spec.Functions[0].Name)
	})

	t.Run("unmarked Markdown retains legacy raw behavior with warning", func(t *testing.T) {
		spec := NewParser().ParseWithOptions(minimal, ParseOptions{
			Mode:       InputModeAuto,
			SourceName: "legacy.md",
		})

		assert.Equal(t, InputModeRaw, spec.InputMode)
		require.Len(t, spec.Functions, 1)
		require.NotEmpty(t, spec.ParseWarnings)
		assert.Contains(t, spec.ParseWarnings[0], "legacy raw Markdown")
	})

	t.Run("stdin is treated as extracted input", func(t *testing.T) {
		spec := NewParser().ParseWithOptions(minimal, ParseOptions{
			Mode:       InputModeAuto,
			SourceName: "<stdin>",
		})

		assert.Equal(t, InputModeExtracted, spec.InputMode)
		require.Len(t, spec.Functions, 1)
		assert.Empty(t, spec.ParseWarnings)
	})
}

func TestParseWithOptionsMarkdownWarnsOnUnterminatedLiveFence(t *testing.T) {
	input := "# Guide\n\n```simplex\n" + `FUNCTION: live() → result

RULES:
  - return result

DONE_WHEN:
  - result is returned

EXAMPLES:
  () → result

ERRORS:
  - any unhandled condition → fail with descriptive message
`

	spec := NewParser().ParseWithOptions(input, ParseOptions{Mode: InputModeMarkdown})

	require.Len(t, spec.Functions, 1)
	assert.True(t, containsWarning(spec.ParseWarnings, "unterminated Simplex fence"))
}

func TestInputModeFallbacks(t *testing.T) {
	mode, warnings := resolveInputMode("FUNCTION: f() → result", ParseOptions{})
	assert.Equal(t, InputModeRaw, mode)
	assert.Empty(t, warnings)

	mode, warnings = resolveInputMode("FUNCTION: f() → result", ParseOptions{Mode: InputMode("invalid")})
	assert.Equal(t, InputModeRaw, mode)
	require.Len(t, warnings, 1)
	assert.Contains(t, warnings[0], "unrecognized input mode")

	regions, warnings := selectInputRegions("FUNCTION: f() → result", InputMode("invalid"), 1)
	require.Len(t, regions, 1)
	assert.Empty(t, warnings)
}

func TestParseFenceOpeningRejectsShortMarkerAndBacktickInInfo(t *testing.T) {
	_, ok := parseFenceOpening("``x")
	assert.False(t, ok)

	_, ok = parseFenceOpening("```simplex`invalid")
	assert.False(t, ok)
}

func containsWarning(warnings []string, substring string) bool {
	for _, warning := range warnings {
		if strings.Contains(warning, substring) {
			return true
		}
	}
	return false
}
