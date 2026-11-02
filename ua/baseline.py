"""The baseline release: our own published package used as the build template.

`manifests/baseline.json` pins one release ZIP by SHA-256. The ZIP is looked up
in `local/baseline/` and, when a URL is set, downloaded there first. Nothing is
written to `build/` or `dist/` before the checksum matches.
"""
from __future__ import annotations

import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .formats import uap
from .util import UaError, read_json, sha256, sha256_file

MANIFEST = paths.MANIFESTS / "baseline.json"
UAP_MEMBER = "scripts/UKRAINIAN.uap"


@dataclass
class Baseline:
    version: str
    zip_path: Path
    files: dict[str, bytes]
    resources: list[tuple[str, bytes]]


def manifest() -> dict:
    return read_json(MANIFEST)


def locate(download: bool = True) -> Path:
    info = manifest()
    target = paths.BASELINES / info["file"]
    if not target.exists() and download and info.get("url"):
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        urllib.request.urlretrieve(info["url"], partial)
        if sha256_file(partial) != info["sha256"]:
            partial.unlink()
            raise UaError(f"Downloaded baseline {info['file']} has a wrong SHA-256")
        partial.replace(target)
    if not target.exists():
        hint = f"download {info['url']}" if info.get("url") else "copy the release ZIP"
        raise UaError(f"Baseline {info['file']} not found in {paths.BASELINES}; {hint} there")
    if sha256_file(target) != info["sha256"]:
        raise UaError(f"Baseline {target} does not match manifests/baseline.json (SHA-256)")
    return target


def load(download: bool = True) -> Baseline:
    info = manifest()
    path = locate(download)
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    package = files.get(UAP_MEMBER)
    if package is None or sha256(package) != info["uap_sha256"]:
        raise UaError(f"{UAP_MEMBER} inside the baseline does not match manifests/baseline.json")
    return Baseline(info["version"], path, files, uap.read(package))
