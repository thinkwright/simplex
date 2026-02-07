// Package main provides the CLI entry point for simplex-lint.
package main

import (
	"fmt"
	"io"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/brannn/simplex/lint/internal/checks"
	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// version is set at build time via ldflags
var version = "dev"

// CLI flags
var (
	flagFormat    string
	flagFix       bool
	flagNoLLM     bool
	flagProvider  string
	flagModel     string
	flagAPIKey    string
	flagAPIBase   string
	flagMaxRules  int
	flagMaxInputs int
	flagCache     bool
	flagNoCache   bool
	flagVerbose   bool
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
correctness, complexity limits, and semantic clarity.

It combines deterministic checks (structural, complexity) with optional
LLM-based semantic validation (coverage, observability, behavioral).

Examples:
  simplex-lint spec.md
  simplex-lint specs/*.md
  simplex-lint --format json spec.md
  simplex-lint --no-llm spec.md
  cat spec.md | simplex-lint -`,
	Args:    cobra.MinimumNArgs(0),
	Version: version,
	RunE:    runLint,
}

func init() {
	// Output options
	rootCmd.Flags().StringVar(&flagFormat, "format", "text", "Output format: text, json")
	rootCmd.Flags().BoolVar(&flagVerbose, "verbose", false, "Show detailed check progress")

	// Fix options
	rootCmd.Flags().BoolVar(&flagFix, "fix", false, "Auto-fix simple issues (disabled by default)")

	// LLM options
	rootCmd.Flags().BoolVar(&flagNoLLM, "no-llm", false, "Skip semantic checks (offline mode)")
	rootCmd.Flags().StringVar(&flagProvider, "provider", "", "LLM provider: anthropic, openai, glm, minimax, ollama")
	rootCmd.Flags().StringVar(&flagModel, "model", "", "Model identifier (provider-specific)")
	rootCmd.Flags().StringVar(&flagAPIKey, "api-key", "", "API key (or use environment variable)")
	rootCmd.Flags().StringVar(&flagAPIBase, "api-base", "", "Base URL for self-hosted models")

	// Threshold options
	rootCmd.Flags().IntVar(&flagMaxRules, "max-rules", 15, "Override max RULES items")
	rootCmd.Flags().IntVar(&flagMaxInputs, "max-inputs", 6, "Override max function inputs")

	// Cache options
	rootCmd.Flags().BoolVar(&flagCache, "cache", true, "Enable result caching")
	rootCmd.Flags().BoolVar(&flagNoCache, "no-cache", false, "Disable result caching")
}

func runLint(cmd *cobra.Command, args []string) error {
	// Apply env var defaults now that cobra has parsed flags
	applyEnvDefaults()

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
	linter := NewLinter(LinterConfig{
		MaxRules:  flagMaxRules,
		MaxInputs: flagMaxInputs,
		NoLLM:     flagNoLLM,
		Verbose:   flagVerbose,
	})

	// Process each input
	var results []result.LintResult
	for _, input := range inputs {
		r := linter.Lint(input)
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

// InputSource represents a spec to be linted.
type InputSource struct {
	Name    string
	Content string
}

// LinterConfig holds configuration for the linter.
type LinterConfig struct {
	MaxRules  int
	MaxInputs int
	NoLLM     bool
	Verbose   bool
}

// Linter performs linting on Simplex specifications.
type Linter struct {
	parser             *parser.Parser
	structuralChecker  *checks.StructuralChecker
	complexityChecker  *checks.ComplexityChecker
	evolutionChecker   *checks.EvolutionChecker
	determinismChecker *checks.DeterminismChecker
	config             LinterConfig
}

// NewLinter creates a new Linter with the given configuration.
func NewLinter(config LinterConfig) *Linter {
	complexityConfig := checks.DefaultComplexityConfig()
	if config.MaxRules > 0 {
		complexityConfig.MaxRules = config.MaxRules
	}
	if config.MaxInputs > 0 {
		complexityConfig.MaxInputs = config.MaxInputs
	}

	return &Linter{
		parser:             parser.NewParser(),
		structuralChecker:  checks.NewStructuralChecker(),
		complexityChecker:  checks.NewComplexityCheckerWithConfig(complexityConfig),
		evolutionChecker:   checks.NewEvolutionChecker(),
		determinismChecker: checks.NewDeterminismChecker(),
		config:             config,
	}
}

// Lint performs all linting checks on the input and returns a result.
func (l *Linter) Lint(input InputSource) *result.LintResult {
	r := result.NewLintResult(input.Name)

	// Parse the spec
	spec := l.parser.Parse(input.Content)

	// Add any parse warnings
	for _, w := range spec.ParseWarnings {
		r.AddWarning("W001", w, "parse")
	}

	// Run all checkers (each handles empty function lists internally)
	l.structuralChecker.Check(spec, r)
	l.complexityChecker.Check(spec, r)
	l.evolutionChecker.Check(spec, r)
	l.determinismChecker.Check(spec, r)

	// Update stats
	r.Stats.Functions = len(spec.Functions)
	r.Stats.Examples = l.countTotalExamples(spec)
	r.Stats.Branches = l.countTotalBranches(spec)

	// Calculate coverage percent if we have branches
	if r.Stats.Branches > 0 {
		r.Stats.CoveragePercent = float64(r.Stats.Examples) / float64(r.Stats.Branches) * 100
	}

	// Semantic checks (if LLM enabled)
	if !l.config.NoLLM {
		// TODO: Implement LLM-based semantic checks in Phase 3/4
		if l.config.Verbose {
			fmt.Fprintln(os.Stderr, "Note: Semantic checks not yet implemented")
		}
	}

	return r
}

// countTotalExamples counts all examples across all functions.
func (l *Linter) countTotalExamples(spec *parser.ParsedSpec) int {
	total := 0
	for _, fn := range spec.Functions {
		if ex := fn.GetExamples(); ex != "" {
			total += checks.CountExamples(ex)
		}
	}
	return total
}

// countTotalBranches counts all branches across all functions.
func (l *Linter) countTotalBranches(spec *parser.ParsedSpec) int {
	total := 0
	for _, fn := range spec.Functions {
		if rules := fn.GetRules(); rules != "" {
			total += checks.CountBranches(rules)
		}
	}
	return total
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

// applyEnvDefaults fills in flag values from environment variables
// when the user didn't provide them on the command line.
// Called inside RunE after cobra has parsed flags.
func applyEnvDefaults() {
	if flagProvider == "" {
		if v := os.Getenv("SIMPLEX_LINT_PROVIDER"); v != "" {
			flagProvider = v
		}
	}
	if flagModel == "" {
		if v := os.Getenv("SIMPLEX_LINT_MODEL"); v != "" {
			flagModel = v
		}
	}
	if os.Getenv("NO_COLOR") != "" {
		color.NoColor = true
	}
}
