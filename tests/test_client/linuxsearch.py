import time
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:

    def prettyPrinter(dictionary: Dict[str, Any]) -> None:
        pass

else:
    from novaprinter import prettyPrinter


def _image_dict(name: str, info_hash: str, size: str) -> Dict[str, str]:
    return {
        "link": f"magnet:?xt=urn:btih:{info_hash}",
        "name": name,
        "size": size,
        "seeds": "-1",
        "leech": "-1",
        "engine_url": "-1",
    }


_TABLE = [
    _image_dict(
        "ubuntu-22.04.3-desktop-amd64.iso",
        "75439d5de343999ab377c617c2c647902956e282",
        "4.69 GiB",
    ),
    _image_dict(
        "ubuntu-20.04.6-desktop-amd64.iso",
        "5f5e8848426129ab63cb4db717bb54193c1c1ad7",
        "4.05 GiB",
    ),
    _image_dict(
        "debian-12.1.0-amd64-netinst.iso",
        "a9164e99d5181cfef0c23c209334103619080908",
        "627.0 MiB",
    ),
]


class linuxsearch:
    url = "http://example.com"
    name = "Linux Search"
    supported_categories = {
        "all": "0",
        "software": "3",
    }

    def search(self, what: str, cat: str = "all") -> None:
        for item in _TABLE:
            name = item["name"]
            if what in name:
                prettyPrinter(item)

        # keep search status in "Running" from "Stopped"
        time.sleep(60)
