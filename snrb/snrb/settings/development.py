"""
Django development settings for SNRB project.

Extends base.py with development-specific overrides.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Allow browsable API renderer in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)
