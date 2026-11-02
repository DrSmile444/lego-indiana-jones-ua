# Design: документація

## Context

Мотивацію описано в `proposal.md`. Матеріал для документації:

- `README.md` старого репозиторію (хроніка версій);
- `docs/research/*.md` (ASI, UAP, текстури, PC-меню, font2-краш, приціл, імена в редакторі);
- `docs/spike-notes/*` (формат FNT, перші нотатки, глосарій);
- `docs/research/cultural-adaptations.md`, `CHANGELOG.md`, `LICENSE`;
- скриншоти автора (9 знімків 2560×1440, Steam);
- скриншот шрифтового дослідження (накладання Franklin Gothic Medium на атлас TT).

## Goals / Non-Goals

**Goals:** три шари документації для трьох аудиторій, без дублювання
(README → коротко й з посиланнями, `docs/` → докладно, сайт → бере тексти з
`docs/`).

**Non-Goals:** сайт і його стиль (`pages-site`), тексти для kuli, Steam,
Telegram і LBK (`release-v1-1-10`, лише в `local/`).

## Decisions

### D1. Структура README

```
[hero: головне меню з укр. логотипом]
# LEGO Індіана Джонс: Оригінальні пригоди — українізатор
[бейдж версії] [Завантажити 1.1.10] [Сайт]
Що це (2 речення) · Статус: повний переклад
Встановлення (3 кроки) · Видалення · Сумісність (Steam ✓, Steam Deck, GOG ✗ не перевірено)
Скриншоти (3: підказка з ї/є, «Валєра», «Круглики»)
Що перекладено (текст 598+194+38, шрифти, 9 текстур, логотип, редактор)
Як ми це робили (абзац + посилання на docs/approach.md)
Інструменти (таблиця: назва → посилання → навіщо)
FAQ (антивірус, інша версія, сейви, як повернути англійську)
Зворотний зв'язок (Issues, Telegram dimkasmile)
Для розробників (посилання на docs/setup.md, architecture, research)
Автори й подяки · Ліцензії · Дисклеймер
## About (English)
```

### D2. Скриншоти

Знімки оптимізуються до JPEG/WebP шириною 1600 px (≤300 КБ) в
`docs/screenshots/` з осмисленими назвами:

| Файл | Джерело (`local/production-screenshots/`) |
|---|---|
| `main-menu.jpg` | `20261031110009_1.jpg` |
| `hint-dig.jpg` | `20261031110319_1.jpg` |
| `pause-barnett.jpg` | `20261031111053_1.jpg` |
| `exit-dialog.jpg` | `20261031135150_1.jpg` |
| `hint-switch.jpg` | `20261031135403_1.jpg` |
| `studs-krugliky.jpg` | `20261031135702_1.jpg` |
| `shop-valera.jpg` | `20261102171345_1.jpg` |
| `editor-forelka.jpg` | `20261102171409_1.jpg` |
| `pause-post-room.jpg` | `20261102171513_1.jpg` |

Hero: `main-menu.jpg`. Це також джерело `og:image` для сайту.

### D3. Карта переписування досліджень

| Нова сторінка `docs/` | Джерела |
|---|---|
| `approach.md` | перші нотатки, глосарій, культурні адаптації, CHANGELOG |
| `tooling.md` | перші нотатки, `fnt-format-findings.md`, README ASI, TT Font Studio |
| `setup.md` | `repo-foundation` (doctor/extract/build), README інсталерів |
| `architecture.md` | `docs/uap.md`, `asi-v0.1.8.md`, `uap-*.md` |
| `research/fonts.md` | `fnt-format-findings.md`, `font2-crash-investigation.md`, `controller-icon-baseline.md`, приціл, шрифтове порівняння |
| `research/textures.md` | `uap-textures-loading.md`, README каталогу текстур |
| `research/pc-menu.md` | `pc-menu-text-investigation.md` |
| `research/runtime-loading.md` | `uap-text-loading.md`, `uap-mod-loader-compatibility.md`, `asi-v0.1.8.md` |
| `research/character-editor.md` | `custom-character-saved-names.md`, `docs/issues/character-editor-up-arrow.md` |
| `research/cultural-adaptations.md` | однойменний файл (оновлений: Форелька, Льоля) |

Сирі `*.json`, `*.log` і дампи не переносяться. Кожна сторінка закінчується
посиланням «Повні докази — в архіві досліджень» без прив'язки до приватного
репозиторію, доки його не відкрито.

### D4. Початковий список інструментів

| Інструмент | Роль |
|---|---|
| TT Font Studio (github.com/DrSmile444/tt-font-studio) | редагування FNT, метрик і атласу в браузері |
| QuickBMS + `ttgames.bms` | розпакування DAT |
| TTGames-Explorer-Rebirth | довідка щодо формату FT2/FNT |
| TTGames LEGO Documentation, BactaTank Classic | документація з модингу TT |
| Ultimate ASI Loader 9.7.4 (ThirteenAG) | завантаження плагіна |
| Affinity | рендер гліфів, шари текстур |
| Python 3, MSVC Build Tools x86, Windows SDK | збірка |
| Tesseract/OCR (через `ocr_texture_catalog.ps1`) | пошук тексту на текстурах |
| Claude Code, Codex | асистування в дослідженні й чернетках |

Під час виконання список звіряється з усіма скриптами й нотатками; посилання
й версії перевіряються.

### D5. Розділ про ШІ

Тон — факти, без виправдань. Розділ структуровано як таблицю «Хто що робив»:

| Автор | ШІ-асистент |
|---|---|
| ідея й рішення | дослідження форматів |
| глосарій і культурні адаптації | пошук адрес у пам'яті |
| вичитка кожного рядка | розпакування |
| живе QA | чернетки перекладу та інструменти |

Плюс опис процесу контексту: рядок → ID → де з'являється в грі → глосарій →
переклад → перевірка в грі.

### D6. CHANGELOG

Верхній запис `## 1.1.10 — <дата публікації>`: «Перший публічний реліз нового
репозиторію; вміст локалізації відповідає 0.1.10». Нижче йдуть записи
0.1.10…0.1.0 зі старого CHANGELOG і README. Посилання на `local/` і старі ZIP
вилучаються, а згадки сторонніх матеріалів переписуються нейтрально.

## Risks / Trade-offs

- [Статус «повний переклад» без завершеного проходження] → Рішення автора.
  Канали зворотного зв'язку помітні на першому екрані.
- [Посилання на архів досліджень у приватному репозиторії] → Не давати мертвих
  посилань; писати «архів досліджень автора».
- [Скриншоти з логотипами правовласників] → Використовуються як ілюстрації
  перекладу, а не як айдентика проєкту.
