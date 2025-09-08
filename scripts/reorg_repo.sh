#!/usr/bin/env bash

set -euo pipefail

# Repo Reorganization Helper
# - Creates a new git branch
# - Normalizes directories (scripts/, logs/, outputs/)
# - Moves common scripts to scripts/
# - Relocates Hydra conf/ into sociology_simulation/conf/
# - Adds an ignore block for runtime artifacts
#
# Safe by default: runs in DRY-RUN mode unless --apply is provided.
#
# Usage examples:
#   bash scripts/reorg_repo.sh                 # dry-run summary only
#   bash scripts/reorg_repo.sh --apply         # perform changes (no commit)
#   bash scripts/reorg_repo.sh --apply --commit
#   bash scripts/reorg_repo.sh --apply --branch chore/reorg-20250101
#   bash scripts/reorg_repo.sh --help

DRY_RUN=1
CREATE_COMMIT=0
BRANCH_NAME=""
FORCE=0

notice() { echo "[reorg] $*"; }
warn()   { echo "[reorg][warn] $*" >&2; }
die()    { echo "[reorg][error] $*" >&2; exit 1; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

usage() {
  cat <<'USAGE'
Repo Reorganization Script

Options:
  --apply            Execute changes (default is dry-run)
  --commit           Create a commit at the end
  --branch <name>    Branch to create/switch to (default: chore/reorg-YYYYMMDD)
  --force            Run even with a dirty working tree
  --help             Show this help

Behavior:
  - Creates directories: scripts/, logs/, outputs/
  - Ensures .gitignore has web_data/, logs/, outputs/, __pycache__/ etc.
  - Moves run_simple_web_simulation.py to scripts/ if present
  - Moves conf/ to sociology_simulation/conf/ (merging if needed)
  - Moves root-level script-like Python files (run_*.py, *_script.py) to scripts/
    (excludes tests and package files)

Dry-run shows planned actions only. Use --apply to perform them.
USAGE
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) DRY_RUN=0; shift ;;
    --commit) CREATE_COMMIT=1; shift ;;
    --branch) BRANCH_NAME="${2:-}"; [[ -n "$BRANCH_NAME" ]] || die "--branch requires a name"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

ROOT_DIR=$(pwd)

# Basic checks
require_cmd git
[[ -d .git ]] || die "Please run from the repository root (no .git found)."

# Heuristic: ensure expected package or metadata is present
if [[ ! -d sociology_simulation ]] && [[ ! -f pyproject.toml ]]; then
  warn "Neither 'sociology_simulation/' nor 'pyproject.toml' found at root; proceeding cautiously."
fi

# Ensure clean working tree unless forced
if [[ "$FORCE" -ne 1 ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    die "Working tree is not clean. Commit/stash changes or use --force."
  fi
fi

# Create/switch to branch
if [[ -z "$BRANCH_NAME" ]]; then
  BRANCH_NAME="chore/reorg-$(date +%Y%m%d)"
fi

branch_exists() { git rev-parse --verify --quiet "$1" >/dev/null 2>&1; }
current_branch() { git rev-parse --abbrev-ref HEAD; }

switch_to_branch() {
  local name="$1"
  if branch_exists "$name"; then
    notice "Switching to existing branch: $name"
    if [[ "$DRY_RUN" -eq 0 ]]; then git checkout "$name"; else echo git checkout "$name"; fi
  else
    notice "Creating and switching to new branch: $name"
    if [[ "$DRY_RUN" -eq 0 ]]; then git checkout -b "$name"; else echo git checkout -b "$name"; fi
  fi
}

switch_to_branch "$BRANCH_NAME"

do_run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$*"
  else
    eval "$@"
  fi
}

ensure_dir() {
  local d="$1"
  if [[ ! -d "$d" ]]; then
    notice "Create directory: $d"
    do_run mkdir -p "$d"
  fi
}

git_mv_safe() {
  # git mv if both source exists and target path not occupied
  local src="$1" dst="$2"
  if [[ -e "$src" ]]; then
    if [[ -e "$dst" ]]; then
      warn "Target already exists, skipping move: $src -> $dst"
    else
      notice "Move: $src -> $dst"
      do_run git mv "$src" "$dst"
    fi
  fi
}

append_gitignore_block() {
  local gi=".gitignore"
  local begin="# BEGIN repo-reorg ignore block"
  local end="# END repo-reorg ignore block"
  local block="${begin}
web_data/
logs/
outputs/
.venv/
.python-version
__pycache__/
.pytest_cache/
${end}"

  if [[ -f "$gi" ]] && grep -q "$begin" "$gi"; then
    notice ".gitignore already contains reorg block"
  else
    notice "Append ignore block to .gitignore"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "cat >> .gitignore <<'BLOCK'"; echo "$block"; echo "BLOCK"
    else
      touch "$gi"
      # shellcheck disable=SC2129
      echo "$begin" >> "$gi"
      echo "web_data/" >> "$gi"
      echo "logs/" >> "$gi"
      echo "outputs/" >> "$gi"
      echo ".venv/" >> "$gi"
      echo ".python-version" >> "$gi"
      echo "__pycache__/" >> "$gi"
      echo ".pytest_cache/" >> "$gi"
      echo "$end" >> "$gi"
    fi
  fi
}

# Ensure key directories
ensure_dir scripts
ensure_dir logs
ensure_dir outputs

# Update .gitignore with runtime and env artifacts
append_gitignore_block

# Move simple web runner into scripts/
if [[ -f run_simple_web_simulation.py ]]; then
  git_mv_safe run_simple_web_simulation.py scripts/run_simple_web_simulation.py
fi

# Move root-level script-y Python files into scripts/ (exclude tests)
while IFS= read -r -d '' f; do
  base=$(basename "$f")
  case "$base" in
    test_*.py|conftest.py|setup.py)
      continue ;;
  esac
  # Skip if already under scripts/ or package dir
  case "$f" in
    ./scripts/*|./sociology_simulation/*)
      continue ;;
  esac
  git_mv_safe "$f" "scripts/$base"
done < <(find . -maxdepth 1 -type f \( -name 'run_*.py' -o -name '*_script.py' \) -print0)

# Relocate Hydra conf/ into package directory if present
if [[ -d conf ]]; then
  ensure_dir sociology_simulation
  if [[ ! -d sociology_simulation/conf ]]; then
    notice "Relocate conf/ -> sociology_simulation/conf/"
    git_mv_safe conf sociology_simulation/conf
  else
    notice "Merge conf/* into sociology_simulation/conf/"
    shopt -s dotglob nullglob
    for item in conf/*; do
      tgt="sociology_simulation/conf/$(basename "$item")"
      if [[ -e "$tgt" ]]; then
        warn "Target exists, skipping: $item -> $tgt"
      else
        git_mv_safe "$item" "$tgt"
      fi
    done
    shopt -u dotglob nullglob
    # Remove empty conf/ if possible
    if [[ -d conf ]] && [[ -z "$(ls -A conf 2>/dev/null || true)" ]]; then
      notice "Remove empty conf/ directory"
      if [[ "$DRY_RUN" -eq 0 ]]; then rmdir conf || true; else echo rmdir conf; fi
    fi
  fi
fi

# Final: optionally create a commit
if [[ "$CREATE_COMMIT" -eq 1 ]]; then
  notice "Creating commit with reorg changes"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo git add -A
    echo git commit -m "chore(repo): reorganize directories per guidelines"
  else
    git add -A
    git commit -m "chore(repo): reorganize directories per guidelines"
  fi
else
  notice "No commit created (omit --commit)."
fi

notice "Done. Review changes with: git status && git diff --stat"

