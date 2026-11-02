# localization-build Specification

## Purpose
Describes how the localization package (UAP, ASI, ZIP) is built deterministically from repository sources at each reproduction level, so any update can start from a clean clone.

## Requirements

### Requirement: Text update without game files
The build SHALL use the resources of a baseline release, pinned in a manifest by URL and SHA-256, as its template. It SHALL apply the translation JSON values to the text resources (`ENGLISH.TXT`, `TRC.CSV`, credits files, PC menu strings) and SHALL carry fonts and textures over unchanged. Game files SHALL NOT be required at this level.

#### Scenario: Fixing one string
- **WHEN** a developer changes a string in `translations/english_txt_ua.json` and runs the build on a clean clone without `game/`
- **THEN** the build produces a new `UKRAINIAN.uap` in which only the `ENGLISH.TXT` resource changed

#### Scenario: Baseline does not match the manifest
- **WHEN** the downloaded or local baseline package has a different SHA-256
- **THEN** the build stops before writing anything to `build/` or `dist/`

### Requirement: Baseline release is reproduced
A build from unchanged sources SHALL reproduce the baseline `UKRAINIAN.uap` byte for byte.

#### Scenario: Migration check
- **WHEN** the build runs on a clean clone with baseline release v0.1.10
- **THEN** the SHA-256 of the produced `UKRAINIAN.uap` equals `6f1b4e65e3f3922b52779c15d73afaf176fa8610efb131a4977bb35e3356964a`

### Requirement: Font and texture rebuild
With extracted game files and local dependencies present, the build SHALL rebuild the changed Font 1, Font 2 and the nine translated DDS textures from our glyphs and layers and SHALL compare the result with the baseline release.

#### Scenario: Full rebuild without changes
- **WHEN** a developer with an extracted game runs a full rebuild without source changes
- **THEN** every rebuilt FNT and DDS either matches the baseline byte for byte or the difference is explained in the build report

### Requirement: Native build with tests
Building `UKRAINIAN.asi` SHALL run from repository sources with `/MT /W4 /WX` and SHALL run smoke and regression tests (UTF-8 names, editor buffer, textures) before packaging.

#### Scenario: A test fails
- **WHEN** any native test fails
- **THEN** packaging does not happen and the build returns a non-zero exit code

### Requirement: Safe installation and rollback
`install` SHALL copy the package into a given game directory, back up files it overwrites, and SHALL NOT overwrite a foreign ASI loader without confirmation. `uninstall` SHALL restore the pre-installation state.

#### Scenario: Installing over a foreign loader
- **WHEN** the game directory already contains a `dinput8.dll` with an unknown SHA-256
- **THEN** `install` stops and explains what to do without changing any files

#### Scenario: Rollback
- **WHEN** `uninstall` runs after `install`
- **THEN** the SHA-256 of every file in the game directory equals the pre-installation state

### Requirement: Finished release output is not overwritten
A release build SHALL refuse to overwrite an existing output of the same version.

#### Scenario: Rebuilding a version
- **WHEN** `dist/` already contains the 1.1.10 package
- **THEN** a release build for the same version fails
