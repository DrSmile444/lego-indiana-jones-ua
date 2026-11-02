# native/

`UKRAINIAN.asi` — x86 плагін для Ultimate ASI Loader. Він:
- підміняє ресурси гри даними з `UKRAINIAN.uap`: тексти, шрифти й текстури, причому DAT лишаються незмінними;
- підміняє 38 рядків PC-меню в пам'яті (EXE на диску не змінюється);
- виправляє 16-байтовий буфер імені в редакторі персонажів і задає початкові імена.

```powershell
pwsh native/build.ps1 -SmokeTest     # build/native/asi/UKRAINIAN.asi + тести
pwsh native/build.ps1 -TextureTest   # побайтова перевірка C++ патчера текстур (потрібні game/ і build/UKRAINIAN.uap)
```

- `asi/proxy.cpp`: вхідна точка й PC-меню. `overlay.h` / `textures.h`: UAP, хуки файлів, текстури. `custom_names*.h`: редактор персонажів.
- `asi/pc_menu_table.json`: перевірена таблиця адрес PC-меню Steam-версії. 38 оригінальних підписів зберігаються, щоб ASI перевіряв їх перед заміною.
- `asi/*_test.cpp`: smoke- і регресійні тести. `coexistence_probe.cpp`: другий ASI для перевірки сумісності.
- `vendor/ultimate-asi-loader-9.7.4/`: офіційна `dinput8.dll` (MIT) з `provenance.json` (джерело й SHA-256).
- `-Legacy` / `-FontUpscaleExperiment`: старий режим `dinput8.dll`-проксі для досліджень (див. `experiments/`).

Подробиці в `docs/architecture.md`.
