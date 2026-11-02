# Spec Delta

## Purpose

Gives players a simple, predictable way to report a translation error or a game problem with enough context for the author to reproduce it.

## ADDED Requirements

### Requirement: Feedback channels
README and the site SHALL name two channels: GitHub Issues and direct messages to Telegram `dimkasmile`.

#### Scenario: Player without a GitHub account
- **WHEN** a player has no GitHub account
- **THEN** they find the Telegram contact

### Requirement: Issue templates
The repository SHALL provide "Text error" and "Crash or game problem" templates. Both SHALL ask what happened, which level or screen, a screenshot and a save file when possible, and SHALL tell where game saves are located.

#### Scenario: Reporting a text error
- **WHEN** a player opens a new issue with the "Text error" template
- **THEN** the form asks for a screenshot, level or screen, current text and the suggested wording

#### Scenario: Reporting a crash
- **WHEN** a player opens an issue with the "Crash" template
- **THEN** the form asks for steps, level, save file, localization version and platform (Steam, Steam Deck, other)
