#!/usr/bin/env python3
import argparse
import contextlib
import dataclasses
import os
import re
import shlex
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence

HERE = Path(__file__).parent
PROJECT_PATH = HERE.parents[1]


@dataclasses.dataclass
class Context:
    verbose: bool = False
    docker_bin: str = "docker"
    dry_run: bool = False

    tag_spec: List[str] = dataclasses.field(default_factory=list)

    # build stage
    file: Optional[str] = None
    """Dockerfile path"""

    tags: List[str] = dataclasses.field(default_factory=list)
    """Image tags"""

    image_args: Dict[str, str] = dataclasses.field(default_factory=dict)
    """--build-arg in build stage"""

    build_target: Optional[str] = None
    """--target in build stage"""

    # run stage
    run_args: List[str] = dataclasses.field(default_factory=list)
    """arguments to container in run stage"""


def get_parser() -> argparse.ArgumentParser:
    epilog = """
    Examples:

    $ python3 run-container.py --base-image debian:bookworm pytest.sh
    Run pytest.sh on debian bookworm container.

    $ python3 run.py --qbittorrent 4.6
    Run pytest.sh with qBittorrent v4.6 compiled from source.

    $ python3 run-container.py --file qbittorrent-5.0.Dockerfile \\
        --build-arg=QBITTORRENT_COMMIT=master pytest.sh
    Run pytest.sh with latest qBittorrent (assuming v5.0).
    """
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(epilog),
    )
    p.add_argument(
        "--verbose",
        "-v",
        default=False,
        action="store_true",
    )
    p.add_argument(
        "--podman",
        default=False,
        action="store_true",
        help="Use Podman instead",
    )
    p.add_argument(
        "--file",
        "-f",
        default=None,
        help="Dockerfile location (absolute or relative to this script)",
    )
    p.add_argument(
        "--tag",
        "-t",
        dest="tags",
        default=[],
        action="append",
        help="Image tags",
    )
    p.add_argument(
        "--build-target",
        default="pytest",
        help="Target in build stage",
    )
    p.add_argument(
        "--build-arg",
        dest="build_args",
        default=[],
        action="append",
        help="Image build arguments",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print commands may issue",
    )
    p.add_argument(
        "--base-image",
        help="Base image (e.g. debian:bookworm) to derive other options.",
    )
    p.add_argument(
        "--qbittorrent",
        dest="qbittorrent_version",
        help="qBittorent version (e.g. 4.6) to derive other options.",
    )
    return p


def _run(
    args: Sequence[str],
    *,
    dry_run: bool = False,
    **kwargs,
) -> int:
    assert all(isinstance(s, str) for s in args), args
    print("Command:", " ".join(shlex.quote(s) for s in args))

    if kwargs:
        print("Command kwargs:", kwargs)

    if dry_run:
        print("Command is skipped.")
        return 0

    completed = subprocess.run(
        args,
        **kwargs,
    )
    return completed.returncode


def _prepare_context(
    ns: argparse.Namespace,
    run_args: List[str],
) -> Context:
    image_args = {}
    for build_arg in ns.build_args:
        key, eq, value = build_arg.partition("=")
        if not eq:
            # Use local environment if equality sign is missing
            value = os.environ.get(key, "")
        image_args[key] = value

    run_args = list(run_args)
    if run_args and run_args[0] == "--":
        run_args.pop(0)

    ctx = Context(
        verbose=ns.verbose,
        docker_bin="podman" if ns.podman else "docker",
        file=ns.file,
        tags=ns.tags,
        build_target=ns.build_target,
        image_args=image_args,
        run_args=run_args,
    )

    if ns.qbittorrent_version is not None:
        _update_from_qbittorent(ctx, ns.qbittorrent_version)
    if ns.base_image is not None:
        _update_from_base_image(ctx, ns.base_image)

    return ctx


def _update_from_qbittorent(ctx: Context, version: str):
    """Update context from --qbittorrent"""
    match = re.match(r"\d+(?:\.\d)*", version)

    if match is None:
        raise ValueError(f"Bad version: {version}")

    if ctx.file is None:
        ctx.file = f"qbittorrent-{version}.Dockerfile"

    ctx.tag_spec.append(f"qbittorrent-{version}")


def _update_from_base_image(ctx: Context, base_image: str):
    """Update context from --base-image"""
    match = re.match(
        r"(?P<name>debian|ubuntu|pypy|python):(?P<tag>(?![.-])[a-zA-Z0-9.-]{1,128})",
        base_image,
    )

    if match is None:
        raise ValueError(f"Bad name: {base_image}")

    base_name = match.group("name")
    base_tag = match.group("tag")

    if ctx.file is None:
        ctx.file = "Dockerfile"

    fqn = f"docker.io/library/{base_name}:{base_tag}"
    ctx.image_args.setdefault("BASE_IMAGE", fqn)
    ctx.tag_spec.append(f"{base_name}-{base_tag}")


def _build_image(ctx: Context, iidfile: Path) -> str:
    """Build a container and return its image id"""
    env = {}
    if "DOCKER_BUILDKIT" not in os.environ:
        env["DOCKER_BUILDKIT"] = "1"

    args = [ctx.docker_bin, "build"]

    assert ctx.file is not None
    args.extend(("--file", ctx.file))

    if ctx.build_target is not None:
        args.extend(("--target", ctx.build_target))

    for key, value in ctx.image_args.items():
        args.extend(("--build-arg", f"{key}={value}"))

    for tag in ctx.tags:
        args.extend(("--tag", tag))

    if ctx.tag_spec:
        args.extend(("--tag", f"aioqbt/{ctx.build_target}:{'-'.join(ctx.tag_spec)}"))

    args.extend(("--iidfile", str(iidfile)))

    args.append(str(HERE))

    _run(args, check=True, env=env, cwd=str(HERE), dry_run=ctx.dry_run)

    if not ctx.dry_run:
        return iidfile.read_text()
    else:
        return "<IMAGE ID PLACEHOLDER>"


def _run_image(ctx: Context, image_id: str):
    """Run an image and return its exit code"""
    args = [
        ctx.docker_bin,
        "run",
        "-it",
        "--rm",
        f"--mount=type=bind,src={PROJECT_PATH!s},dst=/aioqbt,ro",
        "--mount=type=volume,src=aioqbt-pip-cache,dst=/root/.cache/pip",
        image_id,
        *ctx.run_args,
    ]

    return _run(args, dry_run=ctx.dry_run)


def main() -> None:
    p = get_parser()
    ns, run_args = p.parse_known_args()

    ctx = _prepare_context(ns, run_args)
    if ctx.verbose:
        print("argparse:", ns)
        print("config:", ctx)

    if ctx.file is None:
        print("No dockerfile is inferred. Try --file, --base-image, and/or --qbittorrent")
        raise SystemExit(1)

    with contextlib.ExitStack() as ctx_stack:
        if not ctx.dry_run:
            temp_prefix = "aioqbt-container-"
            temp_dir = ctx_stack.enter_context(tempfile.TemporaryDirectory(prefix=temp_prefix))
            iidfile = Path(temp_dir, "iidfile")
        else:
            iidfile = Path("/dev/null")

        image_id = _build_image(ctx, iidfile)
        print("ImageId:", image_id)

        returncode = _run_image(ctx, image_id)
        raise SystemExit(returncode)


if __name__ == "__main__":
    main()
