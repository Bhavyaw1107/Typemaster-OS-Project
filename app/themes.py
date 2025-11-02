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


# -------- Built-in themes (6) --------
THEMES: List[Theme] = [
    Theme(  # warm yellow on charcoal (Monkeytype "Serika"-style)
        name="Serika Dark",
        background="#0b0f14",
        primary="#e6e6e6",
        secondary="#9aa1a9",
        accent="#f5d061",
    ),
    Theme(  # Dracula palette
        name="Dracula",
        background="#282a36",
        primary="#f8f8f2",
        secondary="#6272a4",
        accent="#bd93f9",
    ),
    Theme(  # One Dark
        name="One Dark",
        background="#1e2127",
        primary="#e6e6e6",
        secondary="#7f848e",
        accent="#e5c07b",
    ),
    Theme(  # Catppuccin Mocha aesthetic theme
        name="Catppuccin Mocha",
        background="#1e1e2e",
        primary="#cdd6f4",     
        secondary="#a6adc8",   
        accent="#f5e0dc",      
    ),

    Theme(  # Tokyo Night
        name="Tokyo Night",
        background="#1a1b26",
        primary="#c0caf5",
        secondary="#7aa2f7",
        accent="#ff9e64",
    ),
    Theme(  # Nord (keep a cool option)
        name="Nord",
        background="#2e3440",
        primary="#eceff4",
        secondary="#88c0d0",
        accent="#bf616a",
    ),
]

# set which theme loads first (0 = Serika Dark)
DEFAULT_THEME_INDEX = 0

_CUSTOM_FILE = Path("themes.json")
_BUILTIN_COUNT = len(THEMES)


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
    """Persist only custom themes (not the built-ins) to themes.json."""
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
        # Never crash on save; silently ignore I/O errors.
        pass


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
        # Ignore malformed file
        pass


def add_runtime_theme_from_dict(d: Dict[str, Any]) -> int:
    """
    Append a theme at runtime and persist it to themes.json (customs only).
    Returns the index of the new theme.
    """
    theme = _theme_from_dict(d)
    THEMES.append(theme)

    # Persist only customs (everything after the built-ins)
    custom = THEMES[_BUILTIN_COUNT:]
    _save_custom_themes(custom)
    return len(THEMES) - 1
