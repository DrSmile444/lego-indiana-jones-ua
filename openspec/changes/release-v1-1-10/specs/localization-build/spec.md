# Spec Delta

## ADDED Requirements

### Requirement: Translation reaches both English locales
The package SHALL show the translation whether the game runs with an English (United Kingdom) or English (United States) system locale. It SHALL provide a translated `AMERICAN.TXT` overlay containing exactly the IDs of the original overlay, a translated `AMERICAN_CREDITS.TXT`, and the translation in both the ENGLISH and AMERICAN columns of `TRC.CSV`, leaving the other language columns unchanged.

#### Scenario: Steam Deck with the default Proton locale
- **WHEN** the game runs with an en-US locale (Proton default on Steam Deck)
- **THEN** the 18 overlay strings, the save/load dialogs and the credits titles are shown in Ukrainian, the same as with an en-GB locale

#### Scenario: Template not yet in the baseline
- **WHEN** the baseline release predates `AMERICAN.TXT` and `game/` is not extracted
- **THEN** the build stops with an error that names the missing template and the extraction command

## MODIFIED Requirements

### Requirement: Baseline release is reproduced
A build from unchanged sources SHALL reproduce the `UKRAINIAN.uap` recorded in the release manifest of the current `VERSION` byte for byte.

#### Scenario: Migration check
- **WHEN** the text build runs with the pinned baseline and the sources of the current version
- **THEN** the SHA-256 of the produced `UKRAINIAN.uap` equals the value in `manifests/releases/<VERSION>.json`
