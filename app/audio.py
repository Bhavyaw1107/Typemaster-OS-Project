from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl

class AudioEngine:
    def __init__(self):
        self.key = QSoundEffect()
        self.ok = QSoundEffect()
        self.err = QSoundEffect()
        self.enabled = True

    def load_from_theme(self, theme):
        def load(effect, path):
            effect.setSource(QUrl.fromLocalFile(path))
            effect.setVolume(0.25)
        load(self.key, theme.sfx_key)
        load(self.ok, theme.sfx_ok)
        load(self.err, theme.sfx_err)

    def play_key(self):  self.enabled and self.key.play()
    def play_ok(self):   self.enabled and self.ok.play()
    def play_err(self):  self.enabled and self.err.play()
