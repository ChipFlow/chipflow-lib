# SPDX-License-Identifier: BSD-2-Clause
# Configuration file for the Sphinx documentation builder.

# Add parent folder to path so we can pick up module
import os
import sys
doctest_path = [os.path.abspath('..')]

# -- Project information

project = 'ChipFlow'
copyright = 'ChipFlow'
author = 'ChipFlow'

release = 'alpha'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

# -- Options for EPUB output
epub_show_urls = 'footnote'
