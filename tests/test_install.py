"""Test-mode install: the ini goes into the game folder, never into the player package."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ua.pipeline import install, package


def fake_bundle() -> dict[str, bytes]:
    return {name: f"content of {name}".encode() for name in package.FILES}


class TestModeInstallTest(unittest.TestCase):
    def test_test_config_is_not_in_the_player_package(self):
        self.assertNotIn(package.TEST_CONFIG, package.FILES)

    def test_install_writes_and_uninstall_removes_the_test_ini(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(install, "_check_game"), \
                mock.patch.object(install, "build_bundle", fake_bundle), \
                mock.patch.object(install, "loader", lambda: (b"loader", b"", {})):
            game = Path(folder)
            install.install(game, None, test_mode=True)
            ini = (game / package.TEST_CONFIG).read_bytes()
            self.assertIn(b"KeepRunning=1\r\n", ini)
            (game / "scripts/screens").mkdir()
            (game / "scripts/screens/keys.txt").write_text("1C")
            with self.assertRaises(Exception):
                install.install(game, None, test_mode=True)  # already installed
            install.uninstall(game)
            self.assertFalse((game / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
