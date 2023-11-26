# This Dockerfile builds qBittorrent v4.6 on debian bookworm.
# Qt5 is used.

ARG BASE_IMAGE=debian:bookworm

ARG LIBTORRENT_COMMIT=v2.0.9

# Support release-4.3 to release-4.6 so far
ARG QBITTORRENT_COMMIT=release-4.6.0
#ARG QBITTORRENT_COMMIT=release-4.5.0
#ARG QBITTORRENT_COMMIT=release-4.4.0
#ARG QBITTORRENT_COMMIT=release-4.3.0


# base stage
FROM $BASE_IMAGE AS base

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y netbase; \
    rm -rf /var/lib/apt/lists/*

# Download source code from github.com
FROM base AS checkout

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git ca-certificates; \
    rm -rf /var/lib/apt/lists/*

ARG LIBTORRENT_COMMIT
RUN set -eux; \
    mkdir -p /data/libtorrent; \
    cd /data/libtorrent; \
    git init .; \
    git remote add origin "https://github.com/arvidn/libtorrent.git"; \
    git fetch --depth=1 origin "$LIBTORRENT_COMMIT"; \
    git checkout FETCH_HEAD; \
    git submodule update --init --depth=1 --recursive

ARG QBITTORRENT_COMMIT
RUN set -eux; \
    mkdir -p /data/qbittorrent; \
    cd /data/qbittorrent; \
    git init .; \
    git remote add origin "https://github.com/qbittorrent/qBittorrent.git"; \
    git fetch --depth=1 origin "$QBITTORRENT_COMMIT"; \
    git checkout FETCH_HEAD; \
    git submodule update --init --depth=1 --recursive

# Build qbittorrent-nox
FROM base AS build

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git ca-certificates \
        rsync bash-completion vim less \
        build-essential ninja-build cmake \
        libssl-dev zlib1g-dev \
        libboost-dev qtbase5-dev qttools5-dev; \
    rm -rf /var/lib/apt/lists/*

COPY --from=checkout /data/libtorrent /data/libtorrent
RUN set -eux; \
    cmake -B /build/libtorrent -S /data/libtorrent -G Ninja; \
    cmake --build /build/libtorrent; \
    cmake --install /build/libtorrent

COPY --from=checkout /data/qbittorrent /data/qbittorrent
RUN set -eux; \
    cmake -B /build/qbittorrent -S /data/qbittorrent -G Ninja -DGUI=OFF; \
    cmake --build /build/qbittorrent; \
    cmake --install /build/qbittorrent

# Copy qbittorrent-nox and shared library to /stage
RUN set -eux; \
    ldconfig; \
    qbittorrent-nox --version; \
    mkdir -p /stage; \
    find /usr/local \( -name qbittorrent-nox -o -name '*.so*' \) -exec cp -av --parents -t /stage '{}' +

# nox stage: provide qbittorrent-nox
FROM base AS nox

COPY --from=build /stage/usr/local /usr/local

# Install deps, update linker cache, and do a simple check
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libqt5core5a libqt5network5 libqt5sql5-sqlite libqt5xml5 \
        libssl3; \
    rm -rf /var/lib/apt/lists/*; \
    ldconfig; \
    qbittorrent-nox --version || { ldd /usr/local/bin/qbittorrent-nox && exit 1; }

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
