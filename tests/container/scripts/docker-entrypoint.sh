#!/bin/sh

set -e

if [ -z "${WORKDIR:-}" ]; then
  export WORKDIR="${HOME}/aioqbt"
fi

mkdir -p "$WORKDIR"
cd "$WORKDIR" || { echo "change WORKDIR failed" && exit 1; }

if [ $# -eq 0 ]; then
  set -- bash --
fi

exec "$@"
