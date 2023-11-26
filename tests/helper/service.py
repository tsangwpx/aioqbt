import base64
import contextlib
import hashlib
import logging
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple, Union


def _find_free_port(socket_type: int, host: str = "") -> int:
    """Find a free port to use"""
    assert socket_type in (socket.SOCK_STREAM, socket.SOCK_DGRAM)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    host, port = sock.getsockname()
    sock.close()

    assert isinstance(port, int)
    return port


def _wait_port_open(port: int, count: int, pause: float = 1) -> None:
    # connect to a port repeatly until it is open or maximum number of attempts is reached
    assert count >= 1, count

    for attempt in range(1, count + 1):
        error: Optional[Exception] = None

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(("127.0.0.1", port))
            except ConnectionRefusedError as ex:
                error = ex

        if error is None:
            return

        if attempt == count:
            raise error

        time.sleep(pause)

    raise AssertionError("unreachable")


def _combine_lists(*args: Sequence[str]) -> List[str]:
    result: List[str] = []
    for seq in args:
        assert not isinstance(seq, str), "Oops."
        result.extend(seq)

    return result


_DEFAULT_EXECUTABLE = (
    # use line-buffered stdout to capture WebUI URL and credential
    # even though it is not used currently: pytest --log-cli-level=DEBUG
    "stdbuf",
    "-oL",
    "qbittorrent-nox",
)


def _process_executable(executable: Union[str, Sequence[str], None]) -> List[str]:
    if executable is None:
        executable = _DEFAULT_EXECUTABLE

    if isinstance(executable, str):
        return [executable]
    else:
        return list(executable)


def _make_profile_conf(profile_path: Path) -> None:
    """
    Generate qBittorrent.conf in correct place

    Default user and password are set to "admin" and "adminadmin" respectively.
    """
    username = "admin"
    password = "adminadmin"

    # PBKDF-HMAC-SHA512 parameters
    salt = b"salt" * 4
    assert len(salt) == 16
    hash_name = "sha512"
    iterations = 100000

    derived_key = hashlib.pbkdf2_hmac(hash_name, password.encode("utf-8"), salt, iterations)
    dk_b64 = base64.b64encode(derived_key).decode("ascii")
    salt_b64 = base64.b64encode(salt).decode("ascii")

    txt = rf"""
    [Preferences]
    WebUI\Username="{username}"
    WebUI\Password_PBKDF2="@ByteArray({salt_b64}:{dk_b64})"
    """
    txt = textwrap.dedent(txt.lstrip("\n"))

    conf_path = profile_path.joinpath("qBittorrent/config/qBittorrent.conf")
    conf_path.parent.mkdir(exist_ok=True, parents=True)
    conf_path.write_text(txt, encoding="utf-8")


@contextlib.contextmanager
def server_process(
    profile_path: Path,
    port: Optional[int] = None,
    *,
    executable: Union[str, Sequence[str], None] = None,
    logger: Optional[logging.Logger] = None,
) -> Iterator[Tuple[str, int]]:
    if sys.platform.startswith("win"):
        raise RuntimeError("Server process is not supported on platform")

    if logger is None:
        logger = logging.getLogger("server_process")

    _make_profile_conf(profile_path)

    if port is None:
        port = _find_free_port(socket.SOCK_STREAM, "127.0.0.1")

    executable = _process_executable(executable)

    args = [
        f"--profile={profile_path}",
        f"--webui-port={port:d}",
    ]
    args = _combine_lists(executable, args)

    logger.debug("server command: %r", args)

    communication_done = False
    process = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    def log_stdout_stderr(stdout: Optional[bytes], stderr: Optional[bytes]) -> None:
        """Log stdout and stderr"""
        ts = time.time()

        stdout = stdout or b""
        stderr = stderr or b""

        assert logger is not None

        for line in stdout.splitlines():
            logger.info("server stdout %.3f: %r", ts, line)

        for line in stderr.splitlines():
            logger.error("server stderr %.3f: %r", ts, line)

    def do_communicate(input: Optional[bytes] = None, timeout: Optional[float] = None) -> None:
        """Call communicate and send outputs to logger"""

        nonlocal communication_done
        if communication_done:
            # Do not pull process after its exit.
            # it would strangely cause duplicated outputs.
            return

        try:
            stdout, stderr = process.communicate(input, timeout)
        except subprocess.TimeoutExpired as ex:
            log_stdout_stderr(ex.stdout, ex.stderr)
            raise
        else:
            # If reach here, the process has exited.
            # set the done flag
            communication_done = True
            log_stdout_stderr(stdout, stderr)

    try:
        _wait_port_open(port, 5)

        try:
            do_communicate(timeout=1 / 10)
        except subprocess.TimeoutExpired:
            pass

        # seem that the stdout is buffered on the child process.
        # WebUI URL cannot be read so "localhost" is a good guess.
        yield "localhost", port
    finally:
        logger.debug("Terminate process %d", process.pid)
        process.terminate()

        try:
            do_communicate(timeout=3)
        except subprocess.TimeoutExpired:
            logger.warning("Kill process %d", process.pid)
            process.kill()
