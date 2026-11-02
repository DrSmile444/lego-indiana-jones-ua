# PC menu: strings baked into the EXE

After `ENGLISH.TXT` was translated, part of the menu stayed in English: "Quit
to Windows", "Video Settings", "Screen Resolution", "Shadows"… One screen
showed both «Назад» and "Back". This page explains where these strings come
from and how they were translated without modifying `LEGOIndy.exe`.

## Where the text comes from

Searching for the phrases across all the unpacked game resources (9,903
files, 6.5 GB) found no match at all. The strings turned up in the EXE
itself: two embedded tables of 38 entries each,
`(u32 id, u32 string_pointer)`, with a `(38, 0)` terminator.

Verified build: Steam, `LEGOIndy.exe` 7,847,936 bytes, SHA-256
`c12f7348ec63aed61f56eb15d825f15b8340500668fa8c8dcf06c2f332e5e5fd`,
image base `0x400000`.

| Object | VA |
|---|---|
| Source English tables | `0x921D10`, `0x921E48` |
| Active array (38 pointers, 152 bytes) | `0x9D0C30` |
| Initialization flag | `0x9D0CC8` |
| Initializer | `0x521230` |
| String getters | `0x4B1EF0`, `0x620A10`, `0x6960B0` |

The code section of the Steam file on disk cannot be disassembled directly,
so the addresses and instructions were verified against the memory of the
running process (`ReadProcessMemory`, with no changes to memory). Simplified,
the getter logic is:

```c
if (!pc_strings_initialized)
    initialize_pc_strings_from_embedded_language_table();  // 0x521230
return pc_strings[id];
```

The initializer picks an embedded table based on the game language, zeroes
the active array and copies the pointers into it. No file reading happens
here, so changes to `ENGLISH.TXT` or `TRC.CSV` do not affect these menus.
Switching the language only selects a different embedded table; Ukrainian is
not among them.

That is why the same words exist twice: `Back` with ID 727 in `ENGLISH.TXT`
was already «Назад», while `Back` with PC ID 10 is a separate EXE string.

| PC ID | Original | Translation |
|---|---|---|
| 1 | Quit to Windows | Вийти до Windows |
| 18 | Video Settings | Налаштування відео |
| 19 | Screen Resolution | Роздільність екрана |
| 29 | Effects Settings | Налаштування ефектів |
| 15 / 16 | On / Off | Увімк. / Вимк. |

`FSAA: Edge AA` is made of two separate strings — the name and the value.
All 38 translations are in `translations/pc_menu_ua.json`.

## Fix options

| Approach | EXE unchanged | Verdict |
|---|---|---|
| TXT/CSV only | yes | does not work: a different text access path |
| Patching the EXE with new strings | no | possible, but modifies a game file and limits string length |
| A module that replaces pointers in memory | yes | **chosen** |

## How the replacement works

The plugin keeps the Ukrainian UTF-8 strings in its own memory and rewrites
the pointers:

1. It verifies the EXE's SHA-256 and every entry of both English tables: the
   ID, the pointer and the English string itself.
2. It rewrites 76 pointers (38 in each source table).
3. If the active array is already populated, it updates its 38 pointers too.
   If not, the game itself copies the already-Ukrainian addresses during
   initialization.

For example, PC ID 19 initially points to `Screen Resolution` inside the
EXE, and after the replacement to «Роздільність екрана» in the plugin's
memory. The string can be longer than the original because it has its own
storage. The module must stay loaded until the process exits: the game's
tables reference its memory.

When started early through the ASI Loader, the table pages have the
`PAGE_WRITECOPY` attribute; later, `PAGE_READWRITE`. The plugin accepts both
after fully verifying the entries; Windows creates a private copy of the page
by itself. `VirtualProtect` is not needed for the PC pages.

Initially (0.1.4) this was a separate `dinput8.dll` proxy library that
forwarded DirectInput calls to the real system library. Since 0.1.6 the
PC-menu strings live in the `UKRAINIAN/PC_MENU.UTF8` entry of the UAP package
(null-separated strings), and since 0.1.8 the replacement is performed by the
ASI plugin. The mechanism stayed the same.

## Checks

- Reading the memory of the running game: 76 source and 38 active pointers,
  an exact match of the Ukrainian UTF-8 strings with the JSON.
- Every character of the translation exists in the main font.
- With a different EXE, the plugin skips the replacement and the game stays
  in English.
- The author checked «Вийти до Windows» (Quit to Windows), the video and
  effects menus and the option values in the game.

Not checked: every possible option value at every resolution, and switching
the language during play.

The full evidence is in the author's research archive.
