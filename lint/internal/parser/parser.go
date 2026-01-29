// Package parser provides a soft parser for Simplex specification files.
// It extracts structure without enforcing strict grammar, tolerating
// formatting variations while identifying landmarks and their content.
package parser

import (
	"regexp"
	"strings"
)

// Known landmark names
const (
	// Structural landmarks
	LandmarkDATA       = "DATA"
	LandmarkCONSTRAINT = "CONSTRAINT"
	LandmarkFUNCTION   = "FUNCTION"
	LandmarkBASELINE   = "BASELINE"
	LandmarkEVAL       = "EVAL"

	// Function landmarks
	LandmarkRULES       = "RULES"
	LandmarkDONE_WHEN   = "DONE_WHEN"
	LandmarkEXAMPLES    = "EXAMPLES"
	LandmarkERRORS      = "ERRORS"
	LandmarkREADS       = "READS"
	LandmarkWRITES      = "WRITES"
	LandmarkTRIGGERS    = "TRIGGERS"
	LandmarkNOT_ALLOWED = "NOT_ALLOWED"
	LandmarkHANDOFF     = "HANDOFF"
	LandmarkUNCERTAIN   = "UNCERTAIN"
	LandmarkDETERMINISM = "DETERMINISM"
)

// StructuralLandmarks are top-level landmarks that define spec structure.
var StructuralLandmarks = map[string]bool{
	LandmarkDATA:       true,
	LandmarkCONSTRAINT: true,
	LandmarkFUNCTION:   true,
	LandmarkBASELINE:   true,
	LandmarkEVAL:       true,
}

// FunctionLandmarks are landmarks that appear within a FUNCTION block.
var FunctionLandmarks = map[string]bool{
	LandmarkRULES:       true,
	LandmarkDONE_WHEN:   true,
	LandmarkEXAMPLES:    true,
	LandmarkERRORS:      true,
	LandmarkREADS:       true,
	LandmarkWRITES:      true,
	LandmarkTRIGGERS:    true,
	LandmarkNOT_ALLOWED: true,
	LandmarkHANDOFF:     true,
	LandmarkUNCERTAIN:   true,
	LandmarkBASELINE:    true,
	LandmarkEVAL:        true,
	LandmarkDETERMINISM: true,
}

// RequiredFunctionLandmarks must be present in every FUNCTION block.
var RequiredFunctionLandmarks = map[string]bool{
	LandmarkRULES:     true,
	LandmarkDONE_WHEN: true,
	LandmarkEXAMPLES:  true,
	LandmarkERRORS:    true,
}

// Landmark represents a parsed landmark block.
type Landmark struct {
	Name       string // e.g., "FUNCTION", "RULES"
	Content    string // raw content after the landmark declaration
	LineNumber int    // 1-based line number where landmark starts
}

// FunctionBlock represents a parsed FUNCTION with its nested landmarks.
type FunctionBlock struct {
	Signature  string              // e.g., "filter_policies(policies, ids, tags) → filtered list"
	Name       string              // e.g., "filter_policies"
	Inputs     []string            // e.g., ["policies", "ids", "tags"]
	ReturnType string              // e.g., "filtered list"
	Landmarks  map[string]Landmark // nested landmarks (RULES, DONE_WHEN, etc.)
	LineNumber int                 // 1-based line number where FUNCTION starts
}

// ParsedSpec represents the fully parsed specification.
type ParsedSpec struct {
	Functions     []FunctionBlock
	DataBlocks    []Landmark
	Constraints   []Landmark
	RawText       string
	ParseWarnings []string // non-fatal parse issues
}

// landmarkMatch represents a regex match for a landmark.
type landmarkMatch struct {
	name       string
	content    string // content on same line as landmark
	lineNumber int
	startIndex int
	endIndex   int
}

// Parser provides methods for parsing Simplex specifications.
type Parser struct {
	// landmarkPattern matches landmarks: ALL_CAPS followed by colon
	landmarkPattern *regexp.Regexp
	// functionSigPattern extracts function name, inputs, and return type
	functionSigPattern *regexp.Regexp
}

// NewParser creates a new Parser instance.
func NewParser() *Parser {
	return &Parser{
		// Match landmarks: word boundary, ALL_CAPS (with underscores), colon
		// Captures: (1) landmark name, (2) rest of line after colon
		landmarkPattern: regexp.MustCompile(`(?m)^([A-Z][A-Z_]+):\s*(.*)$`),
		// Match function signature: name(args) → return_type
		// Handles both → and -> for arrow
		functionSigPattern: regexp.MustCompile(`^(\w+)\s*\(([^)]*)\)\s*(?:→|->)\s*(.+)$`),
	}
}

// Parse parses a Simplex specification text and returns a ParsedSpec.
func (p *Parser) Parse(text string) *ParsedSpec {
	spec := &ParsedSpec{
		Functions:     []FunctionBlock{},
		DataBlocks:    []Landmark{},
		Constraints:   []Landmark{},
		RawText:       text,
		ParseWarnings: []string{},
	}

	// Find all landmark matches
	matches := p.findLandmarks(text)
	if len(matches) == 0 {
		return spec
	}

	// Extract content for each landmark (content goes until next landmark)
	landmarks := p.extractLandmarkContent(text, matches)

	// Organize landmarks into structure
	p.organizeLandmarks(spec, landmarks)

	return spec
}

// findLandmarks finds all landmark declarations in the text.
func (p *Parser) findLandmarks(text string) []landmarkMatch {
	var matches []landmarkMatch

	// Find all matches
	allMatches := p.landmarkPattern.FindAllStringSubmatchIndex(text, -1)

	for _, m := range allMatches {
		if len(m) < 6 {
			continue
		}

		name := text[m[2]:m[3]]
		content := ""
		if m[4] >= 0 && m[5] >= 0 {
			content = text[m[4]:m[5]]
		}

		// Calculate line number
		lineNumber := strings.Count(text[:m[0]], "\n") + 1

		matches = append(matches, landmarkMatch{
			name:       name,
			content:    strings.TrimSpace(content),
			lineNumber: lineNumber,
			startIndex: m[0],
			endIndex:   m[1],
		})
	}

	return matches
}

// extractLandmarkContent extracts full content for each landmark.
func (p *Parser) extractLandmarkContent(text string, matches []landmarkMatch) []Landmark {
	var landmarks []Landmark

	for i, m := range matches {
		// Content starts after the landmark line
		contentStart := m.endIndex

		// Content ends at next landmark or EOF
		var contentEnd int
		if i+1 < len(matches) {
			contentEnd = matches[i+1].startIndex
		} else {
			contentEnd = len(text)
		}

		// Extract and clean content
		content := text[contentStart:contentEnd]
		content = strings.TrimSpace(content)

		// If there was content on the landmark line, prepend it
		if m.content != "" {
			if content != "" {
				content = m.content + "\n" + content
			} else {
				content = m.content
			}
		}

		landmarks = append(landmarks, Landmark{
			Name:       m.name,
			Content:    content,
			LineNumber: m.lineNumber,
		})
	}

	return landmarks
}

// organizeLandmarks organizes landmarks into the spec structure.
func (p *Parser) organizeLandmarks(spec *ParsedSpec, landmarks []Landmark) {
	var currentFunction *FunctionBlock

	for _, lm := range landmarks {
		switch {
		case lm.Name == LandmarkFUNCTION:
			// Start a new function block
			fn := p.parseFunctionBlock(lm)
			spec.Functions = append(spec.Functions, fn)
			currentFunction = &spec.Functions[len(spec.Functions)-1]

		case lm.Name == LandmarkDATA:
			spec.DataBlocks = append(spec.DataBlocks, lm)
			currentFunction = nil // DATA is structural, ends current function context

		case lm.Name == LandmarkCONSTRAINT:
			spec.Constraints = append(spec.Constraints, lm)
			currentFunction = nil // CONSTRAINT is structural, ends current function context

		case FunctionLandmarks[lm.Name]:
			// This is a function-level landmark
			if currentFunction != nil {
				currentFunction.Landmarks[lm.Name] = lm
			} else {
				// Function landmark without parent FUNCTION - add warning
				spec.ParseWarnings = append(spec.ParseWarnings,
					"landmark "+lm.Name+" at line "+string(rune(lm.LineNumber+'0'))+" appears outside FUNCTION block")
			}

		default:
			// Unrecognized landmark - add warning but don't fail
			spec.ParseWarnings = append(spec.ParseWarnings,
				"unrecognized landmark: "+lm.Name+" at line "+string(rune(lm.LineNumber+'0')))
		}
	}
}

// parseFunctionBlock parses a FUNCTION landmark into a FunctionBlock.
func (p *Parser) parseFunctionBlock(lm Landmark) FunctionBlock {
	fb := FunctionBlock{
		Signature:  lm.Content,
		LineNumber: lm.LineNumber,
		Landmarks:  make(map[string]Landmark),
	}

	// Try to parse the signature
	// First line of content should be the signature
	sigLine := lm.Content
	if idx := strings.Index(lm.Content, "\n"); idx >= 0 {
		sigLine = lm.Content[:idx]
	}
	sigLine = strings.TrimSpace(sigLine)
	fb.Signature = sigLine

	matches := p.functionSigPattern.FindStringSubmatch(sigLine)
	if len(matches) >= 4 {
		fb.Name = matches[1]
		fb.ReturnType = strings.TrimSpace(matches[3])

		// Parse inputs
		inputStr := strings.TrimSpace(matches[2])
		if inputStr != "" {
			inputs := strings.Split(inputStr, ",")
			for _, inp := range inputs {
				inp = strings.TrimSpace(inp)
				if inp != "" {
					fb.Inputs = append(fb.Inputs, inp)
				}
			}
		}
	} else {
		// Couldn't parse signature - use the whole line as name
		fb.Name = sigLine
	}

	return fb
}

// GetFunctionByName returns a function by name, or nil if not found.
func (spec *ParsedSpec) GetFunctionByName(name string) *FunctionBlock {
	for i := range spec.Functions {
		if spec.Functions[i].Name == name {
			return &spec.Functions[i]
		}
	}
	return nil
}

// HasLandmark checks if a function has a specific landmark.
func (fb *FunctionBlock) HasLandmark(name string) bool {
	_, ok := fb.Landmarks[name]
	return ok
}

// GetLandmark returns a landmark by name, or nil if not found.
func (fb *FunctionBlock) GetLandmark(name string) *Landmark {
	if lm, ok := fb.Landmarks[name]; ok {
		return &lm
	}
	return nil
}

// GetRules returns the RULES landmark content, or empty string if not found.
func (fb *FunctionBlock) GetRules() string {
	if lm := fb.GetLandmark(LandmarkRULES); lm != nil {
		return lm.Content
	}
	return ""
}

// GetExamples returns the EXAMPLES landmark content, or empty string if not found.
func (fb *FunctionBlock) GetExamples() string {
	if lm := fb.GetLandmark(LandmarkEXAMPLES); lm != nil {
		return lm.Content
	}
	return ""
}

// GetDoneWhen returns the DONE_WHEN landmark content, or empty string if not found.
func (fb *FunctionBlock) GetDoneWhen() string {
	if lm := fb.GetLandmark(LandmarkDONE_WHEN); lm != nil {
		return lm.Content
	}
	return ""
}

// GetErrors returns the ERRORS landmark content, or empty string if not found.
func (fb *FunctionBlock) GetErrors() string {
	if lm := fb.GetLandmark(LandmarkERRORS); lm != nil {
		return lm.Content
	}
	return ""
}

// GetBaseline returns the BASELINE landmark content, or empty string if not found.
func (fb *FunctionBlock) GetBaseline() string {
	if lm := fb.GetLandmark(LandmarkBASELINE); lm != nil {
		return lm.Content
	}
	return ""
}

// GetEval returns the EVAL landmark content, or empty string if not found.
func (fb *FunctionBlock) GetEval() string {
	if lm := fb.GetLandmark(LandmarkEVAL); lm != nil {
		return lm.Content
	}
	return ""
}

// HasBaseline checks if the function has a BASELINE landmark.
func (fb *FunctionBlock) HasBaseline() bool {
	return fb.HasLandmark(LandmarkBASELINE)
}

// HasEval checks if the function has an EVAL landmark.
func (fb *FunctionBlock) HasEval() bool {
	return fb.HasLandmark(LandmarkEVAL)
}

// GetDeterminism returns the DETERMINISM landmark content, or empty string if not found.
func (fb *FunctionBlock) GetDeterminism() string {
	if lm := fb.GetLandmark(LandmarkDETERMINISM); lm != nil {
		return lm.Content
	}
	return ""
}

// HasDeterminism checks if the function has a DETERMINISM landmark.
func (fb *FunctionBlock) HasDeterminism() bool {
	return fb.HasLandmark(LandmarkDETERMINISM)
}
