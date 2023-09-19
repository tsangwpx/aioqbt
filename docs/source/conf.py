# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

_HERE = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "../.."))

sys.path.append(os.path.join(_HERE, "_ext"))

import aioqbt

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "aioqbt"
copyright = "2022, Aaron"
author = "Aaron"
version = aioqbt.__version__
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "_sphinx_monkeypatch",
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "aiohttp": ("https://docs.aiohttp.org/en/stable/", None),
}

# -- Options for Python ------------------------------------------------------
python_display_short_literal_types = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "style_external_links": False,
    "navigation_depth": 4,
}
html_context = {
    "display_github": True,
    "github_user": "tsangwpx",
    "github_repo": "aioqbt",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}
html_css_files = [
    "custom.css",
]

# -- Options for extlinks
extlinks = {
    "issue": ("https://github.com/tsangwpx/aioqbt/issues/%s", "issue %s"),
    "APIWiki": (
        "https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)%s",
        "[APIWiki %s]",
    ),
}

# -- Options for autodoc
autodoc_member_order = "bysource"
