#!/bin/bash

if [ ! -e /aioqbt/pyproject.toml ]; then
    echo "/aioqbt/pyproject.toml is missing. Forget to bind mount the project?"
    exit 1
fi

if [ -z "$WORKDIR" ]; then
  echo "Missing \$WORKDIR"
  exit 1
fi

find "$WORKDIR" -maxdepth 1 -mindepth 1 -exec rm -rf '{}' +
git -C /aioqbt/ checkout-index -a -f --prefix="$WORKDIR/"
