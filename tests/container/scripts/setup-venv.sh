#!/bin/bash

# Initialize a venv in ~/.venv and install current project in editable mode
set -eu

_find_base_python() {
    local executable="${PYTHON_EXECUTABLE:-}"

    if [ -z "$executable" ]; then
        local exec_prefix
        exec_prefix="$(/usr/bin/env python3 -c 'import sys; print(sys.base_exec_prefix)')"
        executable="${exec_prefix}/bin/python3"
    fi

    [ -x "$executable" ] || exit 1
    echo "$executable"
}

[ -e pyproject.toml ] || { echo 'Missing pyproject.toml in workign directory'; exit 1; }

if [ -z "${VIRTUAL_ENV:-}" ]; then
    export VIRTUAL_ENV="${HOME}/.venv"
fi

BASE_PYTHON="$(_find_base_python)" || { echo 'Cannot find python'; exit 1; }
"$BASE_PYTHON" -m venv --clear "$VIRTUAL_ENV"
. "${VIRTUAL_ENV}/bin/activate"

# pip>=19.0 is required to build package with PEP-517
python3 -m pip install --upgrade --force 'pip>=19.0'

[ $# -eq 0 ] && set -- '.[test]'
python3 -m pip install "$@"
