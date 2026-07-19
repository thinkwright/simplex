#!/usr/bin/env bash
set -euo pipefail

study_root="/home/bran/code/simplex/research/simplex-fidelity-v1"
simplex_root="/home/bran/code/simplex"
thinkbench_root="/home/bran/code/thinkbench"
simplex_commit="9b1ad43674a715448141a6f09060c82ce626c9a3"
thinkbench_commit="06425846016014bee7aade6e4a4ba5b75a321f93"

if [[ "$(git -C "$simplex_root" rev-parse HEAD)" != "$simplex_commit" ]]; then
  echo "Simplex revision differs from the frozen protocol" >&2
  exit 1
fi
if [[ "$(git -C "$thinkbench_root" rev-parse HEAD)" != "$thinkbench_commit" ]]; then
  echo "ThinkBench revision differs from the frozen protocol" >&2
  exit 1
fi

export THINKBENCH_TASKS="$study_root/generated/tasks"
export THINKBENCH_MODELS="$study_root/models.together.json"
export THINKBENCH_RESULTS="$study_root/raw-runs"
export THINKBENCH_TRIALS=3
export THINKBENCH_EFFORT=native
export THINKBENCH_PARALLEL=2

runner_options=(
  --prompt-pack "$study_root/generated/prompt-pack"
  --condition simplex-fidelity-v1
  --job-seed 2026071901
)

if [[ "${1:-}" == "--list" ]]; then
  runner_options+=(--list)
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--list]" >&2
  exit 2
elif [[ -z "${TOGETHER_API_KEY:-}" ]]; then
  task_provider_key="$(pass show providers/together/api-key)"
  if [[ -z "$task_provider_key" ]]; then
    echo "Together API key is empty" >&2
    exit 1
  fi
  export TOGETHER_API_KEY="$task_provider_key"
  unset task_provider_key
fi

exec cargo run --quiet --release --manifest-path "$thinkbench_root/runner/Cargo.toml" -- \
  "${runner_options[@]}" \
  glm-5.2 minimax-m3 qwen3.7-max
