"""Locale alias tables for Helen stdlib.

Each locale module exports an ``ALIASES`` dict mapping localized names
to canonical English stdlib function names.

Usage at startup (by interpreter):
    from helen.stdlib.locales import register_all_aliases
    register_all_aliases()

All locales are loaded unconditionally — the user's ``locale`` config
setting only affects presentation (docs, LSP, error messages), not
what names are available at runtime.
"""

from __future__ import annotations

from typing import Mapping

# Available locales: code → module
# Add new languages by dropping a new module here (e.g. ja.py).
_LOCALES: dict[str, str] = {
    "zh": "helen.stdlib.locales.zh",
}


def all_aliases() -> dict[str, dict[str, str]]:
    """Return a mapping of locale_code → {alias: canonical} for all locales."""
    import importlib
    result: dict[str, dict[str, str]] = {}
    for code, module_path in _LOCALES.items():
        mod = importlib.import_module(module_path)
        aliases: Mapping[str, str] = getattr(mod, "ALIASES", {})
        result[code] = dict(aliases)
    return result


def register_all_aliases() -> None:
    """Register aliases from all locales into the global stdlib registry.

    Returns a tuple (registered, skipped) counts for diagnostics.
    Skipped aliases are those whose canonical name isn't in stdlib
    or that conflict with an existing alias pointing elsewhere.
    """
    from helen.stdlib import stdlib

    registered = 0
    skipped = 0
    for _locale, aliases in all_aliases().items():
        for alias, canonical in aliases.items():
            if stdlib.register_alias(alias, canonical):
                registered += 1
            else:
                skipped += 1
    return registered, skipped
