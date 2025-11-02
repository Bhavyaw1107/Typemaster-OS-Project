from dataclasses import dataclass
from typing import List, Dict, Any
import os, json

@dataclass
class Theme:
    name: str
    bg: str
    surface: str
    text: str
    text_muted: str
    correct: str
    error: str
    caret: str
    accent: str
    graph_line: str
    sfx_key: str
    sfx_ok: str
    sfx_err: str

def _sfx(p): return f"assets/sfx/{p}"

THEMES: List[Theme] = [
    Theme("Midnight Neon", "#0b0f14", "#111825", "#e6f0ff", "#93a4bd", "#33ff99", "#ff4d4d", "#9cdcfe", "#7aa2f7", "#5ac8fa",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Solar Dawn", "#fdf6e3", "#f5e5ba", "#3b3a30", "#6b6a5f", "#2aa198", "#dc322f", "#657b83", "#b58900", "#cb4b16",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Forest Mist", "#0f1a13", "#14231a", "#e4ffe8", "#98c1a3", "#5de682", "#ff6b6b", "#c0f5d6", "#8bd3dd", "#7bd389",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Cherry Cola", "#1a0f12", "#2a1820", "#ffdfe8", "#f29db6", "#ff4f9a", "#ff3355", "#ffd1e0", "#ff7ab3", "#ff93c9",
          _sfx("key_tock.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Nordic Ice", "#2e3440", "#3b4252", "#eceff4", "#d8dee9", "#88c0d0", "#bf616a", "#81a1c1", "#8fbcbb", "#5e81ac",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Dracula Pro", "#282a36", "#343746", "#f8f8f2", "#bdc1c6", "#50fa7b", "#ff5555", "#f1fa8c", "#bd93f9", "#8be9fd",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Ocean Hush", "#0a1b2a", "#0e2537", "#eaf6ff", "#b7d4ec", "#3dd5f3", "#ff6b6b", "#b3ecff", "#57cc99", "#4ea8de",
          _sfx("key_water.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("City Pop", "#13111c", "#1b1826", "#f1eaff", "#b6a8ff", "#80ffea", "#ff4d6d", "#f1eaff", "#a29bfe", "#74c0fc",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Matcha Latte", "#faf7f0", "#efe8da", "#3b3a3a", "#7a746b", "#56b870", "#e65a5a", "#7e7b6f", "#c9a227", "#70a97e",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Monochrome", "#121212", "#1e1e1e", "#e6e6e6", "#9a9a9a", "#76ff7a", "#ff6e6e", "#bfbfbf", "#64b5f6", "#90caf9",
          _sfx("key_tock.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Aurora", "#0b1020", "#101833", "#eaf2ff", "#a7b7d9", "#5cf28e", "#ff6a88", "#9dc1ff", "#8ad7ff", "#6ee7f0",
          _sfx("key_air.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Cappuccino", "#2b241f", "#3b3028", "#f6efe9", "#c9b6a4", "#84cc16", "#ef4444", "#f2e7da", "#f59e0b", "#a3e635",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Hacker Green", "#0b0b0b", "#111111", "#b9f6ca", "#66bb6a", "#00ff87", "#ff1744", "#e0f7fa", "#1de9b6", "#00e676",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Sunset Fade", "#120b24", "#1a1033", "#ffe6f2", "#f2b5d4", "#ff8fab", "#ff5d8f", "#ffe3f1", "#ffd166", "#ef476f",
          _sfx("key_tock.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Sandstone", "#201a17", "#2a231f", "#f6ede8", "#d1c1b6", "#7bd88f", "#f07178", "#c3b5a7", "#f2c791", "#9ad4d6",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Retro Terminal", "#0d0e0d", "#141614", "#e5ffe5", "#93e1a2", "#00ff7f", "#ff5555", "#d1ffd1", "#00d7af", "#00ffaa",
          _sfx("key_type.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Lavender Sky", "#16131a", "#1f1a28", "#f5e9ff", "#d6c4f3", "#9ef0ff", "#ff7aa2", "#b5a8ff", "#c9a7eb", "#a5d8ff",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Steel Blue", "#0d141b", "#15202b", "#e6eef5", "#a3b2bf", "#4fdbb6", "#ff6f6f", "#9ec1d9", "#5aa9e6", "#4cc9f0",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Mocha Mint", "#1b1410", "#241b15", "#fff2e6", "#e0c8b3", "#53e2ae", "#ff7d7d", "#ffe8d5", "#f3b562", "#7be495",
          _sfx("key_tock.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Slate Pop", "#0e1217", "#151b23", "#eaf0f7", "#9db0c3", "#5eead4", "#f87171", "#c7d2fe", "#60a5fa", "#22d3ee",
          _sfx("key_click.wav"), _sfx("ok.wav"), _sfx("err.wav")),
    Theme("Paper White", "#ffffff", "#f6f7f8", "#222222", "#6b7280", "#16a34a", "#dc2626", "#111827", "#3b82f6", "#2563eb",
          _sfx("key_soft.wav"), _sfx("ok.wav"), _sfx("err.wav")),
]
DEFAULT_THEME_INDEX = 0

# ---- Optional custom theme IO ----
def theme_from_dict(d: Dict[str, Any]) -> Theme:
    req = ["name","bg","surface","text","text_muted","correct","error","caret","accent","graph_line","sfx_key","sfx_ok","sfx_err"]
    for k in req:
        if k not in d:
            raise ValueError(f"Missing theme field: {k}")
    return Theme(**{k: d[k] for k in req})

def add_runtime_theme_from_dict(d: Dict[str, Any]):
    THEMES.append(theme_from_dict(d))

def load_custom_themes():
    p = "assets/themes"
    if not os.path.isdir(p):
        return
    for fn in os.listdir(p):
        if fn.lower().endswith(".json"):
            try:
                with open(os.path.join(p, fn), "r", encoding="utf-8") as f:
                    add_runtime_theme_from_dict(json.load(f))
            except Exception:
                pass
