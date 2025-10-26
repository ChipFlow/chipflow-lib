# SPDX-License-Identifier: BSD-2-Clause
# Configuration file for the Sphinx documentation builder.

# Add parent folder to path so we can pick up module
import os
import sys
from pprint import pformat

sys.path.insert(0, os.path.abspath('../../chipflow_lib'))

from chipflow_lib import __version__

doctest_path = [os.path.abspath('..')]

# -- Project information

project = 'chipflow-lib'
copyright = 'ChipFlow Limited, 2021-2025'
author = 'ChipFlow Platform Team'

release = 'alpha'
version = __version__

master_doc = "index"


# -- General configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autodoc.typehints',
    'sphinx.ext.doctest',
    'sphinx.ext.duration',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    # 'autoapi.extension',  # Temporarily disabled due to CI import issues
    'sphinxcontrib.autoprogram',
    'sphinxcontrib.autodoc_pydantic',
    'sphinx_design',
]

html_theme = 'furo'
html_logo = '_assets/chipflow-logo.svg'
html_title = "ChipFlow Platform Documentation"
html_static_path = ['_assets']

html_theme_options = {
    "dark_css_variables": {
        "admonition-font-size": "0.9 rem",
    },
    "light_css_variables": {
        "admonition-font-size": "0.9 rem",
    },
}

autodoc_typehints = 'description'

# AutoAPI configuration - temporarily disabled due to CI import issues
#
# AutoAPI is encountering "Unable to read file" errors for ALL Python modules
# in the CI environment, preventing it from generating any API documentation.
# This appears to be related to import-time issues during the refactoring work.
#
# Root cause investigation needed:
# - Possible circular imports preventing module loading
# - Import-time side effects that fail in CI but not locally
# - Python path or module resolution differences in CI
#
# Workaround: Using manual sphinx.ext.autodoc directives in platform-api.rst
# TODO: Re-enable AutoAPI once import issues are resolved
#
# autoapi_dirs = [
#         "../chipflow_lib",
#         ]
# autoapi_generate_api_docs = False
# autoapi_template_dir = "_templates/autoapi"
# # autoapi_verbose_visibility = 2
# autoapi_keep_files = True
# autoapi_options = [
#     'members',
#     'show-inheritance',
#     'show-module-summary',
#     'imported-members',
# ]

# Exclude in-progress stuff and template files
exclude_patterns = [
    "_templates",  # Exclude template files from being read as RST
    "unfinished",
]

intersphinx_mapping = {
    'py': ('https://docs.python.org/3/', None),
    'amaranth': ('https://amaranth-lang.org/docs/amaranth/v0.5.4/', None),
    # 'chipflow': ('https://docs.chipflow.io/', None),
}
intersphinx_disabled_domains = ['std']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_ivar = True
napoleon_include_init_with_doc = True
napoleon_include_special_with_doc = True
napoleon_custom_sections = [
    ("Arguments", "params_style"), # by default displays as "Parameters"
    ("Attributes", "params_style"), # by default displays as "Variables", which is confusing
    ("Members", "params_style"), # `amaranth.lib.wiring` signature members
]


rst_prolog = """
.. role:: py(code)
   :language: python
"""

rst_epilog = """
.. |required| replace:: :bdg-primary-line:`Required`
.. |optional| replace:: :bdg-secondary-line:`Optional`
"""

# -- Options for EPUB output
epub_show_urls = 'footnote'
