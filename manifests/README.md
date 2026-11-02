# manifests/

Контрольні суми, які роблять збірку відтворюваною й перевірюваною.

- `baseline.json`: реліз, з якого текстова збірка бере шаблон (ZIP і SHA-256, URL після публікації).
- `game-files.json`: файли Steam-версії, які видобуває `ua extract`, і SHA-256 підтримуваного `LEGOIndy.exe`.
- `inputs.json`: сторонні входи в `local/` (QuickBMS, `ttgames.bms`, донорський шрифт, Adventure, Franklin Gothic) з джерелами й SHA-256.
- `releases/<версія>.json`: склад і SHA-256 кожного опублікованого пакета.
