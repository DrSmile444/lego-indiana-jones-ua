# project-documentation Specification

## Purpose
Defines what the repository documentation must explain to players, curious readers and developers, so the project is understandable and can be continued without its author.

## Requirements

### Requirement: README is a storefront for players
`README.md` SHALL start with a game screenshot showing the Ukrainian interface and SHALL contain, before the first technical section, a link to the latest release, installation in at most three steps, translation status, game version compatibility and how to uninstall.

#### Scenario: A player opens the repository
- **WHEN** a non-technical person opens the repository page
- **THEN** the first screen shows that this is a Ukrainian translation and contains a download link

### Requirement: Honest compatibility
Documentation SHALL list verified game versions (Steam) separately from unverified ones (GOG) and SHALL change the Steam Deck status only based on an actual check.

#### Scenario: GOG user
- **WHEN** a GOG user reads the compatibility section
- **THEN** they see their version was not verified and how to report results

### Requirement: Tooling list in README and in detail in docs
README SHALL contain a concise tooling list with links. `docs/tooling.md` SHALL describe each tool with link, version, license when known, and what it was used for.

#### Scenario: A developer looks for the unpacking tool
- **WHEN** a reader looks for the DAT unpacking tool
- **THEN** they find QuickBMS and `ttgames.bms` with links and versions and a pointer to the instructions in `docs/setup.md`

### Requirement: Open description of the approach and AI role
Documentation SHALL explain how the translation was built (string context, glossary, cultural adaptations, live QA) and which work the AI assistant did (format and memory research, unpacking, translation drafts, tools) versus the author (idea, glossary, decisions, proofreading, in-game verification).

#### Scenario: A reader asks whether this is machine translation
- **WHEN** a person reads the approach section
- **THEN** they understand the division of roles between the author and the AI and see how every string was verified

### Requirement: Font research with evidence
Documentation SHALL describe how the game font was identified (Franklin Gothic Medium) with render parameters and an overlay screenshot, and SHALL explain that only raster glyphs, not the font file, are part of the repository and the release.

#### Scenario: Font license question
- **WHEN** a reader asks whether the commercial font is redistributed
- **THEN** the documentation explains that only rendered glyphs are distributed and where to lawfully obtain the font for own experiments

### Requirement: Disclaimer and licenses
README SHALL contain a disclaimer that this is an unofficial fan project not affiliated with the rights holders of the game, and a link to `LICENSE` with the MIT, CC BY 4.0 and third-party split.

#### Scenario: Legal section check
- **WHEN** a reader looks for terms of use
- **THEN** they find the disclaimer and the license split without reading code

### Requirement: Complete changelog
`CHANGELOG.md` SHALL contain every version from 0.1.0 to 0.1.10 and a top entry 1.1.10 explaining that its content matches 0.1.10 and that it is the first public release. Entries SHALL NOT contain links to local paths.

#### Scenario: Looking up version 0.1.5
- **WHEN** a reader looks for the changes of 0.1.5
- **THEN** they find an entry without dead links to `local/` or old repository ZIPs

### Requirement: Neutral naming of third-party Cyrillic materials
Documentation SHALL refer to third-party Cyrillic materials neutrally ("Cyrillic localization", "third-party Cyrillic font patch") and SHALL NOT name specific countries, companies or package names of such materials.

#### Scenario: Describing the origin of the Font 1 base
- **WHEN** documentation explains where the Cyrillic base of the font came from
- **THEN** it uses neutral wording

### Requirement: English summary
README SHALL contain a short English About section for international modders with links to technical documents.

#### Scenario: Foreign modder
- **WHEN** a modder who does not read Ukrainian opens the README
- **THEN** they understand what the project is and find the technical documents

### Requirement: Key game terms are explained
The cultural adaptations document SHALL explain, in Ukrainian and English, why the currency is «круглики» and why the Extras menu is «Бонуси», listing the alternatives considered and why each was rejected.

#### Scenario: A reader asks why not «Чити»
- **WHEN** a reader opens the cultural adaptations page
- **THEN** they find the considered options for the Extras menu, including «Чити», with the reasoning for «Бонуси»
