package checks

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/thinkwright/simplex/lint/internal/parser"
	"github.com/thinkwright/simplex/lint/internal/result"
)

func checkVersion(t *testing.T, source string) (*result.LintResult, string) {
	t.Helper()
	parsed := parser.NewParser().Parse(source)
	r := result.NewLintResult("test.simplex")
	version := NewVersionChecker().Check(parsed, r)
	return r, version
}

func TestVersionCheckerAcceptsSupportedAndLegacyDeclarations(t *testing.T) {
	for _, version := range []string{"0.5", "0.6"} {
		t.Run(version, func(t *testing.T) {
			r, got := checkVersion(t, "SIMPLEX: "+version+"\n\n# title\nFUNCTION: f() → result")
			assert.Equal(t, version, got)
			assert.Empty(t, r.Errors)
			assert.Empty(t, r.Warnings)
		})
	}
}

func TestVersionCheckerAllowsUnversionedDocuments(t *testing.T) {
	r, version := checkVersion(t, "FUNCTION: f() → result")
	assert.Empty(t, version)
	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
}

func TestVersionCheckerRejectsMalformedUnsupportedAndDuplicateDeclarations(t *testing.T) {
	tests := []struct {
		name string
		spec string
		code string
	}{
		{"malformed", "SIMPLEX: v0.6\nFUNCTION: f() → result", "E090"},
		{"empty", "SIMPLEX:\nFUNCTION: f() → result", "E090"},
		{"extra content", "SIMPLEX: 0.6\nnot a comment\nFUNCTION: f() → result", "E090"},
		{"unsupported", "SIMPLEX: 0.7\nFUNCTION: f() → result", "E091"},
		{"duplicate", "SIMPLEX: 0.6\nSIMPLEX: 0.6\nFUNCTION: f() → result", "E092"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			r, _ := checkVersion(t, test.spec)
			require.NotEmpty(t, r.Errors)
			assert.Contains(t, issueCodes(r.Errors), test.code)
		})
	}
}

func TestVersionCheckerRelatesCoversToLanguageVersion(t *testing.T) {
	function := `FUNCTION: f() → result
COVERS:
  - E1 → R1`

	unversioned, _ := checkVersion(t, function)
	require.Len(t, unversioned.Warnings, 1)
	assert.Equal(t, "W090", unversioned.Warnings[0].Code)

	legacy, _ := checkVersion(t, "SIMPLEX: 0.5\n"+function)
	require.Len(t, legacy.Errors, 1)
	assert.Equal(t, "E093", legacy.Errors[0].Code)

	current, _ := checkVersion(t, "SIMPLEX: 0.6\n"+function)
	assert.Empty(t, current.Errors)
	assert.Empty(t, current.Warnings)
}

func issueCodes(issues []result.LintError) []string {
	codes := make([]string, 0, len(issues))
	for _, issue := range issues {
		codes = append(codes, issue.Code)
	}
	return codes
}
