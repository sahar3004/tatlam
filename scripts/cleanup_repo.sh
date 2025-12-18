##!/usr/bin/env bash
set -euo pipefail

# One-shot repository cleanup for tracked junk and artifacts
# Usage: bash scripts/cleanup_repo.sh

red()  { printf "\033[31m%s\033[0m\n" "$*"; }
blue() { printf "\033[34m%s\033[0m\n" "$*"; }

git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "${git_root}" ]; then
  red "Not in a git repository. Aborting."
  exit 1
fi
cd "$git_root"

blue "Staging .gitignore updates (if any)."
if [ -f .gitignore ]; then
  git add .gitignore || true
fi

# Candidates to remove from the index if tracked
TO_REMOVE=(
  "=." # stray file named '='
  "="   # literal '=' if present
  ".pre-commit-config 2.yaml"
  "pyproject 2.toml"
  "tatlam.egg-info"
  "$OUT"
  "artifacts"
  "__pycache__"
  ".hypothesis"
)

blue "Removing tracked junk from git index if present..."
for path in "${TO_REMOVE[@]}"; do
  if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    blue " - git rm -r --cached --force $path"
    git rm -r --cached --force "$path" || true
  fi
done

# Remove tracked Python bytecode anywhere
blue "Removing tracked __pycache__ and *.pyc from index..."
# shellcheck disable=SC2016
mapfile -t pycache_tracked < <(git ls-files | grep -E '(.*__pycache__.*|.*\.pyc$)' || true)
if [ ${#pycache_tracked[@]} -gt 0 ]; then
  git rm -r --cached --force "${pycache_tracked[@]}" || true
fi

# Ensure directories exist in working tree but remain untracked
mkdir -p artifacts runs "$OUT" || true

blue "Creating a .gitkeep in artifacts/ to retain directory structure (optional)."
mkdir -p artifacts && touch artifacts/.gitkeep || true

blue "Done. Create a commit to finalize cleanup:"
echo "  git commit -m 'chore: cleanup tracked artifacts and duplicates'"
