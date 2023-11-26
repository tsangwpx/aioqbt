#!/bin/sh

sync-worktree.sh
setup-venv.sh

. "$HOME/.venv/bin/activate"

pytest "$@"
