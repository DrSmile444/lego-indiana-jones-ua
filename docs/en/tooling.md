# Tooling

The complete list of programs, libraries and reference sources used in the
project: what each one is, where to get it, which version, under which
license and exactly what it is used for. How to install and run everything is
covered in [setup.md](setup.md).

The "Level" column shows when a tool is needed:
**text** — building a text update without the game,
**native** — building the plugin,
**full** — rebuilding fonts and textures from the game files,
**research** — investigations only.

## The author's own tools

| Tool | Version / license | Purpose | Level |
|---|---|---|---|
| [TT Font Studio](https://github.com/DrSmile444/tt-font-studio) ([online](https://drsmile444.github.io/tt-font-studio/)) | current, MIT | An in-browser editor for `.FNT` fonts: atlas, glyph rectangles, X/Y/Width, text preview. It grew out of the glyph viewer in which the sampling windows of the Ukrainian letters were tuned by hand ([fonts.md](research/fonts.md)). | full, research |
| `python -m ua` (the `ua/` folder) | this repository, MIT | The single CLI: validation, extraction, build, installation ([setup.md](setup.md)). | all |
| `tools/` | this repository, MIT | Texture catalog with OCR, `.FNT` and dump inspectors, game memory reading. | research |

## Unpacking and TT Games formats

| Tool | Version / license | Purpose | Level |
|---|---|---|---|
| [QuickBMS](https://aluigi.altervista.org/quickbms.htm) (Luigi Auriemma) | 0.12.0 — current on the author's site; GPL-2.0 | Unpacking `GAME.DAT`, `RAIDERS.DAT`, `TEMPLE.DAT`, `CRUSADE.DAT`. Invoked by `python -m ua extract`. | full |
| [`ttgames.bms`](https://github.com/linterniGamer/Tt-Games-quickbms-scripts) | script 0.9.11a; no license stated in the repository | QuickBMS script for TT Games DAT files; explicitly supports LEGO Indiana Jones. | full |
| [TTGames-Explorer-Rebirth](https://github.com/AcK77/TTGames-Explorer-Rebirth) (AcK77) | MIT | Reference: its `.ft2` parser (`Formats/FT2.cs`) hinted at the `(X, Y, Width)` glyph metric layout in our `.FNT`. No code was copied. | research |
| [TTGames LEGO Documentation](https://github.com/AlubJ/TTGames-LEGO-Documentation) (AlubJ) | license not detected by GitHub | Community documentation: how to unpack DAT files and run classic TT games from unpacked resources. | research |
| [BactaTank Classic](https://github.com/AlubJ/BactaTank-Classic) (AlubJ) | MIT | A model and texture tool for classic TT games; reference for resource structure and for the practice of not distributing game resources. | research |

## Loading into the game

| Tool | Version / license | Purpose | Level |
|---|---|---|---|
| [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) (ThirteenAG) | [9.7.4](https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/tag/v9.7.4), x86, `Ultimate-ASI-Loader-NoPDB.zip`; MIT + licenses of bundled components | `dinput8.dll` in the game root loads `scripts/UKRAINIAN.asi` and calls `InitializeASI`. The binary is vendored unchanged in `native/vendor/ultimate-asi-loader-v9.7.4/`, with its SHA-256 and provenance in `provenance.json`. | native, release |

## Graphics and fonts

| Tool | Version / license | Purpose | Level |
|---|---|---|---|
| [Affinity](https://affinity.serif.com/) (Designer / Photo) | commercial | Font identification by overlay, rendering Franklin Gothic Medium glyphs (46.62 pt, 3 pt outside stroke), texture and logo layers (`.af` in `assets/`). | full (for graphics edits) |
| Franklin Gothic Medium (ITC / Monotype) | commercial font, **not shipped** | Source of the six new Font 1 letters. Obtain it legally and place it in `local/fonts/`. | full |
| Adventure (Neale Davidson, [Pixel Sagas](https://www.dafont.com/adventure.font)) | fan font, author's terms | Source of the Font 2 glyphs. Kept in `local/donors/`. | full |
| A third-party Cyrillic font patch | third-party material, **not shipped** | Base atlas for Font 1. The file and its SHA-256 are described in `manifests/inputs.json`. | full |
| [ImageMagick](https://imagemagick.org/) | 7.x, ImageMagick License | Optimizing screenshots for the documentation and the site. | documentation |

## Languages, build and tests

| Tool | Version / license | Purpose | Level |
|---|---|---|---|
| [Python](https://www.python.org/downloads/) | 3.10+ (developed on 3.12); PSF | The `ua` CLI, formats, UAP build, checks. | all |
| [Pillow](https://pypi.org/project/pillow/) | current; MIT-CMU | Glyph rendering, PNG ↔ DDS, texture previews. | full |
| [pytest](https://pypi.org/project/pytest/) | current; MIT | Tests for formats, the index and baseline reproduction. | all |
| [capstone](https://pypi.org/project/capstone/) | optional; BSD | Disassembly when analyzing crash dumps and reading memory. | research |
| [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), C++ workload (x86) | 2022; free Microsoft license | The `cl.exe` compiler for `UKRAINIAN.asi` and the x86 tests. `native/build.ps1` finds it via `vswhere`. | native |
| [Windows SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) | 10/11 | Win32 headers and libraries for the plugin. | native |
| PowerShell | 5.1 or 7 | `native/build.ps1` and helper scripts. | native |
| [Windows OCR](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr) (`Windows.Media.Ocr`) | built into Windows 10/11; requires the English language pack | Recognizing the lettering on 5,939 textures while searching for what to translate. Tesseract was not used. | research |
| Git, [GitHub CLI](https://cli.github.com/) | current | Repository work and publishing releases. | release |

## AI assistants

| Tool | Purpose |
|---|---|
| [Claude Code](https://claude.com/product/claude-code) (Anthropic) | Research into the game's formats and memory, tools, tests, documentation, translation drafts. |
| [Codex](https://openai.com/codex/) (OpenAI) | The same: a second pair of eyes for research and code. |

The division of roles between the author and AI is described in [approach.md](approach.md).

## Reference sources

- [Microsoft: DLL search order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order)
  and [DllMain restrictions](https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain) —
  why the plugin does nothing in `DllMain`.
- [LEGO Games save file checksum updater](https://github.com/MR-SEVERN-Gaming/Lego-Games-save-file-checksum-updater) —
  cross-checking the save checksum formula ([character-editor.md](research/character-editor.md)).
- [Microsoft: Franklin Gothic](https://learn.microsoft.com/en-us/typography/font-list/franklin-gothic) —
  information on the typeface and the products it ships with.
- [Plast: about the organization](https://plast.org.ua/about/) — the rationale for the «Пластун» (Plastun) adaptation.
- [TT Mod Manager](https://github.com/BrickBench/TTModManager) — a look at how
  other mods deliver files, to assess compatibility.

## Cross-check against the scripts

When the project was migrated, every script in the research archive that
invokes an external program was checked against this list:

| What was invoked | Entry in the list |
|---|---|
| `quickbms.exe` + `ttgames.bms` | QuickBMS |
| `cl.exe`, `vswhere.exe` in the plugin build | Visual Studio Build Tools |
| `Windows.Media.Ocr` in the texture catalog OCR script | Windows OCR |
| `capstone` in dump analysis and memory reading | capstone |
| `PIL` in the font and texture builders | Pillow |
| `steam.exe -applaunch 32330` in test runs | Steam (your own copy of the game) |
| `powershell.exe` / `pwsh` in the installer tests | PowerShell |
