# Architecture

How a JSON translation becomes a package, and how that package gets into the
game process. Details of each part are in the research section:
[runtime loading](research/runtime-loading.md), [fonts](research/fonts.md),
[textures](research/textures.md), [PC menu](research/pc-menu.md),
[character editor](research/character-editor.md).

## Overview

```text
                         BUILD (python -m ua, native/build.ps1)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ translations/*.json ──┐                                                       │
 │ index/*.json ─────────┤ ua validate                                           │
 │                       v                                                       │
 │ baseline release ─> ua build --level text ─> TXT, CSV, credits, PC_MENU.UTF8 ─┐│
 │ (manifests/                                                                  ││
 │  baseline.json)   ua build --level full:                                     ││
 │ game/ + local/ ──>   fonts    ──> 7 FNT files (Font 1 ×4, Font 2 ×3) ────────┤│
 │ assets/       ──>   textures ──> 9 DDS, key = SHA-256 of original pixels ────┤│
 │                                                                              v│
 │                                                    ua/formats/uap.py: UKRAINIAN.uap
 │ translations/pc_menu_ua.json ─> native/build.ps1 ─> UKRAINIAN.asi             │
 │ native/vendor/ ──────────────────────────────────> dinput8.dll (ASI Loader)    │
 │                                    ua build --release ─> dist/*.zip (6 files)  │
 └───────────────────────────────────────────────────────────────────────────────┘

                                 GAME (process memory)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ LEGOIndy.exe ──import──> dinput8.dll (Ultimate ASI Loader 9.7.4)               │
 │                              │ LoadLibrary + InitializeASI                     │
 │                              v                                                 │
 │                     scripts/UKRAINIAN.asi                                      │
 │                       1. SHA-256 of EXE, function bytes, UAP entries, or stop  │
 │                       2. reads scripts/UKRAINIAN.uap into RAM                  │
 │                       3. installs detours:                                     │
 │                                                                                │
 │  engine: open resource ──> path in UAP? ──yes──> memory stream over UAP        │
 │          (0x6B44F0 etc.)        │no              (text, fonts, credits)        │
 │                                 v                                              │
 │                        original read from DAT ──> buffer ──> DDS with a known  │
 │                        (0x6B55A0, 0x6B7440)          hash? ──yes──> copy DDS   │
 │                                                                     from UAP   │
 │  EXE PC tables (0x921D10, 0x921E48, 0x9D0C30) ──> pointers to UTF-8 strings    │
 │  character editor (0x64C6AF, 0x64C6FF, 0x64C76D, 0x5F4BB2) ──> UTF-8 adapters  │
 │                                                                                │
 │  DAT and EXE on disk are never modified; log: scripts/legoindy-ua-pc.log       │
 └───────────────────────────────────────────────────────────────────────────────┘
```

## The player package

```text
dinput8.dll                               Ultimate ASI Loader 9.7.4 x86, unmodified
scripts/UKRAINIAN.asi                     our plugin, exports InitializeASI
scripts/UKRAINIAN.uap                     translation resources
scripts/UKRAINIAN/README.txt              instructions
scripts/UKRAINIAN/LICENSE.txt             LICENSE + full texts of MIT and CC BY 4.0
scripts/UKRAINIAN/LICENSE-ASI-Loader.txt  notices for the loader and its components
```

## The UAP1 format

`UKRAINIAN.uap` is a custom container with no compression or encryption. The
game does not understand it; only the plugin reads it. All numbers are
little-endian.

| Part | Contents |
|---|---|
| Header, 12 bytes | magic `55 41 50 31 0D 0A 1A 00` (`UAP1\r\n\x1a\0`), u32 entry count |
| Index, 296 bytes per entry | ASCII path[256], u32 offset, u32 size, SHA-256[32] |
| Data | resource bytes |

- Byte-identical resources point to the same data range. This is how seven
  font file names take up the space of two fonts.
- The SHA-256 in the index verifies the integrity of every entry at startup.
- The package is loaded into memory once and lives until the game exits;
  nothing is unpacked to disk.

Entries in the 1.1.10 package (23):

| Path in UAP | What it is |
|---|---|
| `STUFF/TEXT/ENGLISH.TXT` | the main text (UTF-8 with BOM, CRLF, lines `ID [pc] "text"`) |
| `STUFF/TEXT/AMERICAN.TXT` | an 18-line overlay that the game reads on top of `ENGLISH.TXT` when the system language is "English (United States)", e.g. under Proton on the Steam Deck |
| `STUFF/TEXT/TRC.CSV` | save dialogs (UTF-16; the translation is written to the ENGLISH and AMERICAN columns, other languages unchanged) |
| `STUFF/TEXT/ENGLISH_CREDITS.TXT`, `PC_ENGLISH_CREDITS.TXT`, `AMERICAN_CREDITS.TXT` | credits: headings translated, names unchanged |
| `STUFF/TEXT/FONT_PC.FNT`, `PC_FONT.FNT`, `PC_FONT_PC.FNT`, `PC_FONT_NGC.FNT` | Font 1 (shared data) |
| `STUFF/TEXT/FONT2.FNT`, `FONT2_PC.FNT`, `FONT2_NGC.FNT` | Font 2 (shared data) |
| `UKRAINIAN/PC_MENU.UTF8` | the 38 PC strings, separated by a null byte |
| `UKRAINIAN/TEXTURES/<SHA-256>.DDS` ×9 | Ukrainian textures; the name is the hash of the original pixels |

`python -m ua` can unpack and build UAP files (`ua/formats/uap.py`). Editing
an unpacked file is pointless: changes go into the sources, and the package is
rebuilt.

## The plugin in the game

Startup sequence:

1. The loader loads `UKRAINIAN.asi` and calls `InitializeASI`. `DllMain`
   only records the module handle.
2. `InitOnceExecuteOnce` guarantees a single initialization; the module is
   pinned until the process exits.
3. The EXE's SHA-256 is checked. Unknown EXE — the translation is disabled
   and the game runs as the original.
4. The UAP next to the plugin is read and every entry is verified.
5. The prologue bytes of every function to be hooked are verified.
6. Detours are installed (text, CSV, reads for DDS), and the PC tables and
   character editor calls are redirected.

Any mismatch in steps 3–5 means the corresponding part is not enabled and the
engine runs as usual. The log is written to `scripts/legoindy-ua-pc.log`.

## `native/` modules

| File | Role |
|---|---|
| `native/asi/proxy.cpp` | entry point: `InitializeASI` (ASI mode) or the DirectInput exports (old proxy build), EXE check, log, PC table replacement |
| `native/asi/overlay.h` | reading and verifying the UAP, detours of resource functions, memory streams, size correction, whole-file interception for the CSV |
| `native/asi/textures.h` | detour of the resource read function for DDS replacement |
| `native/asi/texture_buffer.h` | finding DDS in a buffer, pixel hashing, copying the Ukrainian DDS |
| `native/asi/custom_names.h` | character editor adapters and the default-name formatter for «Форелька»/«Льоля» |
| `native/asi/custom_name_utf8.h` | selecting a whole UTF-8 letter for a name cell |
| `native/asi/practice_cutscenes.h` | test mode for auto-completing cutscenes; tests only, not in the release |
| `native/asi/generate_strings.py` | generates the PC-menu C strings and addresses from `translations/pc_menu_ua.json` and `pc_menu_table.json` |
| `native/asi/pc_menu_table.json` | the verified table of the EXE's PC strings: addresses and the original English strings |
| `native/asi/ukrainian.def`, `dinput8.def` | exports of the ASI (`InitializeASI`) and of the old proxy build |
| `native/asi/smoke_test.cpp`, `proxy_smoke_test.cpp` | smoke tests of the ASI and the old proxy build on an unsupported process |
| `native/asi/custom_name_test.cpp` | x86 editor regressions: buffer, UTF-8 cells, formatter, cutscene test mode |
| `native/asi/texture_test.cpp` | runs the C++ DDS replacement on the original GSC files and compares against a reference |
| `native/asi/coexistence_probe.cpp` | a second test ASI for checking plugin coexistence |
| `native/build.ps1` | build and tests (`-SmokeTest`, `-TextureTest`, `-Legacy`, `-FontUpscaleExperiment`) |
| `native/vendor/ultimate-asi-loader-v9.7.4/` | the official `dinput8.dll`, `LICENSE.txt`, `provenance.json` with SHA-256 |

## `ua/` modules

| Module | Role |
|---|---|
| `ua/__main__.py`, `ua/cli.py` | `python -m ua <command>`: `doctor`, `validate`, `extract`, `build`, `install`, `uninstall`, `verify`, `unpack`, `index`, `test-textures` |
| `ua/doctor.py` | which reproduction levels are available on the machine and what is missing |
| `ua/paths.py` | repository zones and the `UA_GAME_DIR`, `UA_LOCAL_DIR` variables |
| `ua/util.py` | hashing, JSON, output |
| `ua/baseline.py` | the baseline release from `manifests/baseline.json`: lookup, download, SHA-256 check |
| `ua/formats/txt.py` | `ENGLISH.TXT`: BOM, CRLF, `;` comments, lines `ID [pc] "text"` |
| `ua/formats/trc_csv.py` | `TRC.CSV` in UTF-16, changing only the English column |
| `ua/formats/credits.py` | credits files |
| `ua/formats/fnt.py` | `.FNT`: metrics, mapping with re-sorting, adding glyphs, footer |
| `ua/formats/uap.py` | reading, verifying and writing UAP1 |
| `ua/formats/bc_gray.py`, `bc_color.py` | block DXT encoders (grayscale without color fringing; color for textures) |
| `ua/pipeline/validate.py` | translation checks: IDs, tokens, glyphs, glossary |
| `ua/pipeline/index.py` | generating the string index `index/*.json` from the baseline release |
| `ua/pipeline/text.py` | text level: JSON → TXT/CSV/credits/PC menu on top of the template |
| `ua/pipeline/extract.py` | extraction from DAT via QuickBMS and the `game-files.json` check |
| `ua/pipeline/fonts.py` | full level: Font 1 and Font 2 using `tools/fonts/` |
| `ua/pipeline/textures.py` | full level: 9 DDS from PNG layers, re-encoding only changed blocks |
| `ua/pipeline/package.py` | reproducible six-file ZIP |
| `ua/pipeline/install.py` | installation with backup, rollback, static verification |

## Data and manifests

| Path | Contents |
|---|---|
| `translations/` | our translation keyed by ID, and the glossary |
| `index/` | IDs, `pc` markers, tokens and font character sets; no game text |
| `assets/fonts/` | our glyphs, render parameters, manual metric fixes |
| `assets/textures/` | Ukrainian layers, `.af` projects, `manifest.json` with hashes of originals and results |
| `manifests/baseline.json` | the baseline release for the text build |
| `manifests/game-files.json` | which game files are needed, with their SHA-256 |
| `manifests/inputs.json` | third-party inputs in `local/`: QuickBMS, donors, fonts, MSVC |
| `tools/` | research tools: fonts, textures and OCR, PC menu, runtime, saves |
| `experiments/` | parked experiments with their status (×2 atlas, targeting tests) |

## Why it is built this way

- **Memory instead of game files.** The DAT and EXE files stay original,
  installing and uninstalling means three files, and the package weighs
  ~3 MB instead of 182 MB.
- **Pixel hash as the texture key.** One entry covers every copy of an image,
  and a texture changed by another mod is not overwritten.
- **Verification before every change.** With an unfamiliar EXE or a corrupted
  package, the game simply stays in English.
- **The official loader instead of a custom proxy.** The translation coexists
  with other ASI mods.
- **The previous release as the template.** Fixing a string does not require
  the game, and the `CSV` with other languages and the credits with names
  never end up in git.
