# Design: сайт проєкту

## Context

Мотивацію описано в `proposal.md`, вимоги — у `specs/project-site/spec.md`.
Тексти готує `docs-rewrite` у `docs/`, а скриншоти лежать у `docs/screenshots/`.
Автор уже має досвід GitHub Pages (`drsmile444.github.io/tt-font-studio`).
Сайт двомовний: українська — корінь (`/`), англійська — `/en/` (рішення автора після першої версії).

## Goals / Non-Goals

**Goals:** запам'ятовуване оформлення, яке відчувається як «LEGO-пригода», за
мінімальної підтримки: Markdown-зміст з `docs/`, стандартні можливості
Starlight (пошук, темна тема, навігація).

**Non-Goals:**
- власний домен;
- аналітика з cookies;
- хостинг ZIP на сайті;
- мови, крім української та англійської.

## Decisions

### D1. Astro Starlight

Starlight дає пошук (Pagefind), навігацію, темну тему й українську локаль
інтерфейсу. Через `customCss` і заміну компонентів (`Hero`, `Header`, `Footer`,
`PageFrame`) можна зробити повністю власний стиль.

Альтернатива VitePress простіша, але гірше підходить для кастомних
Astro-компонентів (слайдер, галерея). Рукописний лендинг означав би
дублювання змісту.

### D2. Палітра й типографіка

| Токен | Світла | Темна | Роль |
|---|---|---|---|
| `--paper` | `#F3E6C8` пергамент | `#1E1812` | фон |
| `--ink` | `#2B1D12` | `#EFE3C8` | текст |
| `--brick-red` | `#C8102E` | `#E2453B` | основний акцент, кнопка |
| `--brick-yellow` | `#F2C230` | `#F5CD4A` | другий акцент, штифти |
| `--leather` | `#8A5A2B` | `#B07A45` | рамки, маршрут |
| `--map-line` | `#B79A6A` | `#4A3C2C` | лінії мапи |

Шрифти з відкритими ліцензіями та підтримкою кирилиці:
- заголовки — `Rubik` (жирний, «цеглинковий»);
- текст — `Inter` або `IBM Plex Sans`.

Контраст перевіряється для обох тем.

### D3. Кастомні SVG

- `stud.svg` — штифт як маркер списків і роздільник;
- `brick-button` — кнопка «Завантажити» у формі цеглинки 2×4 з тінню й
  натисканням (CSS + SVG);
- `route.svg` — пунктирний маршрут між точками-таймлайнами для «Як ми це
  робили» (дослідження → шрифти → переклад → рушій → QA → реліз);
- `compass.svg`, `map-bg.svg` — фон hero з мапою й сіткою;
- знак проєкту — власна цеглинка з тризубом-штифтом або літерою «Ї» (без
  логотипів правовласників).

Усі SVG малюються вручну і використовують `currentColor` і CSS-змінні, тож
автоматично підтримують світлу й темну теми.

### D4. Компоненти

- `DownloadButton.astro`: на клієнті запитує
  `api.github.com/repos/DrSmile444/lego-indiana-jones-ua/releases/latest` і бере
  `browser_download_url` ZIP. Під час збірки вбудовується значення за
  замовчуванням (версія з `manifests/releases/`); fallback — сторінка Releases.
- `BeforeAfter.astro`: слайдер «англійською / українською» для головного меню.
  Англійський знімок автор робить окремо; доки його немає, показується одиночний
  скриншот.
- `Gallery.astro`: сітка скриншотів з лайтбоксом без зовнішніх залежностей.
- `Glossary.astro`: таблиця з пошуком, генерується з `glossary.json`.
- `StudCounter`: декоративний лічильник «кругликів» на головній (пасхалка).

### D5. Структура сайту й джерела

```
site/
  astro.config.mjs        base: /lego-indiana-jones-ua, locale uk
  src/content/docs/
    index.mdx             головна (hero, кнопка, 3 кроки, галерея)
    install.md faq.md feedback.md
    approach.mdx          таймлайн-маршрут + docs/approach.md
    tooling.md            <- docs/tooling.md
    research/*.md         <- docs/research/*.md
    glossary.mdx          <- translations/glossary.json
    adaptations.md        <- docs/research/cultural-adaptations.md
    en/                   англійські відповідники сторінок (index, install, faq, feedback, glossary)
  src/components/ src/styles/ src/assets/svg/
  scripts/sync-docs.mjs   копіює docs/ у content перед збіркою, переписує відносні посилання
```

`sync-docs` запускається в `prebuild`. Згенеровані файли в `content` позначено
й проігноровано git, а джерелом лишається `docs/`.

### D6. Публікація

`.github/workflows/pages.yml`: тригер — push у `master` зі змінами в `site/**`,
`docs/**` чи `translations/glossary.json`. Кроки: Node LTS → `npm ci` →
`npm run build` → `actions/upload-pages-artifact` → `actions/deploy-pages`.

### D7. Англійська версія

Starlight i18n: `root` = `uk`, `en` = `/en/`. Рядки компонентів зібрано в типізованому словнику
`src/i18n/strings.ts` (англійський словник має той самий тип, тож пропущений рядок ловить перевірка
типів). Англійські документи — `docs/en/` як дзеркало `docs/`; `sync-docs.mjs --strict` падає,
якщо відповідника бракує. Лайтбокс центрується явно (`position: fixed; inset: 0; margin: auto`),
бо скидання стилів Starlight обнуляє стандартний `margin: auto` у `<dialog>`.

## Risks / Trade-offs

- [Стиль «під LEGO» може виглядати як офіційний сайт] → Власний знак,
  дисклеймер у підвалі, жодних логотипів правовласників в айдентиці.
- [API GitHub має ліміт запитів] → Значення за замовчуванням вбудоване під час
  збірки, а запит до API лише уточнює його.
- [Синхронізація docs → content ламає посилання] → `sync-docs` переписує
  посилання й падає на битих.
- [Англійський знімок для «до/після» ще не зроблено] → Компонент деградує до
  одиночного скриншота.
