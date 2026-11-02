"""python -m ua <command> — one entry point for every reproduction level.

  doctor                  what can be built on this machine, and what is missing
  validate                translation checks (no game files needed; runs in CI)
  build [--level full]    UKRAINIAN.uap from the baseline release (+ fonts/textures)
  build --release X.Y.Z   also build the ASI and the release ZIP in dist/
  extract --game DIR      unpack the needed files from Steam DAT archives into game/
  install --game DIR      install a release ZIP with backups
  uninstall --game DIR    restore the state recorded by install
  verify --game DIR       installed files still match the package
  index                   regenerate index/ from the baseline release
  unpack UAP DIR          verify and extract a UAP package for inspection
  test-textures --exe EXE byte-compare the C++ texture patcher (level 1)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import baseline, doctor, paths
from .formats import uap
from .util import UaError, ensure_utf8_console, say


def _validate(_args) -> int:
    from .pipeline import validate
    report = validate.run()
    for message in report.errors:
        say(f"ERROR   {message}")
    for message in report.warnings:
        say(f"WARNING {message}")
    say(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


def _build(args) -> int:
    from .pipeline import build
    build.run(args.level, args.release)
    return 0


def _extract(args) -> int:
    from .pipeline import extract
    extract.extract(args.game, everything=args.all, force=args.force)
    say(f"Extracted and verified into {paths.GAME}")
    return 0


def _package_path(args) -> Path:
    if args.package:
        return args.package
    from .pipeline import package
    ver = package.version()
    candidate = paths.DIST / ver / package.archive_name(ver)
    if not candidate.exists():
        raise UaError(f"{candidate} not found; pass --package or run `python -m ua build --release {ver}`")
    return candidate


def _install(args) -> int:
    from .pipeline import install
    backup = install.install(args.game, _package_path(args), args.allow_foreign_loader)
    say(f"Installed. Backups of replaced files: {backup}")
    return 0


def _uninstall(args) -> int:
    from .pipeline import install
    install.uninstall(args.game)
    say("Uninstalled; the previous files are restored.")
    return 0


def _verify(args) -> int:
    from .pipeline import install
    problems = install.verify(args.game)
    for problem in problems:
        say(f"PROBLEM {problem}")
    say("Installed package matches." if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def _index(_args) -> int:
    from .pipeline import build, index, text
    base = baseline.load()
    for path in index.write(index.build(build.with_added_text(base.resources), text.load_translations())):
        say(f"wrote {path.relative_to(paths.REPO)}")
    return 0


def _unpack(args) -> int:
    count = uap.unpack_to(args.source.read_bytes(), args.destination)
    say(f"Verified and extracted {count} entries to {args.destination}")
    return 0


def _test_textures(args) -> int:
    from .pipeline import texture_test
    texture_test.run(args.exe)
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_console()
    parser = argparse.ArgumentParser(prog="python -m ua", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")
    sub.add_parser("doctor", help="check dependencies per level").set_defaults(func=lambda a: doctor.run())
    sub.add_parser("validate", help="validate translations").set_defaults(func=_validate)
    p = sub.add_parser("build", help="build UKRAINIAN.uap (and a release)")
    p.add_argument("--level", choices=("text", "full"), default="text")
    p.add_argument("--release", metavar="VERSION")
    p.set_defaults(func=_build)
    p = sub.add_parser("extract", help="extract needed game files into game/")
    p.add_argument("--game", type=Path, required=True)
    p.add_argument("--all", action="store_true", help="extract complete DAT archives")
    p.add_argument("--force", action="store_true", help="replace different content in game/")
    p.set_defaults(func=_extract)
    for name, func, text in (("install", _install, "install a release ZIP"),
                             ("uninstall", _uninstall, "restore pre-install state"),
                             ("verify", _verify, "check installed files")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--game", type=Path, required=True)
        if name == "install":
            p.add_argument("--package", type=Path)
            p.add_argument("--allow-foreign-loader", action="store_true")
        p.set_defaults(func=func)
    sub.add_parser("index", help="regenerate index/ from the baseline").set_defaults(func=_index)
    p = sub.add_parser("unpack", help="extract a UAP package")
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    p.set_defaults(func=_unpack)
    p = sub.add_parser("test-textures", help="compare the C++ texture patcher (level 1)")
    p.add_argument("--exe", type=Path, required=True)
    p.set_defaults(func=_test_textures)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UaError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
