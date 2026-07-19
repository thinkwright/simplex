// Package main provides the CLI entry point for simplex-lint.
package main

import (
	"fmt"
	"io"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/thinkwright/simplex/lint"
	"github.com/thinkwright/simplex/lint/internal/result"
)

// version is set at build time via ldflags
var version = "dev"

// CLI flags
var (
	flagFormat    string
	flagMaxRules  int
	flagMaxInputs int
	flagInputMode string
)

func main() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(2)
	}
}

var rootCmd = &cobra.Command{
	Use:   "simplex-lint [files...]",
	Short: "Lint Simplex specification files",
	Long: `simplex-lint validates Simplex specification files for structural
correctness, complexity limits, evolution metadata, and determinism declarations.

Checks are deterministic. The linter does not execute examples or perform
LLM-based semantic validation.

Examples:
  simplex-lint spec.md
  simplex-lint specs/*.md
  simplex-lint --format json spec.md
  cat spec.md | simplex-lint -`,
	Args:    cobra.MinimumNArgs(0),
	Version: version,
	RunE:    runLint,
}

func init() {
	// Output options
	rootCmd.Flags().StringVar(&flagFormat, "format", "text", "Output format: text, json")
	rootCmd.Flags().StringVar(&flagInputMode, "input-mode", "auto", "Input interpretation: auto, raw, markdown, extracted")

	// Threshold options
	rootCmd.Flags().IntVar(&flagMaxRules, "max-rules", 15, "Override max RULES items (positive integer)")
	rootCmd.Flags().IntVar(&flagMaxInputs, "max-inputs", 6, "Override max function inputs (positive integer)")
}

func runLint(cmd *cobra.Command, args []string) error {
	if os.Getenv("NO_COLOR") != "" {
		color.NoColor = true
	}

	if err := validateCLIOptions(); err != nil {
		return err
	}

	inputMode, err := parseInputMode(flagInputMode)
	if err != nil {
		return err
	}

	// Determine input sources
	var inputs []InputSource

	if len(args) == 0 || (len(args) == 1 && args[0] == "-") {
		// Read from stdin
		content, err := io.ReadAll(os.Stdin)
		if err != nil {
			return fmt.Errorf("failed to read stdin: %w", err)
		}
		inputs = append(inputs, InputSource{Name: "<stdin>", Content: string(content)})
	} else {
		// Read from files
		for _, path := range args {
			content, err := os.ReadFile(path)
			if err != nil {
				return fmt.Errorf("failed to read %s: %w", path, err)
			}
			inputs = append(inputs, InputSource{Name: path, Content: string(content)})
		}
	}

	// Create linter with current configuration
	linter := lint.New(lint.Config{
		MaxRules:  flagMaxRules,
		MaxInputs: flagMaxInputs,
		InputMode: inputMode,
	})

	// Process each input
	var results []result.LintResult
	for _, input := range inputs {
		r := linter.Lint(input.Name, input.Content)
		results = append(results, *r)
	}

	// Output results
	if len(results) == 1 {
		outputSingle(results[0], flagFormat)
	} else {
		outputMultiple(results, flagFormat)
	}

	// Exit code based on validity
	for _, r := range results {
		if !r.Valid {
			os.Exit(1)
		}
	}

	return nil
}

func validateCLIOptions() error {
	if flagFormat != "text" && flagFormat != "json" {
		return fmt.Errorf("invalid --format %q: expected text or json", flagFormat)
	}
	if flagMaxRules <= 0 {
		return fmt.Errorf("invalid --max-rules %d: expected a positive integer", flagMaxRules)
	}
	if flagMaxInputs <= 0 {
		return fmt.Errorf("invalid --max-inputs %d: expected a positive integer", flagMaxInputs)
	}
	return nil
}

func parseInputMode(value string) (lint.InputMode, error) {
	mode := lint.InputMode(value)
	switch mode {
	case lint.InputModeAuto, lint.InputModeRaw, lint.InputModeMarkdown, lint.InputModeExtracted:
		return mode, nil
	default:
		return "", fmt.Errorf("invalid --input-mode %q: expected auto, raw, markdown, or extracted", value)
	}
}

// InputSource represents a spec to be linted.
type InputSource struct {
	Name    string
	Content string
}

func outputSingle(r result.LintResult, format string) {
	switch format {
	case "json":
		data, _ := r.ToJSON()
		fmt.Println(string(data))
	default:
		fmt.Print(r.ToText())
	}
}

func outputMultiple(results []result.LintResult, format string) {
	m := result.NewMultiResult(results)

	switch format {
	case "json":
		data, _ := m.ToJSON()
		fmt.Println(string(data))
	default:
		fmt.Print(m.ToText())
	}
}
