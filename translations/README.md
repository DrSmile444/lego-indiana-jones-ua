# translations/

Джерело правди для всього тексту локалізації. Тільки український текст: англійських рядків гри тут немає.

| Файл | Що містить | Ключ |
|---|---|---|
| `english_txt_ua.json` | 598 рядків `STUFF/TEXT/ENGLISH.TXT`; ті самі значення йдуть в `AMERICAN.TXT` (18 ID, локаль США) | ID рядка |
| `trc_csv_ua.json` | перекладені мітки `STUFF/TEXT/TRC.CSV` (записуються в колонки ENGLISH і AMERICAN) | LABEL |
| `credits_ua.json` | заголовки й посади в титрах (`ENGLISH_CREDITS.TXT`, `PC_ENGLISH_CREDITS.TXT`, `AMERICAN_CREDITS.TXT`) | номер рядка |
| `pc_menu_ua.json` | 38 рядків PC-меню з `LEGOIndy.exe` (підміняє ASI) | 0–37 |
| `glossary.json` | глосарій: затверджені імена, місця, терміни; `ids` перевіряє `ua validate` | англійський термін |

Після правки: `python -m ua validate`, потім `python -m ua build`. Імена людей і студій у титрах не перекладаються, тому їх тут немає.
П'ять посад локалізаційної команди в `PC_ENGLISH_CREDITS.TXT` навмисно лишилися англійською (див. `index/credits.json`, `translate: false`).
