"""Report which reproduction levels are available on this machine and what is missing."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import baseline, paths
from .pipeline import extract
from .util import UaError, read_json, sha256_file


def _check(label: str, ok: bool, fix: str = "") -> bool:
    print(f"  [{'ok' if ok else '--'}] {label}" + ("" if ok or not fix else f"\n        -> {fix}"))
    return ok


def _input(identifier: str) -> dict:
    return next(i for i in read_json(paths.MANIFESTS / "inputs.json")["inputs"] if i["id"] == identifier)


def _input_ok(identifier: str) -> bool:
    item = _input(identifier)
    path = paths.REPO / item["path"]
    return path.exists() and sha256_file(path) == item["sha256"]


def _msvc() -> bool:
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not vswhere.exists():
        return False
    result = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                             "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                            capture_output=True, text=True)
    return bool(result.stdout.strip())


def run() -> int:
    print("Text level (translation fixes; no game files needed):")
    try:
        baseline.locate(download=False)
        base_ok = True
    except UaError as error:
        base_ok = False
        reason = str(error)
    text_ok = _check("baseline release ZIP (manifests/baseline.json)", base_ok,
                     "" if base_ok else reason + " — or run `python -m ua build` with network access")

    print("Level 1 — fonts and textures (needs your Steam copy):")
    game_ok = _check("extracted game files (game/)", not extract.verify(),
                     "python -m ua extract --game \"<Steam>/LEGO Indiana Jones The Original Adventures\"")
    qbms_ok = _check("QuickBMS + ttgames.bms (local/tools/quickbms/)", _input_ok("quickbms") and _input_ok("ttgames-bms"),
                     "see docs/setup.md, section QuickBMS")
    donor_ok = _check("third-party Cyrillic font patch (local/donors/cyrillic-font-patch/)", _input_ok("cyrillic-font-patch"),
                      "see manifests/inputs.json")
    adv_ok = _check("fan font Adventure (local/donors/)", _input_ok("adventure-ttf"), "see manifests/inputs.json")
    fr_ok = _check("Franklin Gothic Medium (local/fonts/)", _input_ok("franklin-gothic-medium"),
                   "license it from the rights holder; see docs/setup.md")
    try:
        import PIL  # noqa: F401
        pil_ok = True
    except ImportError:
        pil_ok = False
    _check("Python Pillow", pil_ok, "python -m pip install -r requirements.txt")

    print("Native — UKRAINIAN.asi:")
    native_ok = _check("Visual Studio C++ x86 Build Tools + Windows SDK", _msvc(), "see docs/setup.md")
    _check("PowerShell 7 (pwsh)", shutil.which("pwsh") is not None, "https://aka.ms/powershell")

    print()
    print(f"Text build:     {'available' if text_ok else 'NOT available'}")
    print(f"Full build:     {'available' if text_ok and game_ok and donor_ok and adv_ok and fr_ok and pil_ok else 'NOT available'}")
    print(f"Extraction:     {'available' if qbms_ok else 'NOT available'}")
    print(f"Release (ASI):  {'available' if text_ok and native_ok else 'NOT available'}")
    return 0
