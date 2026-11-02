"""Repository rules: no game files, documented folders, no machine-specific paths."""
import re
import subprocess
import unittest

from ua import paths

GAME_EXTENSIONS = {".dat", ".gsc", ".fnt", ".dds", ".ttf", ".otf"}
IGNORED_ROOTS = {"local", "game", "build", "dist", ".git", "node_modules"}
TOP_LEVEL = ["translations", "index", "assets", "native", "ua", "manifests", "tools", "experiments", "tests", "docs"]
ABSOLUTE = re.compile(r"[A-Z]:[\\/](?:Users|SteamLibrary|Downloads|Projects)|SteamLibrary", re.I)


def repository_files():
    """Tracked files when git knows them, otherwise every file outside ignored zones."""
    try:
        listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                                cwd=paths.REPO, capture_output=True, text=True, check=True).stdout.split("\n")
        files = [paths.REPO / line for line in listed if line]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in paths.REPO.rglob("*") if p.is_file()
            and not IGNORED_ROOTS & set(p.relative_to(paths.REPO).parts)]


class RepositoryTest(unittest.TestCase):
    def test_no_game_or_font_files(self):
        offenders = [p.relative_to(paths.REPO).as_posix() for p in repository_files()
                     if p.suffix.lower() in GAME_EXTENSIONS]
        self.assertEqual(offenders, [])

    def test_top_level_folders_have_readme(self):
        missing = [name for name in TOP_LEVEL if not (paths.REPO / name / "README.md").exists()]
        self.assertEqual(missing, [])

    def test_no_machine_specific_paths_in_code(self):
        offenders = []
        for p in repository_files():
            if p.suffix.lower() not in {".py", ".ps1", ".cpp", ".h", ".mjs", ".ts"}:
                continue
            if "tests" in p.relative_to(paths.REPO).parts[:1]:
                continue
            for number, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if ABSOLUTE.search(line):
                    offenders.append(f"{p.relative_to(paths.REPO).as_posix()}:{number}")
        self.assertEqual(offenders, [])

    def test_translation_values_have_no_long_english_text(self):
        from ua.pipeline.text import load_translations
        tr = load_translations()
        values = list(tr["english"].values()) + list(tr["trc"].values()) + list(tr["pc_menu"].values())
        for lines in tr["credits"].values():
            values += list(lines.values())
        english = [v for v in values if re.fullmatch(r"[\x20-\x7e]+", v) and re.search(r"[a-z]{4,}\s+[a-z]{4,}", v)]
        self.assertEqual(english, [])


if __name__ == "__main__":
    unittest.main()
