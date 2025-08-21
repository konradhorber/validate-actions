# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'validate-actions'
copyright = '2025, konradhorber'
author = 'konradhorber'
release = '1.0.3'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# -- Autodoc configuration --------------------------------------------------
autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
}

# Clean up type signatures  
autodoc_typehints = 'description'  # Move type hints to parameter descriptions
python_use_unqualified_type_names = True  # Use short names like Event instead of validate_actions.domain_model.ast.Event

# Generate autosummary
autosummary_generate = True
autosummary_generate_overwrite = True  # Always regenerate autosummary files

# Path to Python source
import os
import sys

sys.path.insert(0, os.path.abspath('..'))
