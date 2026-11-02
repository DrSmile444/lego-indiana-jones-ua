# game-asset-acquisition Specification

## Purpose
Guarantees that every game file and third-party dependency can be obtained from a clean clone through a documented, verifiable recipe, without repeating research.

## Requirements

### Requirement: Acquisition recipe is documented
Documentation SHALL list every external build dependency (Steam copy of the game, QuickBMS with `ttgames.bms`, fonts, donor files, MSVC Build Tools, Python) with its source, version, checksum when the file is fixed, placement, and the reproduction level that needs it.

#### Scenario: Update from a clean clone
- **WHEN** a developer clones the repository on a new computer and follows the setup guide
- **THEN** they can gather every required input without consulting the old repository or notes outside the repository

#### Scenario: Commercial font
- **WHEN** the recipe references Franklin Gothic Medium
- **THEN** it names the font, weight and render parameters and a lawful way to license it, without links to unofficial copies

### Requirement: Environment diagnostics
The CLI SHALL provide a `doctor` command that checks dependencies for each reproduction level and reports which levels are available and what is missing.

#### Scenario: Extracted game is missing
- **WHEN** `doctor` runs without a `game/` directory
- **THEN** it reports that the text level is available, the asset rebuild level is not, and prints the command to fix it

### Requirement: Extraction with version check
The CLI SHALL provide an `extract` command that unpacks DAT archives from a given game copy into `game/` using QuickBMS and verifies the extracted files required by the build against a manifest of expected SHA-256 values.

#### Scenario: Supported game version
- **WHEN** `extract` runs against the Steam copy used for the release
- **THEN** all files in the manifest match and the command succeeds

#### Scenario: Different game version
- **WHEN** at least one required file has a different SHA-256
- **THEN** the command names the mismatching files and exits with an error

### Requirement: The installed game is never modified by acquisition
`extract` and `doctor` SHALL only read files of the installed game and SHALL NOT modify them.

#### Scenario: Extraction from the Steam copy
- **WHEN** `extract` completes
- **THEN** the SHA-256 of DAT and EXE files in the game directory equal their values before the run
