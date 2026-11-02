# repository-layout Specification

## Purpose
Defines which content lives in public git, which stays local only, and which is published as a binary release, so the repository stays legally clean and no prior work is lost.

## Requirements

### Requirement: Public git contains no game files
The repository SHALL NOT contain original or extracted game resources (DAT, GSC, original DDS, FNT, TXT or CSV files of the game) nor English strings of the game, except screenshots and illustrations used in documentation, the English source terms used as glossary keys, and the 38 original PC menu labels the runtime verifies at their addresses before replacing them. Translated texture layers (our Ukrainian PNGs) are our creative work and are allowed.

#### Scenario: Tracked file audit
- **WHEN** CI checks the list of tracked files
- **THEN** no file has a `.DAT`, `.GSC`, `.FNT` or `.DDS` extension outside allowed synthetic test fixtures, and no translation JSON contains English game text

#### Scenario: Attempt to commit a game file
- **WHEN** a developer places an extracted game file into `game/` or `local/`
- **THEN** git does not track it because these directories are ignored

### Requirement: Local zones are documented
The repository SHALL have a `.gitignore` covering `local/`, `game/`, `build/` and `dist/`, and documentation SHALL explain the purpose of each zone.

#### Scenario: New contributor looks for where to put files
- **WHEN** a person reads the setup documentation
- **THEN** they see that the extracted game goes to `game/`, third-party fonts and donors go to `local/`, and build results go to `build/` and `dist/`

### Requirement: Binary packages live in GitHub Releases
Release ZIP packages, `UKRAINIAN.uap` and `UKRAINIAN.asi` SHALL be published only as GitHub Release assets with checksums and SHALL NOT be committed to git.

#### Scenario: After a release build
- **WHEN** a release build completes
- **THEN** results are in the ignored `dist/` directory and only the release manifest with SHA-256 values is committed

### Requirement: Tools and experiments are preserved
Every working tool and native module of the old repository SHALL be migrated or explicitly recorded as intentionally not migrated, with a reason. Unfinished experiments SHALL live in `experiments/` with a status description.

#### Scenario: Migration audit
- **WHEN** the old repository inventory is compared with the new repository
- **THEN** every tool has a counterpart in the new repository or an entry in the migration log with a reason

#### Scenario: Font 1 x2 experiment
- **WHEN** a developer opens `experiments/`
- **THEN** they find the doubled-font experiment with a description of what works, what does not, and how to resume it

### Requirement: Every directory explains its purpose
Every top-level directory SHALL have a short README or a description in the architecture document explaining what it contains and why.

#### Scenario: Reader opens an unfamiliar directory
- **WHEN** a person browses a top-level directory
- **THEN** they find an explanation of its contents without reading code
