"""The text build reproduces the UKRAINIAN.uap of the current release byte for byte.

Skipped when an input is not available locally: the baseline ZIP, or — while the
baseline predates the US-locale resources — the extracted game templates.
"""
import unittest

from ua import baseline, paths
from ua.formats import uap
from ua.pipeline import build, package, text
from ua.util import UaError, read_json, sha256


class ReleaseReproductionTest(unittest.TestCase):
    def test_text_build_matches_release_manifest(self):
        manifest = paths.MANIFESTS / "releases" / f"{package.version()}.json"
        if not manifest.exists():
            self.skipTest(f"{manifest.name} not built yet")
        try:
            resources = build.with_added_text(baseline.load(download=False).resources)
        except UaError as error:
            self.skipTest(str(error))
        rebuilt = uap.pack(text.apply(resources))
        expected = read_json(manifest)["files"]["scripts/UKRAINIAN.uap"]["sha256"]
        self.assertEqual(sha256(rebuilt), expected)


if __name__ == "__main__":
    unittest.main()
