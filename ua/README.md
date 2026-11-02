# ua/

CLI і бібліотека збірки: `python -m ua --help`.

- `cli.py`: команди `doctor`, `validate`, `build`, `extract`, `install`, `uninstall`, `verify`, `index`, `unpack`, `test-textures`.
- `paths.py`: зони репозиторію (`game/`, `local/`, `build/`, `dist/`) та їх перевизначення змінними середовища.
- `baseline.py`: базовий реліз — шаблон збірки, закріплений у `manifests/baseline.json`.
- `doctor.py`: які рівні відтворення доступні.
- `formats/`: формати TT Games і наші (`txt`, `trc_csv`, `credits`, `fnt`, `uap`, DXT-кодувальники `bc_color`/`bc_gray`).
- `pipeline/`: `text` (переклад → текстові ресурси), `fonts` і `textures` (рівень 1), `index`, `validate`, `extract`, `package` (ZIP), `install`, `build` (оркестрація), `texture_test`.

Залежність одна: Pillow (`requirements.txt`). Вона потрібна лише для рівня 1.
