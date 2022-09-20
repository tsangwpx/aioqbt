import operator
from typing import Any, Dict, List, Union

BencodeTypes = Union[int, bytes, str, Dict[str, Any], List[Any]]


class BencodeError(Exception):
    pass


def dumps(obj: BencodeTypes, encoding: str = "utf-8") -> bytes:
    def iterencode(o):
        if isinstance(o, int):
            yield b"i%de" % o
        elif isinstance(o, (bytes, str)):
            if isinstance(o, str):
                o = o.encode(encoding)
            yield b"%d:" % len(o)
            yield o
        elif isinstance(o, list):
            yield b"l"
            for v in o:
                yield from iterencode(v)
            yield b"e"
        elif isinstance(o, dict):
            yield b"d"
            pairs = []
            seen = set()

            for k, v in o.items():
                if isinstance(k, str):
                    k = k.encode(encoding)
                if k in seen:
                    raise ValueError(f"Duplicated key: {k!r}")
                pairs.append((k, v))

            pairs.sort(key=operator.itemgetter(0))

            for k, v in pairs:
                yield b"%d:" % len(k)
                yield k
                yield from iterencode(v)
            yield b"e"
        else:
            raise ValueError(f"Unexpected value: {type(o)!r}")

    return b"".join(iterencode(obj))


__all__ = ("BencodeError", "dumps")
