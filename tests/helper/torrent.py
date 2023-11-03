import random
from hashlib import sha1
from typing import Any, List, Mapping, NamedTuple, Optional, Tuple

from helper import bencode
from helper.lang import randbytes


class TorrentData(NamedTuple):
    hash: str
    name: str
    data: bytes

    @property
    def magnet(self) -> str:
        return f"magnet:?xt=urn:btih:{self.hash}"


class PieceHasher:
    def __init__(self, piece_length: int):
        if piece_length <= 0:
            raise ValueError(f"piece_length = {piece_length!r}")

        self._finalized = False
        self._pieces: List[bytes] = []
        self._piece_length = piece_length
        self._hasher = sha1()
        self._hasher_rem = piece_length

    def _consume(self, data: bytes, final: bool) -> None:
        if self._finalized:
            raise ValueError("finalize() has been called")

        pos = 0
        remaining = len(data)

        while remaining > 0:
            consumed = min(remaining, self._hasher_rem)
            self._hasher.update(data[pos : pos + consumed])
            pos += consumed
            remaining -= consumed
            self._hasher_rem -= consumed

            if self._hasher_rem == 0:
                self._pieces.append(self._hasher.digest())
                self._hasher = sha1()
                self._hasher_rem = self._piece_length

        if not final:
            return

        self._finalized = True
        if self._hasher_rem < self._piece_length:
            self._pieces.append(self._hasher.digest())

    def update(self, data: bytes) -> None:
        self._consume(data, False)

    def finalize(self, data: bytes = b"") -> List[bytes]:
        self._consume(data, True)
        return self._pieces

    @property
    def pieces(self) -> List[bytes]:
        return self._pieces

    @property
    def piece_length(self) -> int:
        return self._piece_length


def _rand_and_message(name: str) -> Tuple[random.Random, str]:
    r = random.Random(name)
    message = randbytes(r, 16).hex()
    return r, message


def make_torrent_single(
    name: str,
    torrent: Optional[Mapping[str, Any]] = None,
) -> TorrentData:
    piece_length = 16 * 1024
    torrent = dict(torrent) if torrent else {}

    r, message = _rand_and_message(name)
    data = message.encode("latin-1")
    pieces = PieceHasher(piece_length).finalize(data)

    info_dict = {
        "length": len(data),
        "name": name,
        "piece length": piece_length,
        "pieces": b"".join(pieces),
    }
    info_hash = sha1(bencode.dumps(info_dict)).hexdigest()
    torrent["info"] = info_dict
    torrent_bytes = bencode.dumps(torrent)

    return TorrentData(
        hash=info_hash,
        name=name,
        data=torrent_bytes,
    )


def make_torrent_files(
    name: str,
    torrent: Optional[Mapping[str, Any]] = None,
) -> TorrentData:
    piece_length = 16 * 1024
    torrent = dict(torrent) if torrent else {}

    r, message = _rand_and_message(name)

    # list of (file path, file content)
    contents: List[Tuple[str, bytes]] = []

    for i in range(5):
        file_path = f"files/{i:02d}.txt"
        file_data = randbytes(r, piece_length // 2).hex().encode("latin-1")
        contents.append((file_path, file_data))

    files = []
    piece_hasher = PieceHasher(piece_length)

    for file_path, file_data in contents:
        files.append(
            {
                "path": file_path.split("/"),
                "length": len(file_data),
            }
        )
        piece_hasher.update(file_data)

    pieces = piece_hasher.finalize()

    info_dict = {
        "name": name,
        "files": files,
        "piece length": piece_length,
        "pieces": b"".join(pieces),
    }
    info_hash = sha1(bencode.dumps(info_dict)).hexdigest()
    torrent["info"] = info_dict
    torrent_bytes = bencode.dumps(torrent)

    return TorrentData(
        hash=info_hash,
        name=name,
        data=torrent_bytes,
    )
