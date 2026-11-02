"""Level 1: byte-compare the C++ texture patcher (native/asi/textures.h) with Python.

For every GSC container of a translated texture, the expected result is the
original container with each occurrence replaced by the rebuilt DDS from
build/UKRAINIAN.uap. texture_test.exe applies the UAP in the same way the ASI
does in memory and must produce identical bytes.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .. import paths
from ..formats import uap
from ..util import UaError, read_json, say
from .build import OUTPUT
from .textures import MANIFEST


def run(exe: Path) -> None:
    if not OUTPUT.exists():
        raise UaError("build/UKRAINIAN.uap missing; run `python -m ua build` first")
    resources = dict(uap.read(OUTPUT.read_bytes()))
    containers: dict[tuple[str, str], list[tuple[int, bytes]]] = {}
    for item in read_json(MANIFEST)["textures"]:
        payload = resources[f"UKRAINIAN/TEXTURES/{item['uap_key']}.DDS"]
        for occurrence in item["occurrences"]:
            containers.setdefault((occurrence["archive"], occurrence["resource"]), []).append(
                (occurrence["offset"], payload))
    with tempfile.TemporaryDirectory() as work:
        for (archive, resource), patches in sorted(containers.items()):
            original = paths.GAME / archive / resource
            expected = bytearray(original.read_bytes())
            for offset, payload in patches:
                expected[offset:offset + len(payload)] = payload
            target = Path(work) / "expected.bin"
            target.write_bytes(expected)
            result = subprocess.run([str(exe), str(OUTPUT), str(original), str(target)],
                                    capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                raise UaError(f"{resource}: C++ patcher differs ({result.returncode}) {result.stdout} {result.stderr}")
    say(f"PASS: {len(containers)} GSC containers patched identically by the C++ code")
