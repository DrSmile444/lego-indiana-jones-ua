# release-distribution Specification

## Purpose
Defines how localization releases are versioned, packaged, published and announced, so players receive a verified package and the author controls every public action.

## Requirements

### Requirement: Version scheme
Public releases SHALL be numbered `1.1.X`. The first public release SHALL be 1.1.10. Versions 0.1.x SHALL remain in the changelog as research releases.

#### Scenario: Next update
- **WHEN** a fix ships after 1.1.10
- **THEN** it is numbered 1.1.11

### Requirement: Package content
The release ZIP SHALL contain exactly `dinput8.dll` (Ultimate ASI Loader, unchanged), `scripts/UKRAINIAN.asi`, `scripts/UKRAINIAN.uap`, `scripts/UKRAINIAN/README.txt`, `scripts/UKRAINIAN/LICENSE.txt` and `scripts/UKRAINIAN/LICENSE-ASI-Loader.txt`, and SHALL NOT contain saves, logs or test settings.

#### Scenario: ZIP content check
- **WHEN** the release ZIP is unpacked
- **THEN** it contains the six expected files and their SHA-256 values match the release manifest

### Requirement: 1.1.10 extends the 0.1.10 content
Release 1.1.10 SHALL keep the fonts, textures, PC menu and character editor behaviour of 0.1.10 unchanged and SHALL change only text resources: the US-locale coverage (`AMERICAN.TXT`, `AMERICAN_CREDITS.TXT`, the AMERICAN column of `TRC.CSV`) and the corrected launcher strings 1235-1237 and 1449.

#### Scenario: UAP comparison with 0.1.10
- **WHEN** the resources of the 1.1.10 `UKRAINIAN.uap` are compared with 0.1.10
- **THEN** every FNT, DDS and PC menu resource is byte-identical, and the only changed or added resources are `ENGLISH.TXT`, `TRC.CSV`, `AMERICAN.TXT` and `AMERICAN_CREDITS.TXT`

### Requirement: Checksums and manifest
Every release SHALL have a manifest at `manifests/releases/<version>.json` in git and a `SHA256SUMS` file among the GitHub Release assets.

#### Scenario: A player verifies the download
- **WHEN** a player compares the SHA-256 of the downloaded ZIP with `SHA256SUMS`
- **THEN** the values match

### Requirement: Public actions only with consent
Creating the public repository, pushing, publishing a release and enabling Pages SHALL happen only after explicit author confirmation for each action. Until then the new repository SHALL have no commits.

#### Scenario: Preparation finished
- **WHEN** the build and documentation are complete
- **THEN** the working tree stays uncommitted and the author is shown what will be published

### Requirement: Announcement texts stay out of git
Texts for kuli, Steam, Telegram and LBK Launcher SHALL be stored in `local/distribution/` and SHALL NOT be tracked by git.

#### Scenario: Git check
- **WHEN** `git ls-files` runs
- **THEN** no file from `local/` is listed

### Requirement: Baseline release for future builds
After 1.1.10 is published, the baseline manifest SHALL point to the 1.1.10 ZIP in GitHub Releases, so text updates build from a clean clone without private files.

#### Scenario: Build after publishing
- **WHEN** a developer runs a text build on a clean clone
- **THEN** the baseline package downloads from GitHub Release 1.1.10 and passes the SHA-256 check
