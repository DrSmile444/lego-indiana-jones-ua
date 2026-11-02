# Архітектура

Як із JSON-перекладу виходить пакет і як цей пакет потрапляє в процес гри.
Подробиці кожної частини — у розділі досліджень: [завантаження в рантаймі](research/runtime-loading.md),
[шрифти](research/fonts.md), [текстури](research/textures.md),
[PC-меню](research/pc-menu.md), [редактор персонажів](research/character-editor.md).

## Загальна схема

```text
                         ЗБІРКА (python -m ua, native/build.ps1)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ translations/*.json ──┐                                                       │
 │ index/*.json ─────────┤ ua validate                                           │
 │                       v                                                       │
 │ базовий реліз ──> ua build --level text ──> TXT, CSV, титри, PC_MENU.UTF8 ─┐  │
 │ (manifests/                                                                 │  │
 │  baseline.json)   ua build --level full:                                    │  │
 │ game/ + local/ ──>   fonts    ──> 7 файлів FNT (Font 1 ×4, Font 2 ×3) ─────┤  │
 │ assets/       ──>   textures ──> 9 DDS, ключ = SHA-256 пікселів оригіналу ─┤  │
 │                                                                             v  │
 │                                                    ua/formats/uap.py: UKRAINIAN.uap
 │ translations/pc_menu_ua.json ─> native/build.ps1 ─> UKRAINIAN.asi             │
 │ native/vendor/ ──────────────────────────────────> dinput8.dll (ASI Loader)    │
 │                                    ua build --release ─> dist/*.zip (6 файлів) │
 └───────────────────────────────────────────────────────────────────────────────┘

                                 ГРА (пам'ять процесу)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ LEGOIndy.exe ──імпорт──> dinput8.dll (Ultimate ASI Loader 9.7.4)               │
 │                              │ LoadLibrary + InitializeASI                     │
 │                              v                                                 │
 │                     scripts/UKRAINIAN.asi                                      │
 │                       1. SHA-256 EXE, байти функцій, записи UAP — інакше стоп  │
 │                       2. читає scripts/UKRAINIAN.uap у RAM                     │
 │                       3. ставить detour-и:                                     │
 │                                                                                │
 │  рушій: відкрити ресурс ──> шлях є в UAP? ──так──> memory stream над UAP       │
 │         (0x6B44F0 тощо)          │ні                (тексти, шрифти, титри)    │
 │                                  v                                             │
 │                        оригінальне читання з DAT ──> буфер ──> є DDS з відомим │
 │                        (0x6B55A0, 0x6B7440)          хешем? ──так──> копія DDS │
 │                                                                     з UAP      │
 │  PC-таблиці EXE (0x921D10, 0x921E48, 0x9D0C30) ──> вказівники на UTF-8 рядки   │
 │  редактор персонажів (0x64C6AF, 0x64C6FF, 0x64C76D, 0x5F4BB2) ──> UTF-8 адаптери│
 │                                                                                │
 │  DAT і EXE на диску не змінюються; журнал: scripts/legoindy-ua-pc.log          │
 └───────────────────────────────────────────────────────────────────────────────┘
```

## Пакет гравця

```text
dinput8.dll                               Ultimate ASI Loader 9.7.4 x86, без змін
scripts/UKRAINIAN.asi                     наш плагін, експорт InitializeASI
scripts/UKRAINIAN.uap                     ресурси перекладу
scripts/UKRAINIAN/README.txt              інструкція
scripts/UKRAINIAN/LICENSE.txt             LICENSE + повні тексти MIT і CC BY 4.0
scripts/UKRAINIAN/LICENSE-ASI-Loader.txt  повідомлення loader-а та його компонентів
```

## Формат UAP1

`UKRAINIAN.uap` — власний контейнер без стиснення й шифрування. Гра його не
розуміє, його читає лише плагін. Усі числа little-endian.

| Частина | Вміст |
|---|---|
| Заголовок, 12 байтів | magic `55 41 50 31 0D 0A 1A 00` (`UAP1\r\n\x1a\0`), u32 кількість записів |
| Індекс, по 296 байтів на запис | ASCII-шлях[256], u32 offset, u32 size, SHA-256[32] |
| Дані | байти ресурсів |

- Побайтово однакові ресурси посилаються на той самий діапазон даних. Так сім
  імен шрифтових файлів займають місце двох шрифтів.
- SHA-256 в індексі перевіряє цілісність кожного запису під час запуску.
- Пакет завантажується в пам'ять один раз і живе до кінця гри; на диск нічого
  не розпаковується.

Записи пакета 1.1.10 (23):

| Шлях у UAP | Що це |
|---|---|
| `STUFF/TEXT/ENGLISH.TXT` | основний текст (UTF-8 з BOM, CRLF, рядки `ID [pc] "текст"`) |
| `STUFF/TEXT/AMERICAN.TXT` | надбудова з 18 рядків, яку гра читає поверх `ENGLISH.TXT` при мові системи «англійська (США)», наприклад у Proton на Steam Deck |
| `STUFF/TEXT/TRC.CSV` | діалоги збереження (UTF-16; переклад записано в колонки ENGLISH і AMERICAN, інші мови без змін) |
| `STUFF/TEXT/ENGLISH_CREDITS.TXT`, `PC_ENGLISH_CREDITS.TXT`, `AMERICAN_CREDITS.TXT` | титри: перекладено заголовки, імена без змін |
| `STUFF/TEXT/FONT_PC.FNT`, `PC_FONT.FNT`, `PC_FONT_PC.FNT`, `PC_FONT_NGC.FNT` | Font 1 (спільні дані) |
| `STUFF/TEXT/FONT2.FNT`, `FONT2_PC.FNT`, `FONT2_NGC.FNT` | Font 2 (спільні дані) |
| `UKRAINIAN/PC_MENU.UTF8` | 38 PC-рядків, розділених нульовим байтом |
| `UKRAINIAN/TEXTURES/<SHA-256>.DDS` ×9 | українські текстури; ім'я — хеш пікселів оригіналу |

`python -m ua` уміє розпакувати й зібрати UAP (`ua/formats/uap.py`). Редагувати
розпакований файл марно: правки вносяться в джерела, а пакет збирається заново.

## Плагін у грі

Порядок запуску:

1. Loader завантажує `UKRAINIAN.asi` і викликає `InitializeASI`. `DllMain`
   лише запам'ятовує модуль.
2. `InitOnceExecuteOnce` гарантує одну ініціалізацію; модуль закріплюється до
   кінця процесу.
3. Перевіряється SHA-256 EXE. Невідомий EXE — переклад вимкнено, гра працює
   як оригінал.
4. Читається UAP поруч із плагіном, перевіряється кожен запис.
5. Перевіряються початкові байти кожної функції, яку буде перехоплено.
6. Встановлюються detour-и (тексти, CSV, читання для DDS), підміняються
   PC-таблиці та виклики редактора персонажів.

Будь-яка розбіжність на кроках 3–5 означає, що відповідна частина не
вмикається і рушій працює штатно. Журнал пишеться в `scripts/legoindy-ua-pc.log`.

## Модулі `native/`

| Файл | Роль |
|---|---|
| `native/asi/proxy.cpp` | точка входу: `InitializeASI` (режим ASI) або експорти DirectInput (стара proxy-збірка), перевірка EXE, журнал, підміна PC-таблиць |
| `native/asi/overlay.h` | читання й перевірка UAP, detour-и ресурсних функцій, memory streams, корекція розміру, перехоплення цілого файла для CSV |
| `native/asi/textures.h` | detour функції читання ресурсу для підміни DDS |
| `native/asi/texture_buffer.h` | пошук DDS у буфері, хеш пікселів, копіювання українського DDS |
| `native/asi/custom_names.h` | адаптери редактора персонажів і форматер початкових імен «Форелька»/«Льоля» |
| `native/asi/custom_name_utf8.h` | вибір цілої UTF-8 літери для комірки імені |
| `native/asi/practice_cutscenes.h` | тестовий режим автозавершення катсцен; лише в тестах, у реліз не входить |
| `native/asi/generate_strings.py` | генерує C-рядки PC-меню й адреси з `translations/pc_menu_ua.json` і `pc_menu_table.json` |
| `native/asi/pc_menu_table.json` | перевірена таблиця PC-рядків EXE: адреси й оригінальні англійські рядки |
| `native/asi/ukrainian.def`, `dinput8.def` | експорти ASI (`InitializeASI`) і старої proxy-збірки |
| `native/asi/smoke_test.cpp`, `proxy_smoke_test.cpp` | smoke test ASI і старої proxy-збірки на непідтримуваному процесі |
| `native/asi/custom_name_test.cpp` | x86-регресії редактора: буфер, UTF-8 комірки, форматер, тестовий режим катсцен |
| `native/asi/texture_test.cpp` | прогін C++ підміни DDS на оригінальних GSC і порівняння з еталоном |
| `native/asi/coexistence_probe.cpp` | тестовий другий ASI для перевірки співіснування плагінів |
| `native/build.ps1` | збірка й тести (`-SmokeTest`, `-TextureTest`, `-Legacy`, `-FontUpscaleExperiment`) |
| `native/vendor/ultimate-asi-loader-v9.7.4/` | офіційний `dinput8.dll`, `LICENSE.txt`, `provenance.json` з SHA-256 |

## Модулі `ua/`

| Модуль | Роль |
|---|---|
| `ua/__main__.py`, `ua/cli.py` | `python -m ua <команда>`: `doctor`, `validate`, `extract`, `build`, `install`, `uninstall`, `verify`, `unpack`, `index`, `test-textures` |
| `ua/doctor.py` | які рівні відтворення доступні на машині й чого бракує |
| `ua/paths.py` | зони репозиторію й змінні `UA_GAME_DIR`, `UA_LOCAL_DIR` |
| `ua/util.py` | хешування, JSON, вивід |
| `ua/baseline.py` | базовий реліз з `manifests/baseline.json`: пошук, завантаження, перевірка SHA-256 |
| `ua/formats/txt.py` | `ENGLISH.TXT`: BOM, CRLF, коментарі `;`, рядки `ID [pc] "текст"` |
| `ua/formats/trc_csv.py` | `TRC.CSV` у UTF-16, зміна лише англійської колонки |
| `ua/formats/credits.py` | файли титрів |
| `ua/formats/fnt.py` | `.FNT`: метрики, mapping з пересортуванням, додавання гліфів, footer |
| `ua/formats/uap.py` | читання, перевірка й запис UAP1 |
| `ua/formats/bc_gray.py`, `bc_color.py` | блокові DXT-кодери (сірий без кольорових домішок; кольоровий для текстур) |
| `ua/pipeline/validate.py` | перевірки перекладу: ID, токени, гліфи, глосарій |
| `ua/pipeline/index.py` | генерація індексу рядків `index/*.json` з базового релізу |
| `ua/pipeline/text.py` | текстовий рівень: JSON → TXT/CSV/титри/PC-меню поверх шаблону |
| `ua/pipeline/extract.py` | видобування з DAT через QuickBMS і перевірка `game-files.json` |
| `ua/pipeline/fonts.py` | повний рівень: Font 1 і Font 2 за допомогою `tools/fonts/` |
| `ua/pipeline/textures.py` | повний рівень: 9 DDS з PNG-шарів, перекодування лише змінених блоків |
| `ua/pipeline/package.py` | відтворюваний ZIP із шести файлів |
| `ua/pipeline/install.py` | встановлення з резервною копією, відкат, статична перевірка |

## Дані й маніфести

| Шлях | Що там |
|---|---|
| `translations/` | наш переклад за ID і глосарій |
| `index/` | ID, маркери `pc`, токени й набори символів шрифтів; без тексту гри |
| `assets/fonts/` | наші гліфи, параметри рендеру, ручні виправлення метрик |
| `assets/textures/` | українські шари, проєкти `.af`, `manifest.json` з хешами оригіналів і результатів |
| `manifests/baseline.json` | базовий реліз для текстової збірки |
| `manifests/game-files.json` | які файли гри потрібні й їхні SHA-256 |
| `manifests/inputs.json` | сторонні входи в `local/`: QuickBMS, донори, шрифти, MSVC |
| `tools/` | інструменти досліджень: шрифти, текстури й OCR, PC-меню, рантайм, сейви |
| `experiments/` | відкладені експерименти зі статусом (атлас ×2, тести прицілу) |

## Чому так

- **Пам'ять замість файлів гри.** DAT і EXE лишаються оригінальними, установка
  й видалення — це три файли, а пакет важить ~3 МБ замість 182 МБ.
- **Хеш пікселів як ключ текстури.** Один запис покриває всі копії картинки, а
  змінена іншим модом текстура не перезаписується.
- **Перевірка перед кожною зміною.** Для незнайомого EXE чи пошкодженого
  пакета гра просто лишається англійською.
- **Офіційний loader замість власного proxy.** Переклад співіснує з іншими
  ASI-модами.
- **Попередній реліз як шаблон.** Виправлення рядка не потребує гри, а `CSV`
  з іншими мовами й титри з іменами не потрапляють у git.
