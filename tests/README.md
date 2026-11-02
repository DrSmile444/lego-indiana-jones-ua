# tests/

`python -m unittest discover -s tests -t .` — те саме запускає CI.

- `test_formats.py`: формати UAP/TXT/CSV/титрів на синтетичних даних.
- `test_validation.py`: `ua validate` проходить і ловить типові помилки.
- `test_repository.py`: у репозиторії немає файлів гри й шрифтів, у кожної теки є README, у коді немає машинних шляхів.
- `test_baseline_reproduction.py`: текстова збірка дає побайтово базовий `UKRAINIAN.uap` (тест пропускається, якщо базового ZIP немає).

Рівень 1 і нативні тести запускаються локально: `python -m ua build --level full`, `pwsh native/build.ps1 -SmokeTest -TextureTest`.
