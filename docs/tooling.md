# Інструменти

Повний список програм, бібліотек і довідкових джерел, які використано в
проєкті: що це, де взяти, яка версія, за якою ліцензією і для чого саме.
Як усе встановити й запустити — у [setup.md](setup.md).

Колонка «Рівень» показує, коли інструмент потрібен:
**текст** — збірка текстового оновлення без гри,
**нативний** — збірка плагіна,
**повний** — перезбирання шрифтів і текстур з файлів гри,
**дослідження** — лише для розслідувань.

## Власні інструменти автора

| Інструмент | Версія / ліцензія | Для чого | Рівень |
|---|---|---|---|
| [TT Font Studio](https://github.com/DrSmile444/tt-font-studio) ([онлайн](https://drsmile444.github.io/tt-font-studio/)) | актуальна, MIT | Редактор шрифтів `.FNT` у браузері: атлас, прямокутники гліфів, X/Y/Width, попередній перегляд тексту. Виріс із переглядача гліфів, у якому вручну підібрано вікна вибірки українських літер ([fonts.md](research/fonts.md)). | повний, дослідження |
| `python -m ua` (тека `ua/`) | цей репозиторій, MIT | Єдиний CLI: перевірка, видобування, збірка, встановлення ([setup.md](setup.md)). | усі |
| `tools/` | цей репозиторій, MIT | Каталог текстур з OCR, інспектори `.FNT` і дампів, читання пам'яті гри. | дослідження |

## Розпакування й формати TT Games

| Інструмент | Версія / ліцензія | Для чого | Рівень |
|---|---|---|---|
| [QuickBMS](https://aluigi.altervista.org/quickbms.htm) (Luigi Auriemma) | 0.12.0 — актуальна на сайті автора; GPL-2.0 | Розпакування `GAME.DAT`, `RAIDERS.DAT`, `TEMPLE.DAT`, `CRUSADE.DAT`. Викликається з `python -m ua extract`. | повний |
| [`ttgames.bms`](https://github.com/linterniGamer/Tt-Games-quickbms-scripts) | скрипт 0.9.11a; ліцензію в репозиторії не вказано | Сценарій QuickBMS для DAT ігор TT Games, прямо підтримує LEGO Indiana Jones. | повний |
| [TTGames-Explorer-Rebirth](https://github.com/AcK77/TTGames-Explorer-Rebirth) (AcK77) | MIT | Довідка: парсер `.ft2` (`Formats/FT2.cs`) підказав розкладку метрик гліфів `(X, Y, Width)` у нашому `.FNT`. Код не копіювався. | дослідження |
| [TTGames LEGO Documentation](https://github.com/AlubJ/TTGames-LEGO-Documentation) (AlubJ) | ліцензія не визначена GitHub | Документація спільноти: як розпаковувати DAT і запускати класичні ігри TT з розпакованими ресурсами. | дослідження |
| [BactaTank Classic](https://github.com/AlubJ/BactaTank-Classic) (AlubJ) | MIT | Інструмент для моделей і текстур класичних ігор TT; довідка щодо структури ресурсів і практики не поширювати ресурси гри. | дослідження |

## Завантаження в гру

| Інструмент | Версія / ліцензія | Для чого | Рівень |
|---|---|---|---|
| [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) (ThirteenAG) | [9.7.4](https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/tag/v9.7.4), x86, `Ultimate-ASI-Loader-NoPDB.zip`; MIT + ліцензії вбудованих компонентів | `dinput8.dll` у корені гри завантажує `scripts/UKRAINIAN.asi` і викликає `InitializeASI`. Бінарний файл вендорено без змін у `native/vendor/ultimate-asi-loader-v9.7.4/` з SHA-256 і походженням у `provenance.json`. | нативний, реліз |

## Графіка й шрифти

| Інструмент | Версія / ліцензія | Для чого | Рівень |
|---|---|---|---|
| [Affinity](https://affinity.serif.com/) (Designer / Photo) | комерційна | Ідентифікація шрифту накладанням, рендер гліфів Franklin Gothic Medium (46,62 pt, обведення 3 pt назовні), шари текстур і логотипа (`.af` в `assets/`). | повний (для правок графіки) |
| Franklin Gothic Medium (ITC / Monotype) | комерційний шрифт, **не постачається** | Джерело шести нових літер Font 1. Отримайте легально й покладіть у `local/fonts/`. | повний |
| Adventure (Neale Davidson, [Pixel Sagas](https://www.dafont.com/adventure.font)) | фанатський шрифт, умови автора | Джерело гліфів Font 2. Лежить у `local/donors/`. | повний |
| Стороння кирилична латка шрифту | сторонній матеріал, **не постачається** | Атлас-основа Font 1. Файл і SHA-256 описано в `manifests/inputs.json`. | повний |
| [ImageMagick](https://imagemagick.org/) | 7.x, ImageMagick License | Оптимізація скриншотів документації та сайту. | документація |

## Мови, збірка й тести

| Інструмент | Версія / ліцензія | Для чого | Рівень |
|---|---|---|---|
| [Python](https://www.python.org/downloads/) | 3.10+ (розробка на 3.12); PSF | CLI `ua`, формати, збірка UAP, перевірки. | усі |
| [Pillow](https://pypi.org/project/pillow/) | актуальна; MIT-CMU | Рендер гліфів, PNG ↔ DDS, прев'ю текстур. | повний |
| [pytest](https://pypi.org/project/pytest/) | актуальна; MIT | Тести форматів, індексу й відтворення бази. | усі |
| [capstone](https://pypi.org/project/capstone/) | необов'язкова; BSD | Дизасемблювання в аналізі дампів падінь і читанні пам'яті. | дослідження |
| [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), робоче навантаження C++ (x86) | 2022; безкоштовна ліцензія Microsoft | Компілятор `cl.exe` для `UKRAINIAN.asi` і x86-тестів. `native/build.ps1` шукає його через `vswhere`. | нативний |
| [Windows SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) | 10/11 | Заголовки й бібліотеки Win32 для плагіна. | нативний |
| PowerShell | 5.1 або 7 | `native/build.ps1` та службові сценарії. | нативний |
| [Windows OCR](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr) (`Windows.Media.Ocr`) | вбудований у Windows 10/11, потрібен англійський мовний пакет | Розпізнавання написів на 5 939 текстурах під час пошуку того, що перекладати. Tesseract не використовувався. | дослідження |
| Git, [GitHub CLI](https://cli.github.com/) | актуальні | Робота з репозиторієм і публікація релізів. | реліз |

## ШІ-асистенти

| Інструмент | Для чого |
|---|---|
| [Claude Code](https://claude.com/product/claude-code) (Anthropic) | Дослідження форматів і пам'яті гри, інструменти, тести, документація, чернетки перекладу. |
| [Codex](https://openai.com/codex/) (OpenAI) | Те саме: друга пара очей у дослідженнях і коді. |

Розподіл ролей між автором і ШІ описано в [approach.md](approach.md).

## Довідкові джерела

- [Microsoft: порядок пошуку DLL](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order)
  і [обмеження DllMain](https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain) —
  чому плагін нічого не робить у `DllMain`.
- [LEGO Games save file checksum updater](https://github.com/MR-SEVERN-Gaming/Lego-Games-save-file-checksum-updater) —
  звірка формули контрольної суми сейву ([character-editor.md](research/character-editor.md)).
- [Microsoft: Franklin Gothic](https://learn.microsoft.com/en-us/typography/font-list/franklin-gothic) —
  відомості про гарнітуру та продукти, з якими вона постачається.
- [Пласт: про організацію](https://plast.org.ua/about/) — обґрунтування адаптації «Пластун».
- [TT Mod Manager](https://github.com/BrickBench/TTModManager) — огляд того, як
  інші моди доставляють файли, для оцінки сумісності.

## Звірка зі скриптами

Під час переносу проєкту кожен скрипт дослідницького архіву, що викликає
зовнішню програму, звірено з цим списком:

| Що викликалося | Рядок у списку |
|---|---|
| `quickbms.exe` + `ttgames.bms` | QuickBMS |
| `cl.exe`, `vswhere.exe` у збірці плагіна | Visual Studio Build Tools |
| `Windows.Media.Ocr` у сценарії OCR каталогу текстур | Windows OCR |
| `capstone` у розборі дампів і читанні пам'яті | capstone |
| `PIL` у збирачах шрифтів і текстур | Pillow |
| `steam.exe -applaunch 32330` у тестових запусках | Steam (власна копія гри) |
| `powershell.exe` / `pwsh` у тестах інсталятора | PowerShell |
