# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- sys path ----------------------------------------------------------------
# 絶対パスで指定する。 GitHub actions に必要。
import sys
from pathlib import Path

sys.path.insert(0, str(Path("../../../").resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "deredata"
copyright = "2026, tomosatoP"
author = "tomosatoP"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.apidoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.todo",
    "sphinx.ext.githubpages",
]

apidoc_modules = [
    {
        "path": "../../../deredata",
        "destination": "modules",
        "max_depth": 2,
        "separate_modules": True,
        "module_first": True,
        "implicit_namespaces": True,
        "automodule_options": {
            "members",
            "show-inheritance",
            "undoc-members",
        },
    }
]

add_module_names = False
autoclass_content = "both"
autodoc_member_order = "bysource"
autodoc_typehints = "description"


templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "ja"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "nature"
html_static_path = ["_static"]
