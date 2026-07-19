package checks

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/thinkwright/simplex/lint/internal/parser"
	"github.com/thinkwright/simplex/lint/internal/result"
)

// SupportedSpecVersion is the newest Simplex language version understood by
// this linter. It is intentionally separate from the binary release version.
const SupportedSpecVersion = "0.6"

var versionPattern = regexp.MustCompile(`^[0-9]+\.[0-9]+$`)

// VersionChecker validates an optional SIMPLEX language declaration.
type VersionChecker struct{}

// NewVersionChecker creates a deterministic language-version checker.
func NewVersionChecker() *VersionChecker {
	return &VersionChecker{}
}

// Check validates version declarations and returns the declared version, or
// an empty string for backward-compatible unversioned documents.
func (c *VersionChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) string {
	declarations := spec.SimplexDeclarations
	if len(declarations) == 0 {
		c.checkVersionedFeatures(spec, "", r)
		return ""
	}

	if len(declarations) > 1 {
		for _, declaration := range declarations[1:] {
			r.AddError(
				"E092",
				"SIMPLEX language version may be declared only once",
				fmt.Sprintf("line %d", declaration.LineNumber),
			)
		}
	}

	declaration := declarations[0]
	version, extraContent := declaredVersionValue(declaration.Content)
	if extraContent {
		r.AddError(
			"E090",
			"SIMPLEX declaration must contain only one major.minor version",
			fmt.Sprintf("line %d", declaration.LineNumber),
		)
	}
	if !versionPattern.MatchString(version) {
		r.AddError(
			"E090",
			"SIMPLEX declaration must contain one major.minor version such as 0.6",
			fmt.Sprintf("line %d", declaration.LineNumber),
		)
		return version
	}

	if version != "0.5" && version != SupportedSpecVersion {
		r.AddError(
			"E091",
			fmt.Sprintf("SIMPLEX version %s is not supported; this linter supports 0.5 and %s", version, SupportedSpecVersion),
			fmt.Sprintf("line %d", declaration.LineNumber),
		)
	}

	c.checkVersionedFeatures(spec, version, r)
	return version
}

func declaredVersionValue(content string) (string, bool) {
	version := ""
	extra := false
	for _, line := range strings.Split(content, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if version == "" {
			version = trimmed
		} else {
			extra = true
		}
	}
	return version, extra
}

func (c *VersionChecker) checkVersionedFeatures(spec *parser.ParsedSpec, version string, r *result.LintResult) {
	hasCovers := false
	for _, fn := range spec.Functions {
		if fn.HasLandmark(parser.LandmarkCOVERS) {
			hasCovers = true
			break
		}
	}
	if !hasCovers {
		return
	}

	switch version {
	case "":
		r.AddWarning(
			"W090",
			"COVERS uses v0.6 semantics; declare SIMPLEX: 0.6 for version-aware tooling",
			"spec",
		)
	case "0.5":
		r.AddError(
			"E093",
			"COVERS is not defined by declared SIMPLEX version 0.5",
			"spec",
		)
	}
}
