# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Configuración de Django
sys.path.insert(0, os.path.abspath('../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'global_exchange.settings'
import django
django.setup()

# -- Project information -----------------------------------------------------

project = 'global-exchange'
copyright = '2025, EQUIPO_3'
author = 'EQUIPO_3'
release = '0.1'

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser", # Soporte para Markdown
    "sphinx_design", # Componentes visuales
    "sphinx_copybutton", # Botón para copiar código
    "sphinx.ext.autodoc", # Documentación automática
    "sphinx.ext.viewcode", # Vista del código fuente
    "sphinx.ext.napoleon", # Google y NumPy style
    "sphinx.ext.autosummary" # Resumen automático de módulos
]
autosummary_generate = True

# Configuración del tema HTML

templates_path = ['_templates']
exclude_patterns = [
   "**/migrations/*",
   "**/admin/*",
   "**/tests/*",
   "**/settings/*",
   "api/*migrations*",
   "api/*admin*",
   "api/*tests*",
   "api/*settings*",
   "**/management/*",
   "api/*management*"
]

language = "es"

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
