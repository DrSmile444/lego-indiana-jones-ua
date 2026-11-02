"""Install, uninstall and statically verify the package in a game folder.

Every file we overwrite is backed up first under
`<game>/ukrainian-localization-backup/<timestamp>/`, and `install-state.json`
records what was there before, so `uninstall` restores the exact prior state.
"""
from __future__ import annotations

import datetime
import shutil
import zipfile
from pathlib import Path

from ..util import UaError, read_json, sha256, sha256_file, write_json
from .package import FILES, SUPPORTED_EXE_SHA256, loader

STATE_DIR = "ukrainian-localization-backup"
STATE = "install-state.json"


def _check_game(game: Path) -> None:
    exe = game / "LEGOIndy.exe"
    if not exe.exists():
        raise UaError(f"{game}: LEGOIndy.exe not found — point --game at the game folder")
    digest = sha256_file(exe)
    if digest != SUPPORTED_EXE_SHA256:
        raise UaError(f"Unsupported LEGOIndy.exe (SHA-256 {digest}); only the Steam build is supported")


def read_package(source: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    if set(files) != set(FILES):
        raise UaError(f"{source}: unexpected package content {sorted(files)}")
    return files


def install(game: Path, source: Path, allow_foreign_loader: bool = False) -> Path:
    _check_game(game)
    files = read_package(source)
    known_loader = sha256(loader()[0])
    current_loader = game / "dinput8.dll"
    if current_loader.exists() and sha256_file(current_loader) != known_loader and not allow_foreign_loader:
        raise UaError("The game already has a different dinput8.dll (another mod or loader). "
                      "Keep it if it is a compatible x86 ASI loader and copy only scripts/, "
                      "or rerun with --allow-foreign-loader to replace it (it will be backed up).")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = game / STATE_DIR / stamp
    state = {"package": source.name, "installed_at": stamp, "files": {}}
    written: list[Path] = []
    try:
        for name, data in files.items():
            target = game / name
            entry = {"sha256": sha256(data), "previous": None}
            if target.exists():
                copy = backup / name
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, copy)
                entry["previous"] = {"backup": copy.relative_to(game).as_posix(), "sha256": sha256_file(target)}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append(target)
            state["files"][name] = entry
    except Exception:
        _restore(game, state)
        raise
    write_json(game / STATE_DIR / STATE, state)
    return backup


def _restore(game: Path, state: dict) -> None:
    for name, entry in state["files"].items():
        target = game / name
        previous = entry.get("previous")
        if previous:
            shutil.copy2(game / previous["backup"], target)
        elif target.exists():
            target.unlink()
    scripts_dir = game / "scripts" / "UKRAINIAN"
    for folder in (scripts_dir, game / "scripts"):
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()


def uninstall(game: Path) -> None:
    state_path = game / STATE_DIR / STATE
    if not state_path.exists():
        raise UaError(f"{state_path} not found: nothing installed by `ua install`. "
                      "Manual removal: delete scripts/UKRAINIAN.asi, scripts/UKRAINIAN.uap, scripts/UKRAINIAN/")
    state = read_json(state_path)
    _restore(game, state)
    for name, entry in state["files"].items():
        previous = entry.get("previous")
        target = game / name
        if previous and sha256_file(target) != previous["sha256"]:
            raise UaError(f"Restore check failed for {name}")
        if not previous and target.exists():
            raise UaError(f"{name} still exists after uninstall")
    state_path.rename(state_path.with_name(f"uninstalled-{state['installed_at']}.json"))


def verify(game: Path) -> list[str]:
    """Static check: installed files equal the recorded package hashes."""
    _check_game(game)
    state_path = game / STATE_DIR / STATE
    if not state_path.exists():
        raise UaError("No install-state.json; install with `python -m ua install` first")
    problems = []
    for name, entry in read_json(state_path)["files"].items():
        target = game / name
        if not target.exists():
            problems.append(f"missing {name}")
        elif sha256_file(target) != entry["sha256"]:
            problems.append(f"changed {name}")
    return problems
