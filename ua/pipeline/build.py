"""Build UKRAINIAN.uap (text or full level) and, optionally, the release package."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import baseline as baseline_module
from .. import paths
from ..formats import uap
from ..util import UaError, say, sha256
from . import fonts, package, text, textures

OUTPUT = paths.BUILD / "UKRAINIAN.uap"
UNPACKED = paths.BUILD / "uap-unpacked"


def _replace(resources: list[tuple[str, bytes]], new: dict[str, bytes]) -> list[tuple[str, bytes]]:
    missing = set(new) - {name for name, _ in resources}
    if missing:
        raise UaError(f"Template has no resources {sorted(missing)}")
    return [(name, new.get(name, data)) for name, data in resources]


def with_added_text(resources: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Append text resources the baseline does not have yet, using game/ as template."""
    present = {name for name, _ in resources}
    added = []
    for name in paths.ADDED_TEXT:
        if name not in present:
            try:
                added.append((name, paths.game_file(name).read_bytes()))
            except FileNotFoundError as error:
                raise UaError(f"{name} is not in the baseline yet; its template comes from game/. {error}")
    return resources + added


def build_uap(level: str) -> tuple[bytes, list[str], str]:
    base = baseline_module.load()
    resources = with_added_text(base.resources)
    notes: list[str] = []
    if level == "full":
        say("Level 1: rebuilding fonts and textures from game/ and local/")
        resources = _replace(resources, fonts.build())
        texture_resources, differences = textures.build()
        resources = _replace(resources, dict(texture_resources))
        notes += differences
    resources = text.apply(resources)
    data = uap.pack(resources)
    before = dict(base.resources)
    changed = [name for name, data in resources if before.get(name) != data]
    paths.BUILD.mkdir(exist_ok=True)
    OUTPUT.write_bytes(data)
    if UNPACKED.exists():
        shutil.rmtree(UNPACKED)
    uap.unpack_to(data, UNPACKED)
    return data, changed, base.version


def native_asi() -> bytes:
    script = paths.NATIVE / "build.ps1"
    result = subprocess.run(["pwsh", "-NoProfile", "-File", str(script), "-SmokeTest"],
                            capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise UaError(f"native/build.ps1 failed:\n{result.stdout[-3000:]}\n{result.stderr[-2000:]}")
    return (paths.BUILD / "native/asi/UKRAINIAN.asi").read_bytes()


def run(level: str, release: str | None) -> Path:
    data, changed, base_version = build_uap(level)
    say(f"UKRAINIAN.uap: {len(data)} bytes, SHA-256 {sha256(data)}")
    say(f"Changed against baseline {base_version}: {', '.join(changed) if changed else 'nothing (byte-identical)'}")
    if not release:
        return OUTPUT
    if release != package.version():
        raise UaError(f"--release {release} does not match VERSION ({package.version()})")
    say("Native: building and testing UKRAINIAN.asi")
    asi = native_asi()
    archive = package.release(release, data, asi, base_version, changed)
    say(f"Release: {archive}")
    return archive
