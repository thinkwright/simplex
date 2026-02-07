// Package lint provides a public API for linting Simplex specifications.
package lint

import (
	"github.com/brannn/simplex/lint/internal/checks"
	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// Result is a linting result for a single spec.
type Result = result.LintResult

// Error is a single linting issue (error or warning).
type Error = result.LintError

// Stats is summary statistics for a linted spec.
type Stats = result.LintStats

// Config holds configuration for the linter.
type Config struct {
	MaxRules  int
	MaxInputs int
}

// Linter performs linting on Simplex specifications.
type Linter struct {
	parser             *parser.Parser
	structuralChecker  *checks.StructuralChecker
	complexityChecker  *checks.ComplexityChecker
	evolutionChecker   *checks.EvolutionChecker
	determinismChecker *checks.DeterminismChecker
	config             Config
}

// New creates a new Linter with the given configuration.
func New(config Config) *Linter {
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

// Lint validates a Simplex spec and returns the result.
func (l *Linter) Lint(name, content string) *Result {
	r := result.NewLintResult(name)

	spec := l.parser.Parse(content)

	for _, w := range spec.ParseWarnings {
		r.AddWarning("W001", w, "parse")
	}

	l.structuralChecker.Check(spec, r)
	l.complexityChecker.Check(spec, r)
	l.evolutionChecker.Check(spec, r)
	l.determinismChecker.Check(spec, r)

	r.Stats.Functions = len(spec.Functions)
	r.Stats.Examples = l.countTotalExamples(spec)
	r.Stats.Branches = l.countTotalBranches(spec)

	if r.Stats.Branches > 0 {
		r.Stats.CoveragePercent = float64(r.Stats.Examples) / float64(r.Stats.Branches) * 100
	}

	return r
}

func (l *Linter) countTotalExamples(spec *parser.ParsedSpec) int {
	total := 0
	for _, fn := range spec.Functions {
		if ex := fn.GetExamples(); ex != "" {
			total += checks.CountExamples(ex)
		}
	}
	return total
}

func (l *Linter) countTotalBranches(spec *parser.ParsedSpec) int {
	total := 0
	for _, fn := range spec.Functions {
		if rules := fn.GetRules(); rules != "" {
			total += checks.CountBranches(rules)
		}
	}
	return total
}

// DefaultLinter creates a linter with default settings.
func DefaultLinter() *Linter {
	return New(Config{})
}

// LintString is a convenience function that lints a spec string with defaults.
func LintString(content string) *Result {
	return DefaultLinter().Lint("input", content)
}
