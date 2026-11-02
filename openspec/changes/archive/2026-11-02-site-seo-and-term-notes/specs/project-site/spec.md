# Spec Delta

## ADDED Requirements

### Requirement: Search engine optimization
Every indexable page SHALL have a unique title and description, a canonical URL, `hreflang` alternates for both languages, `og:locale` in `ll_CC` form and robots directives allowing indexing (the 404 page SHALL be `noindex`). The home pages SHALL use titles built around the search queries for the localization and SHALL embed JSON-LD `WebSite` and `SoftwareApplication` data with the current version and the direct download URL. The FAQ pages SHALL embed `FAQPage` data generated from their questions, and other pages SHALL embed `BreadcrumbList` data.

#### Scenario: Home page markup
- **WHEN** a crawler fetches the Ukrainian home page
- **THEN** the title starts with «Українізатор LEGO Indiana Jones», and the JSON-LD contains a `SoftwareApplication` whose `softwareVersion` and `downloadUrl` match the latest release manifest

#### Scenario: FAQ rich data
- **WHEN** a question heading is added to the FAQ page
- **THEN** the next build includes it in the page's `FAQPage` JSON-LD without manual edits
