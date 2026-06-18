"""Shared, lazily-built singletons for the API routers.

One store + one provider across routers so a persona created via /personas is
visible to /generate. Heavy backends (media gate) are still built lazily on first
content generation so the server can boot without the ML stack.
"""

from __future__ import annotations

from avatar_studio.config import Settings

_settings = Settings.from_env()
_store = None
_registry = None


def settings() -> Settings:
    return _settings


def store():
    global _store
    if _store is None:
        from avatar_studio.factory import build_store

        _store = build_store(_settings)
    return _store


def registry():
    global _registry
    if _registry is None:
        from avatar_studio.factory import build_provider
        from avatar_studio.personas.registry import PersonaRegistry

        _registry = PersonaRegistry(store(), build_provider(_settings))
    return _registry


def gen_context():
    """Built per call: the media gate is heavy and not needed until generating."""
    from avatar_studio.factory import build_gen_context

    return build_gen_context(_settings, store=store())


def copywriter():
    from avatar_studio.factory import build_copywriter

    return build_copywriter(_settings)
