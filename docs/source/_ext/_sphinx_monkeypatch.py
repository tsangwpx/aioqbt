import functools
import itertools
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple, Union

from docutils.nodes import Element
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util.inspect import signature_from_str, stringify_signature

from aioqbt.bittorrent import InfoHash, InfoHashes, InfoHashesOrAll


@functools.cache
def stringify_annotation(anno: Any, mode: str) -> str:
    from sphinx.util.typing import stringify_annotation

    return stringify_annotation(anno, mode)


class ReplacementAnnotations:
    """
    Replacement annotation

    Typehints are stringified to compare, substitute, and cached.
    """

    def __init__(self, mode: str):
        """
        :param mode: stringify() mode
        """
        assert mode in {"smart", "fully-qualified", "fully-qualified-except-typing"}, mode
        self._mode = mode

        # param -> (qualname prefix, target, replacement)
        self._registry: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)

        # (prefix, param) -> target -> replacement
        self._table: Dict[Tuple[str, str], Dict[str, str]] = defaultdict(dict)

    @classmethod
    def _get_prefixes(cls, name: str) -> List[str]:
        if not name:
            return [""]
        parts = name.split(".")
        prefixes = list(itertools.accumulate(parts, lambda a, b: f"{a}.{b}"))
        prefixes.reverse()
        prefixes.append("")
        return prefixes

    def add_rule(self, prefix: str, param: str, target: Any, replacement: Any):
        """
        :param prefix: qualname prefix
        :param param: parameter name
        :param target: original type hint
        :param replacement: replacement type hint
        """
        target = stringify_annotation(target, self._mode)
        replacement = stringify_annotation(replacement, self._mode)

        item = (
            prefix,
            target,
            replacement,
        )
        self._registry[param].append(item)

        current = self._table[(prefix, param)].setdefault(target, replacement)
        if current != replacement:
            raise RuntimeError(f"Duplicate rule {prefix!r} {param!r} {target!r} {replacement!r}")

    def find_replacement(self, name: str, param: str, target: Any) -> Optional[str]:
        """
        Find a replacement for annotation ``target`` located
        in ``name`` and ``param`` or return ``None`` if unavailable.
        """

        for prefix in self._get_prefixes(name):
            loc = (prefix, param)

            if loc not in self._table:
                continue

            result = self._table[loc].get(stringify_annotation(target, self._mode))
            if result is None:
                continue

            return result

        return None


def _builder_inited(app: Sphinx):
    if app.config.autodoc_typehints_format == "short":
        mode = "smart"
        tilde = "~"
    else:
        mode = "fully-qualified"
        tilde = ""

    ra = ReplacementAnnotations(mode)

    qn_hash = f"{tilde}aioqbt.bittorrent.InfoHash"
    qn_hashes = Iterable[qn_hash]
    qn_hashes_all = Union[qn_hashes, Literal["all"]]

    table = [
        ("aioqbt", "hash", InfoHash, qn_hash),
        ("aioqbt", "hashes", InfoHashes, qn_hashes),
        ("aioqbt", "hashes", InfoHashesOrAll, qn_hashes_all),
        ("aioqbt", "id", InfoHashes, qn_hashes),
        ("aioqbt", "id", InfoHashesOrAll, qn_hashes_all),
    ]

    for package, param, target, repl in table:
        ra.add_rule(package, param, target, repl)
        ra.add_rule(package, param, Optional[target], Optional[repl])

    app.env._monkeypatch_repl_annos = ra


def _process_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: Callable,
    options: Dict[str, Any],
    signature: Optional[str],
    return_annotation: Optional[str],
):
    if what not in {"function", "method"}:
        return

    if signature in (None, "", "()") and return_annotation in (None, ""):
        # trivial
        return

    ra: ReplacementAnnotations = app.env._monkeypatch_repl_annos

    sig = signature_from_str(signature)
    parameters = list(sig.parameters.values())
    changed = False

    for i, param in enumerate(parameters):
        if param.annotation is None:
            continue

        repl = ra.find_replacement(name, param.name, param.annotation)
        if repl is None:
            continue

        changed = True
        parameters[i] = param.replace(annotation=repl)

    new_return_anno = return_annotation

    if return_annotation is not None:
        new_return_anno = ra.find_replacement(name, "return", return_annotation)
        if new_return_anno is None:
            new_return_anno = return_annotation
        else:
            changed = True

    if not changed:
        return

    sig = sig.replace(parameters=parameters)
    new_signature = stringify_signature(sig)

    if new_signature == signature and new_return_anno == return_annotation:
        return

    return new_signature, new_return_anno


def _missing_reference(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: Element,
):
    # Redirect missing "class" xref to "data" in Python domain
    # which may be type hints
    if node.get("refdomain") != "py":
        return None
    reftarget = node.get("reftarget")
    if reftarget is None or not reftarget.startswith("aioqbt."):
        return None
    if node.get("reftype") not in ("class",):
        return None

    domain = env.get_domain("py")
    result = domain.resolve_xref(
        env,
        node["refdoc"],
        app.builder,
        "data",
        reftarget,
        node,
        contnode,
    )
    return result


def setup(app: Sphinx):
    app.setup_extension("sphinx.ext.autodoc")

    app.connect("builder-inited", _builder_inited)
    app.connect("autodoc-process-signature", _process_signature)
    app.connect("missing-reference", _missing_reference)

    return {
        "version": "1.0.0",
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
