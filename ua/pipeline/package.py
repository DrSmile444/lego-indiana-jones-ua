"""Release package: loader + ASI + UAP + README + licenses, as a reproducible ZIP."""
from __future__ import annotations

import datetime
import zipfile
from pathlib import Path

from .. import paths
from ..util import UaError, read_json, sha256, write_json

LOADER_DIR = paths.NATIVE / "vendor/ultimate-asi-loader-v9.7.4"
PACKAGE_TEMPLATE = paths.ASSETS / "package/README.txt"
NOTES_TEMPLATE = paths.ASSETS / "package/RELEASE_NOTES.md"
REPOSITORY = "https://github.com/DrSmile444/lego-indiana-jones-ua"
SUPPORTED_EXE_SHA256 = "c12f7348ec63aed61f56eb15d825f15b8340500668fa8c8dcf06c2f332e5e5fd"
FILES = ("dinput8.dll", "scripts/UKRAINIAN.asi", "scripts/UKRAINIAN.uap",
         "scripts/UKRAINIAN/README.txt", "scripts/UKRAINIAN/LICENSE.txt",
         "scripts/UKRAINIAN/LICENSE-ASI-Loader.txt")
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def version() -> str:
    return (paths.REPO / "VERSION").read_text(encoding="utf-8").strip()


def archive_name(ver: str) -> str:
    return f"lego-indiana-jones-ua-{ver}.zip"


def loader() -> tuple[bytes, bytes, dict]:
    provenance = read_json(LOADER_DIR / "provenance.json")
    dll = (LOADER_DIR / "dinput8.dll").read_bytes()
    if sha256(dll) != provenance["dll_sha256"]:
        raise UaError("Vendored Ultimate ASI Loader does not match provenance.json")
    return dll, (LOADER_DIR / "LICENSE.txt").read_bytes(), provenance


def project_license() -> bytes:
    parts = [paths.REPO / "LICENSE", paths.REPO / "LICENSES/MIT.txt", paths.REPO / "LICENSES/CC-BY-4.0.txt"]
    return ("\n\n".join(p.read_text(encoding="utf-8").rstrip() for p in parts) + "\n").encode("utf-8")


def readme(ver: str) -> bytes:
    return PACKAGE_TEMPLATE.read_text(encoding="utf-8").replace("{version}", ver).encode("utf-8")


def bundle(ver: str, package: bytes, asi: bytes) -> dict[str, bytes]:
    dll, loader_license, _ = loader()
    files = {
        "dinput8.dll": dll,
        "scripts/UKRAINIAN.asi": asi,
        "scripts/UKRAINIAN.uap": package,
        "scripts/UKRAINIAN/README.txt": readme(ver),
        "scripts/UKRAINIAN/LICENSE.txt": project_license(),
        "scripts/UKRAINIAN/LICENSE-ASI-Loader.txt": loader_license,
    }
    assert tuple(files) == FILES
    return files


def write_zip(target: Path, files: dict[str, bytes]) -> None:
    """Fixed timestamps and order make the archive reproducible."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name], compresslevel=9)
    with zipfile.ZipFile(target) as check:
        if check.testzip() is not None or check.namelist() != list(FILES):
            raise UaError(f"{target}: archive verification failed")
        for name in FILES:
            if check.read(name) != files[name]:
                raise UaError(f"{target}: {name} differs after writing")


def changelog_section(ver: str) -> str:
    """The body of `## <ver> — date` in CHANGELOG.md, without its heading."""
    text = (paths.REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    start = text.find(f"## {ver} ")
    if start < 0:
        raise UaError(f"CHANGELOG.md has no section for {ver}")
    body = text[text.index("\n", start) + 1:]
    end = body.find("\n## ")
    return (body if end < 0 else body[:end]).strip()


def release_notes(ver: str, archive: Path, digest: str) -> str:
    """GitHub Release body: a prominent download link first, then changes."""
    return (NOTES_TEMPLATE.read_text(encoding="utf-8")
            .replace("{archive}", archive.name)
            .replace("{size_mb}", f"{archive.stat().st_size / 1_000_000:.0f}")
            .replace("{download_url}", f"{REPOSITORY}/releases/download/v{ver}/{archive.name}")
            .replace("{sha256}", digest)
            .replace("{changes}", changelog_section(ver)))


def release(ver: str, package: bytes, asi: bytes, baseline_version: str, changed: list[str]) -> Path:
    destination = paths.DIST / ver
    manifest_path = paths.MANIFESTS / "releases" / f"{ver}.json"
    if destination.exists():
        raise UaError(f"{destination} already exists; released versions are never overwritten")
    files = bundle(ver, package, asi)
    destination.mkdir(parents=True)
    archive = destination / archive_name(ver)
    write_zip(archive, files)
    for name, data in files.items():
        target = destination / "files" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    digest = sha256(archive.read_bytes())
    (destination / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="ascii", newline="\n")
    (destination / "RELEASE_NOTES.md").write_text(release_notes(ver, archive, digest), encoding="utf-8", newline="\n")
    _, _, provenance = loader()
    write_json(manifest_path, {
        "version": ver,
        "date": datetime.date.today().isoformat(),
        "archive": archive.name,
        "archive_size": archive.stat().st_size,
        "archive_sha256": digest,
        "files": {name: {"size": len(data), "sha256": sha256(data)} for name, data in files.items()},
        "baseline": baseline_version,
        "changed_uap_resources": changed,
        "supported_exe_sha256": SUPPORTED_EXE_SHA256,
        "loader": provenance,
    })
    return archive
