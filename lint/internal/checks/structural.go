// Package checks provides linting checks for Simplex specifications.
package checks

import (
	"fmt"

	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// StructuralChecker performs structural validation of Simplex specs.
type StructuralChecker struct{}

// NewStructuralChecker creates a new StructuralChecker.
func NewStructuralChecker() *StructuralChecker {
	return &StructuralChecker{}
}

// Check performs all structural checks on the parsed spec.
func (c *StructuralChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) {
	c.checkFunctionExists(spec, r)
	if len(spec.Functions) == 0 {
		return // No point checking function landmarks if no functions exist
	}
	c.checkRequiredLandmarks(spec, r)
	c.checkDataReferences(spec, r)
}

// checkFunctionExists verifies at least one FUNCTION block exists.
// Error E001: No FUNCTION block found
func (c *StructuralChecker) checkFunctionExists(spec *parser.ParsedSpec, r *result.LintResult) {
	if len(spec.Functions) == 0 {
		r.AddError("E001", "No FUNCTION block found", "spec")
	}
}

// checkRequiredLandmarks verifies each function has all required landmarks.
// Error E002: FUNCTION missing RULES
// Error E003: FUNCTION missing DONE_WHEN
// Error E004: FUNCTION missing EXAMPLES
// Error E005: FUNCTION missing ERRORS
func (c *StructuralChecker) checkRequiredLandmarks(spec *parser.ParsedSpec, r *result.LintResult) {
	for _, fn := range spec.Functions {
		loc := formatFunctionLocation(fn.Name)

		if !fn.HasLandmark(parser.LandmarkRULES) {
			r.AddError("E002", "FUNCTION missing RULES landmark", loc)
		}

		if !fn.HasLandmark(parser.LandmarkDONE_WHEN) {
			r.AddError("E003", "FUNCTION missing DONE_WHEN landmark", loc)
		}

		if !fn.HasLandmark(parser.LandmarkEXAMPLES) {
			r.AddError("E004", "FUNCTION missing EXAMPLES landmark", loc)
		}

		if !fn.HasLandmark(parser.LandmarkERRORS) {
			r.AddErrorWithSuggestion(
				"E005",
				"FUNCTION missing ERRORS landmark",
				loc,
				"Add ERRORS: block with at least: - any unhandled condition → fail with descriptive message",
				true,
			)
		}
	}
}

// checkDataReferences verifies that referenced DATA types are defined.
// Error E006: DATA type referenced but not defined
func (c *StructuralChecker) checkDataReferences(spec *parser.ParsedSpec, r *result.LintResult) {
	// Build set of defined DATA types
	definedTypes := make(map[string]bool)
	for _, data := range spec.DataBlocks {
		// DATA block content starts with the type name
		typeName := extractTypeName(data.Content)
		if typeName != "" {
			definedTypes[typeName] = true
		}
	}

	// Check function signatures for type references
	for _, fn := range spec.Functions {
		// Check return type
		if fn.ReturnType != "" {
			checkTypeReference(fn.ReturnType, definedTypes, fn.Name, r, spec)
		}
	}
}

// extractTypeName extracts the type name from DATA block content.
// DATA content format: "TypeName\n  field: type\n  ..."
func extractTypeName(content string) string {
	// First line or first word is the type name
	for i, ch := range content {
		if ch == '\n' || ch == ' ' || ch == '\t' {
			if i > 0 {
				return content[:i]
			}
			break
		}
	}
	// If no whitespace found, the whole content might be the name
	if len(content) > 0 && len(content) < 100 {
		return content
	}
	return ""
}

// checkTypeReference checks if a type reference is valid.
func checkTypeReference(typeName string, definedTypes map[string]bool, funcName string, r *result.LintResult, spec *parser.ParsedSpec) {
	// Skip common built-in/primitive types
	builtins := map[string]bool{
		"string": true, "int": true, "integer": true, "number": true,
		"bool": true, "boolean": true, "float": true, "double": true,
		"list": true, "array": true, "map": true, "dict": true,
		"any": true, "void": true, "none": true, "null": true,
		"result": true, "output": true, "sum": true, "filtered": true,
		"valid": true, "issues": true, "timestamp": true, "id": true,
	}

	// Normalize: lowercase, strip "list of", etc.
	normalized := normalizeTypeName(typeName)

	if builtins[normalized] {
		return
	}

	// Check if it's a defined DATA type
	if definedTypes[normalized] || definedTypes[typeName] {
		return
	}

	// Only report if we have DATA blocks defined (otherwise user isn't using typed specs)
	if len(spec.DataBlocks) > 0 {
		r.AddWarning("E006",
			fmt.Sprintf("Return type '%s' may reference undefined DATA type", typeName),
			formatFunctionLocation(funcName))
	}
}

// normalizeTypeName normalizes a type name for comparison.
func normalizeTypeName(name string) string {
	// Convert to lowercase
	result := make([]byte, 0, len(name))
	for i := 0; i < len(name); i++ {
		ch := name[i]
		if ch >= 'A' && ch <= 'Z' {
			result = append(result, ch+32) // lowercase
		} else if ch >= 'a' && ch <= 'z' {
			result = append(result, ch)
		} else if ch == ' ' || ch == '_' {
			// Skip spaces and underscores
		} else {
			result = append(result, ch)
		}
	}

	normalized := string(result)

	// Strip common prefixes
	prefixes := []string{"listof", "arrayof", "setof"}
	for _, prefix := range prefixes {
		if len(normalized) > len(prefix) && normalized[:len(prefix)] == prefix {
			return normalized[len(prefix):]
		}
	}

	return normalized
}

// formatFunctionLocation formats a function name for error location.
func formatFunctionLocation(name string) string {
	if name == "" {
		return "FUNCTION (unnamed)"
	}
	return fmt.Sprintf("FUNCTION %s", name)
}
