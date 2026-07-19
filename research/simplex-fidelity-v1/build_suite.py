#!/usr/bin/env python3
"""Build the external ThinkBench tasks and Simplex prompt pack for this study."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
FAMILIES_PATH = SOURCES / "families.json"
GENERATED = ROOT / "generated"
ARTIFACT_MANIFEST = ROOT / "artifact-manifest.json"
THINKBENCH = Path("/home/bran/code/thinkbench")
SIMPLEX = Path("/home/bran/code/simplex")
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def substitute(value: str, replacements: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in replacements:
            raise ValueError(f"missing substitution {name!r} in {value!r}")
        return replacements[name]

    return PLACEHOLDER.sub(replace, value)


def item_lines(items: list[dict], replacements: dict[str, str], indent: str = "  ") -> list[str]:
    return [f"{indent}- [{item['id']}] {substitute(item['text'], replacements)}" for item in items]


def render_prompt(family: dict, variant_name: str, variant: dict) -> str:
    replacements = variant["values"]
    lines = ["SIMPLEX: 0.6", ""]
    if family.get("constraints"):
        lines.append(f"CONSTRAINT: {family['name']}_contract")
        lines.extend(item_lines(family["constraints"], replacements))
        lines.append("")

    lines.extend(
        [
            f"FUNCTION: implement_{family['name']}() → output",
            "",
            "RULES:",
        ]
    )
    lines.extend(item_lines(family["rules"], replacements))
    lines.append("")

    baseline = family.get("baseline")
    if baseline:
        lines.extend(["BASELINE:", f"  reference: {baseline['reference']}", "  preserve:"])
        lines.extend(item_lines(baseline["preserve"], replacements, "    "))
        lines.append("  evolve:")
        lines.extend(item_lines(baseline["evolve"], replacements, "    "))
        lines.append("")
        evaluation = family["eval"]
        lines.extend(
            [
                "EVAL:",
                f"  preserve: {evaluation['preserve']}",
                f"  evolve: {evaluation['evolve']}",
                f"  grading: {evaluation['grading']}",
                "",
            ]
        )

    determinism = family.get("determinism")
    if determinism:
        lines.extend(["DETERMINISM:", f"  level: {determinism['level']}", "  stable:"])
        lines.extend(item_lines(determinism["stable"], replacements, "    "))
        lines.append("")

    lines.append("DONE_WHEN:")
    lines.extend(item_lines(family["done_when"], replacements))
    lines.extend(["", "EXAMPLES:"])
    for example in family["examples"]:
        text = substitute(example["text"], replacements)
        lines.append(f"  - [{example['id']}] {example['kind']}: {text}")
    lines.extend(["", "ERRORS:"])
    lines.extend(item_lines(family["errors"], replacements))
    lines.append("  - any unhandled condition → fail with descriptive message")
    lines.extend(["", "COVERS:"])
    for example in family["examples"]:
        lines.append(f"  - {example['id']} → {', '.join(example['covers'])}")
    return "\n".join(lines) + "\n"


def contract_items(family: dict) -> list[dict]:
    items = []
    for role, key in [
        ("CONSTRAINT", "constraints"),
        ("RULES", "rules"),
        ("DONE_WHEN", "done_when"),
        ("ERRORS", "errors"),
    ]:
        items.extend({"id": item["id"], "role": role} for item in family.get(key, []))
    if family.get("baseline"):
        items.extend(
            {"id": item["id"], "role": "BASELINE.preserve"}
            for item in family["baseline"]["preserve"]
        )
        items.extend(
            {"id": item["id"], "role": "BASELINE.evolve"}
            for item in family["baseline"]["evolve"]
        )
    if family.get("determinism"):
        items.extend(
            {"id": item["id"], "role": "DETERMINISM.stable"}
            for item in family["determinism"]["stable"]
        )
    return items


def validate_family(family: dict) -> None:
    contract = contract_items(family)
    contract_ids = [item["id"] for item in contract]
    example_ids = [item["id"] for item in family["examples"]]
    all_ids = contract_ids + example_ids
    if len(all_ids) != len(set(all_ids)):
        raise ValueError(f"{family['name']}: duplicate stable identifier")
    covered = set()
    for example in family["examples"]:
        if not example["covers"]:
            raise ValueError(f"{family['name']}: example {example['id']} has no COVERS target")
        unknown = set(example["covers"]) - set(contract_ids)
        if unknown:
            raise ValueError(f"{family['name']}: unknown COVERS targets {sorted(unknown)}")
        covered.update(example["covers"])
    missing = set(contract_ids) - covered
    if missing:
        raise ValueError(f"{family['name']}: uncovered contract items {sorted(missing)}")
    variants = family["variants"]
    if len(variants) != 3 or "base" not in variants:
        raise ValueError(f"{family['name']}: expected base plus two variants")
    slugs = [variant["slug"] for variant in variants.values()]
    if len(slugs) != len(set(slugs)):
        raise ValueError(f"{family['name']}: duplicate task slug")
    target = family["mutation_target"]
    if target not in contract_ids:
        raise ValueError(f"{family['name']}: unknown mutation target {target}")

    base = variants["base"]
    for name, variant in variants.items():
        for rule in family["rules"]:
            base_text = substitute(rule["text"], base["values"])
            variant_text = substitute(rule["text"], variant["values"])
            if rule["id"] != target and base_text != variant_text:
                raise ValueError(f"{family['name']}/{name}: non-target rule {rule['id']} changed")
        for example in family["examples"]:
            base_text = substitute(example["text"], base["values"])
            variant_text = substitute(example["text"], variant["values"])
            if target not in example["covers"] and base_text != variant_text:
                raise ValueError(
                    f"{family['name']}/{name}: example {example['id']} changed without covering {target}"
                )


def git_commit(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def build_tree(destination: Path) -> dict:
    families_doc = json.loads(FAMILIES_PATH.read_text(encoding="utf-8"))
    families = families_doc["families"]
    common_grader = (SOURCES / "grader_common.py").read_text(encoding="utf-8")
    prompts = {}
    variant_rows = []
    seen_slugs = set()

    for family in families:
        validate_family(family)
        reference_template = (SOURCES / family["name"] / "reference.py").read_text(encoding="utf-8")
        grader_body = (SOURCES / family["name"] / "grader.py").read_text(encoding="utf-8")
        contracts = contract_items(family)
        for variant_name, variant in family["variants"].items():
            slug = variant["slug"]
            if slug in seen_slugs:
                raise ValueError(f"duplicate task slug {slug}")
            seen_slugs.add(slug)
            mode = variant["mode"]
            prompt = render_prompt(family, variant_name, variant)
            prompt_path = destination / "prompt-pack" / "prompts" / f"{slug}.simplex"
            write_text(prompt_path, prompt)
            prompts[slug] = f"prompts/{slug}.simplex"

            task = destination / "tasks" / slug
            write_text(
                task / "brief.txt",
                "This experimental task must be run with the simplex-fidelity-v1 prompt pack.",
            )
            grader = (
                common_grader.rstrip()
                + "\n\n"
                + f"MODE = {mode!r}\nTASK_SLUG = {slug!r}\n\n"
                + grader_body.lstrip()
            )
            write_text(task / "grade.py", grader)
            reference = reference_template.replace("__MODE__", mode)
            write_text(task / "reference" / family["project"] / "public.py", reference)
            write_text(task / "reference" / family["project"] / "__init__.py", "from .public import *")
            if family["name"] == "detreport":
                write_text(
                    task / "reference" / family["project"] / "__main__.py",
                    "import json\nimport sys\n\nfrom .public import build_report\n\n"
                    "with open(sys.argv[1], encoding='utf-8') as handle:\n"
                    "    events = json.load(handle)\n"
                    "print(build_report(events))",
                )

            variant_rows.append(
                {
                    "task": slug,
                    "family": family["name"],
                    "variant": variant_name,
                    "mode": mode,
                    "base": variant_name == "base",
                    "mutation_target": family["mutation_target"],
                    "requirements": contracts,
                    "examples": [
                        {"id": example["id"], "covers": example["covers"]}
                        for example in family["examples"]
                    ],
                    "prompt": f"prompt-pack/prompts/{slug}.simplex",
                }
            )

    pack = {
        "$schema": "https://raw.githubusercontent.com/thinkwright/thinkbench/main/prompt-packs/schema.json",
        "schema_version": 1,
        "name": "simplex-fidelity-v1",
        "format": "simplex-v0.6",
        "description": "Simplex-only controlled execution-fidelity pilot",
        "prompts": dict(sorted(prompts.items())),
    }
    write_text(destination / "prompt-pack" / "pack.json", json.dumps(pack, indent=2, sort_keys=True))
    write_text(
        destination / "variants.json",
        json.dumps({"schema_version": 1, "variants": variant_rows}, indent=2, sort_keys=True),
    )
    return {"families": len(families), "tasks": len(variant_rows), "variants": variant_rows}


def hash_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def source_hashes() -> dict[str, str]:
    paths = [
        ROOT / "PROTOCOL.md",
        ROOT / "study.json",
        ROOT / "models.together.json",
        ROOT / "build_suite.py",
        ROOT / "validate_suite.py",
        ROOT / "analyze.py",
        ROOT / "run_controlled.sh",
        ROOT / "construction-report.json",
        ROOT / "tests" / "test_analyze.py",
    ]
    paths.extend(path for path in sorted(SOURCES.rglob("*")) if path.is_file())
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}


def expected_manifest(temp_generated: Path, summary: dict) -> dict:
    generated_hashes = {
        path.relative_to(temp_generated).as_posix(): sha256_file(path)
        for path in sorted(temp_generated.rglob("*"))
        if path.is_file()
    }
    return {
        "schema_version": 1,
        "study": "simplex-fidelity-v1",
        "status": "pre-inference",
        "simplex_commit": git_commit(SIMPLEX),
        "thinkbench_commit": git_commit(THINKBENCH),
        "protocol_sha256": sha256_file(ROOT / "PROTOCOL.md"),
        "study_sha256": sha256_file(ROOT / "study.json"),
        "model_config_sha256": sha256_file(ROOT / "models.together.json"),
        "analysis_sha256": sha256_file(ROOT / "analyze.py"),
        "construction_report_sha256": sha256_file(ROOT / "construction-report.json"),
        "families": summary["families"],
        "tasks": summary["tasks"],
        "expected_cells": json.loads((ROOT / "study.json").read_text(encoding="utf-8"))["matrix"]["expected_cells"],
        "source_files": source_hashes(),
        "generated_files": generated_hashes,
    }


def compare_files(expected_root: Path, actual_root: Path) -> list[str]:
    expected = {
        path.relative_to(expected_root).as_posix(): sha256_file(path)
        for path in expected_root.rglob("*")
        if path.is_file()
    }
    actual = {
        path.relative_to(actual_root).as_posix(): sha256_file(path)
        for path in actual_root.rglob("*")
        if path.is_file()
    }
    issues = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            issues.append(f"missing generated file: {name}")
        elif name not in expected:
            issues.append(f"unexpected generated file: {name}")
        elif expected[name] != actual[name]:
            issues.append(f"stale generated file: {name}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify generated artifacts without replacing them")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="simplex-fidelity-build-") as directory:
        temp_generated = Path(directory) / "generated"
        summary = build_tree(temp_generated)
        manifest = expected_manifest(temp_generated, summary)
        manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

        if args.check:
            issues = compare_files(temp_generated, GENERATED) if GENERATED.is_dir() else ["generated directory is missing"]
            if not ARTIFACT_MANIFEST.is_file():
                issues.append("artifact-manifest.json is missing")
            elif ARTIFACT_MANIFEST.read_text(encoding="utf-8") != manifest_text:
                issues.append("artifact-manifest.json is stale")
            if issues:
                for issue in issues:
                    print(issue)
                return 1
            print(f"generated artifacts are current: {summary['tasks']} tasks")
            return 0

        if GENERATED.exists():
            if GENERATED.resolve() != (ROOT / "generated").resolve():
                raise RuntimeError("refusing to replace an unexpected generated directory")
            shutil.rmtree(GENERATED)
        shutil.copytree(temp_generated, GENERATED)
        ARTIFACT_MANIFEST.write_text(manifest_text, encoding="utf-8")
        print(f"built {summary['tasks']} tasks across {summary['families']} families")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
