"""Extract the game files the build needs from the Steam DAT archives via QuickBMS.

QuickBMS and ttgames.bms are third-party and live in local/tools/quickbms/
(see manifests/inputs.json for versions and checksums). Only files listed in
manifests/game-files.json are extracted unless `--all` is given. The Steam folder
is opened read-only; its DAT/EXE hashes are compared before and after.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import paths
from ..util import UaError, read_json, say, sha256_file

QUICKBMS = paths.TOOLS_BIN / "quickbms/quickbms.exe"
SCRIPT = paths.TOOLS_BIN / "quickbms/ttgames.bms"
DATS = ("GAME", "RAIDERS", "TEMPLE", "CRUSADE")


def manifest() -> dict:
    return read_json(paths.MANIFESTS / "game-files.json")


def _snapshot(game: Path) -> dict[str, str]:
    return {name: sha256_file(game / name) for name in [f"{d}.DAT" for d in DATS] + ["LEGOIndy.exe"]}


def verify(root: Path | None = None) -> list[str]:
    """Return problems with the extracted files (empty list = all good)."""
    root = root or paths.GAME
    problems = []
    for relative, digest in manifest()["files"].items():
        path = root / relative
        if not path.exists():
            problems.append(f"missing {relative}")
        elif sha256_file(path) != digest:
            problems.append(f"different {relative}")
    return problems


def extract(game: Path, everything: bool = False, force: bool = False) -> None:
    if not QUICKBMS.exists() or not SCRIPT.exists():
        raise UaError(f"QuickBMS not found in {QUICKBMS.parent}; see docs/setup.md (Рівень 1)")
    if not (game / "LEGOIndy.exe").exists():
        raise UaError(f"{game}: LEGOIndy.exe not found")
    info = manifest()
    if sha256_file(game / "LEGOIndy.exe") != info["steam_exe_sha256"]:
        say("  warning: LEGOIndy.exe differs from the supported Steam build; file checks will decide")
    before = _snapshot(game)
    wanted: dict[str, list[str]] = {}
    for relative in info["files"]:
        archive, inner = relative.split("/", 1)
        wanted.setdefault(archive, []).append(inner)
    with tempfile.TemporaryDirectory(dir=paths.REPO) as staging:
        staging = Path(staging)
        for archive in DATS:
            if not everything and archive not in wanted:
                continue
            args = [str(QUICKBMS), "-o", "-Y"]
            if not everything:
                args += ["-f", ";".join("*" + Path(p).name for p in wanted[archive])]
            args += [str(SCRIPT), str(game / f"{archive}.DAT"), str(staging / archive)]
            say(f"  {archive}.DAT ...")
            result = subprocess.run(args, capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                raise UaError(f"QuickBMS failed on {archive}.DAT:\n{result.stdout[-1500:]}{result.stderr[-1500:]}")
        problems = verify(staging)
        if problems:
            raise UaError("Extracted files do not match manifests/game-files.json "
                          "(different game version?):\n  " + "\n  ".join(problems))
        if paths.GAME.exists() and any(paths.GAME.iterdir()) and not force:
            existing = verify()
            if not existing:
                say("  game/ already contains identical files; nothing to do")
                return
            raise UaError(f"{paths.GAME} already has different content; rerun with --force to replace it")
        if paths.GAME.exists():
            shutil.rmtree(paths.GAME)
        shutil.copytree(staging, paths.GAME)
    if _snapshot(game) != before:
        raise UaError("The Steam folder changed during extraction — this must never happen")
