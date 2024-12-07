#!/bin/sh

# /aioqbt is usually owned by different owner in container
git config --global --add safe.directory /aioqbt

sync-worktree.sh
setup-venv.sh --editable '.[dev,test]'

. "$HOME/.venv/bin/activate"

if [ $# -eq 0 ]; then
    set -- bash
fi

exec "$@"
