# Simplex execution fidelity pilot v1 protocol

Status: **frozen, pre-inference**

Protocol date: 2026-07-19

## Research question

How faithfully, locally, and consistently do selected coding models translate a valid Simplex
v0.6 specification into observable software behavior?

This is a Simplex-only characterization study. It does not estimate a causal effect relative to
prose prompting and must not be described as doing so.

## Design

The unit of inference is one fresh autonomous-agent execution of a task variant. Six task families
each have a base specification and two variants. Within a family, each variant changes the
semantics of exactly one identified requirement. The API, all non-target requirements, grader
check inventory, agent system prompt, tools, model configuration, and run limits remain fixed.

The planned matrix is:

```text
6 families x 3 variants x 3 models x 3 trials = 162 cells
```

Job order is shuffled once using the frozen seed. Trial labels identify analytical cells; they do
not imply shared provider randomness or identical sampling seeds.

## Task families and controlled mutations

| family | behavioral domain | mutation target | base | variant A | variant B |
|---|---|---|---|---|---|
| `cursorvault` | cursor pagination | `R4` cursor interpretation | exclusive record ID | inclusive record ID | zero-based offset |
| `configweave` | recursive configuration merge | `R4` list merge | replace | concatenate | stable union |
| `idledger` | idempotent state changes | `R5` conflicting command ID | raise conflict | first command wins | last command replaces atomically |
| `tokenquota` | clock-driven token bucket | `R4` fractional refill | preserve fraction | floor | ceiling |
| `wirecodec` | versioned deterministic wire format | `R6` unknown fields | discard | reject | preserve under `extras` |
| `detreport` | deterministic aggregate reporting | `R5` group ordering | ascending | descending | first appearance |

The target requirement, its visible examples, and the variant-specific expected values may differ.
All other semantic items must remain byte-identical after rendering apart from task identity and
the project-location sentence needed by seeded tasks.

## Models and inference configuration

All three models use one Together endpoint and the checked-in `models.together.json`:

| analysis name | provider model ID | reasoning request | transport |
|---|---|---|---|
| GLM 5.2 | `zai-org/GLM-5.2` | provider/model default | non-streaming |
| MiniMax M3 | `MiniMaxAI/MiniMax-M3` | explicitly disabled | non-streaming |
| Qwen 3.7 Max | `Qwen/Qwen3.7-Max` | provider/model default | streaming with usage |

The runner uses `THINKBENCH_EFFORT=native`, so it does not add a cross-model
`reasoning_effort` override. Other frozen settings are:

- Temperature: `0.3`
- Per-request output cap: `65,536` tokens
- Agent-loop limit: 60 model turns
- Complete-cell wall-clock limit: 600 seconds, including retries and backoff
- Grader limit: 60 seconds
- Maximum request attempts per model turn: 5
- Maximum whole-agent attempts per cell: 3
- Runner parallelism: 2 cells
- Trials: 3 per task/model cell
- Job-order seed: `2026071901`
- Simplex revision: `9b1ad43674a715448141a6f09060c82ce626c9a3`
- ThinkBench revision: `06425846016014bee7aade6e4a4ba5b75a321f93`

The configured prices are bookkeeping inputs for estimated cost, not claims about current public
pricing. The three model IDs were present in Together's authenticated model list immediately
before freezing this protocol. The artifact manifest records hashes for the model configuration,
protocol, source ledger, generated tasks and prompts, construction report, and analysis code.

## Grading contract

Each hidden grader emits both the standard ThinkBench aggregate fields and a requirement-level
scorecard. Every check records:

- check name;
- requirement ID;
- requirement type;
- whether it is a direct visible-example check or a held-out check;
- visible example ID when applicable; and
- pass/fail status with a bounded failure note.

A requirement passes only when all checks assigned to it pass. The task score is the unweighted
fraction of requirements that pass, preventing requirements with more hidden cases from receiving
more weight. Full-contract success requires every requirement to pass.

The generated reference implementation for each variant must pass its grader. The base reference
must fail each mutation grader only on the mutation target, and each mutation reference must fail
the base grader only on that same target. These are construction checks, not model observations.

## Frozen primary outcomes

1. **Requirement fidelity:** macro-average requirement pass rate, first within task family and
   model, then summarized without pooling model tokenization.
2. **Full-contract success:** fraction of behaviorally observed cells with all requirements passed.
3. **Target adaptation:** mutation-target pass rate in mutation variants.
4. **Non-target preservation:** pass rate over requirements not designated as the mutation target.
5. **Collateral regression:** mutation-minus-base change in non-target pass rate within each
   family and model.
6. **False-completeness rate:** fraction of all declared example-requirement pairs in
   behaviorally evaluated cells for which every direct visible check passes but at least one
   held-out check for that requirement fails. The conditional rate among visible-passing pairs is
   also reported as a diagnostic, but it is not the primary denominator.

All task-level and model-level values must be reported. A pooled headline value may supplement but
must not replace them.

## Secondary outcomes

- first-request input tokens;
- cumulative cached and uncached input tokens;
- completion and total tokens;
- API turns and tool calls;
- wall-clock duration;
- estimated cost;
- request retries, whole-agent attempts, timeouts, budget exhaustion, and provider rejection;
- across-trial dispersion for behavioral and resource outcomes.

Provider-rejected cells are unobserved rather than behavioral failures. A complete-cell timeout or
agent-loop error is a prespecified behavioral failure and all requirements are recorded as failed.
Setup, grader, or result-integrity failures are infrastructure exclusions. Resource telemetry is
eligible only for a completed grader result with positive input telemetry, no request retry, and
one whole-agent attempt. Token comparisons remain within a model.

## Planned figures

1. Requirement-type by model fidelity heatmap.
2. Target-adaptation versus non-target-preservation scatter plot for each mutation.
3. Visible-example versus held-out-target calibration chart.
4. Trial-level full-contract and requirement-fidelity minimum-to-maximum plot. These are observed
   dispersion ranges, not confidence intervals.
5. Within-model resource distributions for behaviorally successful and unsuccessful cells.

Per-task tables, exclusions, and all scorecards belong in the technical appendix.

## Integrity and review gates

Before inference:

1. Every generated prompt passes the released Simplex v0.6 linter with zero diagnostics.
2. Every reference and cross-variant construction test passes.
3. Every requirement and example ID is unique and appears in the generated manifest.
4. Every grader check maps to a known requirement.
5. Every requirement has at least one held-out check.
6. Every declared example-requirement pair has a direct visible check.
7. The expected 162-cell Cartesian matrix resolves through ThinkBench `--list`.
8. Protocol, sources, generated artifacts, runner revision, and model configuration are hashed.
9. No inference result from this study has been inspected while changing the protocol or suite.

An independent semantic review is desirable before treating a later replication as confirmatory.
This first run remains an engineering pilot even if every mechanical gate passes.

## Analysis and publication boundary

The dependency-free `analyze.py` script, metric definitions, exclusion rules, and five primary
figure definitions are frozen before task-level inference begins. It rejects missing, unexpected,
or duplicate cells by default and retains cell-, requirement-, check-, and example-pair-level
tables. Additional analyses may be added only as clearly labelled exploratory work.

Appropriate claims describe execution fidelity, mutation sensitivity, preservation, traceability
calibration, variance, and resource use for the tested models and tasks. Inappropriate claims
include superiority over prose, general coding-agent performance, formal semantic coverage, or
provider-independent effects.
