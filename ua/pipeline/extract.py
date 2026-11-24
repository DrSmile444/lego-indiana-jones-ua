"""Extract the game files the build needs from the Steam DAT archives via QuickBMS.

QuickBMS and ttgames.bms are third-party and live in local/tools/quickbms/
(see manifests/inputs.json for versions and checksums). Only files listed in
manifests/game-files.json are extracted unless `--all` is given. The Steam folder
is opened read-only; its DAT/EXE hashes are compared before and after.

extract_lsw3 takes the 2x button icon font from LEGO Star Wars III: The Clone Wars
(manifests/game-files.json "lsw3_files") into game/LSW3/; see font_hd.py (buttons).
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


def verify(root: Path | None = None, key: str = "files") -> list[str]:
    """Return problems with the extracted files (empty list = all good)."""
    root = root or paths.GAME
    problems = []
    for relative, digest in manifest()[key].items():
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


LSW3_EXE = "LEGOCloneWars.exe"


def _stamp(game: Path, archives: list[str]) -> dict[str, tuple[int, int]]:
    """Size and write time of each archive: the LEGO Star Wars III DATs are too large to hash."""
    return {a: ((game / f"{a}.DAT").stat().st_size, (game / f"{a}.DAT").stat().st_mtime_ns) for a in archives}


def extract_lsw3(game: Path) -> None:
    """Extract the LEGO Star Wars III files the button icons need into game/LSW3/."""
    if not QUICKBMS.exists() or not SCRIPT.exists():
        raise UaError(f"QuickBMS not found in {QUICKBMS.parent}; see docs/setup.md (Рівень 1)")
    if not (game / LSW3_EXE).exists():
        raise UaError(f"{game}: {LSW3_EXE} not found (LEGO Star Wars III: The Clone Wars Steam folder)")
    files = manifest()["lsw3_files"]
    archives = sorted({relative.split("/", 1)[0] for relative in files})
    before = _stamp(game, archives)
    target = paths.GAME / "LSW3"
    with tempfile.TemporaryDirectory(dir=paths.REPO) as staging:
        staging = Path(staging)
        for archive in archives:
            inner = [r.split("/", 1)[1] for r in files if r.startswith(archive + "/")]
            filters = ";".join("{}" + name.replace("/", "\\") for name in inner)
            args = [str(QUICKBMS), "-o", "-Y", "-f", filters, str(SCRIPT),
                    str(game / f"{archive}.DAT"), str(staging / archive)]
            say(f"  LEGO Star Wars III {archive}.DAT ...")
            result = subprocess.run(args, capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                raise UaError(f"QuickBMS failed on {archive}.DAT:\n{result.stdout[-1500:]}{result.stderr[-1500:]}")
        problems = verify(staging, "lsw3_files")
        if problems:
            raise UaError("LEGO Star Wars III files do not match manifests/game-files.json:\n  "
                          + "\n  ".join(problems))
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(staging, target)
    if _stamp(game, archives) != before:
        raise UaError("The LEGO Star Wars III folder changed during extraction — this must never happen")
