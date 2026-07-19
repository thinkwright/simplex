# Simplex execution fidelity pilot v1 — controlled results

This report characterizes execution fidelity under the tested Simplex v0.6 specifications. It does not compare Simplex with prose and does not estimate a representation effect.

## Run inventory

- Run ID: `1784490337`
- Planned cells: 162
- Recorded cells: 162
- Behaviorally evaluated cells: 162
- Clean resource-eligible cells: 142

## Primary outcomes by model

| model | requirement fidelity | full-contract success | target adaptation | non-target preservation | false completeness | behavioral cells |
|---|---:|---:|---:|---:|---:|---:|
| glm-5.2 | 80.7% | 22.2% | 88.9% | 77.2% | 4.7% | 54 |
| minimax-m3 | 84.9% | 31.5% | 88.9% | 83.1% | 5.6% | 54 |
| qwen3.7-max | 84.9% | 20.4% | 97.2% | 83.6% | 6.8% | 54 |

Target adaptation and non-target preservation use mutation variants only. False completeness is the fraction of all declared example–requirement pairs where visible evidence passed while held-out evidence for the same requirement failed.

## Collateral regression by mutation

`delta` is mutation non-target fidelity minus the corresponding base non-target fidelity within family and model.

| family | mutation | model | base | mutation | delta |
|---|---|---|---:|---:|---:|
| configweave | concat | glm-5.2 | 100.0% | 100.0% | +0.000 |
| configweave | concat | minimax-m3 | 100.0% | 100.0% | +0.000 |
| configweave | concat | qwen3.7-max | 100.0% | 100.0% | +0.000 |
| configweave | union | glm-5.2 | 100.0% | 100.0% | +0.000 |
| configweave | union | minimax-m3 | 100.0% | 100.0% | +0.000 |
| configweave | union | qwen3.7-max | 100.0% | 100.0% | +0.000 |
| cursorvault | inclusive | glm-5.2 | 88.9% | 88.9% | +0.000 |
| cursorvault | inclusive | minimax-m3 | 88.9% | 88.9% | +0.000 |
| cursorvault | inclusive | qwen3.7-max | 88.9% | 88.9% | +0.000 |
| cursorvault | offset | glm-5.2 | 88.9% | 88.9% | +0.000 |
| cursorvault | offset | minimax-m3 | 88.9% | 88.9% | +0.000 |
| cursorvault | offset | qwen3.7-max | 88.9% | 88.9% | +0.000 |
| detreport | descending | glm-5.2 | 90.0% | 90.0% | +0.000 |
| detreport | descending | minimax-m3 | 96.7% | 73.3% | -0.233 |
| detreport | descending | qwen3.7-max | 90.0% | 90.0% | +0.000 |
| detreport | firstseen | glm-5.2 | 90.0% | 60.0% | -0.300 |
| detreport | firstseen | minimax-m3 | 96.7% | 73.3% | -0.233 |
| detreport | firstseen | qwen3.7-max | 90.0% | 90.0% | +0.000 |
| idledger | firstwins | glm-5.2 | 94.4% | 97.2% | +0.028 |
| idledger | firstwins | minimax-m3 | 94.4% | 97.2% | +0.028 |
| idledger | firstwins | qwen3.7-max | 88.9% | 77.8% | -0.111 |
| idledger | lastwins | glm-5.2 | 94.4% | 63.9% | -0.306 |
| idledger | lastwins | minimax-m3 | 94.4% | 100.0% | +0.056 |
| idledger | lastwins | qwen3.7-max | 88.9% | 88.9% | +0.000 |
| tokenquota | ceiling | glm-5.2 | 55.6% | 63.0% | +0.074 |
| tokenquota | ceiling | minimax-m3 | 70.4% | 70.4% | +0.000 |
| tokenquota | ceiling | qwen3.7-max | 63.0% | 77.8% | +0.148 |
| tokenquota | floor | glm-5.2 | 55.6% | 63.0% | +0.074 |
| tokenquota | floor | minimax-m3 | 70.4% | 51.9% | -0.185 |
| tokenquota | floor | qwen3.7-max | 63.0% | 63.0% | +0.000 |
| wirecodec | preserve | glm-5.2 | 76.2% | 50.0% | -0.262 |
| wirecodec | preserve | minimax-m3 | 71.4% | 78.6% | +0.071 |
| wirecodec | preserve | qwen3.7-max | 73.8% | 73.8% | +0.000 |
| wirecodec | reject | glm-5.2 | 76.2% | 76.2% | +0.000 |
| wirecodec | reject | minimax-m3 | 71.4% | 73.8% | +0.024 |
| wirecodec | reject | qwen3.7-max | 73.8% | 73.8% | +0.000 |

## Figures

- [Requirement fidelity heatmap](figures/requirement-fidelity-heatmap.svg)
- [Target adaptation versus preservation](figures/target-preservation-scatter.svg)
- [Visible versus held-out calibration](figures/visible-heldout-calibration.svg)
- [Across-trial dispersion](figures/trial-dispersion.svg)
- [Resource distributions](figures/resource-distributions.svg)

## Exclusions and limitations

- No cells were excluded from behavioral analysis.
- Timeouts and agent errors are prespecified behavioral failures and receive failed requirement outcomes; provider rejections are unobserved.
- Resource summaries exclude any cell with request retries, whole-agent retries, missing token telemetry, or no completed grader result.
- Across-trial ranges are descriptive and are not confidence intervals.
- These six synthetic families and three models do not support claims about general software-engineering performance or superiority over another prompt representation.
- The task authors also implemented the graders; independent semantic review remains desirable before confirmatory replication.

## Machine-readable outputs

- `analysis.json`: summaries, classifications, and provenance
- `cells.csv`: one row per planned inference cell
- `requirements.csv`: one row per evaluated requirement observation
- `checks.csv`: grader-check outcomes for completed graders
- `calibration.csv`: declared example–requirement calibration pairs
