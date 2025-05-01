# SPDX-License-Identifier: BSD-2-Clause
# Configuration file for the Sphinx documentation builder.

# Add parent folder to path so we can pick up module
import os
import sys
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
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'autoapi.extension',
    'sphinx.ext.napoleon'
]

html_theme = 'sphinx_book_theme'
html_logo = '_static/chipflow-logo.svg'
html_title = "ChipFlow Platform Documentation"


html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

html_static_path = ['_static']

html_theme_options = {
    "home_page_in_toc": True,
    "repository_url": "https://github.com/ChipFlow/chipflow-lib",
    "repository_branch": "master",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "show_navbar_depth": 3,
    # "announcement": "<b>v3.0.0</b> is now out! See the Changelog for details",
}

autodoc_typehints = 'description'

autoapi_dirs = ["../chipflow_lib"]
autoapi_options = [
    'members',
    'undoc-members',
    'show-inheritance',
    'show-module-summary',
    'imported-members',
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

# -- Options for EPUB output
epub_show_urls = 'footnote'
