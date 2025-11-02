import json, os
from pathlib import Path

DEFAULT_TEXT = (
    "Welcome to Typemaster — press any key to start. "
    "Type this text; correct keystrokes glow green, mistakes glow red. "
    "Watch live WPM and accuracy on the right, and discover your weak keys."
)

_DEFAULT_FILE = Path("assets/texts/default.txt")

STAKEHOLDERS_PATH = "data/stakeholders.json"

_FALLBACK = (
    "Welcome to Typemaster!\n\n"
    "Type this paragraph to test the app. "
    "You can replace this default text by editing assets/texts/default.txt."
)


def ensure_stakeholders_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(STAKEHOLDERS_PATH):
        default = {
            "title": "Welcome to Typemaster",
            "subtitle": "Press any key to start. Type the prompt exactly. Correct = green, mistakes = red. Live WPM & accuracy on the right.",
            "stakeholders": [],
        }
        with open(STAKEHOLDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)


def load_stakeholders():
    try:
        with open(STAKEHOLDERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"title": "Welcome to Typemaster", "subtitle": "", "stakeholders": []}


def ensure_app_files():
    # Data dir + results file
    os.makedirs("data", exist_ok=True)
    if not os.path.exists("data/test_results.json"):
        with open("data/test_results.json", "w", encoding="utf-8") as f:
            json.dump([], f)

    # SFX placeholders so QSoundEffect has valid targets
    os.makedirs("assets/sfx", exist_ok=True)
    for fn in (
        "key_click.wav",
        "ok.wav",
        "err.wav",
        "key_soft.wav",
        "key_tock.wav",
        "key_water.wav",
        "key_air.wav",
        "key_type.wav",
    ):
        p = os.path.join("assets/sfx", fn)
        if not os.path.exists(p):
            open(p, "ab").close()

    # Styles + themes dir
    os.makedirs("assets", exist_ok=True)
    if not os.path.exists("assets/styles.css"):
        with open("assets/styles.css", "w", encoding="utf-8") as f:
            f.write(
                "/* Extend styles if you want; most colors come from theme palettes. */"
            )
    os.makedirs("assets/themes", exist_ok=True)

    # Stakeholders JSON
    ensure_stakeholders_file()


def load_default_text() -> str:
    try:
        if _DEFAULT_FILE.exists():
            return (
                _DEFAULT_FILE.read_text(encoding="utf-8").strip().replace("\r\n", "\n")
            )
    except Exception:
        pass
    return _FALLBACK
