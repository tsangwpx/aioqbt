#!/bin/bash

if [ ! -e /aioqbt/pyproject.toml ]; then
    echo "/aioqbt/pyproject.toml is missing. Forget to bind mount the project?"
    exit 1
fi

if [ -z "$WORKDIR" ]; then
  echo "Missing \$WORKDIR"
  exit 1
fi

rsync -ah --delete \
  --exclude=/.git \
  --exclude='/.*cache' \
  --exclude='/.coverage**' \
  --exclude=/build \
  --exclude=/htmlcov \
  --exclude=/docs/build \
  /aioqbt/ "${WORKDIR}/"
