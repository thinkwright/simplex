package lint

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const validSimplexBlock = `FUNCTION: identity(value) → value

RULES:
  - return value

DONE_WHEN:
  - value is returned

EXAMPLES:
  (1) → 1

ERRORS:
  - any unhandled condition → fail with descriptive message
`

func TestLinterMarkdownModeUsesOnlyLabeledFences(t *testing.T) {
	input := "FUNCTION: prose_example() → ignored\n\n```\n" +
		"FUNCTION: unlabeled_example() → ignored\n```\n\n```simplex\n" +
		validSimplexBlock + "```\n"

	linter := New(Config{InputMode: InputModeMarkdown})
	result := linter.Lint("guide.md", input)

	assert.True(t, result.Valid)
	assert.Equal(t, 1, result.Stats.Functions)
	assert.Empty(t, result.Warnings)
}

func TestLinterAutoModeUsesSourceName(t *testing.T) {
	input := "FUNCTION: prose_example() → ignored\n\n```simplex\n" + validSimplexBlock + "```\n"

	linter := New(Config{InputMode: InputModeAuto})
	result := linter.Lint("guide.md", input)

	assert.True(t, result.Valid)
	assert.Equal(t, 1, result.Stats.Functions)
	assert.Empty(t, result.Warnings)
}

func TestLinterAutoModeWarnsForLegacyRawMarkdown(t *testing.T) {
	linter := New(Config{InputMode: InputModeAuto})
	result := linter.Lint("legacy.md", validSimplexBlock)

	assert.True(t, result.Valid)
	require.Len(t, result.Warnings, 1)
	assert.Equal(t, "W001", result.Warnings[0].Code)
	assert.Contains(t, result.Warnings[0].Message, "legacy raw Markdown")
}

func TestDefaultLinterRemainsRaw(t *testing.T) {
	result := DefaultLinter().Lint("legacy.md", validSimplexBlock)

	assert.True(t, result.Valid)
	assert.Empty(t, result.Warnings)
}
