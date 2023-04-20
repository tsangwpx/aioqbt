import os
import sys
from typing import Union

if sys.version_info >= (3, 9):
    StrPath = Union[str, os.PathLike[str]]
else:
    StrPath = Union[str, os.PathLike]
