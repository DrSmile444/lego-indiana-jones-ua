# Proposal: SEO сайту й пояснення термінів

## Why

Гравці шукатимуть українізатор у Google за запитами на кшталт «українізатор LEGO Indiana Jones»,
«Лего Індіана Джонс українською», «LEGO Indiana Jones Ukrainian». Сайт мав базові мета-теги, але
без структурованих даних і з дубльованим заголовком головної. Автор також попросив пояснити на
сайті, чому валюта — «круглики», а меню Extras — «Бонуси».

## What Changes

- Middleware Starlight (`site/src/routeData.ts`):
  - заголовки головних сторінок під пошукові запити, назва сайту з ключовими словами;
  - `og:locale` у форматі `uk_UA`/`en_US` з альтернативою, `og:type=website` для головних, robots-мета (`noindex` для 404);
  - JSON-LD: `WebSite` + `SoftwareApplication` (версія, пряме посилання на ZIP, безкоштовно, скриншоти, гра як `VideoGame`) на головних, `FAQPage` з розділу FAQ, `BreadcrumbList` на решті сторінок.
- Слогани головних сторінок містять природні ключові фрази (українізатор, Лего Індіана Джонс, Steam Deck).
- У культурних адаптаціях (укр. й англ.) — розділи «Чому круглики» та «Чому Бонуси, а не Чити» з розглянутими варіантами; FAQ посилається на них.

## Capabilities

### Modified Capabilities

- `project-site`: пошукова оптимізація.
- `project-documentation`: пояснення ключових ігрових термінів.

## Impact

`site/src/routeData.ts`, `site/astro.config.mjs`, головні сторінки, FAQ, `docs/research/cultural-adaptations.md`, `docs/en/research/cultural-adaptations.md`.
