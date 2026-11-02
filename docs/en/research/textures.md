# Textures with lettering

Part of the game's English text is not strings but images: the logo, the
splash screen, signs, instrument panels. To translate them, we had to find
every such texture among thousands of resources, repaint the lettering and
deliver it to the game without distributing whole game archives.

## Search: inventory and OCR

Textures are stored as DDS inside the GSC containers of scenes and menus,
which in turn live in four DAT archives (`GAME`, `RAIDERS`, `TEMPLE`,
`CRUSADE`). The inventory went like this:

1. Unpack the DAT files (QuickBMS + `ttgames.bms`, see [setup.md](../setup.md)).
2. Find every DDS in GSC containers and standalone files: 819 files, 12,133
   occurrences, **5,939 unique** images (by SHA-256).
3. Recognize the text on each one: the built-in Windows OCR
   (`Windows.Media.Ocr`, English language) for 5,936 textures. For 77
   candidates, a second OCR pass with upscaling; for 174, three rotations of
   the image (signs are sometimes rotated).
4. Review the candidates by eye and compile the list.

The result is an HTML gallery searchable by ID, path and recognized text. It
is generated from the game files, so it is not stored in git; the tooling is
in `tools/textures/` (`export_game_textures.py`, `ocr_texture_catalog.ps1`, `build_texture_catalog.py`). BIK videos, fonts and text tables are not part of the
inventory: they are separate resource types.

## What was translated

| ID | What it is | Where to see it in the game |
|---|---|---|
| T2525 | The «Індіана Джонс» (Indiana Jones) logo | Main menu (7 `TITLES_*` containers) |
| T2526 | The subtitle «Оригінальні пригоди» (The Original Adventures) | Main menu |
| T2743 | TT Games / LucasArts splash screen | Before the main menu |
| T2748 | The same, variant with the rating badge | Before the main menu, depending on region |
| T1407 | Bank signs in Venice | *The Last Crusade*, chapter 1, facades and cutscenes |
| T1030 | Another variant of the same signs | Intro of chapter 1 and finale of chapter 3 of *The Last Crusade* |
| T0573 | Electrical instrument panel | *The Last Crusade*, chapter 2 "Castle Rescue" |
| T1941 | The "ABC" board → «АБВ» | Custom character editor, the rename option |
| T2522 | College illustration | Menu and transition illustrations (`PICTURES_3_PC.GSC`) |

Deliberately not translated: the ESRB rating badge (an organization's mark),
demo screens and console warnings (not shown in the Steam version), a
decorative poster in the airship scene and a handwritten note in Shanghai (no
unambiguously legible text).

## How the lettering was drawn

Every texture was exported to a PNG of the same size with transparency. The
author repainted only the lettering in Affinity, without moving any other
elements: the scene takes its coordinates from the GSC, so the canvas cannot
be cropped or scaled. The Ukrainian layer is kept separately as
`assets/textures/<id>-ukrainian.png` together with an `.af` project. There are
no original DDS files in the repository.

When building the DDS:

- the size, format (DXT1/DXT5), header and all mip levels are preserved;
- 4×4 blocks the lettering does not touch are copied from the original
  without recompression, so the rest of the atlas stays byte-for-byte as it
  was;
- changed blocks are encoded by our own encoder (`ua/formats/bc_color.py`),
  and every mip level is verified by decoding it.

## How textures get into the game

Before version 0.1.7 the translation required replacing whole GSC files (the
package weighed 182 MB). Now the plugin substitutes the image at read time:

1. The game reads a resource from the DAT into a buffer.
2. The plugin searches the buffer for the `DDS ` signature.
3. It compares width, height, FourCC and the number of mip levels.
4. It computes the SHA-256 of the **pixels** — the data after the 128-byte
   DDS header.
5. If the hash matches a known original, it copies the Ukrainian DDS of the
   same size in its place. All other bytes of the resource stay unchanged.

The hash does not cover the header because the engine modifies the DDS flags
in memory without touching the image: with a whole-file hash, unchanged
images were not recognized. The UAP entry key is
`UKRAINIAN/TEXTURES/<pixel SHA-256>.DDS`, so a single entry covers every copy
of the image across scenes (9 images → 21 containers).

If another mod has already changed the pixels of this texture, the hash does
not match and the plugin leaves it alone. The mechanism needs the whole DDS
in a single buffer; in practice that is how the engine reads it.

## Checks

| Check | Result |
|---|---|
| The same C++ replacement code on the original GSC files | 21/21 byte-identical to the verified graphics release |
| Repeated replacement on an already translated buffer | bytes do not change |
| Pixels changed by another mod | replacement is skipped |
| Changed header flags with the same pixels | replacement works |
| Missing or corrupted UAP | the game's functions stay original |

The logo, the subtitle, the main menu and the «АБВ» board in the character
editor were inspected live. The splash screen replacement is confirmed by the
loading log. The Venice signs, the castle panel and the college illustration
were verified byte-for-byte at the container level; a separate live look at
these scenes is among the things to do during a full playthrough.

The full evidence is in the author's research archive.
