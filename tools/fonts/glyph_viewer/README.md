# Glyph viewer

Показує прямокутники гліфів із таблиці метрик FNT поверх реального атласу шрифту. Через нього підбиралися ручні виправлення метрик у `assets/fonts/font*/overrides.json`.

```powershell
python -m ua build                                              # build/uap-unpacked/… з поточними FNT
python tools/fonts/glyph_viewer/export_glyph_atlas.py build/uap-unpacked/STUFF/TEXT/PC_FONT_PC.FNT
python tools/fonts/glyph_viewer/export_glyph_atlas.py build/uap-unpacked/STUFF/TEXT/FONT2_PC.FNT --suffix 2
python tools/fonts/glyph_viewer/render_boxes_png.py --scale 2 --labels   # статичний atlas_boxes.png
```

Результат з'являється в `build/glyph_viewer/`: `atlas*.png`, `glyphs*.json`, `glyph_data*.js` і копія `viewer.html`. Відкрийте `build/glyph_viewer/viewer.html` у браузері, щоб гортати гліфи, перевіряти зразок тексту на справжніх пікселях і експортувати виправлення. Згенеровані атласи містять пікселі шрифтів гри, тому в git вони не потрапляють.

Сучасна альтернатива для редагування — TT Font Studio: https://drsmile444.github.io/tt-font-studio/.
