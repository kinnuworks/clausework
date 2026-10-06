#!/bin/sh
# Create the five headless Claude Code seats. Usage: seat-setup.sh <abs result repo>
# Flags follow other teams' public write-ups; confirm with `band agent create --help`.
set -eu
export PATH="$HOME/.local/bin:$HOME/.orbstack/bin:/opt/homebrew/bin:$PATH"
REPO="$1"
for seat in lead builder finisher examiner inspector; do
  band agent create --session "seat-$seat" --name "$seat" \
    --description "Clausework factory seat: $seat" \
    --transport claude-code-cli --runtime-auth subscription \
    --runtime-model claude-opus-5-5 --runtime-effort high \
    --claude-permission-mode bypassPermissions \
    --claude-context-mode local_config \
    --cwd "$REPO" --instructions-file "$REPO/mandates/$seat.md"
done
band sessions --all
