#!/usr/bin/env python3
"""Generate or verify the post-run Simplex fidelity archive manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "archive-manifest.json"


def excluded(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if path == OUTPUT:
        return True
    if "__pycache__" in relative.parts or ".pytest_cache" in relative.parts:
        return True
    if path.suffix in {".pyc", ".pyo", ".pyd"}:
        return True
    parts = relative.parts
    return (
        len(parts) >= 5
        and parts[0] == "raw-runs"
        and "workspace" in parts
        and ".cache" in parts
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build() -> dict:
    files: dict[str, dict[str, int | str]] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or excluded(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return {
        "schema_version": 1,
        "study": "simplex-fidelity-v1",
        "run_id": 1784490337,
        "hash_algorithm": "sha256",
        "scope": "all retained regular files below the study root except this manifest",
        "exclusions": [
            "archive-manifest.json (self-reference)",
            "Python bytecode and __pycache__ directories",
            "pytest caches",
            "package-manager caches below raw-run workspaces",
        ],
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files.values()),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the current manifest")
    mode.add_argument("--check", action="store_true", help="verify the checked-in manifest")
    args = parser.parse_args()

    expected = build()
    if args.write:
        OUTPUT.write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"wrote {OUTPUT.name}: {expected['file_count']} files, "
            f"{expected['total_bytes']} bytes"
        )
        return 0

    if not OUTPUT.exists():
        raise SystemExit(f"missing {OUTPUT}; run with --write")
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if actual != expected:
        raise SystemExit("archive manifest is stale; run with --write and review the change")
    print(
        f"archive manifest is current: {expected['file_count']} files, "
        f"{expected['total_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
