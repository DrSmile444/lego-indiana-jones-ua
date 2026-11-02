# Spec Delta

## Purpose

A public project site from which players download the localization and learn how it was made, and where readers and developers find detailed explanations of the approach.

## ADDED Requirements

### Requirement: Home page leads to the download
The home page SHALL show a game screenshot with the Ukrainian interface, the current version number and a "Download" button that points to the ZIP of the latest GitHub release. If the version cannot be determined, the button SHALL point to the Releases page.

#### Scenario: A player clicks "Download"
- **WHEN** a visitor clicks the download button
- **THEN** the latest release ZIP downloads from GitHub, not from a copy hosted on the site

#### Scenario: GitHub API unavailable
- **WHEN** the releases API request fails
- **THEN** the button points to the repository Releases page and the page keeps working

### Requirement: Site content
The site SHALL have sections for installation and uninstallation, FAQ, how it was made, tooling with links, research, glossary, cultural adaptations, and feedback (GitHub Issues and Telegram `dimkasmile`).

#### Scenario: A reader looks for tooling
- **WHEN** a visitor opens the tooling section
- **THEN** they see the same list as `docs/tooling.md`, with links

### Requirement: Single source text
Research and tooling pages SHALL be built from the repository `docs/` files. The glossary SHALL be generated from `translations/glossary.json` at site build time.

#### Scenario: Glossary change
- **WHEN** an approved term is added to `glossary.json`
- **THEN** it appears on the glossary page after the next build without manual site edits

### Requirement: Themed design without third-party branding
The site SHALL have its own LEGO-adventure style (palette, custom SVGs, brick-shaped button) and SHALL NOT use LEGO or Indiana Jones logos or their proprietary typefaces as the site logo or identity. Game screenshots are allowed as illustrations.

#### Scenario: Header check
- **WHEN** a visitor looks at the header and favicon
- **THEN** they see the project's own mark, not a rights holder's logo

### Requirement: Disclaimer on every page
The footer of every page SHALL contain an unofficial fan project disclaimer and a link to the licenses.

#### Scenario: Any page
- **WHEN** a visitor scrolls to the bottom of a page
- **THEN** they see the disclaimer and the license link

### Requirement: Accessibility and responsiveness
The site SHALL render correctly at phone width (from 360 px) without horizontal scrolling and SHALL provide light and dark themes with sufficient text contrast (WCAG AA).

#### Scenario: Phone
- **WHEN** a page is opened on a 360 px wide screen
- **THEN** content is readable without horizontal scrolling and the download button is reachable

### Requirement: Social previews
Every page SHALL have `og:image`, title and description so links unfurl well in Telegram and other messengers.

#### Scenario: Link in Telegram
- **WHEN** a site link is shared in Telegram
- **THEN** the preview shows a screenshot, title and Ukrainian description

### Requirement: Automatic publishing
The site SHALL be built and published to GitHub Pages automatically after changes to `site/`, `docs/` or `translations/glossary.json` on the main branch.

#### Scenario: Documentation change
- **WHEN** a change to `docs/` lands on the main branch
- **THEN** the workflow builds and publishes the site without manual steps

### Requirement: Full English version
Every page of the site SHALL exist in Ukrainian (root) and English (`/en/`), with a language switcher that leads to the counterpart of the current page. English documentation pages SHALL be built from `docs/en/`, mirroring `docs/`, and the CI build SHALL fail when an English counterpart is missing.

#### Scenario: Switching language
- **WHEN** a visitor on a Ukrainian page selects English in the language switcher
- **THEN** the English version of the same page opens, including localized components, footer disclaimer and glossary

#### Scenario: Missing translation in CI
- **WHEN** a document is added to `docs/` without a counterpart in `docs/en/`
- **THEN** the strict site build fails and names the missing file

### Requirement: Screenshot viewer is centered
The screenshot lightbox SHALL be centered in the viewport at every screen size.

#### Scenario: Opening a screenshot on a wide screen
- **WHEN** a visitor opens a screenshot on a 2560 px wide window
- **THEN** the viewer is horizontally and vertically centered over the dimmed page
