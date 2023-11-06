import contextlib
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator, Optional, Tuple


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


@contextlib.contextmanager
def server_process(
    profile_path: Path,
    port: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> Iterator[Tuple[str, int]]:
    if sys.platform.startswith("win"):
        raise RuntimeError("Server process is not supported on platform")

    if logger is None:
        logger = logging.getLogger("server_process")

    if port is None:
        # Find a free port to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))  # use IPv4 explicitly
        host, port = sock.getsockname()
        sock.close()

    args = [
        "/usr/bin/qbittorrent-nox",
        f"--profile={profile_path}",
        f"--webui-port={port:d}",
    ]

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
        try:
            do_communicate(timeout=1 / 10)
        except subprocess.TimeoutExpired:
            pass

        _wait_port_open(port, 5)

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
