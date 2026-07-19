#!/usr/bin/env python3
"""Analyze one frozen Simplex fidelity run and emit tables plus publication-ready SVGs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_VARIANTS = ROOT / "generated" / "variants.json"
DEFAULT_STUDY = ROOT / "study.json"
BEHAVIOR_FAILURE_OUTCOMES = {"timeout", "agent_error"}
MODEL_COLORS = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706"]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON: {error}") from error
    return rows


def read_last_json(path: Path) -> dict:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"empty scorecard: {path}")
    return json.loads(lines[-1])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def rate(rows: list[dict], field: str = "passed") -> float | None:
    return mean(1.0 if row[field] else 0.0 for row in rows)


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def distribution(values) -> dict:
    values = [float(value) for value in values]
    if not values:
        return {"n": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None, "mean": None}
    return {
        "n": len(values),
        "min": min(values),
        "q1": quantile(values, 0.25),
        "median": quantile(values, 0.5),
        "q3": quantile(values, 0.75),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def requirement_type(requirement_id: str) -> str:
    return {
        "R": "rule",
        "D": "done_when",
        "X": "error",
        "C": "constraint",
        "P": "baseline_preserve",
        "V": "baseline_evolve",
        "S": "determinism_stable",
    }.get(requirement_id[:1], "contract")


def condition_names(session: dict) -> list[str]:
    names = []
    for value in session.get("conditions", []):
        names.append(value["name"] if isinstance(value, dict) else value)
    return names


def expected_keys(study: dict, variants: list[dict]) -> set[tuple[str, str, str, int]]:
    return {
        (variant["task"], study["condition"], model, trial)
        for variant in variants
        for model in study["models"]
        for trial in range(1, study["trials"] + 1)
    }


def row_key(row: dict) -> tuple[str, str, str, int]:
    return (row["task"], row["condition"], row["worker"], int(row["trial"]))


def validate_session(session: dict, study: dict, variants: list[dict]) -> None:
    expected_tasks = {variant["task"] for variant in variants}
    actual_tasks = set(session.get("tasks", []))
    if actual_tasks != expected_tasks:
        raise ValueError(f"session task mismatch: missing={sorted(expected_tasks - actual_tasks)}, unexpected={sorted(actual_tasks - expected_tasks)}")
    if set(session.get("models", [])) != set(study["models"]):
        raise ValueError("session model inventory differs from study.json")
    if condition_names(session) != [study["condition"]]:
        raise ValueError("session condition differs from study.json")
    if int(session.get("trials", -1)) != int(study["trials"]):
        raise ValueError("session trial count differs from study.json")
    if int(session.get("job_seed", -1)) != int(study["job_seed"]):
        raise ValueError("session job seed differs from study.json")


def validate_scorecard(scorecard: dict, variant: dict, path: Path) -> None:
    expected = [item["id"] for item in variant["requirements"]]
    actual = list(scorecard.get("requirements", {}))
    if set(actual) != set(expected):
        raise ValueError(f"{path}: requirement mismatch: expected={sorted(expected)}, actual={sorted(actual)}")
    grouped = defaultdict(list)
    for check in scorecard.get("checks", []):
        requirement_id = check.get("requirement_id")
        if requirement_id not in expected:
            raise ValueError(f"{path}: check maps to unknown requirement {requirement_id!r}")
        if check.get("evidence") not in {"visible", "hidden"}:
            raise ValueError(f"{path}: invalid evidence value in {check.get('name')!r}")
        grouped[requirement_id].append(check)
    for requirement_id in expected:
        checks = grouped[requirement_id]
        if not checks:
            raise ValueError(f"{path}: no checks for {requirement_id}")
        derived = all(bool(check.get("passed")) for check in checks)
        declared = bool(scorecard["requirements"][requirement_id].get("passed"))
        if derived != declared:
            raise ValueError(f"{path}: derived status differs for {requirement_id}")
        if not any(check.get("evidence") == "hidden" for check in checks):
            raise ValueError(f"{path}: no held-out check for {requirement_id}")
    derived_passed = sum(bool(scorecard["requirements"][item].get("passed")) for item in expected)
    if derived_passed != int(scorecard.get("passed", -1)) or len(expected) != int(scorecard.get("total", -1)):
        raise ValueError(f"{path}: aggregate counts differ from requirement statuses")
    derived_score = derived_passed / len(expected)
    if not math.isclose(derived_score, float(scorecard.get("score", -1)), abs_tol=1e-12):
        raise ValueError(f"{path}: aggregate score differs from requirement statuses")


def scorecard_path(run_dir: Path, row: dict) -> Path:
    label = f"{row['task']}__{row['condition']}__{row['worker']}__t{int(row['trial'])}"
    return run_dir / label / "scorecard.json"


def resource_eligible(row: dict, has_scorecard: bool) -> bool:
    return (
        has_scorecard
        and row.get("outcome_kind") == "completed"
        and int(row.get("request_retries", 0)) == 0
        and int(row.get("attempts", 1)) == 1
        and int(row.get("first_prompt_tokens", 0)) > 0
        and int(row.get("prompt_tokens", 0)) > 0
    )


def build_tables(run_dir: Path, rows: list[dict], variants: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    by_task = {variant["task"]: variant for variant in variants}
    cells: list[dict] = []
    requirements: list[dict] = []
    checks: list[dict] = []
    calibration: list[dict] = []

    for row in sorted(rows, key=row_key):
        variant = by_task[row["task"]]
        path = scorecard_path(run_dir, row)
        scorecard = read_last_json(path) if path.is_file() else None
        if scorecard is not None:
            validate_scorecard(scorecard, variant, path)
            if (
                int(row.get("passed", -1)) != int(scorecard["passed"])
                or int(row.get("total", -1)) != int(scorecard["total"])
                or not math.isclose(float(row.get("score", -1)), float(scorecard["score"]), abs_tol=1e-12)
            ):
                raise ValueError(f"{path}: runner aggregate differs from preserved scorecard")
            analysis_status = "graded"
        elif row.get("outcome_kind") in BEHAVIOR_FAILURE_OUTCOMES:
            analysis_status = "imputed_behavioral_failure"
        elif row.get("outcome_kind") == "provider_rejected":
            analysis_status = "excluded_provider_rejection"
        else:
            analysis_status = "excluded_infrastructure"

        base_fields = {
            "task": row["task"],
            "family": variant["family"],
            "variant": variant["variant"],
            "base": bool(variant["base"]),
            "mutation_target": variant["mutation_target"],
            "model": row["worker"],
            "trial": int(row["trial"]),
        }
        requirement_rows = []
        check_rows = []
        if scorecard is not None:
            for item in variant["requirements"]:
                requirement_id = item["id"]
                value = scorecard["requirements"][requirement_id]
                requirement_rows.append(
                    {
                        **base_fields,
                        "requirement_id": requirement_id,
                        "requirement_role": item["role"],
                        "requirement_type": value.get("type", requirement_type(requirement_id)),
                        "is_mutation_target": requirement_id == variant["mutation_target"],
                        "passed": bool(value["passed"]),
                        "imputed": False,
                    }
                )
            for check in scorecard["checks"]:
                check_rows.append(
                    {
                        **base_fields,
                        "name": check.get("name", ""),
                        "requirement_id": check["requirement_id"],
                        "requirement_type": check.get("requirement_type", requirement_type(check["requirement_id"])),
                        "evidence": check["evidence"],
                        "example_id": check.get("example_id"),
                        "passed": bool(check["passed"]),
                        "note": check.get("note", ""),
                    }
                )
        elif analysis_status == "imputed_behavioral_failure":
            for item in variant["requirements"]:
                requirement_rows.append(
                    {
                        **base_fields,
                        "requirement_id": item["id"],
                        "requirement_role": item["role"],
                        "requirement_type": requirement_type(item["id"]),
                        "is_mutation_target": item["id"] == variant["mutation_target"],
                        "passed": False,
                        "imputed": True,
                    }
                )

        full_contract = all(item["passed"] for item in requirement_rows) if requirement_rows else None
        fidelity = rate(requirement_rows) if requirement_rows else None
        target_rows = [item for item in requirement_rows if item["is_mutation_target"]]
        non_target_rows = [item for item in requirement_rows if not item["is_mutation_target"]]
        eligible = resource_eligible(row, scorecard is not None)
        cell = {
            **base_fields,
            "outcome_kind": row.get("outcome_kind", ""),
            "analysis_status": analysis_status,
            "behavioral": bool(requirement_rows),
            "requirement_fidelity": fidelity,
            "full_contract": full_contract,
            "target_pass": rate(target_rows),
            "non_target_fidelity": rate(non_target_rows),
            "import_ok": bool(scorecard.get("import_ok")) if scorecard is not None else False,
            "resource_eligible": eligible,
            "secs": float(row.get("secs", 0.0)),
            "prompt_bytes": int(row.get("prompt_bytes", 0)),
            "prompt_chars": int(row.get("prompt_chars", 0)),
            "prompt_lines": int(row.get("prompt_lines", 0)),
            "first_prompt_tokens": int(row.get("first_prompt_tokens", 0)),
            "first_cached_tokens": int(row.get("first_cached_tokens", 0)),
            "first_completion_tokens": int(row.get("first_completion_tokens", 0)),
            "prompt_tokens": int(row.get("prompt_tokens", 0)),
            "cached_tokens": int(row.get("cached_tokens", 0)),
            "uncached_tokens": max(0, int(row.get("prompt_tokens", 0)) - int(row.get("cached_tokens", 0))),
            "completion_tokens": int(row.get("completion_tokens", 0)),
            "total_tokens": int(row.get("prompt_tokens", 0)) + int(row.get("completion_tokens", 0)),
            "api_calls": int(row.get("api_calls", 0)),
            "tool_calls": int(row.get("calls", 0)),
            "request_retries": int(row.get("request_retries", 0)),
            "agent_attempts": int(row.get("attempts", 1)),
            "cost_usd": float(row.get("cost_usd", 0.0)),
            "note": row.get("note", ""),
        }

        visible_by_pair = defaultdict(list)
        hidden_by_requirement = defaultdict(list)
        for check in check_rows:
            if check["evidence"] == "visible" and check["example_id"]:
                visible_by_pair[(check["example_id"], check["requirement_id"])].append(check)
            elif check["evidence"] == "hidden":
                hidden_by_requirement[check["requirement_id"]].append(check)
        declared_pairs = {
            (example["id"], requirement_id)
            for example in variant["examples"]
            for requirement_id in example["covers"]
        }
        if scorecard is not None and scorecard.get("import_ok"):
            actual_pairs = set(visible_by_pair)
            if actual_pairs != declared_pairs:
                raise ValueError(
                    f"{path}: visible example-target mismatch: missing={sorted(declared_pairs - actual_pairs)}, unexpected={sorted(actual_pairs - declared_pairs)}"
                )
        if requirement_rows:
            for example_id, requirement_id in sorted(declared_pairs):
                visible_checks = visible_by_pair[(example_id, requirement_id)]
                hidden_checks = hidden_by_requirement[requirement_id]
                if scorecard is not None and scorecard.get("import_ok"):
                    visible_pass = all(check["passed"] for check in visible_checks)
                    hidden_pass = all(check["passed"] for check in hidden_checks)
                else:
                    visible_pass = False
                    hidden_pass = False
                calibration.append(
                    {
                        **base_fields,
                        "example_id": example_id,
                        "requirement_id": requirement_id,
                        "visible_pass": visible_pass,
                        "hidden_pass": hidden_pass,
                        "false_complete": visible_pass and not hidden_pass,
                        "imputed": scorecard is None or not bool(scorecard.get("import_ok")),
                    }
                )

        cells.append(cell)
        requirements.extend(requirement_rows)
        checks.extend(check_rows)

    return cells, requirements, checks, calibration


def summarize(cells: list[dict], requirements: list[dict], calibration: list[dict], models: list[str]) -> dict:
    behavioral_cells = [row for row in cells if row["behavioral"]]
    mutation_requirements = [row for row in requirements if not row["base"]]

    def metrics(cell_rows, requirement_rows, pair_rows) -> dict:
        target = [row for row in requirement_rows if not row["base"] and row["is_mutation_target"]]
        non_target = [row for row in requirement_rows if not row["base"] and not row["is_mutation_target"]]
        visible_passed = [row for row in pair_rows if row["visible_pass"]]
        return {
            "behavioral_cells": len(cell_rows),
            "requirement_observations": len(requirement_rows),
            "requirement_fidelity": rate(requirement_rows),
            "full_contract_success": rate(cell_rows, "full_contract"),
            "target_observations": len(target),
            "target_adaptation": rate(target),
            "non_target_observations": len(non_target),
            "non_target_preservation": rate(non_target),
            "example_target_pairs": len(pair_rows),
            "visible_pair_pass": rate(pair_rows, "visible_pass"),
            "held_out_pair_pass": rate(pair_rows, "hidden_pass"),
            "false_completeness": rate(pair_rows, "false_complete"),
            "false_completeness_given_visible_pass": rate(visible_passed, "false_complete"),
        }

    model_summary = []
    for model in models:
        model_summary.append(
            {
                "model": model,
                **metrics(
                    [row for row in behavioral_cells if row["model"] == model],
                    [row for row in requirements if row["model"] == model],
                    [row for row in calibration if row["model"] == model],
                ),
            }
        )

    families = sorted({row["family"] for row in cells})
    family_model = []
    for family in families:
        for model in models:
            family_model.append(
                {
                    "family": family,
                    "model": model,
                    **metrics(
                        [row for row in behavioral_cells if row["family"] == family and row["model"] == model],
                        [row for row in requirements if row["family"] == family and row["model"] == model],
                        [row for row in calibration if row["family"] == family and row["model"] == model],
                    ),
                }
            )

    variant_model = []
    mutations = sorted({(row["family"], row["variant"]) for row in cells if not row["base"]})
    for family, variant in mutations:
        for model in models:
            selected = [row for row in mutation_requirements if row["family"] == family and row["variant"] == variant and row["model"] == model]
            variant_model.append(
                {
                    "family": family,
                    "variant": variant,
                    "model": model,
                    "target_adaptation": rate([row for row in selected if row["is_mutation_target"]]),
                    "non_target_preservation": rate([row for row in selected if not row["is_mutation_target"]]),
                }
            )

    collateral = []
    for family, variant in mutations:
        for model in models:
            family_rows = [row for row in requirements if row["family"] == family and row["model"] == model and not row["is_mutation_target"]]
            base_rate = rate([row for row in family_rows if row["base"]])
            variant_rate = rate([row for row in family_rows if row["variant"] == variant])
            collateral.append(
                {
                    "family": family,
                    "variant": variant,
                    "model": model,
                    "base_non_target": base_rate,
                    "variant_non_target": variant_rate,
                    "collateral_delta": None if base_rate is None or variant_rate is None else variant_rate - base_rate,
                }
            )

    type_model = []
    for req_type in sorted({row["requirement_type"] for row in requirements}):
        for model in models:
            selected = [row for row in requirements if row["requirement_type"] == req_type and row["model"] == model]
            type_model.append({"requirement_type": req_type, "model": model, "n": len(selected), "fidelity": rate(selected)})

    trial_model = []
    trials = sorted({row["trial"] for row in behavioral_cells})
    for model in models:
        for trial in trials:
            selected_cells = [row for row in behavioral_cells if row["model"] == model and row["trial"] == trial]
            selected_requirements = [row for row in requirements if row["model"] == model and row["trial"] == trial]
            trial_model.append(
                {
                    "model": model,
                    "trial": trial,
                    "cells": len(selected_cells),
                    "requirement_fidelity": rate(selected_requirements),
                    "full_contract_success": rate(selected_cells, "full_contract"),
                }
            )

    resource_rows = [row for row in cells if row["resource_eligible"]]
    resources = []
    for model in models:
        for success in [True, False]:
            selected = [row for row in resource_rows if row["model"] == model and row["full_contract"] is success]
            resources.append(
                {
                    "model": model,
                    "full_contract": success,
                    "cells": len(selected),
                    "first_prompt_tokens": distribution(row["first_prompt_tokens"] for row in selected),
                    "total_tokens": distribution(row["total_tokens"] for row in selected),
                    "completion_tokens": distribution(row["completion_tokens"] for row in selected),
                    "seconds": distribution(row["secs"] for row in selected),
                    "cost_usd": distribution(row["cost_usd"] for row in selected),
                    "api_calls": distribution(row["api_calls"] for row in selected),
                    "tool_calls": distribution(row["tool_calls"] for row in selected),
                }
            )

    overall = metrics(behavioral_cells, requirements, calibration)
    return {
        "overall": overall,
        "model": model_summary,
        "family_model": family_model,
        "variant_model": variant_model,
        "collateral": collateral,
        "requirement_type_model": type_model,
        "trial_model": trial_model,
        "resources": resources,
    }


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def pct(value: float | None) -> str:
    return "NA" if value is None else f"{value * 100:.1f}%"


def number(value: float | None, digits: int = 1) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def svg_text(x, y, value, size=13, anchor="start", weight="normal", fill="#111827") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{html.escape(str(value))}</text>'


def svg_document(width: int, height: int, elements: list[str], title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">\n'
        f'<rect width="100%" height="100%" fill="white"/>\n'
        + "\n".join(elements)
        + "\n</svg>\n"
    )


def blue(value: float | None) -> str:
    if value is None:
        return "#e5e7eb"
    low = (239, 246, 255)
    high = (30, 64, 175)
    value = max(0.0, min(1.0, value))
    rgb = tuple(round(a + (b - a) * value) for a, b in zip(low, high))
    return "#%02x%02x%02x" % rgb


def chart_heatmap(summary: dict, models: list[str], path: Path) -> None:
    rows = summary["requirement_type_model"]
    types = sorted({row["requirement_type"] for row in rows})
    values = {(row["requirement_type"], row["model"]): row for row in rows}
    cell_w, cell_h, left, top = 200, 58, 210, 90
    width, height = left + cell_w * len(models) + 40, top + cell_h * len(types) + 55
    elements = [svg_text(28, 34, "Requirement fidelity by requirement type and model", 20, weight="600"), svg_text(28, 58, "Cell labels show pass rate and requirement-observation count.", 12, fill="#4b5563")]
    for column, model in enumerate(models):
        elements.append(svg_text(left + column * cell_w + cell_w / 2, top - 18, model, 13, "middle", "600"))
    for row_index, req_type in enumerate(types):
        y = top + row_index * cell_h
        elements.append(svg_text(left - 14, y + 35, req_type, 13, "end"))
        for column, model in enumerate(models):
            x = left + column * cell_w
            value = values.get((req_type, model), {"fidelity": None, "n": 0})
            fidelity = value["fidelity"]
            elements.append(f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" rx="4" fill="{blue(fidelity)}"/>')
            text_fill = "white" if fidelity is not None and fidelity >= 0.58 else "#111827"
            elements.append(svg_text(x + (cell_w - 4) / 2, y + 24, pct(fidelity), 14, "middle", "600", text_fill))
            elements.append(svg_text(x + (cell_w - 4) / 2, y + 43, f"n={value['n']}", 11, "middle", fill=text_fill))
    path.write_text(svg_document(width, height, elements, "Requirement fidelity heatmap"), encoding="utf-8")


def chart_scatter(summary: dict, models: list[str], path: Path) -> None:
    rows = summary["variant_model"]
    panel_w, plot, left, top = 330, 245, 62, 92
    width, height = panel_w * len(models) + 24, 430
    elements = [svg_text(24, 34, "Mutation target adaptation vs non-target preservation", 20, weight="600"), svg_text(24, 58, "Each point is one family mutation; upper-right indicates local, complete adaptation.", 12, fill="#4b5563")]
    abbreviations = {"cursorvault": "CV", "configweave": "CW", "idledger": "IL", "tokenquota": "TQ", "wirecodec": "WC", "detreport": "DR"}
    for model_index, model in enumerate(models):
        x0 = model_index * panel_w + left
        y0 = top
        elements.append(svg_text(x0 + plot / 2, y0 - 18, model, 14, "middle", "600"))
        for tick in range(6):
            value = tick / 5
            x = x0 + value * plot
            y = y0 + plot - value * plot
            elements.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + plot}" stroke="#e5e7eb"/>')
            elements.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + plot}" y2="{y:.1f}" stroke="#e5e7eb"/>')
            elements.append(svg_text(x, y0 + plot + 19, f"{value:.1f}", 10, "middle", fill="#4b5563"))
            if model_index == 0:
                elements.append(svg_text(x0 - 9, y + 4, f"{value:.1f}", 10, "end", fill="#4b5563"))
        elements.append(f'<rect x="{x0}" y="{y0}" width="{plot}" height="{plot}" fill="none" stroke="#111827"/>')
        selected = [row for row in rows if row["model"] == model]
        for point_index, row in enumerate(selected):
            if row["non_target_preservation"] is None or row["target_adaptation"] is None:
                continue
            x = x0 + row["non_target_preservation"] * plot
            y = y0 + plot - row["target_adaptation"] * plot
            color = MODEL_COLORS[model_index % len(MODEL_COLORS)]
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" fill-opacity="0.78" stroke="white"/>')
            label = f"{abbreviations.get(row['family'], row['family'][:2].upper())}:{row['variant'][:4]}"
            dy = -7 if point_index % 2 == 0 else 13
            elements.append(svg_text(x + 6, y + dy, label, 8, fill="#374151"))
    elements.append(svg_text(width / 2, height - 28, "Non-target preservation", 13, "middle", "600"))
    elements.append(f'<text x="18" y="{top + plot / 2}" transform="rotate(-90 18 {top + plot / 2})" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13" text-anchor="middle" font-weight="600" fill="#111827">Target adaptation</text>')
    path.write_text(svg_document(width, height, elements, "Target adaptation versus preservation scatter plot"), encoding="utf-8")


def chart_calibration(summary: dict, models: list[str], path: Path) -> None:
    rows = {row["model"]: row for row in summary["model"]}
    width, height, left, top, plot_h = 900, 470, 85, 90, 300
    group_w = (width - left - 50) / len(models)
    elements = [svg_text(24, 34, "Declared-example and held-out calibration", 20, weight="600"), svg_text(24, 58, "Rates are computed over declared example–requirement pairs.", 12, fill="#4b5563")]
    for tick in range(6):
        value = tick / 5
        y = top + plot_h - value * plot_h
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - 35}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        elements.append(svg_text(left - 10, y + 4, f"{value:.1f}", 11, "end", fill="#4b5563"))
    for index, model in enumerate(models):
        center = left + group_w * (index + 0.5)
        for offset, key, color, label in [(-34, "visible_pair_pass", "#60a5fa", "visible"), (34, "held_out_pair_pass", "#1d4ed8", "held-out")]:
            value = rows[model][key]
            bar_h = 0 if value is None else value * plot_h
            x = center + offset - 26
            y = top + plot_h - bar_h
            elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="52" height="{bar_h:.1f}" fill="{color}"/>')
            elements.append(svg_text(x + 26, y - 7, pct(value), 11, "middle", "600"))
        elements.append(svg_text(center, top + plot_h + 25, model, 12, "middle", "600"))
    elements.extend([
        '<rect x="640" y="52" width="13" height="13" fill="#60a5fa"/>',
        svg_text(659, 63, "visible pair pass", 11),
        '<rect x="760" y="52" width="13" height="13" fill="#1d4ed8"/>',
        svg_text(779, 63, "held-out pair pass", 11),
    ])
    path.write_text(svg_document(width, height, elements, "Visible versus held-out calibration chart"), encoding="utf-8")


def chart_reliability(summary: dict, models: list[str], path: Path) -> None:
    rows = summary["trial_model"]
    width, height, left, top, plot_w = 960, 430, 235, 90, 670
    metrics = [("requirement_fidelity", "requirement fidelity", "#2563eb"), ("full_contract_success", "full-contract success", "#dc2626")]
    elements = [svg_text(24, 34, "Across-trial dispersion", 20, weight="600"), svg_text(24, 58, "Dots are trial aggregates; line spans show the observed minimum and maximum, not confidence intervals.", 12, fill="#4b5563")]
    for tick in range(6):
        value = tick / 5
        x = left + value * plot_w
        elements.append(f'<line x1="{x:.1f}" y1="{top - 12}" x2="{x:.1f}" y2="{height - 55}" stroke="#e5e7eb"/>')
        elements.append(svg_text(x, height - 32, f"{value:.1f}", 11, "middle", fill="#4b5563"))
    row_y = top
    for model in models:
        selected = [row for row in rows if row["model"] == model]
        for metric, label, color in metrics:
            values = [row[metric] for row in selected if row[metric] is not None]
            elements.append(svg_text(left - 16, row_y + 4, f"{model} · {label}", 12, "end"))
            if values:
                x_min = left + min(values) * plot_w
                x_max = left + max(values) * plot_w
                elements.append(f'<line x1="{x_min:.1f}" y1="{row_y}" x2="{x_max:.1f}" y2="{row_y}" stroke="{color}" stroke-width="3"/>')
                for trial_index, value in enumerate(values):
                    x = left + value * plot_w
                    dy = [-5, 0, 5][trial_index % 3]
                    elements.append(f'<circle cx="{x:.1f}" cy="{row_y + dy:.1f}" r="4.5" fill="{color}" stroke="white"/>')
            row_y += 43
        row_y += 11
    path.write_text(svg_document(width, height, elements, "Across-trial reliability interval plot"), encoding="utf-8")


def chart_resources(summary: dict, models: list[str], path: Path) -> None:
    resource_rows = summary["resources"]
    width, height = 1080, 560
    left, top, panel_w, plot_h = 145, 95, 410, 365
    elements = [svg_text(24, 34, "Resource distributions for clean completed cells", 20, weight="600"), svg_text(24, 58, "Box spans Q1–Q3; whiskers span observed min–max. Retried or incomplete telemetry is excluded.", 12, fill="#4b5563")]
    panels = [("total_tokens", "Total tokens"), ("seconds", "Wall-clock seconds")]
    groups = [(model, success) for model in models for success in [True, False]]
    for panel_index, (metric, title) in enumerate(panels):
        x0 = left + panel_index * (panel_w + 100)
        dists = {(row["model"], row["full_contract"]): row[metric] for row in resource_rows}
        maxima = [value["max"] for value in dists.values() if value["max"] is not None]
        maximum = max(maxima) if maxima else 1.0
        elements.append(svg_text(x0 + panel_w / 2, top - 20, title, 14, "middle", "600"))
        for tick in range(5):
            value = maximum * tick / 4
            x = x0 + panel_w * tick / 4
            elements.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#e5e7eb"/>')
            elements.append(svg_text(x, top + plot_h + 22, f"{value:,.0f}", 10, "middle", fill="#4b5563"))
        for group_index, (model, success) in enumerate(groups):
            y = top + 28 + group_index * 54
            if panel_index == 0:
                label = f"{model} · {'pass' if success else 'not full-pass'}"
                elements.append(svg_text(x0 - 12, y + 4, label, 11, "end"))
            dist = dists[(model, success)]
            if dist["n"] == 0:
                elements.append(svg_text(x0 + 5, y + 4, "n=0", 10, fill="#9ca3af"))
                continue
            scale = lambda value: x0 + (value / maximum) * panel_w
            color = "#059669" if success else "#dc2626"
            elements.append(f'<line x1="{scale(dist["min"]):.1f}" y1="{y}" x2="{scale(dist["max"]):.1f}" y2="{y}" stroke="{color}" stroke-width="2"/>')
            elements.append(f'<rect x="{scale(dist["q1"]):.1f}" y="{y - 9}" width="{max(1.0, scale(dist["q3"]) - scale(dist["q1"])):.1f}" height="18" fill="{color}" fill-opacity="0.28" stroke="{color}"/>')
            elements.append(f'<line x1="{scale(dist["median"]):.1f}" y1="{y - 10}" x2="{scale(dist["median"]):.1f}" y2="{y + 10}" stroke="{color}" stroke-width="2"/>')
            elements.append(svg_text(scale(dist["max"]) + 5, y + 4, f"n={dist['n']}", 9, fill="#4b5563"))
    path.write_text(svg_document(width, height, elements, "Resource distributions"), encoding="utf-8")


def markdown_report(study: dict, session: dict, summary: dict, cells: list[dict]) -> str:
    exclusions = defaultdict(int)
    for cell in cells:
        if not cell["behavioral"]:
            exclusions[cell["analysis_status"]] += 1
    lines = [
        "# Simplex execution fidelity pilot v1 — controlled results",
        "",
        "This report characterizes execution fidelity under the tested Simplex v0.6 specifications. It does not compare Simplex with prose and does not estimate a representation effect.",
        "",
        "## Run inventory",
        "",
        f"- Run ID: `{session.get('run_id')}`",
        f"- Planned cells: {study['matrix']['expected_cells']}",
        f"- Recorded cells: {len(cells)}",
        f"- Behaviorally evaluated cells: {sum(1 for row in cells if row['behavioral'])}",
        f"- Clean resource-eligible cells: {sum(1 for row in cells if row['resource_eligible'])}",
        "",
        "## Primary outcomes by model",
        "",
        "| model | requirement fidelity | full-contract success | target adaptation | non-target preservation | false completeness | behavioral cells |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["model"]:
        lines.append(
            f"| {row['model']} | {pct(row['requirement_fidelity'])} | {pct(row['full_contract_success'])} | {pct(row['target_adaptation'])} | {pct(row['non_target_preservation'])} | {pct(row['false_completeness'])} | {row['behavioral_cells']} |"
        )
    lines.extend([
        "",
        "Target adaptation and non-target preservation use mutation variants only. False completeness is the fraction of all declared example–requirement pairs where visible evidence passed while held-out evidence for the same requirement failed.",
        "",
        "## Collateral regression by mutation",
        "",
        "`delta` is mutation non-target fidelity minus the corresponding base non-target fidelity within family and model.",
        "",
        "| family | mutation | model | base | mutation | delta |",
        "|---|---|---|---:|---:|---:|",
    ])
    for row in summary["collateral"]:
        delta = "NA" if row["collateral_delta"] is None else f"{row['collateral_delta']:+.3f}"
        lines.append(f"| {row['family']} | {row['variant']} | {row['model']} | {pct(row['base_non_target'])} | {pct(row['variant_non_target'])} | {delta} |")
    lines.extend([
        "",
        "## Figures",
        "",
        "- [Requirement fidelity heatmap](figures/requirement-fidelity-heatmap.svg)",
        "- [Target adaptation versus preservation](figures/target-preservation-scatter.svg)",
        "- [Visible versus held-out calibration](figures/visible-heldout-calibration.svg)",
        "- [Across-trial dispersion](figures/trial-dispersion.svg)",
        "- [Resource distributions](figures/resource-distributions.svg)",
        "",
        "## Exclusions and limitations",
        "",
    ])
    if exclusions:
        for status, count in sorted(exclusions.items()):
            lines.append(f"- `{status}`: {count} cells")
    else:
        lines.append("- No cells were excluded from behavioral analysis.")
    lines.extend([
        "- Timeouts and agent errors are prespecified behavioral failures and receive failed requirement outcomes; provider rejections are unobserved.",
        "- Resource summaries exclude any cell with request retries, whole-agent retries, missing token telemetry, or no completed grader result.",
        "- Across-trial ranges are descriptive and are not confidence intervals.",
        "- These six synthetic families and three models do not support claims about general software-engineering performance or superiority over another prompt representation.",
        "- The task authors also implemented the graders; independent semantic review remains desirable before confirmatory replication.",
        "",
        "## Machine-readable outputs",
        "",
        "- `analysis.json`: summaries, classifications, and provenance",
        "- `cells.csv`: one row per planned inference cell",
        "- `requirements.csv`: one row per evaluated requirement observation",
        "- `checks.csv`: grader-check outcomes for completed graders",
        "- `calibration.csv`: declared example–requirement calibration pairs",
        "",
    ])
    return "\n".join(lines)


def analyze(run_dir: Path, output_dir: Path, variants_path: Path, study_path: Path, allow_incomplete: bool = False) -> dict:
    study = read_json(study_path)
    variants = read_json(variants_path)["variants"]
    session_path = run_dir / "session.json"
    results_path = run_dir / "results.jsonl"
    session = read_json(session_path)
    rows = read_jsonl(results_path)
    validate_session(session, study, variants)

    expected = expected_keys(study, variants)
    actual = [row_key(row) for row in rows]
    duplicates = sorted({key for key in actual if actual.count(key) > 1})
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    if duplicates or unexpected or (missing and not allow_incomplete):
        raise ValueError(f"matrix mismatch: missing={missing}, unexpected={unexpected}, duplicates={duplicates}")
    selected_rows = [row for row in rows if row_key(row) in expected]
    cells, requirements, checks, calibration = build_tables(run_dir, selected_rows, variants)
    summary = summarize(cells, requirements, calibration, study["models"])

    output_dir.mkdir(parents=True, exist_ok=True)
    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cells.csv", cells)
    write_csv(output_dir / "requirements.csv", requirements)
    write_csv(output_dir / "checks.csv", checks)
    write_csv(output_dir / "calibration.csv", calibration)
    chart_heatmap(summary, study["models"], figures / "requirement-fidelity-heatmap.svg")
    chart_scatter(summary, study["models"], figures / "target-preservation-scatter.svg")
    chart_calibration(summary, study["models"], figures / "visible-heldout-calibration.svg")
    chart_reliability(summary, study["models"], figures / "trial-dispersion.svg")
    chart_resources(summary, study["models"], figures / "resource-distributions.svg")

    analysis = {
        "schema_version": 1,
        "study": study["name"],
        "status": "preliminary-engineering-pilot",
        "run_id": session.get("run_id"),
        "provenance": {
            "run_dir": str(run_dir.resolve()),
            "results_jsonl_sha256": sha256(results_path),
            "session_sha256": sha256(session_path),
            "variants_sha256": sha256(variants_path),
            "study_sha256": sha256(study_path),
        },
        "matrix": {
            "expected_cells": len(expected),
            "recorded_cells": len(selected_rows),
            "missing_cells": [list(key) for key in missing],
            "unexpected_cells": [list(key) for key in unexpected],
            "duplicate_cells": [list(key) for key in duplicates],
            "behavioral_cells": sum(1 for row in cells if row["behavioral"]),
            "resource_eligible_cells": sum(1 for row in cells if row["resource_eligible"]),
            "classifications": dict(sorted((status, sum(1 for row in cells if row["analysis_status"] == status)) for status in {row["analysis_status"] for row in cells})),
        },
        "definitions": {
            "behavioral_failures": sorted(BEHAVIOR_FAILURE_OUTCOMES),
            "provider_rejections": "excluded as unobserved",
            "requirement_weighting": "one vote per requirement observation",
            "false_completeness_denominator": "all declared example-requirement pairs in behaviorally evaluated cells",
            "resource_eligibility": "completed grader, complete positive input telemetry, zero request retries, one whole-agent attempt",
            "trial_intervals": "observed minimum-maximum range; not a confidence interval",
        },
        "summary": summary,
    }
    (output_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "RESULTS.md").write_text(markdown_report(study, session, summary, cells), encoding="utf-8")
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="ThinkBench raw run directory containing session.json")
    parser.add_argument("output_dir", type=Path, help="directory for analysis tables, figures, and report")
    parser.add_argument("--variants", type=Path, default=DEFAULT_VARIANTS)
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--allow-incomplete", action="store_true", help="emit an explicitly incomplete analysis instead of rejecting missing cells")
    args = parser.parse_args()
    analysis = analyze(args.run_dir.resolve(), args.output_dir.resolve(), args.variants.resolve(), args.study.resolve(), args.allow_incomplete)
    print(
        f"analyzed {analysis['matrix']['recorded_cells']}/{analysis['matrix']['expected_cells']} cells; "
        f"behavioral={analysis['matrix']['behavioral_cells']}, resource-eligible={analysis['matrix']['resource_eligible_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
