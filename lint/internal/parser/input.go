package parser

import (
	"path/filepath"
	"strconv"
	"strings"
)

// InputMode controls which parts of an input document are parsed as Simplex.
type InputMode string

const (
	// InputModeRaw parses the entire input while treating fenced blocks as literals.
	InputModeRaw InputMode = "raw"
	// InputModeMarkdown parses only fenced blocks whose first info word is simplex.
	InputModeMarkdown InputMode = "markdown"
	// InputModeExtracted parses a caller-extracted Simplex block.
	InputModeExtracted InputMode = "extracted"
	// InputModeAuto selects a mode from the source name and live Markdown fences.
	InputModeAuto InputMode = "auto"
)

// ParseOptions configures how a source document is interpreted.
type ParseOptions struct {
	Mode       InputMode
	SourceName string
	StartLine  int
}

func (o ParseOptions) startLine() int {
	if o.StartLine > 0 {
		return o.StartLine
	}
	return 1
}

type inputRegion struct {
	detectionText string
	startIndex    int
	endIndex      int
	startLine     int
}

type sourceLine struct {
	text       string
	startIndex int
	endIndex   int
	nextIndex  int
	number     int
}

type fenceMarker struct {
	character byte
	length    int
	info      string
}

type openFence struct {
	marker       fenceMarker
	live         bool
	contentStart int
	contentLine  int
	openingLine  int
}

func resolveInputMode(text string, options ParseOptions) (InputMode, []string) {
	mode := options.Mode
	if mode == "" {
		mode = InputModeRaw
	}

	switch mode {
	case InputModeRaw, InputModeMarkdown, InputModeExtracted:
		return mode, nil
	case InputModeAuto:
		return resolveAutoInputMode(text, options.SourceName)
	default:
		return InputModeRaw, []string{"unrecognized input mode " + string(mode) + "; using raw mode"}
	}
}

func resolveAutoInputMode(text, sourceName string) (InputMode, []string) {
	if sourceName == "<stdin>" {
		return InputModeExtracted, nil
	}

	extension := strings.ToLower(filepath.Ext(sourceName))
	if extension == ".md" || extension == ".markdown" {
		_, _, liveFenceCount := markdownInputRegions(text, 1)
		if liveFenceCount > 0 {
			return InputModeMarkdown, nil
		}
		return InputModeRaw, []string{
			"legacy raw Markdown input: no fenced block labeled simplex was found",
		}
	}

	return InputModeRaw, nil
}

func selectInputRegions(text string, mode InputMode, startLine int) ([]inputRegion, []string) {
	switch mode {
	case InputModeMarkdown:
		regions, warnings, _ := markdownInputRegions(text, startLine)
		return regions, warnings
	case InputModeExtracted, InputModeRaw:
		return []inputRegion{rawInputRegion(text, startLine)}, nil
	default:
		return []inputRegion{rawInputRegion(text, startLine)}, nil
	}
}

func rawInputRegion(text string, startLine int) inputRegion {
	return inputRegion{
		detectionText: maskFencedContent(text),
		startIndex:    0,
		endIndex:      len(text),
		startLine:     startLine,
	}
}

func markdownInputRegions(text string, startLine int) ([]inputRegion, []string, int) {
	var regions []inputRegion
	var warnings []string
	var current *openFence
	liveFenceCount := 0

	for _, line := range sourceLines(text) {
		if current == nil {
			marker, ok := parseFenceOpening(line.text)
			if !ok {
				continue
			}

			live := isSimplexFence(marker.info)
			if live {
				liveFenceCount++
			}
			current = &openFence{
				marker:       marker,
				live:         live,
				contentStart: line.nextIndex,
				contentLine:  startLine + line.number,
				openingLine:  startLine + line.number - 1,
			}
			continue
		}

		if !isFenceClosing(line.text, current.marker) {
			continue
		}

		if current.live {
			regions = append(regions, makeInputRegion(
				text,
				current.contentStart,
				line.startIndex,
				current.contentLine,
			))
		}
		current = nil
	}

	if current != nil && current.live {
		regions = append(regions, makeInputRegion(
			text,
			current.contentStart,
			len(text),
			current.contentLine,
		))
		warnings = append(warnings,
			"unterminated Simplex fence opened at line "+strconv.Itoa(current.openingLine)+"; parsing through end of input")
	}

	return regions, warnings, liveFenceCount
}

func makeInputRegion(text string, startIndex, endIndex, startLine int) inputRegion {
	content := text[startIndex:endIndex]
	return inputRegion{
		detectionText: maskFencedContent(content),
		startIndex:    startIndex,
		endIndex:      endIndex,
		startLine:     startLine,
	}
}

func maskFencedContent(text string) string {
	masked := []byte(text)
	var current *fenceMarker

	for _, line := range sourceLines(text) {
		if current == nil {
			marker, ok := parseFenceOpening(line.text)
			if ok {
				current = &marker
			}
			continue
		}

		if isFenceClosing(line.text, *current) {
			current = nil
			continue
		}

		for index := line.startIndex; index < line.endIndex; index++ {
			masked[index] = ' '
		}
	}

	return string(masked)
}

func sourceLines(text string) []sourceLine {
	lines := make([]sourceLine, 0, strings.Count(text, "\n")+1)
	lineNumber := 1

	for start := 0; start < len(text); lineNumber++ {
		relativeEnd := strings.IndexByte(text[start:], '\n')
		end := len(text)
		next := len(text)
		if relativeEnd >= 0 {
			end = start + relativeEnd
			next = end + 1
		}

		lineText := text[start:end]
		lineText = strings.TrimSuffix(lineText, "\r")
		lines = append(lines, sourceLine{
			text:       lineText,
			startIndex: start,
			endIndex:   end,
			nextIndex:  next,
			number:     lineNumber,
		})

		start = next
	}

	return lines
}

func parseFenceOpening(line string) (fenceMarker, bool) {
	trimmed := strings.TrimLeft(line, " \t")
	if len(trimmed) < 3 || (trimmed[0] != '`' && trimmed[0] != '~') {
		return fenceMarker{}, false
	}

	character := trimmed[0]
	length := 0
	for length < len(trimmed) && trimmed[length] == character {
		length++
	}
	if length < 3 {
		return fenceMarker{}, false
	}

	info := strings.TrimSpace(trimmed[length:])
	if character == '`' && strings.Contains(info, "`") {
		return fenceMarker{}, false
	}

	return fenceMarker{character: character, length: length, info: info}, true
}

func isFenceClosing(line string, marker fenceMarker) bool {
	trimmed := strings.TrimLeft(line, " \t")
	if len(trimmed) < marker.length || trimmed[0] != marker.character {
		return false
	}

	length := 0
	for length < len(trimmed) && trimmed[length] == marker.character {
		length++
	}
	return length >= marker.length && strings.TrimSpace(trimmed[length:]) == ""
}

func isSimplexFence(info string) bool {
	fields := strings.Fields(info)
	return len(fields) > 0 && strings.EqualFold(fields[0], "simplex")
}
