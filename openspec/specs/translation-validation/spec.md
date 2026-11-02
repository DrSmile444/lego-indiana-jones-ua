# translation-validation Specification

## Purpose
Catches translation errors automatically without game files, on every push and locally before a build, so a broken string never reaches a release.

## Requirements

### Requirement: Structural translation validation
The `validate` command SHALL check that every translation JSON is well formed, that every ID in the string index has a translation, that there are no extra IDs, and that `[...]` and `%d`/`%s` tokens match those recorded in the index. The string index is stored in git and contains only IDs, platform markers and tokens, without game text.

#### Scenario: Broken token
- **WHEN** a translation omits a `[...]` button token that the index records
- **THEN** `validate` names the string ID and fails

#### Scenario: Missing translation
- **WHEN** an index ID is absent from the JSON
- **THEN** `validate` fails and names that ID

### Requirement: Glyph coverage
`validate` SHALL check that every character of every translation exists in the character set of the corresponding font recorded in the repository.

#### Scenario: Unsupported character
- **WHEN** a translation contains a character the font lacks (for example an em dash)
- **THEN** `validate` names the string and the character

### Requirement: Glossary consistency
`validate` SHALL check that glossary terms with an approved status are used in their approved form and SHALL emit warnings for deviations.

#### Scenario: Different name form
- **WHEN** a string associated with an approved character name uses another form
- **THEN** `validate` shows a warning with the string ID and the expected form

### Requirement: CI on every push
The repository SHALL have a CI process that runs `validate` and format unit tests on every push and pull request without access to game files.

#### Scenario: Pull request with an error
- **WHEN** a pull request breaks validation
- **THEN** the CI check is marked as failed
