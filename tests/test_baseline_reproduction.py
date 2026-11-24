"""The build reproduces the UKRAINIAN.uap of the current release byte for byte.

A release that changed only text resources is rebuilt at the text level (baseline
ZIP + JSON translations). A release that also changed fonts or textures is rebuilt
at the full level (needs game/). Skipped when an input is not available locally.
"""
import unittest

from ua import baseline, paths
from ua.formats import uap
from ua.pipeline import build, package, text
from ua.util import UaError, read_json, sha256

TEXT_PREFIX = "STUFF/TEXT/"


class ReleaseReproductionTest(unittest.TestCase):
    def test_build_matches_release_manifest(self):
        manifest = paths.MANIFESTS / "releases" / f"{package.version()}.json"
        if not manifest.exists():
            self.skipTest(f"{manifest.name} not built yet")
        release = read_json(manifest)
        full = any(not name.startswith(TEXT_PREFIX) for name in release["changed_uap_resources"])
        try:
            if full:
                rebuilt, _, _ = build.build_uap("full")
            else:
                rebuilt = uap.pack(text.apply(build.with_added_text(baseline.load(download=False).resources)))
        except UaError as error:
            self.skipTest(str(error))
        self.assertEqual(sha256(rebuilt), release["files"]["scripts/UKRAINIAN.uap"]["sha256"])


if __name__ == "__main__":
    unittest.main()
