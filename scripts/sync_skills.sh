#!/usr/bin/env bash
# sync_skills.sh — Sync Helen's skill SSOT to Claude Code's mirror.
#
# SSOT:          helen/skills/<category>/<name>/   (distributed with Helen)
# Mirror:        .claude/skills/<name>/            (Claude Code auto-load)
#
# Why: Helen's runtime `load_skill()` only reads helen/skills/. Claude Code
# auto-loads skills from .claude/skills/. Without sync, the two drift apart
# and developers/AI agents silently edit the wrong copy (see commit
# "fix(skills): reconcile SSOT" for the bug this prevents).
#
# Usage:
#   ./scripts/sync_skills.sh          # from repo root
#   ./scripts/sync_skills.sh --dry-run
#
# Run this BEFORE committing any change that touches helen/skills/.
# Ideally hook it into `git pre-commit` or run via `make skills-sync`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSOT_DIR="$REPO_ROOT/helen/skills"
MIRROR_DIR="$REPO_ROOT/.claude/skills"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "[dry-run] No changes will be made."
fi

if [[ ! -d "$SSOT_DIR" ]]; then
    echo "ERROR: SSOT dir not found: $SSOT_DIR" >&2
    exit 1
fi

# Discover skills: each directory containing a SKILL.md is a skill.
# We flatten helen/skills/<category>/<name>/ → .claude/skills/<name>/.
mapfile -t SKILL_DIRS < <(find "$SSOT_DIR" -name SKILL.md -printf '%h\n' | sort)

echo "Found ${#SKILL_DIRS[@]} skills in SSOT ($SSOT_DIR):"

# Wipe the mirror so removed/renamed skills don't linger.
if [[ $DRY_RUN -eq 0 ]]; then
    rm -rf "$MIRROR_DIR"
    mkdir -p "$MIRROR_DIR"
fi

for skill_path in "${SKILL_DIRS[@]}"; do
    skill_name="$(basename "$skill_path")"
    echo "  - $skill_name  ($skill_path → .claude/skills/$skill_name/)"
    if [[ $DRY_RUN -eq 0 ]]; then
        cp -r "$skill_path" "$MIRROR_DIR/$skill_name"
    fi
done

# Sanity: mirror must have exactly as many skills as SSOT.
if [[ $DRY_RUN -eq 0 ]]; then
    mirror_count=$(find "$MIRROR_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
    sdot_count=${#SKILL_DIRS[@]}
    if [[ "$mirror_count" -ne "$sdot_count" ]]; then
        echo "ERROR: mirror count ($mirror_count) != SSOT count ($sdot_count)" >&2
        exit 1
    fi
    echo "✅ Synced $sdot_count skills to $MIRROR_DIR"
else
    echo "[dry-run] Would sync ${#SKILL_DIRS[@]} skills to $MIRROR_DIR"
fi
