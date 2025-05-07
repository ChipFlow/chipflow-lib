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
    'autoapi.extension',
]

html_theme = 'furo'
html_logo = '_static/chipflow-logo.svg'
html_title = "ChipFlow Platform Documentation"

autodoc_typehints = 'description'

autoapi_dirs = [
        "../chipflow_lib/platforms",
        "../chipflow_lib",
        ]
autoapi_generate_api_docs = True
autoapi_template_dir = "_templates/autoapi"
# autoapi_verbose_visibility = 2
autoapi_keep_files = True
autoapi_options = [
    'members',
    'show-inheritance',
    'show-module-summary',
    'imported-members',
]

# Exclude autoapi templates
exclude_patterns = [autoapi_template_dir]

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

# -- Options for EPUB output
epub_show_urls = 'footnote'
