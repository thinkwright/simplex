# Simplex execution-fidelity pilot v1

This document is the post-run record and data guide for a controlled, Simplex-only coding-agent
experiment conducted on 2026-07-19. It describes the question, design, frozen decisions, execution,
results, limitations, and archived data. The original pre-inference protocol remains unchanged in
[`PROTOCOL.md`](PROTOCOL.md); this document was written after inference and is not part of the
frozen pre-inference artifact set.

## Study record

| field | value |
|---|---|
| Study | `simplex-fidelity-v1` |
| Run ID | `1784490337` |
| Simplex format | v0.6 |
| Simplex revision used for inference | `9b1ad43674a715448141a6f09060c82ce626c9a3` |
| ThinkBench revision | `06425846016014bee7aade6e4a4ba5b75a321f93` |
| Provider | Together |
| Task families | 6 |
| Task variants | 18 |
| Models | 3 |
| Trials per task and model | 3 |
| Planned and recorded cells | 162 |
| Completed graders | 159 |
| Prespecified behavioral failures | 3 timeouts |
| Provider rejections | 0 |
| Clean resource-eligible cells | 142 |

## Research question and claim boundary

The study asks:

> How faithfully, locally, and consistently do selected coding models translate a valid Simplex
> v0.6 specification into observable software behavior?

Every task prompt was a Simplex document. There was no natural-language prose condition. The
experiment therefore characterizes behavior under the tested specifications; it does not estimate
whether Simplex is better or worse than prose, whether Simplex changes token consumption, or whether
the observed behavior generalizes to software engineering as a whole.

The principal objects of measurement were:

- pass or failure for each explicitly identified requirement;
- complete satisfaction of all requirements in a task;
- response to an atomic requirement mutation;
- preservation of requirements that were not changed;
- agreement between direct checks of declared examples and held-out checks;
- variation across three executions; and
- model-reported resource use and operational incidents.

## Experimental design

### Controlled task families

Six synthetic Python package tasks were authored for the study. Each family had one base
specification and two variants. A variant changed the semantics of one named requirement while
keeping the public API, other semantic items, grader-check inventory, agent instructions, and run
limits fixed.

| family | domain | mutation target | base behavior | variant A | variant B | requirements | examples | checks |
|---|---|---|---|---|---|---:|---:|---:|
| `cursorvault` | cursor pagination | `R4` | exclusive record ID | inclusive record ID | zero-based offset | 10 | 6 | 23 |
| `configweave` | recursive configuration merge | `R4` | replace lists | concatenate lists | stable union | 10 | 6 | 20 |
| `idledger` | idempotent state changes | `R5` | conflicting ID raises | first command wins | last command replaces | 13 | 7 | 27 |
| `tokenquota` | clock-driven token bucket | `R4` | preserve fraction | floor fraction | ceiling fraction | 10 | 6 | 22 |
| `wirecodec` | deterministic versioned wire format | `R6` | discard unknown fields | reject unknown fields | preserve in `extras` | 15 | 8 | 37 |
| `detreport` | deterministic aggregate reporting | `R5` | ascending groups | descending groups | first-seen groups | 11 | 7 | 25 |

The counts in the final three columns apply to each of the family's three variants. Sources are in
[`sources/`](sources/); the rendered prompts, seeded tasks, graders, references, and complete variant
ledger are in [`generated/`](generated/).

### Matrix and execution unit

One cell was one fresh autonomous-agent execution of one task variant:

```text
6 families x 3 variants x 3 models x 3 trials x 1 condition = 162 cells
```

Job order was shuffled once with seed `2026071901`. Trial labels identify repeated cells; they do
not imply a provider-side random seed or paired randomness across models. Each agent received the
same fixed system instruction, a fresh seeded workspace, file inspection and editing tools, and a
shell-command tool. The complete agent instruction is retained in
[`raw-runs/1784490337/session.json`](raw-runs/1784490337/session.json).

### Models and inference settings

| analysis name | provider model ID | reasoning request | transport |
|---|---|---|---|
| GLM 5.2 | `zai-org/GLM-5.2` | provider/model default | non-streaming |
| MiniMax M3 | `MiniMaxAI/MiniMax-M3` | explicitly disabled | non-streaming |
| Qwen 3.7 Max | `Qwen/Qwen3.7-Max` | provider/model default | streaming with usage |

The inference settings were frozen before the run:

| setting | value |
|---|---:|
| Temperature | 0.3 |
| Per-request output cap | 65,536 tokens |
| Agent-loop limit | 60 model turns |
| Cell wall-clock limit | 600 seconds |
| Grader limit | 60 seconds |
| Maximum request attempts per turn | 5 |
| Maximum whole-agent attempts per cell | 3 |
| Parallel cells | 2 |
| ThinkBench effort mode | `native` |

`native` means the runner did not impose one cross-model reasoning-effort value. The model file
[`models.together.json`](models.together.json) records the exact endpoint and configuration.
Configured prices were bookkeeping inputs and should not be read as a statement of current public
pricing.

### Construction and grading

The hidden grader for each task emitted an aggregate ThinkBench result and a requirement-level
scorecard. Every check mapped to a known requirement and was marked as either a direct visible
example check or a held-out check. A requirement passed only when all checks assigned to it passed.
The task score was the unweighted fraction of requirements passed. Full-contract success required
every requirement to pass.

Before inference, the following gates passed:

1. All 18 rendered prompts produced zero Simplex v0.6 linter diagnostics.
2. All 18 reference implementations passed their matching graders.
3. All 24 directional cross-variant checks failed only the declared mutation target.
4. Every requirement had at least one held-out check.
5. Every declared example-to-requirement relation had a direct visible check.
6. ThinkBench resolved exactly 18 tasks and the one selected condition.
7. The expected Cartesian matrix contained exactly 162 cells.
8. Protocol, source, generated, runner, model, and analyzer artifacts were hashed before inference.

The construction evidence is in [`construction-report.json`](construction-report.json) and
[`REVIEW.md`](REVIEW.md). The pre-inference artifact-manifest SHA-256 is
`ec1c6b135ba82be11fde68ea1078d8c6d2cc8b2d28f6547af28f0212609c55d9`.
The semantic review was performed by the task author and was not independent.

## Prespecified outcomes and analysis rules

The dependency-free [`analyze.py`](analyze.py) implementation and these definitions were frozen
before inference:

- **Requirement fidelity:** the pass rate over requirement observations.
- **Full-contract success:** the fraction of behaviorally evaluated cells in which every
  requirement passed.
- **Target adaptation:** the mutation-target pass rate in the 12 mutation tasks.
- **Non-target preservation:** the pass rate for unchanged requirements in mutation tasks.
- **Collateral regression:** mutation non-target fidelity minus base non-target fidelity, within
  family and model.
- **False completeness:** a declared example-requirement pair for which all direct visible checks
  passed while at least one held-out check for the same requirement failed.

A complete-cell timeout or agent-loop error was prespecified as a behavioral failure and all its
requirements were imputed as failed. A provider rejection would have been treated as unobserved.
Setup, grader, and result-integrity failures would have been infrastructure exclusions. No cells
fell into those categories.

Resource summaries required a completed grader, positive input-token telemetry, no request retry,
and exactly one whole-agent attempt. This excluded 20 cells: three timeouts and 17 completed cells
with request retries. Because tokenizers and provider accounting differ, token quantities are
descriptive within each model and are not a controlled comparison between models.

## Results

### Overall and by model

Across all cells, 1,555 of 1,863 requirement observations passed (83.5%), and 40 of 162 cells
satisfied the complete contract (24.7%). In mutation tasks, 99 of 108 target observations passed
(91.7%) and 922 of 1,134 unchanged-requirement observations passed (81.3%).

| model | requirement fidelity | full-contract success | target adaptation | non-target preservation | false completeness |
|---|---:|---:|---:|---:|---:|
| GLM 5.2 | 80.7% | 12/54 (22.2%) | 32/36 (88.9%) | 292/378 (77.2%) | 35/738 (4.7%) |
| MiniMax M3 | 84.9% | 17/54 (31.5%) | 32/36 (88.9%) | 314/378 (83.1%) | 41/738 (5.6%) |
| Qwen 3.7 Max | 84.9% | 11/54 (20.4%) | 35/36 (97.2%) | 316/378 (83.6%) | 50/738 (6.8%) |
| **Overall** | **1,555/1,863 (83.5%)** | **40/162 (24.7%)** | **99/108 (91.7%)** | **922/1,134 (81.3%)** | **126/2,214 (5.7%)** |

Requirement fidelity and full-contract success measure different things. A cell could satisfy most
requirements while failing the complete contract because a single requirement failed. The gap
between 83.5% requirement fidelity and 24.7% full-contract success is therefore expected under a
strict all-requirements criterion and is substantively informative.

### Results by family

| family | requirement fidelity | full contract | target adaptation | non-target preservation | false completeness |
|---|---:|---:|---:|---:|---:|
| `configweave` | 270/270 (100.0%) | 27/27 (100.0%) | 18/18 (100.0%) | 162/162 (100.0%) | 0/270 (0.0%) |
| `cursorvault` | 243/270 (90.0%) | 0/27 (0.0%) | 18/18 (100.0%) | 144/162 (88.9%) | 27/351 (7.7%) |
| `detreport` | 250/297 (84.2%) | 2/27 (7.4%) | 15/18 (83.3%) | 143/180 (79.4%) | 25/378 (6.6%) |
| `idledger` | 312/351 (88.9%) | 11/27 (40.7%) | 14/18 (77.8%) | 189/216 (87.5%) | 23/351 (6.6%) |
| `tokenquota` | 182/270 (67.4%) | 0/27 (0.0%) | 17/18 (94.4%) | 105/162 (64.8%) | 5/324 (1.5%) |
| `wirecodec` | 298/405 (73.6%) | 0/27 (0.0%) | 17/18 (94.4%) | 179/252 (71.0%) | 46/540 (8.5%) |

Family difficulty was uneven. `configweave` reached full-contract success in every cell, while
three families had none. Consequently, the pooled result is a description of this selected task
mixture rather than an estimate for an external population of coding tasks.

### Requirement types

| requirement type | observations per model | GLM 5.2 | MiniMax M3 | Qwen 3.7 Max |
|---|---:|---:|---:|---:|
| baseline evolve | 18 | 88.9% | 100.0% | 100.0% |
| baseline preserve | 18 | 88.9% | 100.0% | 100.0% |
| constraint | 63 | 84.1% | 92.1% | 95.2% |
| stable determinism | 9 | 88.9% | 100.0% | 100.0% |
| done-when condition | 54 | 94.4% | 92.6% | 87.0% |
| error behavior | 81 | 79.0% | 79.0% | 81.5% |
| behavioral rule | 378 | 77.5% | 82.0% | 81.7% |

These categories are labels assigned by the study authors. They are useful for locating failure
patterns in this suite but have not been independently validated as a general taxonomy.

### Declared examples and held-out behavior

Direct visible evidence passed for 1,984 of 2,214 declared example-requirement pairs (89.6%).
Held-out evidence passed for 1,880 pairs (84.9%). There were 126 false-completeness pairs, equal to
5.7% of all declared pairs and 6.4% of the 1,984 visible-passing pairs.

This result shows that a direct implementation of the declared examples did not always extend to
the held-out behavior associated with the same requirement. It does not measure formal coverage or
prove that the examples caused the failures.

### Locality and collateral regression

Of the 36 family-mutation-model combinations, 21 had no measured change in non-target fidelity,
eight had a positive change, and seven had a negative change relative to the corresponding base.
The negative descriptive deltas were:

| family | mutation | model | non-target delta |
|---|---|---|---:|
| `detreport` | descending | MiniMax M3 | -23.3 percentage points |
| `detreport` | first-seen | GLM 5.2 | -30.0 percentage points |
| `detreport` | first-seen | MiniMax M3 | -23.3 percentage points |
| `idledger` | first-wins | Qwen 3.7 Max | -11.1 percentage points |
| `idledger` | last-wins | GLM 5.2 | -30.6 percentage points |
| `tokenquota` | floor | MiniMax M3 | -18.5 percentage points |
| `wirecodec` | preserve | GLM 5.2 | -26.2 percentage points |

The three listed GLM mutation cells each include one of the run's three timeouts. Because timeouts
were correctly counted as behavioral failures, their deltas combine implementation behavior with
incomplete execution and should not be interpreted as pure collateral-edit effects. All 36 exact
deltas are retained in [`analysis/1784490337/RESULTS.md`](analysis/1784490337/RESULTS.md) and
[`analysis.json`](analysis/1784490337/analysis.json).

### Across-trial dispersion

| model | trial | requirement fidelity | full-contract success |
|---|---:|---:|---:|
| GLM 5.2 | 1 | 70.5% | 22.2% |
| GLM 5.2 | 2 | 87.0% | 27.8% |
| GLM 5.2 | 3 | 84.5% | 16.7% |
| MiniMax M3 | 1 | 84.1% | 33.3% |
| MiniMax M3 | 2 | 88.4% | 38.9% |
| MiniMax M3 | 3 | 82.1% | 22.2% |
| Qwen 3.7 Max | 1 | 82.6% | 16.7% |
| Qwen 3.7 Max | 2 | 85.5% | 22.2% |
| Qwen 3.7 Max | 3 | 86.5% | 22.2% |

All three GLM timeouts occurred in trial 1, accounting for part of its lower requirement fidelity.
The ranges above are observed dispersion across three executions, not confidence intervals.

### Resource accounting

Raw cumulative provider telemetry, including retry-affected and timed-out cells, was:

| model | input tokens | cached input | completion tokens | total tokens | mean cell seconds | request retries | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| GLM 5.2 | 6,086,826 | 4,230,208 (69.5%) | 899,052 | 6,985,878 | 202.0 | 1 | $7.6549 |
| MiniMax M3 | 2,237,348 | 1,579,136 (70.6%) | 256,470 | 2,493,818 | 56.2 | 0 | $0.6000 |
| Qwen 3.7 Max | 1,227,735 | 539,392 (43.9%) | 396,031 | 1,623,766 | 143.9 | 30 | $2.4130 |
| **Total** | **9,551,909** | **6,348,736** | **1,551,553** | **11,103,462** | — | **31** | **$10.6679** |

Qwen's 30 request retries occurred in 16 cells; GLM's one retry occurred in one cell; MiniMax had
none. All 162 cells used one whole-agent attempt. The run made 1,222 recorded API calls.

For the 142 clean resource-eligible cells, median total tokens and elapsed time were:

| model | clean cells | full-contract token median | other token median | full-contract seconds median | other seconds median |
|---|---:|---:|---:|---:|---:|
| GLM 5.2 | 50 | 133,121 | 110,175 | 146.2 | 142.8 |
| MiniMax M3 | 54 | 22,473 | 30,180 | 45.9 | 48.0 |
| Qwen 3.7 Max | 38 | 22,260 | 27,820 | 129.8 | 119.2 |

There is no consistent within-model direction between resource consumption and complete success in
this small sample. The study has no non-Simplex condition, so these figures cannot support a claim
about Simplex token efficiency.

### Operational incidents

Three GLM cells reached the 600-second complete-cell timeout:

- `detreport_firstseen`, trial 1;
- `idledger_lastwins`, trial 1; and
- `wirecodec_preserve`, trial 1.

They have `meta.json` and prompt records but no completed transcript, grader scorecard, or retained
workspace. The frozen analyzer retained them as behavioral failures. There were no provider
rejections, setup failures, grader failures, duplicate cells, unexpected cells, or missing matrix
cells.

## Interpretation

The pilot yields several bounded observations about this suite:

1. Models usually followed the deliberately changed requirement: mutation-target fidelity was
   91.7% overall.
2. Following the changed requirement did not guarantee preservation of the remaining contract:
   non-target fidelity was 81.3%, with seven negative family-mutation-model deltas.
3. Most individual requirements passed, but exact contract satisfaction was much less frequent.
   This demonstrates the analytical value of requirement-level results rather than establishing a
   benefit of the specification format.
4. Declared examples were informative but not sufficient evidence of complete behavior: visible
   checks passed more often than held-out checks, and false completeness remained measurable.
5. Resource use and reliability differed materially across models, but the design cannot separate
   model, provider, tokenizer, and specification effects.

These are descriptive findings for the tested cells. They are not estimates of a representation
effect and should not be phrased as proof that Simplex improves coding-agent performance.

## Limitations

- There was no prose or alternative-structure condition.
- The six task families were synthetic and deliberately narrow.
- Family difficulty was uneven, including one universally solved family.
- Only three models, one provider, one execution environment, and three trials were used.
- Trial labels did not control provider-side sampling randomness.
- Provider retries and three timeouts affected the observed data.
- The same authors designed the tasks, specifications, references, and graders.
- Requirement pass rates weight requirements equally, regardless of their breadth or difficulty.
- Full-contract success is strict and can be changed by one failed requirement.
- The requirement-type taxonomy and mutation locality judgments were not independently validated.
- The results do not establish formal semantic coverage, general software-engineering ability, or
  provider-independent behavior.

An independently reviewed, frozen replication should precede strong public claims. A future
confirmatory study should retain this archive, predeclare any suite changes, expand task diversity,
increase trials, and separate provider failures from behavioral outcomes with the same explicit
rules.

## Data archive

This branch retains the complete study data other than interpreter and package-manager caches.
Those caches are execution by-products and are excluded by the study-local `.gitignore`.

### Frozen design and construction data

| path | contents |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | Frozen pre-inference protocol and claim boundary |
| [`study.json`](study.json) | Machine-readable matrix, revisions, limits, and model mapping |
| [`models.together.json`](models.together.json) | Frozen provider/model configuration and bookkeeping prices |
| [`sources/`](sources/) | Family definitions, grader sources, and reference sources |
| [`generated/`](generated/) | 18 rendered tasks, prompt pack, references, graders, and variant ledger |
| [`construction-report.json`](construction-report.json) | Matching-reference and cross-variant gate results |
| [`artifact-manifest.json`](artifact-manifest.json) | Pre-inference hashes for frozen artifacts |
| [`REVIEW.md`](REVIEW.md) | Author-side construction and semantic review record |

The `status` values in `PROTOCOL.md`, `study.json`, and `artifact-manifest.json` intentionally remain
pre-inference because those files are preserved frozen records, not current status pages.

### Raw run data

[`raw-runs/1784490337/`](raw-runs/1784490337/) contains:

- `session.json`: the complete runner configuration and resolved matrix;
- `results.jsonl`: 162 aggregate cell records;
- one directory per matrix cell, named by task, condition, model, and trial;
- `meta.json`: outcome and telemetry for every cell;
- `prompt.json` and `prompt.txt`: the resolved prompt for every cell;
- `transcript.txt`: the completed agent interaction for 159 cells;
- `scorecard.json`: requirement and check outcomes for 159 cells; and
- `workspace/`: the final submitted workspace state for each of the 159 completed cells.

The raw `results.jsonl` SHA-256 is
`02e9c644ce9589a1cbb03832eaf51cc70326a25f11e06242495e0bff72835a62`; the raw `session.json`
SHA-256 is `396c8827eb59c2393fbd3399935f739e14d1c837d336b921d67f0621de4e3d1b`.

### Derived analysis data

[`analysis/1784490337/`](analysis/1784490337/) contains the frozen analyzer output:

| file | rows or role |
|---|---|
| [`RESULTS.md`](analysis/1784490337/RESULTS.md) | Automatically generated concise report and all collateral deltas |
| [`analysis.json`](analysis/1784490337/analysis.json) | Machine-readable summaries, classifications, and provenance |
| [`cells.csv`](analysis/1784490337/cells.csv) | 162 rows; one per planned inference cell |
| [`requirements.csv`](analysis/1784490337/requirements.csv) | 1,863 requirement observations |
| [`checks.csv`](analysis/1784490337/checks.csv) | 4,069 completed-grader check observations |
| [`calibration.csv`](analysis/1784490337/calibration.csv) | 2,214 declared example-requirement observations |
| [`figures/`](analysis/1784490337/figures/) | Five article-ready SVG figures |

The CSV files retain identifiers needed to join task, family, variant, model, trial, requirement,
check, and example-pair levels. Boolean fields record pass/failure, mutation role, imputation, and
resource eligibility. `analysis.json` is the authoritative summary of metric values and analysis
classifications; the CSV files are the authoritative long-form analytical tables.

The five figures are:

1. [requirement fidelity by type and model](analysis/1784490337/figures/requirement-fidelity-heatmap.svg);
2. [target adaptation versus non-target preservation](analysis/1784490337/figures/target-preservation-scatter.svg);
3. [visible versus held-out calibration](analysis/1784490337/figures/visible-heldout-calibration.svg);
4. [across-trial dispersion](analysis/1784490337/figures/trial-dispersion.svg); and
5. [clean resource distributions](analysis/1784490337/figures/resource-distributions.svg).

### Analysis and archive tooling

| path | purpose |
|---|---|
| [`build_suite.py`](build_suite.py) | Deterministically render task and prompt artifacts from family sources |
| [`validate_suite.py`](validate_suite.py) | Run reference, evidence-mapping, and cross-variant gates |
| [`run_controlled.sh`](run_controlled.sh) | Archival wrapper used for the controlled run |
| [`analyze.py`](analyze.py) | Validate the matrix and produce tables, summaries, and figures |
| [`tests/test_analyze.py`](tests/test_analyze.py) | Synthetic analyzer tests, including incomplete-matrix rejection |
| [`build_archive_manifest.py`](build_archive_manifest.py) | Generate or verify the post-run archive manifest |
| [`archive-manifest.json`](archive-manifest.json) | SHA-256 and size for every retained experiment file except itself |

The archival run wrapper contains the absolute paths and revision guard used on the execution host.
It is retained verbatim as provenance. It will refuse to run when the Simplex checkout's `HEAD` is
not the frozen v0.6 commit. A replication should place this experiment directory in a worktree at
that revision or create a new, explicitly versioned wrapper and record the deviation.

## Verification and reproduction

From this directory, the non-inference checks are:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 build_suite.py --check
PYTHONDONTWRITEBYTECODE=1 python3 validate_suite.py
PYTHONDONTWRITEBYTECODE=1 python3 build_archive_manifest.py --check
```

Prompt linting additionally requires the Simplex v0.6 linter. The original controlled inference
used `./run_controlled.sh`, which obtains the Together credential from `TOGETHER_API_KEY` or the
local `pass` entry `providers/together/api-key`. Credentials are not stored in this archive.

To reproduce the frozen analysis without inference:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py \
  raw-runs/1784490337 \
  analysis/1784490337
```

Reanalysis should reproduce the checked-in tables and SVGs byte for byte under a compatible Python
environment. A new inference run will receive a new run ID and may differ because provider and model
behavior are not fully deterministic.

## Publication use

The archive is sufficient to produce a readable technical article with traceable tables and
figures. Any publication should:

- call this an engineering pilot or descriptive execution-fidelity study;
- report task- and model-level results, not only a pooled value;
- state that there was no prose comparator;
- disclose the three timeouts and resource exclusions;
- distinguish prespecified outputs from later exploratory analysis;
- state that task and grader review was not independent; and
- avoid causal or general-performance claims unsupported by this design.
