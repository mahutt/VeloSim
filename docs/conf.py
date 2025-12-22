"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'VeloSim'
copyright = '2025, VeloSim Contributors'
author = 'VeloSim Contributors'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

def process_docstring(app, what, name, obj, options, lines):
    """
    Remove MIT license headers from docstrings.

    This processes the docstring lines and removes the MIT license
    if it's the only content or appears at the start.
    """
    if not lines:
        return

    # Join lines to check for MIT license
    full_text = '\n'.join(lines)

    # Check if it starts with MIT License
    if full_text.strip().startswith('MIT License'):
        # Find where the license ends (after "SOFTWARE.")
        license_end_idx = None
        for i, line in enumerate(lines):
            if 'SOFTWARE.' in line:
                license_end_idx = i
                break

        if license_end_idx is not None:
            # Remove all lines up to and including the license end
            # Keep any content after the license
            remaining_lines = lines[license_end_idx + 1:]

            # Clear the lines list and add back only non-license content
            lines.clear()

            # Skip empty lines after license
            start_idx = 0
            for i, line in enumerate(remaining_lines):
                if line.strip():
                    start_idx = i
                    break

            # Only add back if there's actual content after the license
            if start_idx < len(remaining_lines):
                for line in remaining_lines[start_idx:]:
                    lines.append(line)

def setup(app):
    """Setup function for Sphinx."""
    app.connect('autodoc-process-docstring', process_docstring)

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/20/', None),
}

# Suppress warnings for ambiguous cross-references
# We have duplicate class names (Resource, Station, Scenario) in both
# back.models (database ORM) and sim.entities (simulation engine)
suppress_warnings = ['ref.python']
