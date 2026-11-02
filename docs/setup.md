# Налаштування середовища й збірка

Цей документ — рецепт для розробника: як із чистого клону перевірити
переклад, зібрати текстове оновлення, нативний плагін, повністю перезібрати
шрифти й текстури, встановити результат у гру й зібрати реліз. Усі команди
виконуються з кореня репозиторію.

Гравцям це не потрібно: готовий пакет — на сторінці
[релізів](https://github.com/DrSmile444/lego-indiana-jones-ua/releases/latest).

## Зони репозиторію

```text
 PUBLIC GIT                         LOCAL (у .gitignore)                GITHUB RELEASES
 translations/  наш текст           game/    видобуті ресурси гри       lego-indiana-jones-ua-
 index/         ID і токени рядків  local/   донори, шрифти, базові       <версія>.zip
 assets/        наші гліфи й шари            пакети, QuickBMS            + SHA-256
 ua/ native/ tools/ experiments/    build/   проміжні файли
 manifests/ docs/ tests/            dist/    готові пакети
```

- У git **немає файлів гри**, сторонніх шрифтів і донорських матеріалів.
- `local/` і `game/` кожен заповнює зі своїх легальних джерел; що саме там має
  лежати, описують `manifests/inputs.json` і `manifests/game-files.json` разом
  із SHA-256.
- Бінарні пакети живуть у GitHub Releases, а не в git.

Шляхи можна перевизначити змінними середовища:

| Змінна | Що задає | Типово |
|---|---|---|
| `UA_GAME_DIR` | видобуті ресурси гри | `game/` |
| `UA_LOCAL_DIR` | донори, шрифти, базові пакети, QuickBMS | `local/` |

## Рівні відтворення

| Рівень | Що дає | Що потрібно |
|---|---|---|
| Перевірка | `validate`, тести | Git, Python 3 |
| Текст (`--level text`) | новий `UKRAINIAN.uap` зі зміненим текстом | + базовий реліз (завантажується автоматично) |
| Нативний | `UKRAINIAN.asi` | + Windows, Visual Studio C++ x86, Windows SDK |
| Повний (`--level full`) | шрифти й текстури з нуля | + власна Steam-гра, QuickBMS, донори, Franklin Gothic Medium |

`python -m ua doctor` показує, які рівні доступні на цій машині і чого бракує.
`python -m ua --help` перелічує всі команди; крім описаних нижче, є `unpack`
(розпакувати будь-який UAP для огляду), `index` (перегенерувати `index/` з
базового релізу) і `test-textures` (використовується `native/build.ps1 -TextureTest`).

## 1. Перевірка: потрібні лише Git і Python

```powershell
git clone https://github.com/DrSmile444/lego-indiana-jones-ua.git
cd lego-indiana-jones-ua
python -m pip install -r requirements.txt pytest
python -m ua doctor
python -m ua validate
python -m pytest
```

`validate` перевіряє переклади проти індексу `index/*.json`: що всі ID на місці,
службові токени `[...]` і `%d` збережено, кожен символ є у відповідному шрифті,
а терміни відповідають глосарію. Ті самі команди запускає CI.

## 2. Текстове оновлення без гри

Цього рівня достатньо, щоб виправити рядок перекладу.

1. Відредагуйте `translations/*.json`:
   - `english_txt_ua.json` — ключ: числовий ID рядка `ENGLISH.TXT`;
   - `trc_csv_ua.json` — ключ: мітка рядка `TRC.CSV`;
   - файл титрів — заголовки посад і розділів;
   - `pc_menu_ua.json` — 38 PC-рядків (після зміни потрібна ще й нативна збірка);
   - `glossary.json` — терміни (див. [approach.md](approach.md)).
2. Перевірте й зберіть:

   ```powershell
   python -m ua validate
   python -m ua build --level text
   ```

Шаблоном збірки є **попередній опублікований реліз**. `manifests/baseline.json`
закріплює його ZIP за SHA-256; `ua` завантажує його в `local/baseline/`,
звіряє суму, розпаковує `UKRAINIAN.uap`, накладає JSON-переклади на
`ENGLISH.TXT`, `TRC.CSV`, титри й PC-меню та пакує знову. Шрифти й текстури
переходять без змін. Без змін у перекладі результат побайтово дорівнює `UAP`
базового релізу.

Поки 1.1.10 не опубліковано, базою є ZIP 0.1.10 з архіву автора: його треба
вручну покласти в `local/baseline/` (ім'я й SHA-256 — у `manifests/baseline.json`).

## 3. Нативний плагін

Потрібні:

- [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  з робочим навантаженням «Розробка класичних застосунків на C++» і компонентом
  MSVC x86/x64;
- [Windows 10/11 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/);
- Python (генерує C-рядки PC-меню з `translations/pc_menu_ua.json`).

```powershell
./native/build.ps1 -SmokeTest
```

Скрипт знаходить компілятор через `vswhere`, збирає x86 `UKRAINIAN.asi`
(`/MT /W4 /WX /utf-8 /Brepro`) у `build/native/asi/` і запускає тести:

- smoke test: плагін завантажується в непідтримуваний процес, викликає
  `InitializeASI` двічі й нічого не патчить;
- x86-регресії редактора персонажів: UTF-8 комірки, буфер на 16 байтів,
  початкові імена.

Інші режими: `-TextureTest` (порівнює C++ підміну DDS з еталоном; потрібен
`game/`), `-Legacy` (стара proxy-збірка `dinput8.dll`),
`-FontUpscaleExperiment` (див. `experiments/font1-x2/`). Версію в журналі
плагіна береться з файла `VERSION`.

## 4. Повне перезбирання: шрифти й текстури

Потрібне, лише якщо змінюєте гліфи або написи на текстурах.

### 4.1. Гра й QuickBMS

1. Встановіть гру в Steam (англійська мова). Підтримуваний `LEGOIndy.exe` має
   SHA-256 `c12f7348ec63aed61f56eb15d825f15b8340500668fa8c8dcf06c2f332e5e5fd`.
2. Завантажте [QuickBMS](https://aluigi.altervista.org/quickbms.htm) і сценарій
   [`ttgames.bms`](https://github.com/linterniGamer/Tt-Games-quickbms-scripts)
   та покладіть їх так:

   ```text
   local/tools/quickbms/quickbms.exe
   local/tools/quickbms/ttgames.bms
   ```

3. Видобудьте потрібні ресурси:

   ```powershell
   python -m ua extract --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
   ```

   `extract` відкриває теку гри лише для читання, бере файли за списком
   `manifests/game-files.json` (розкладка `game/<назва DAT>/<шлях>`), звіряє
   їхні SHA-256 і перевіряє, що DAT та EXE до й після не змінилися.
   `--all` розпаковує архіви повністю (кілька ГБ; потрібно для каталогу текстур).

### 4.2. Донори й шрифти

| Файл у `local/` | Що це | Де взяти |
|---|---|---|
| `donors/cyrillic-font-patch/PC_FONT_PC.FNT` | атлас-основа Font 1 зі сторонньої кириличної латки шрифту | з теки `STUFF/TEXT` цієї латки; у репозиторії не поширюється |
| `donors/Adventure_Indiana_Jones.ttf` | фанатський шрифт Adventure для Font 2 | [Pixel Sagas / Neale Davidson](https://www.dafont.com/adventure.font), за умовами автора |
| `fonts/Franklin Gothic Medium Regular.ttf` | Franklin Gothic Medium для нових літер Font 1 | ліцензія від правовласника (ITC / Monotype) або разом із ліцензованим Office; у Windows не входить |

Очікувані SHA-256 записано в `manifests/inputs.json`. Інший файл може дати
інші пікселі; `doctor` про це попередить. Чому шрифт не поширюється — у
[research/fonts.md](research/fonts.md#ліцензія-шрифту).

### 4.3. Збірка

```powershell
python -m ua build --level full
```

Font 1 збирається з донорського атласу, наших гліфів і ручних виправлень
метрик з `assets/fonts/font1/`; Font 2 — з оригінального `FONT2_PC.FNT` гри,
шрифту Adventure і `assets/fonts/font2/`. Текстури — з оригінальних DDS у
`game/` і наших шарів `assets/textures/*-ukrainian.png`: перекодовуються лише
змінені блоки 4×4. Проміжні файли лежать у `build/`. Звіт збірки показує,
чи збігаються FNT і DDS з базовим релізом, і пояснює відмінності.

## 5. Встановлення в гру для перевірки

```powershell
python -m ua install --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
python -m ua verify --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
python -m ua uninstall --game "D:\SteamLibrary\steamapps\common\LEGO Indiana Jones The Original Adventures"
```

- `install` перевіряє EXE, копіює шість файлів пакета (типово —
  `dist/<версія>/lego-indiana-jones-ua-<версія>.zip` з кроку 6, тож спершу
  зберіть реліз; інший ZIP можна передати через `--package`) і зберігає все, що
  перезаписує, у `<гра>/ukrainian-localization-backup/<час>/` разом з
  `install-state.json`. Чужий `dinput8.dll` блокує встановлення; якщо це
  свідомо сумісний ASI Loader, додайте `--allow-foreign-loader`.
- `verify` статично звіряє встановлені файли з хешами, записаними під час встановлення.
- `uninstall` повертає точний попередній стан.

Закривайте гру перед кожною з цих команд. Журнал плагіна —
`scripts/legoindy-ua-pc.log` у теці гри. Для перевірки рядків у пам'яті
запущеної гри є `tools/runtime/verify_runtime.py --pid <PID>`.

## 6. Реліз

```powershell
python -m ua build --release 1.1.10
```

Збирає в `dist/<версія>/` відтворюваний ZIP `lego-indiana-jones-ua-<версія>.zip`
(фіксовані дати й порядок файлів) і SHA-256. До пакета входять рівно шість
файлів: loader, `UKRAINIAN.asi`, `UKRAINIAN.uap`, `README.txt` і дві ліцензії.
Наявний реліз не перезаписується. Опублікований реліз стає базою для наступного
текстового оновлення через `manifests/baseline.json`.

## Типові проблеми

| Симптом | Причина й рішення |
|---|---|
| `doctor`: текстовий рівень недоступний | немає базового ZIP у `local/baseline/` і не задано URL у `manifests/baseline.json` |
| `extract`: QuickBMS не знайдено | перевірте шляхи в `local/tools/quickbms/` |
| `build.ps1`: «Visual Studio C++ x86 build tools are required» | доставте компонент MSVC x86/x64 у Visual Studio Installer |
| SHA-256 донора не збігається | інша версія файла; результат може відрізнятися від релізу |
| Гра англійською після `install` | мова гри в Steam не англійська або EXE не підтримується; див. журнал |

## Публікація релізу

1. Оновіть `VERSION` і додайте розділ `## X.Y.Z — дата` у `CHANGELOG.md`.
2. `python -m ua build --release X.Y.Z` створює в `dist/X.Y.Z/` ZIP, `SHA256SUMS` і `RELEASE_NOTES.md`.
   Нотатки починаються з великого посилання «Завантажити» на сам ZIP (шаблон — `assets/package/RELEASE_NOTES.md`),
   щоб гравці не плутали його з архівами `Source code`. Розділ «Що нового» береться з `CHANGELOG.md`.
3. Закомітьте `manifests/releases/X.Y.Z.json`, потім:
   ```powershell
   gh release create vX.Y.Z dist/X.Y.Z/lego-indiana-jones-ua-X.Y.Z.zip dist/X.Y.Z/SHA256SUMS `
     --title "X.Y.Z" --notes-file dist/X.Y.Z/RELEASE_NOTES.md
   ```
4. Переведіть `manifests/baseline.json` на новий реліз (URL ресурсу, SHA-256 ZIP і UAP), щоб наступні текстові
   збірки брали його за шаблон.
