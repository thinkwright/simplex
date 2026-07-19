package checks

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/thinkwright/simplex/lint/internal/parser"
	"github.com/thinkwright/simplex/lint/internal/result"
)

func checkDeterminism(t *testing.T, source string) *result.LintResult {
	t.Helper()
	parsed := parser.NewParser().Parse(source)
	r := result.NewLintResult("test.simplex")
	NewDeterminismChecker().Check(parsed, r)
	return r
}

func TestDeterminismCheckerIgnoresAbsentLandmark(t *testing.T) {
	r := checkDeterminism(t, `FUNCTION: f() → result
RULES:
  - return result`)

	assert.Empty(t, r.Errors)
}

func TestDeterminismCheckerAcceptsSupportedLevels(t *testing.T) {
	for _, level := range []string{"strict", "structural", "semantic"} {
		t.Run(level, func(t *testing.T) {
			r := checkDeterminism(t, `FUNCTION: f() → result
DETERMINISM:

  seed: none
  level: `+level)

			assert.Empty(t, r.Errors)
		})
	}
}

func TestDeterminismCheckerRequiresLevel(t *testing.T) {
	r := checkDeterminism(t, `FUNCTION: f() → result
DETERMINISM:
  seed: none`)

	assert.Contains(t, issueCodes(r.Errors), "E070")
}

func TestDeterminismCheckerRejectsUnknownLevel(t *testing.T) {
	r := checkDeterminism(t, `FUNCTION: f() → result
DETERMINISM:
  level: fuzzy`)

	assert.Contains(t, issueCodes(r.Errors), "E070")
	assert.Contains(t, r.Errors[0].Message, "fuzzy")
}
