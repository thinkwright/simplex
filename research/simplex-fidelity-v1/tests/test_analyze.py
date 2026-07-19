from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analyze  # noqa: E402


def scorecard_for(variant, failed_requirement=None):
    checks = []
    for example in variant["examples"]:
        for requirement_id in example["covers"]:
            checks.append(
                {
                    "name": f"visible_{example['id']}_{requirement_id}",
                    "requirement_id": requirement_id,
                    "requirement_type": analyze.requirement_type(requirement_id),
                    "evidence": "visible",
                    "example_id": example["id"],
                    "passed": True,
                    "note": "",
                }
            )
    for item in variant["requirements"]:
        requirement_id = item["id"]
        checks.append(
            {
                "name": f"hidden_{requirement_id}",
                "requirement_id": requirement_id,
                "requirement_type": analyze.requirement_type(requirement_id),
                "evidence": "hidden",
                "example_id": None,
                "passed": requirement_id != failed_requirement,
                "note": "synthetic failure" if requirement_id == failed_requirement else "",
            }
        )
    requirements = {}
    for item in variant["requirements"]:
        requirement_id = item["id"]
        selected = [check for check in checks if check["requirement_id"] == requirement_id]
        passed_checks = sum(check["passed"] for check in selected)
        requirements[requirement_id] = {
            "type": analyze.requirement_type(requirement_id),
            "passed": passed_checks == len(selected),
            "passed_checks": passed_checks,
            "total_checks": len(selected),
            "visible_checks": sum(check["evidence"] == "visible" for check in selected),
            "hidden_checks": sum(check["evidence"] == "hidden" for check in selected),
        }
    passed = sum(value["passed"] for value in requirements.values())
    return {
        "score": passed / len(requirements),
        "passed": passed,
        "total": len(requirements),
        "import_ok": True,
        "requirements": requirements,
        "checks": checks,
    }


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.study = json.loads((ROOT / "study.json").read_text(encoding="utf-8"))
        self.variants = json.loads((ROOT / "generated" / "variants.json").read_text(encoding="utf-8"))["variants"]

    def make_run(self, root: Path, omit_last=False):
        run_dir = root / "run"
        run_dir.mkdir()
        session = {
            "run_id": 123,
            "models": self.study["models"],
            "trials": self.study["trials"],
            "conditions": [{"name": self.study["condition"], "format": "simplex-v0.6"}],
            "job_seed": self.study["job_seed"],
            "tasks": [variant["task"] for variant in self.variants],
        }
        (run_dir / "session.json").write_text(json.dumps(session), encoding="utf-8")
        rows = []
        for variant in self.variants:
            for model in self.study["models"]:
                for trial in range(1, self.study["trials"] + 1):
                    failed_requirement = None
                    if variant["task"] == "cursorvault_inclusive" and model == "glm-5.2" and trial == 1:
                        failed_requirement = variant["mutation_target"]
                    scorecard = scorecard_for(variant, failed_requirement)
                    row = {
                        "run_id": 123,
                        "worker": model,
                        "model": model,
                        "task": variant["task"],
                        "condition": self.study["condition"],
                        "trial": trial,
                        "outcome_kind": "completed",
                        "score": scorecard["score"],
                        "passed": scorecard["passed"],
                        "total": scorecard["total"],
                        "secs": 10.0 + trial,
                        "prompt_bytes": 1000,
                        "prompt_chars": 1000,
                        "prompt_lines": 40,
                        "first_prompt_tokens": 500,
                        "first_cached_tokens": 0,
                        "first_completion_tokens": 50,
                        "prompt_tokens": 700,
                        "cached_tokens": 100,
                        "completion_tokens": 200,
                        "api_calls": 2,
                        "calls": 3,
                        "request_retries": 0,
                        "attempts": 1,
                        "cost_usd": 0.01,
                        "note": "",
                    }
                    label = f"{variant['task']}__{self.study['condition']}__{model}__t{trial}"
                    cell_dir = run_dir / label
                    cell_dir.mkdir()
                    (cell_dir / "scorecard.json").write_text(json.dumps(scorecard), encoding="utf-8")
                    rows.append(row)
        if omit_last:
            rows.pop()
        (run_dir / "results.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return run_dir

    def test_complete_matrix_emits_frozen_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = self.make_run(root)
            output = root / "output"
            result = analyze.analyze(run_dir, output, ROOT / "generated" / "variants.json", ROOT / "study.json")
            self.assertEqual(result["matrix"]["recorded_cells"], 162)
            self.assertEqual(result["matrix"]["behavioral_cells"], 162)
            self.assertEqual(result["matrix"]["resource_eligible_cells"], 162)
            glm = next(row for row in result["summary"]["model"] if row["model"] == "glm-5.2")
            self.assertLess(glm["target_adaptation"], 1.0)
            self.assertGreater(glm["false_completeness"], 0.0)
            for name in ["analysis.json", "RESULTS.md", "cells.csv", "requirements.csv", "checks.csv", "calibration.csv"]:
                self.assertTrue((output / name).is_file(), name)
            figures = list((output / "figures").glob("*.svg"))
            self.assertEqual(len(figures), 5)
            self.assertTrue(all(path.read_text(encoding="utf-8").startswith("<svg") for path in figures))

    def test_missing_cell_is_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = self.make_run(root, omit_last=True)
            with self.assertRaisesRegex(ValueError, "matrix mismatch"):
                analyze.analyze(run_dir, root / "output", ROOT / "generated" / "variants.json", ROOT / "study.json")


if __name__ == "__main__":
    unittest.main()
