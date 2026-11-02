# Environment setup and build

This document is a developer recipe: how to go from a clean clone to
validating the translation, building a text update and the native plugin,
fully rebuilding fonts and textures, installing the result into the game and
cutting a release. All commands are run from the repository root.

Players do not need any of this: the ready-made package is on the
[releases](https://github.com/DrSmile444/lego-indiana-jones-ua/releases/latest) page.

## Repository zones

```text
 PUBLIC GIT                         LOCAL (in .gitignore)               GITHUB RELEASES
 translations/  our text            game/    extracted game resources   lego-indiana-jones-ua-
 index/         string IDs, tokens  local/   donors, fonts, baseline      <version>.zip
 assets/        our glyphs, layers           packages, QuickBMS         + SHA-256
 ua/ native/ tools/ experiments/    build/   intermediate files
 manifests/ docs/ tests/            dist/    finished packages
```

- Git contains **no game files**, third-party fonts or donor material.
- Everyone fills `local/` and `game/` from their own legal sources; what
  belongs there is described, together with SHA-256 hashes, in
  `manifests/inputs.json` and `manifests/game-files.json`.
- Binary packages live in GitHub Releases, not in git.

Paths can be overridden with environment variables:

| Variable | What it sets | Default |
|---|---|---|
| `UA_GAME_DIR` | extracted game resources | `game/` |
| `UA_LOCAL_DIR` | donors, fonts, baseline packages, QuickBMS | `local/` |

## Reproduction levels

| Level | What you get | What you need |
|---|---|---|
| Validation | `validate`, tests | Git, Python 3 |
| Text (`--level text`) | a new `UKRAINIAN.uap` with updated text | + the baseline release (downloaded automatically) |
| Native | `UKRAINIAN.asi` | + Windows, Visual Studio C++ x86, Windows SDK |
| Full (`--level full`) | fonts and textures from scratch | + your own Steam copy of the game, QuickBMS, donors, Franklin Gothic Medium |

`python -m ua doctor` shows which levels are available on this machine and
what is missing. `python -m ua --help` lists every command; besides those
described below there are `unpack` (unpack any UAP for inspection), `index`
(regenerate `index/` from the baseline release) and `test-textures` (used by
`native/build.ps1 -TextureTest`).

## 1. Validation: only Git and Python needed

```powershell
git clone https://github.com/DrSmile444/lego-indiana-jones-ua.git
cd lego-indiana-jones-ua
python -m pip install -r requirements.txt pytest
python -m ua doctor
python -m ua validate
python -m pytest
```

`validate` checks the translations against the `index/*.json` index: that
every ID is present, the service tokens `[...]` and `%d` are preserved, every
character exists in the corresponding font, and terms match the glossary. CI
runs the same commands.

## 2. Text update without the game

This level is enough to fix a translated string.

1. Edit `translations/*.json`:
   - `english_txt_ua.json` — key: the numeric ID of the `ENGLISH.TXT` line;
   - `trc_csv_ua.json` — key: the `TRC.CSV` row label;
   - the credits file — job titles and section headings;
   - `pc_menu_ua.json` — the 38 PC strings (a change here also requires a native build);
   - `glossary.json` — terminology (see [approach.md](approach.md)).
2. Validate and build:

   ```powershell
   python -m ua validate
   python -m ua build --level text
   ```

The build template is **the previous published release**.
`manifests/baseline.json` pins its ZIP by SHA-256; `ua` downloads it into
`local/baseline/`, verifies the checksum, extracts `UKRAINIAN.uap`, applies
the JSON translations to `ENGLISH.TXT`, `TRC.CSV`, the credits and the PC
menu, and repacks it. Fonts and textures are carried over unchanged. With no
translation changes, the result is byte-identical to the baseline release's
`UAP`.

Until 1.1.10 is published, the baseline is the 0.1.10 ZIP from the author's
archive: it has to be placed in `local/baseline/` by hand (the name and
SHA-256 are in `manifests/baseline.json`).

## 3. Native plugin

You need:

- [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  with the "Desktop development with C++" workload and the MSVC x86/x64
  component;
- the [Windows 10/11 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/);
- Python (it generates the PC-menu C strings from `translations/pc_menu_ua.json`).

```powershell
./native/build.ps1 -SmokeTest
```

The script locates the compiler via `vswhere`, builds the x86
`UKRAINIAN.asi` (`/MT /W4 /WX /utf-8 /Brepro`) into `build/native/asi/` and
runs the tests:

- smoke test: the plugin is loaded into an unsupported process, calls
  `InitializeASI` twice and patches nothing;
- x86 regression tests for the character editor: UTF-8 cells, the 16-byte
  buffer, default names.

Other modes: `-TextureTest` (compares the C++ DDS replacement with a
reference; requires `game/`), `-Legacy` (the old `dinput8.dll` proxy build),
`-FontUpscaleExperiment` (see `experiments/font1-x2/`). The version written
to the plugin log is taken from the `VERSION` file.

## 4. Full rebuild: fonts and textures

Only needed if you change glyphs or the lettering on textures.

### 4.1. The game and QuickBMS

1. Install the game through Steam (English language). The supported
   `LEGOIndy.exe` has SHA-256
   `c12f7348ec63aed61f56eb15d825f15b8340500668fa8c8dcf06c2f332e5e5fd`.
2. Download [QuickBMS](https://aluigi.altervista.org/quickbms.htm) and the
   [`ttgames.bms`](https://github.com/linterniGamer/Tt-Games-quickbms-scripts)
   script, and place them like this:

   ```text
   local/tools/quickbms/quickbms.exe
   local/tools/quickbms/ttgames.bms
   ```

3. Extract the required resources:

   ```powershell
   python -m ua extract --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
   ```

   `extract` opens the game folder read-only, takes the files listed in
   `manifests/game-files.json` (layout `game/<DAT name>/<path>`), verifies
   their SHA-256 and checks that the DAT and EXE files are unchanged before
   and after. `--all` unpacks the archives completely (several GB; needed for
   the texture catalog).

### 4.2. Donors and fonts

| File in `local/` | What it is | Where to get it |
|---|---|---|
| `donors/cyrillic-font-patch/PC_FONT_PC.FNT` | the Font 1 base atlas from a third-party Cyrillic font patch | from that patch's `STUFF/TEXT` folder; not distributed in this repository |
| `donors/Adventure_Indiana_Jones.ttf` | the Adventure fan font for Font 2 | [Pixel Sagas / Neale Davidson](https://www.dafont.com/adventure.font), under the author's terms |
| `fonts/Franklin Gothic Medium Regular.ttf` | Franklin Gothic Medium for the new Font 1 letters | a license from the rights holder (ITC / Monotype) or bundled with licensed Office; not included in Windows |

The expected SHA-256 hashes are recorded in `manifests/inputs.json`. A
different file may produce different pixels; `doctor` will warn about it. Why
the font is not distributed is explained in
[research/fonts.md](research/fonts.md#font-license).

### 4.3. Build

```powershell
python -m ua build --level full
```

Font 1 is built from the donor atlas, our glyphs and the manual metric fixes
in `assets/fonts/font1/`; Font 2 from the game's original `FONT2_PC.FNT`, the
Adventure font and `assets/fonts/font2/`. Textures are built from the original
DDS files in `game/` and our `assets/textures/*-ukrainian.png` layers: only
the changed 4×4 blocks are re-encoded. Intermediate files go to `build/`. The
build report shows whether the FNT and DDS files match the baseline release
and explains any differences.

## 5. Installing into the game for testing

```powershell
python -m ua install --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
python -m ua verify --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
python -m ua uninstall --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
```

- `install` checks the EXE, copies the package's six files (by default
  `dist/<version>/lego-indiana-jones-ua-<version>.zip` from step 6, so build
  the release first; another ZIP can be passed with `--package`) and saves
  everything it overwrites to `<game>/ukrainian-localization-backup/<time>/`
  together with `install-state.json`. A foreign `dinput8.dll` blocks the
  installation; if it is a knowingly compatible ASI Loader, add
  `--allow-foreign-loader`.
- `verify` statically compares the installed files against the hashes
  recorded during installation.
- `uninstall` restores the exact previous state.

Close the game before each of these commands. The plugin log is
`scripts/legoindy-ua-pc.log` in the game folder. To check the strings in the
memory of the running game, use `tools/runtime/verify_runtime.py --pid <PID>`.

## 6. Release

```powershell
python -m ua build --release 1.1.10
```

Builds a reproducible ZIP `lego-indiana-jones-ua-<version>.zip` (fixed
timestamps and file order) plus its SHA-256 into `dist/<version>/`. The
package contains exactly six files: the loader, `UKRAINIAN.asi`,
`UKRAINIAN.uap`, `README.txt` and two licenses. An existing release is never
overwritten. A published release becomes the baseline for the next text
update via `manifests/baseline.json`.

## Common problems

| Symptom | Cause and fix |
|---|---|
| `doctor`: text level unavailable | there is no baseline ZIP in `local/baseline/` and no URL set in `manifests/baseline.json` |
| `extract`: QuickBMS not found | check the paths in `local/tools/quickbms/` |
| `build.ps1`: "Visual Studio C++ x86 build tools are required" | add the MSVC x86/x64 component in the Visual Studio Installer |
| Donor SHA-256 mismatch | a different version of the file; the result may differ from the release |
| Game still in English after `install` | the game language in Steam is not English, or the EXE is not supported; see the log |

## Publishing a release

1. Bump `VERSION` and add a `## X.Y.Z — date` section to `CHANGELOG.md`.
2. `python -m ua build --release X.Y.Z` writes the ZIP, `SHA256SUMS` and `RELEASE_NOTES.md` into `dist/X.Y.Z/`.
   The notes start with a large "Download" link to the ZIP itself (template: `assets/package/RELEASE_NOTES.md`),
   so players don't confuse it with GitHub's `Source code` archives. "What's new" comes from `CHANGELOG.md`.
3. Commit `manifests/releases/X.Y.Z.json`, then:
   ```powershell
   gh release create vX.Y.Z dist/X.Y.Z/lego-indiana-jones-ua-X.Y.Z.zip dist/X.Y.Z/SHA256SUMS `
     --title "X.Y.Z" --notes-file dist/X.Y.Z/RELEASE_NOTES.md
   ```
4. Point `manifests/baseline.json` at the new release (asset URL, ZIP and UAP SHA-256) so later text builds use it as the template.
