# test on Debian/Ubuntu distribution

ARG BASE_IMAGE=debian:bookworm

# base stage
FROM $BASE_IMAGE AS base

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y netbase; \
    rm -rf /var/lib/apt/lists/*

# nox stage: provide qbittorrent-nox
FROM base AS nox

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        qbittorrent-nox; \
    rm -rf /var/lib/apt/lists/*

# dev stage
FROM nox AS dev

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git rsync make vim less bash-completion \
        python3 python3-venv; \
    rm -rf /var/lib/apt/lists/*

# devcontainer stage
FROM dev AS devcontainer

COPY --chmod=0755 scripts/setup-venv.sh /usr/local/bin/

# pytest with readonly bind mount in /aioqbt
FROM dev AS pytest

COPY --chmod=0755 scripts/*.sh /usr/local/bin/
ENTRYPOINT [ "docker-entrypoint.sh" ]
