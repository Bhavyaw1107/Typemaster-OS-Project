# app/themes.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List
import json


@dataclass
class Theme:
    name: str
    background: str
    primary: str
    secondary: str
    accent: str


# -------- Built-in themes --------
THEMES: List[Theme] = [
    Theme(
        name="Monkeytype Dark",
        background="#0f1115",
        primary="#e5e7eb",
        secondary="#6b7280",
        accent="#eab308",
    ),
    Theme(
        name="Monkeytype Light",
        background="#fafafa",
        primary="#111111",
        secondary="#6b6b6b",
        accent="#eab308",
    ),
    Theme(
        name="Nord",
        background="#2e3440",
        primary="#eceff4",
        secondary="#88c0d0",
        accent="#bf616a",
    ),
]

DEFAULT_THEME_INDEX = 0
_CUSTOM_FILE = Path("themes.json")


# -------- helpers --------
def _theme_from_dict(d: Dict[str, Any]) -> Theme:
    required = {"name", "background", "primary", "secondary", "accent"}
    missing = required - set(d.keys())
    if missing:
        raise ValueError(f"Missing theme keys: {', '.join(sorted(missing))}")
    return Theme(
        name=str(d["name"]),
        background=str(d["background"]),
        primary=str(d["primary"]),
        secondary=str(d["secondary"]),
        accent=str(d["accent"]),
    )


def _save_custom_themes(extra: List[Theme]) -> None:
    try:
        payload = [
            {
                "name": t.name,
                "background": t.background,
                "primary": t.primary,
                "secondary": t.secondary,
                "accent": t.accent,
            }
            for t in extra
        ]
        _CUSTOM_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass  # never crash on save


# -------- public API used by UI --------
def load_custom_themes() -> None:
    """Load extra themes from themes.json (if present)."""
    if not _CUSTOM_FILE.exists():
        return
    try:
        data = json.loads(_CUSTOM_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                try:
                    THEMES.append(_theme_from_dict(item))
                except Exception:
                    continue
    except Exception:
        pass


def add_runtime_theme_from_dict(d: Dict[str, Any]) -> int:
    """
    Expected by ui/theme_editor.py.
    - Validates dict
    - Appends to THEMES
    - Persists to themes.json (custom themes only)
    - Returns index of the new theme
    """
    theme = _theme_from_dict(d)
    THEMES.append(theme)

    # First N entries are built-ins; persist only customs
    builtin_count = 3  # keep in sync with built-in list above
    custom = THEMES[builtin_count:]
    _save_custom_themes(custom)
    return len(THEMES) - 1
