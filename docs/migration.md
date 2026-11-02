# Міграція зі старого дослідницького репозиторію

Джерело — архів досліджень автора, коміт `3b7ff01` (стан v0.1.10, 442 відстежувані файли). Тут для кожного файлу вказано, куди він перейшов або чому його не перенесено. Головний доказ, що нічого суттєвого не загубилося (перевірено одразу після перенесення, ще до виправлення локалі США в 1.1.10):

- `python -m ua build` з базовим релізом 0.1.10 дає `UKRAINIAN.uap` зі SHA-256 `6f1b4e65…964a`, побайтово рівний релізу 0.1.10;
- `python -m ua build --level full` перезбирає з нуля Font 1, Font 2 і дев'ять текстур і дає той самий SHA-256;
- `pwsh native/build.ps1 -SmokeTest -TextureTest`: усі нативні тести проходять, а C++ патчер текстур дає ті самі байти, що й Python, для всіх 21 GSC-контейнерів.

Після перевірки міграції в 1.1.10 додано покриття локалі США. Відносно 0.1.10 змінилися лише текстові ресурси (`ENGLISH.TXT`, `TRC.CSV`) і додалися `AMERICAN.TXT` та `AMERICAN_CREDITS.TXT`; усі FNT, DDS і PC-меню лишилися побайтово тими самими. Див. `CHANGELOG.md`.

Позначки: **→** перенесено, **⟳** замінено новим механізмом, **✕** не перенесено (з причиною), **L** лише локально в `local/` (у git не йде).

## Переклад і глосарій

| Старе | Нове |
|---|---|
| `translations/english_txt_ua.json`, `trc_csv_ua.json`, `pc_menu_ua.json` | → `translations/` без змін |
| `translations/glossary.json` | → `translations/glossary.json`; додано `ids` (з приміток) для перевірки, `_meta` без локальних шляхів |
| `translations/credits_titles_ua.json` | ⟳ `translations/credits_ua.json`: ключ тепер номер рядка, а не англійська посада, тож англійського тексту гри в git немає |

## Формати й збірка

| Старе | Нове |
|---|---|
| `tools/loc/txt_format.py`, `trc_csv.py` | → `ua/formats/txt.py`, `ua/formats/trc_csv.py` |
| `tools/loc/credits_format.py` | ⟳ `ua/formats/credits.py` (адресація рядками) |
| `tools/fnt_tool.py` | → `ua/formats/fnt.py` |
| `tools/bc_color_encoder.py`, `bc_gray_encoder.py` | → `ua/formats/bc_color.py`, `bc_gray.py` |
| `runtime/uap/build_pack.py`, `unpack_pack.py` | ⟳ `ua/formats/uap.py`, `python -m ua unpack` |
| `tools/build_translated_textures.py` | ⟳ `ua/pipeline/textures.py` (оригінал вирізається з GSC у `game/`) |
| `runtime/uap/test_textures.py` | ⟳ `ua/pipeline/texture_test.py` (`python -m ua test-textures`, викликається з `native/build.ps1 -TextureTest`) |
| `tools/build_release.py`, `tools/snapshot_*_release.py`, `runtime/asi/release_text_update.py`, `release_editor_update.py`, `build_release_v0110.ps1`, `stage.py`, `snapshot_release.py`, `runtime/uap/snapshot_release.py` | ⟳ `python -m ua build [--release X]` + `ua/pipeline/package.py`; знімки окремих версій більше не потрібні, бо реліз будується з вихідників і базового релізу |
| `installer/*.ps1`, `runtime/asi/install_local.ps1`, `rollback_local.ps1`, `install_text_update.ps1`, `rollback_text_update.ps1`, `tools/install_translated_textures.py`, `tools/test_release_installer.py` | ⟳ `python -m ua install / uninstall / verify` (резервні копії, захист чужого loader-а, відновлення). Встановлення розпакованими файлами (епоха 0.1.0–0.1.5) не переноситься: його замінили ASI і UAP |

## Нативний код

| Старе | Нове |
|---|---|
| `runtime/pc-menu/proxy.cpp`, `dinput8.def`, `generate_strings.py`, `smoke_test.cpp` | → `native/asi/` (`smoke_test.cpp` → `proxy_smoke_test.cpp`); версія в журналі береться з `VERSION` |
| `runtime/uap/*.h`, `texture_test.cpp`, `custom_name_test.cpp` | → `native/asi/` |
| `runtime/asi/ukrainian.def`, `coexistence_probe.cpp`, `smoke_test.cpp` | → `native/asi/` |
| `runtime/asi/vendor/ultimate-asi-loader-v9.7.4/*` | → `native/vendor/ultimate-asi-loader-v9.7.4/` |
| `runtime/pc-menu/build.ps1`, `runtime/asi/build.ps1` | ⟳ `native/build.ps1` (ASI за замовчуванням; `-Legacy` і `-FontUpscaleExperiment` — старий режим проксі) |
| `docs/research/pc-menu-text-audit.json` | ⟳ `native/asi/pc_menu_table.json` (лише EXE SHA, адреси й 38 оригінальних підписів, які ASI перевіряє перед заміною) |
| `runtime/*/dist/*`, `release/dinput8.dll` | ✕ результати збірки: тепер у `build/` і `dist/` |
| `runtime/uap/verification-build.json` | ✕ протокол разової перевірки; результат описано в `docs/research/runtime-loading.md` |
| `runtime/asi/run_test.ps1` | → `tools/runtime/live_test.ps1` (копія гри в `local/test-game`) |
| `runtime/uap/run_test.ps1` | ✕ живий тест старого проксі `dinput8.dll` до 0.1.8 |

## Шрифти

| Старе | Нове |
|---|---|
| `tools/build_font1_*`, `build_font2_*`, `check_fnt_layout.py`, `check_font_coverage.py`, `test_font1_baseline.py`, `test_font2_layout.py`, `test_runtime_ui_glyphs.py`, `audit_runtime_ui_glyphs.py`, `inspect_font_crash.py` | → `tools/fonts/`; шляхи йдуть через `ua.paths`, виклик через `python -m ua build --level full` |
| `tools/glyph_viewer/*.py`, `viewer.html`, `README.md` | → `tools/fonts/glyph_viewer/` (згенеровані дані тепер у `build/glyph_viewer/`) |
| `tools/glyph_viewer/manual_overrides.json`, `manual_overrides2.json` | → `assets/fonts/font1/overrides.json`, `assets/fonts/font2/overrides.json` |
| `tools/glyph_viewer/atlas*.png`, `glyph_data*.js`, `glyphs*.json` | ✕ генеруються з FNT (містять пікселі шрифтів гри) |
| `tools/glyph_viewer/atlasx2.png`, `atlasx3.png`, `atlasx4.png` | L `local/experiments/font1-x2/` (робота автора поверх пікселів гри; в архіві теж є) |
| `fonts/font1/*.FNT`, `fonts/font2/*.FNT` | ✕ похідні ресурси гри: беруться з базового релізу або перезбираються рівнем 1 |
| `fonts/font1/PC_FONT_PC_atlas_2x_REFERENCE.png`, `fonts/preview/*` | ✕ ілюстрації з пікселями шрифтів; суть описано в `docs/research/fonts.md`, доказ збігу шрифту — у `docs/research/img/` |
| `fonts/experiments/font1-x2/README.md`, `build.json`, `tools/build_font1_upscale.py` | → `experiments/font1-x2/` |
| `fonts/experiments/font1-x2/*.FNT`, `dinput8.dll`, `atlas-decoded.png`, `restore.ps1`, `.gitignore` | ✕ результати експерименту відтворюються командами з його README |

## Текстури й графіка

| Старе | Нове |
|---|---|
| `graphics/texture-catalog/to-translate/*-ukrainian.png` (9), `*.af` | → `assets/textures/` |
| `graphics/texture-catalog/translation-list.json`, `built/manifest.json` | ⟳ `assets/textures/manifest.json` (хеші оригіналів, ключі UAP, місця в GSC, очікувані DDS) і `catalog.json` (усі 16 кандидатів) |
| `graphics/texture-catalog/to-translate/originals/*.dds`, `to-translate/T*-*.png` (англійські), `all/`, `review/`, `priority-preview/`, `index.html`, `all-textures.html`, `ocr*.json`, `inventory.json`, `contact-sheet` | ✕ видобуті або похідні зображення гри; генеруються наново `tools/textures/export_game_textures.py`, `build_texture_catalog.py`, `ocr_texture_catalog.ps1` у `build/texture-catalog/` |
| `graphics/texture-catalog/README.md`, `TRANSLATION-LIST.md`, `WHERE-TO-CHECK.md` | ⟳ `docs/research/textures.md` |
| `graphics/texture-catalog/built/*.dds`, `*-compressed-preview.png` | ✕ результат `ua build --level full` |
| `graphics/title-logo/*-ukrainian.png`, `*.af`, `README.md` | → `assets/logo/` |
| `graphics/title-logo/originals/*`, `*.png` (англійські), `built/*` | ✕ ресурси гри / результати збірки |
| `graphics/startup-screen/*` | ✕ стартовий екран входить у дев'ять текстур (`T2743`, `T2748`); опис у `docs/research/textures.md` |
| `tools/export_game_textures.py`, `build_texture_catalog.py`, `ocr_texture_catalog.ps1`, `build_title_logo.py`, `extract_title_logo.py` | → `tools/textures/` |

## Інші інструменти

| Старе | Нове |
|---|---|
| `tools/inspect_pc_menu_text.py`, `verify_pc_menu_dll.py` | → `tools/pc-menu/` |
| `runtime/uap/verify_runtime.py`, `tools/screenshot.ps1` | → `tools/runtime/` |
| `tools/rename_saved_custom_characters.py`, `test_saved_custom_names.py` | → `tools/saves/` |
| `runtime/asi/build_targeting_test.py`, `install_targeting_test.py` | → `experiments/targeting-tests/` (історія методу) |

## Знімки релізів, вміст `release/` і документація

| Старе | Нове |
|---|---|
| `releases/v0.1.0…v0.1.10/*` (ZIP, маніфести, VERSION.md) | ⟳ історія — у `CHANGELOG.md`; бінарні пакети — в архіві автора; публічні релізи — у GitHub Releases, починаючи з 1.1.10; ZIP 0.1.10 — базовий шаблон у `local/baseline/` до публікації 1.1.10 |
| `release/STUFF/**`, `release/LEVELS/**`, `release/CHARS/**`, `release/manifest.json` | ✕ похідні файли гри (повні GSC, FNT, тексти); їх замінили UAP і збірка |
| `README.md` (хроніка) | ⟳ новий `README.md`, `CHANGELOG.md`, `docs/approach.md` |
| `docs/research/*.md`, `docs/uap.md`, `docs/spike-notes/*`, `docs/issues/*` | ⟳ `docs/architecture.md`, `docs/research/*.md` (переписано) |
| `docs/research/**/*.json`, `*.log`, `*.jpg` (докази перевірок) | ✕ сирі протоколи — в архіві досліджень автора |
| `openspec/specs/*`, `openspec/changes/archive/*` | ✕ специфікації v1 спайку; нові специфікації цього репозиторію — в `openspec/specs/` |
| `.claude/`, `.agents/` | ⟳ створені наново `openspec init` |
| `LICENSE`, `LICENSES/*` | → без змін, крім шляху до ліцензії loader-а |

## Локальна зона старого репозиторію

| Що | Де тепер |
|---|---|
| видобута гра | ⟳ `python -m ua extract` → `game/` (перевірка за `manifests/game-files.json`) |
| QuickBMS, `ttgames.bms` | L `local/tools/quickbms/` (SHA-256 у `manifests/inputs.json`) |
| донорський кириличний шрифт, шрифт Adventure | L `local/donors/` (SHA-256 у `manifests/inputs.json`) |
| Franklin Gothic Medium | L `local/fonts/` |
| ZIP 0.1.10 | L `local/baseline/` |
| скриншоти автора | → `docs/screenshots/` |
| проміжні зображення, дампи пам'яті, тестові копії гри, сейви | ✕ в архіві автора; методи описано в `docs/research/` |
