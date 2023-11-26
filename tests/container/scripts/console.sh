#!/bin/sh

sync-worktree.sh
setup-venv.sh --editable '.[dev,test]'

. "$HOME/.venv/bin/activate"

if [ $# -eq 0 ]; then
    set -- bash
fi

exec "$@"
