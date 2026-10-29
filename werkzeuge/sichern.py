"""Sichert alle Spielstände in _sicherungen/ (neben werkzeuge/)<Zeitstempel>.

Aufruf: python sichern.py
Immer vor jeder Änderung am Spielstand ausführen.
"""
import os
import shutil
import time

SAVES = os.path.expandvars(r"%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames")
HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "..", "_sicherungen", time.strftime("%Y-%m-%d_%H-%M-%S"))

if __name__ == "__main__":
    shutil.copytree(SAVES, DEST)
    print("Gesichert nach", os.path.normpath(DEST))
