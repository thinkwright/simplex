package checks

import (
	"fmt"
	"regexp"
	"sort"
	"strings"

	"github.com/thinkwright/simplex/lint/internal/parser"
	"github.com/thinkwright/simplex/lint/internal/result"
)

var (
	itemPrefixPattern = regexp.MustCompile(`^\[([^\]]+)\]\s*(.*)$`)
	traceIDPattern    = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9._-]*$`)
)

var exampleKinds = map[string]bool{
	"value":    true,
	"error":    true,
	"outcome":  true,
	"property": true,
}

type traceItem struct {
	id                 string
	role               string
	location           string
	functionIndex      int
	documentConstraint bool
	example            bool
	expectedCoverage   bool
	exampleKind        string
}

type traceInventory struct {
	items                []traceItem
	unlabelledByFunction map[int]map[string]int
}

type coverageRow struct {
	source   string
	targets  []string
	location string
}

// TraceabilityChecker validates author-declared identifiers and COVERS links.
// It checks reference integrity only; it never claims that a link proves
// semantic coverage.
type TraceabilityChecker struct{}

// NewTraceabilityChecker creates a deterministic traceability checker.
func NewTraceabilityChecker() *TraceabilityChecker {
	return &TraceabilityChecker{}
}

// Check validates stable identifiers and COVERS mappings and records coverage
// statistics on the result.
func (c *TraceabilityChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) {
	inventory := c.collectInventory(spec, r)
	declaredFunctions := make(map[int]bool)
	for index, fn := range spec.Functions {
		if fn.HasLandmark(parser.LandmarkCOVERS) {
			declaredFunctions[index] = true
		}
	}

	if len(inventory.items) == 0 && len(declaredFunctions) == 0 {
		return
	}

	stats := &result.TraceabilityStats{
		Declared:     len(declaredFunctions) > 0,
		Identifiers:  len(inventory.items),
		ExampleKinds: make(map[string]int),
	}
	r.Stats.Traceability = stats

	itemsByID := make(map[string]traceItem)
	broken := false
	for _, item := range inventory.items {
		if item.example {
			stats.ExampleIdentifiers++
			stats.ExampleKinds[item.exampleKind]++
		}
		if first, exists := itemsByID[item.id]; exists {
			r.AddError(
				"E100",
				fmt.Sprintf("duplicate stable identifier %q (first declared at %s)", item.id, first.location),
				item.location,
			)
			broken = true
			continue
		}
		itemsByID[item.id] = item
	}

	if !stats.Declared {
		return
	}

	linkedExamples := make(map[string]bool)
	coveredTargets := make(map[string]bool)
	uniqueLinks := make(map[string]bool)

	for functionIndex := range spec.Functions {
		if !declaredFunctions[functionIndex] {
			continue
		}
		fn := spec.Functions[functionIndex]
		covers := fn.GetLandmark(parser.LandmarkCOVERS)
		if covers == nil || strings.TrimSpace(covers.Content) == "" {
			r.AddError("E101", "COVERS landmark must contain at least one mapping", formatFunctionLocation(fn.Name))
			broken = true
			continue
		}

		rows, malformed := parseCoverageRows(fn, *covers, r)
		if malformed {
			broken = true
		}
		for _, row := range rows {
			source, exists := itemsByID[row.source]
			if !exists || !source.example || source.functionIndex != functionIndex {
				r.AddError(
					"E102",
					fmt.Sprintf("COVERS source %q must identify an EXAMPLES item in this function", row.source),
					row.location,
				)
				broken = true
				continue
			}

			for _, targetID := range row.targets {
				target, exists := itemsByID[targetID]
				if !exists {
					r.AddError("E103", fmt.Sprintf("unknown COVERS target %q", targetID), row.location)
					broken = true
					continue
				}
				if target.example {
					r.AddError("E104", fmt.Sprintf("COVERS target %q is an example, not a contract item", targetID), row.location)
					broken = true
					continue
				}
				if !target.documentConstraint && target.functionIndex != functionIndex {
					r.AddError(
						"E103",
						fmt.Sprintf("COVERS target %q belongs to another function", targetID),
						row.location,
					)
					broken = true
					continue
				}

				linkKey := row.source + "\x00" + targetID
				if !uniqueLinks[linkKey] {
					uniqueLinks[linkKey] = true
					stats.Links++
				}
				linkedExamples[row.source] = true
				coveredTargets[targetID] = true
			}
		}
	}

	for _, item := range inventory.items {
		if !declaredFunctions[item.functionIndex] {
			continue
		}
		if item.example {
			if !linkedExamples[item.id] {
				stats.UnlinkedExamples++
				r.AddWarning("W101", fmt.Sprintf("example [%s] has no declared COVERS link", item.id), item.location)
			}
			continue
		}
		if !item.expectedCoverage {
			continue
		}
		stats.CoverableItems++
		if coveredTargets[item.id] {
			stats.CoveredItems++
		} else {
			stats.UncoveredItems++
			r.AddWarning("W100", fmt.Sprintf("contract item [%s] has no declared example coverage", item.id), item.location)
		}
	}

	for functionIndex := range spec.Functions {
		if !declaredFunctions[functionIndex] {
			continue
		}
		roles := inventory.unlabelledByFunction[functionIndex]
		for _, role := range sortedTraceRoles(roles) {
			count := roles[role]
			stats.UnlabelledItems += count
			if role == "EXAMPLES" {
				stats.UnlinkedExamples += count
			} else {
				stats.CoverableItems += count
				stats.UncoveredItems += count
			}
			r.AddWarning(
				"W102",
				fmt.Sprintf("%s has %d unlabelled traceable item(s); declared traceability is partial", role, count),
				formatFunctionLocation(spec.Functions[functionIndex].Name),
			)
		}
	}

	stats.Complete = !broken && !hasTraceabilityErrors(r) && stats.UncoveredItems == 0 && stats.UnlinkedExamples == 0
}

func (c *TraceabilityChecker) collectInventory(spec *parser.ParsedSpec, r *result.LintResult) traceInventory {
	inventory := traceInventory{
		unlabelledByFunction: make(map[int]map[string]int),
	}

	for _, constraint := range spec.Constraints {
		items, _ := collectTaggedItems(
			constraint.Content,
			"CONSTRAINT",
			fmt.Sprintf("CONSTRAINT at line %d", constraint.LineNumber),
			-1,
			true,
			false,
			false,
			r,
		)
		inventory.items = append(inventory.items, items...)
	}

	roles := []struct {
		landmark string
		expected bool
	}{
		{parser.LandmarkRULES, true},
		{parser.LandmarkDONE_WHEN, true},
		{parser.LandmarkEXAMPLES, false},
		{parser.LandmarkERRORS, true},
		{parser.LandmarkNOT_ALLOWED, true},
		{parser.LandmarkREADS, true},
		{parser.LandmarkWRITES, true},
		{parser.LandmarkTRIGGERS, true},
		{parser.LandmarkHANDOFF, true},
		{parser.LandmarkUNCERTAIN, true},
	}

	for functionIndex, fn := range spec.Functions {
		inventory.unlabelledByFunction[functionIndex] = make(map[string]int)
		for _, definition := range roles {
			landmark := fn.GetLandmark(definition.landmark)
			if landmark == nil {
				continue
			}
			isExample := definition.landmark == parser.LandmarkEXAMPLES
			items, totalExpected := collectTaggedItems(
				landmark.Content,
				definition.landmark,
				formatFunctionLocation(fn.Name),
				functionIndex,
				false,
				isExample,
				definition.expected,
				r,
			)
			inventory.items = append(inventory.items, items...)
			taggedExpected := 0
			for _, item := range items {
				if item.example || item.expectedCoverage {
					taggedExpected++
				}
			}
			if totalExpected > taggedExpected {
				inventory.unlabelledByFunction[functionIndex][definition.landmark] += totalExpected - taggedExpected
			}
		}

		for _, section := range []struct {
			landmark string
			fields   map[string]string
		}{
			{parser.LandmarkBASELINE, map[string]string{"preserve": "BASELINE.preserve", "evolve": "BASELINE.evolve"}},
			{parser.LandmarkDETERMINISM, map[string]string{"stable": "DETERMINISM.stable", "vary": "DETERMINISM.vary"}},
		} {
			landmark := fn.GetLandmark(section.landmark)
			if landmark == nil {
				continue
			}
			items, totals := collectSectionItems(
				landmark.Content,
				section.fields,
				formatFunctionLocation(fn.Name),
				functionIndex,
				r,
			)
			inventory.items = append(inventory.items, items...)
			for role, total := range totals {
				tagged := 0
				for _, item := range items {
					if item.role == role {
						tagged++
					}
				}
				if total > tagged {
					inventory.unlabelledByFunction[functionIndex][role] += total - tagged
				}
			}
		}
	}

	return inventory
}

func collectTaggedItems(content, role, locationPrefix string, functionIndex int, documentConstraint, example, expected bool, r *result.LintResult) ([]traceItem, int) {
	items := make([]traceItem, 0)
	totalExpected := 0
	for lineIndex, line := range strings.Split(content, "\n") {
		candidate, isItem := itemText(line, example)
		if !isItem {
			continue
		}
		itemExpected := example || expected
		if role == parser.LandmarkERRORS && isDefaultFailure(candidate) {
			itemExpected = false
		}
		if itemExpected {
			totalExpected++
		}

		match := itemPrefixPattern.FindStringSubmatch(candidate)
		if len(match) == 0 {
			continue
		}
		id := strings.TrimSpace(match[1])
		text := strings.TrimSpace(match[2])
		location := fmt.Sprintf("%s, %s item %d", locationPrefix, role, lineIndex+1)
		if !traceIDPattern.MatchString(id) {
			r.AddError("E105", fmt.Sprintf("invalid stable identifier %q", id), location)
			continue
		}
		kind := "unclassified"
		if example {
			kind = parseExampleKind(text)
		}
		items = append(items, traceItem{
			id:                 id,
			role:               role,
			location:           location,
			functionIndex:      functionIndex,
			documentConstraint: documentConstraint,
			example:            example,
			expectedCoverage:   itemExpected && !example,
			exampleKind:        kind,
		})
	}
	return items, totalExpected
}

func collectSectionItems(content string, fields map[string]string, locationPrefix string, functionIndex int, r *result.LintResult) ([]traceItem, map[string]int) {
	items := make([]traceItem, 0)
	totals := make(map[string]int)
	currentRole := ""
	for lineIndex, line := range strings.Split(content, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if !strings.HasPrefix(trimmed, "-") {
			key, _, found := strings.Cut(trimmed, ":")
			if !found {
				continue
			}
			currentRole = fields[strings.ToLower(strings.TrimSpace(key))]
			if currentRole == "" {
				continue
			}
		}
		if currentRole == "" || !strings.HasPrefix(trimmed, "-") {
			continue
		}
		candidate := strings.TrimSpace(strings.TrimPrefix(trimmed, "-"))
		if candidate == "" {
			continue
		}
		totals[currentRole]++
		match := itemPrefixPattern.FindStringSubmatch(candidate)
		if len(match) == 0 {
			continue
		}
		id := strings.TrimSpace(match[1])
		location := fmt.Sprintf("%s, %s item %d", locationPrefix, currentRole, lineIndex+1)
		if !traceIDPattern.MatchString(id) {
			r.AddError("E105", fmt.Sprintf("invalid stable identifier %q", id), location)
			continue
		}
		items = append(items, traceItem{
			id:               id,
			role:             currentRole,
			location:         location,
			functionIndex:    functionIndex,
			expectedCoverage: true,
		})
	}
	return items, totals
}

func itemText(line string, example bool) (string, bool) {
	trimmed := strings.TrimSpace(line)
	if trimmed == "" || strings.HasPrefix(trimmed, "#") {
		return "", false
	}
	if strings.HasPrefix(trimmed, "-") {
		candidate := strings.TrimSpace(strings.TrimPrefix(trimmed, "-"))
		if example && !strings.Contains(candidate, "→") && !strings.Contains(candidate, "->") {
			return "", false
		}
		return candidate, candidate != ""
	}
	if example && (strings.Contains(trimmed, "→") || strings.Contains(trimmed, "->")) {
		return trimmed, true
	}
	return "", false
}

func isDefaultFailure(text string) bool {
	return strings.Contains(strings.ToLower(text), "any unhandled")
}

func parseExampleKind(text string) string {
	prefix, _, found := strings.Cut(text, ":")
	if !found {
		return "unclassified"
	}
	kind := strings.ToLower(strings.TrimSpace(prefix))
	if exampleKinds[kind] {
		return kind
	}
	return "unclassified"
}

func parseCoverageRows(fn parser.FunctionBlock, landmark parser.Landmark, r *result.LintResult) ([]coverageRow, bool) {
	rows := make([]coverageRow, 0)
	malformed := false
	for lineIndex, line := range strings.Split(landmark.Content, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		trimmed = strings.TrimSpace(strings.TrimPrefix(trimmed, "-"))
		location := fmt.Sprintf("%s, COVERS item %d", formatFunctionLocation(fn.Name), lineIndex+1)

		left, right, found := splitCoverageArrow(trimmed)
		if !found {
			r.AddError("E101", "COVERS item must use example-id → target-id[, target-id]", location)
			malformed = true
			continue
		}
		source := trimBrackets(strings.TrimSpace(left))
		if !traceIDPattern.MatchString(source) {
			r.AddError("E101", fmt.Sprintf("invalid COVERS source identifier %q", source), location)
			malformed = true
			continue
		}

		targets := make([]string, 0)
		validTargets := true
		for _, rawTarget := range strings.Split(right, ",") {
			target := trimBrackets(strings.TrimSpace(rawTarget))
			if !traceIDPattern.MatchString(target) {
				r.AddError("E101", fmt.Sprintf("invalid COVERS target identifier %q", target), location)
				malformed = true
				validTargets = false
				continue
			}
			targets = append(targets, target)
		}
		if !validTargets {
			continue
		}
		rows = append(rows, coverageRow{source: source, targets: targets, location: location})
	}
	return rows, malformed
}

func splitCoverageArrow(value string) (string, string, bool) {
	if left, right, found := strings.Cut(value, "→"); found {
		return left, right, true
	}
	if left, right, found := strings.Cut(value, "->"); found {
		return left, right, true
	}
	return "", "", false
}

func trimBrackets(value string) string {
	if len(value) >= 2 && strings.HasPrefix(value, "[") && strings.HasSuffix(value, "]") {
		return strings.TrimSpace(value[1 : len(value)-1])
	}
	return value
}

func sortedTraceRoles(roles map[string]int) []string {
	order := []string{
		parser.LandmarkRULES,
		parser.LandmarkDONE_WHEN,
		parser.LandmarkEXAMPLES,
		parser.LandmarkERRORS,
		"BASELINE.preserve",
		"BASELINE.evolve",
		parser.LandmarkNOT_ALLOWED,
		"DETERMINISM.stable",
		"DETERMINISM.vary",
		parser.LandmarkREADS,
		parser.LandmarkWRITES,
		parser.LandmarkTRIGGERS,
		parser.LandmarkHANDOFF,
		parser.LandmarkUNCERTAIN,
	}
	result := make([]string, 0, len(roles))
	seen := make(map[string]bool)
	for _, role := range order {
		if _, exists := roles[role]; exists {
			result = append(result, role)
			seen[role] = true
		}
	}
	extra := make([]string, 0)
	for role := range roles {
		if !seen[role] {
			extra = append(extra, role)
		}
	}
	sort.Strings(extra)
	result = append(result, extra...)
	return result
}

func hasTraceabilityErrors(r *result.LintResult) bool {
	for _, issue := range r.Errors {
		if issue.Code >= "E100" && issue.Code <= "E105" {
			return true
		}
	}
	return false
}
