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
release = '1.0'

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser", # Soporte para Markdown
    "sphinx_design", # Componentes visuales
    "sphinx_copybutton", # Botón para copiar código
    "sphinx.ext.autodoc", # Documentación automática
    "sphinx.ext.viewcode", # Vista del código fuente
    "sphinx.ext.napoleon", # Google y NumPy style
    "sphinx.ext.autosummary", # Resumen automático de módulos
    "sphinx_togglebutton"
]
autosummary_generate = True

autodoc_default_options = {
    'members': True, 
    'undoc-members': True,
    'private-members': False,
    'show-inheritance': False,
    'inherited-members': False,
    'exclude-members': 'DoesNotExist , MultipleObjectsReturned, add_note, with_traceback, args, base_fields, declared_fields, media'
}
autodoc_typehints = "description"
autodoc_class_signature = "separated"   # saca el (*args, **kwargs) del título

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
   "api/*apps*",
   "api/*urls*",
   "**/management/*",
   "api/*management*"
]

language = "es"

def skip_django_noise(app, what, name, obj, skip, options):
    # Filtra helpers y managers/excepciones del ORM
    if name in {"objects", "DoesNotExist", "MultipleObjectsReturned"}:
        return True
    if name.startswith(("get_next_by_", "get_previous_by_")):
        return True
    if name.startswith("get_") and name.endswith("_display"):
        return True
    try:
        from django.db.models.query_utils import DeferredAttribute
        from django.db.models.fields.related_descriptors import (
            ReverseManyToOneDescriptor, ForwardManyToOneDescriptor, ManyToManyDescriptor
        )
        if isinstance(obj, (DeferredAttribute, ReverseManyToOneDescriptor,
                            ForwardManyToOneDescriptor, ManyToManyDescriptor)):
            return True
    except Exception:
        pass
    return skip

def setup(app):
    app.connect("autodoc-skip-member", skip_django_noise)

add_module_names = False
autodoc_member_order = "bysource"

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
