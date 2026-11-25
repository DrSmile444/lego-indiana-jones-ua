# Gamepad buttons four times sharper

The game does not draw the gamepad buttons (A B X Y, LB RB, LT RT, D-pad,
arrows) with the main font. It uses a separate button font. The atlas of this font
is now x4, like Font 1 and Font 2, in the same style as the game.

## Which font the game shows

- The EXE has only one path to the button font: `stuff	extuttons_PC`. The
  engine adds `_PC.FNT`, as it does for `stuff	extont` → `FONT_PC.FNT`. So
  the game loads `STUFF/TEXT/BUTTONS_PC_PC.FNT`. The plugin log confirms it:
  `UAP OPEN: STUFF/TEXT/BUTTONS_PC_PC.FNT`.
- `BUTTONS_PC_PC.FNT`: a 256×128 DXT5 atlas, 9 mip levels, cell height 36,
  18 metric records. Its pixels are the same as in `BUTTONS_PC.FNT` and
  `BUTTONS_360_PC.FNT`: these are the Xbox 360 buttons.
- The PC game does not load the PS2, PS3, PSP, Wii and NGC sets
  (`BUTTONS_*_PC.FNT`), so they stay unchanged.
- With a keyboard, the game writes the key name as text. The button icons
  appear when the player uses a gamepad.

## Where the new pixels come from

LEGO Star Wars III: The Clone Wars has the same set of buttons: the same
colors, gloss, letters and glyph order. Its atlas is 512×256 with a cell of 72
(`FRAMEWORK-DATA/GUI/FONT/BUTTONS_PC_NXG.FT2`). This is original work of the
studio at twice the size. No TT game has a 4× atlas.

1. `python -m ua extract --lsw3 "<LEGO Star Wars III folder>"` takes this FT2
   from the `GAME.DAT` of LEGO Star Wars III into `game/LSW3/` and checks the
   SHA-256 (`manifests/game-files.json`, `lsw3_files`). You can also set the game
   path with the `UA_LSW3_GAME` variable.
2. `python tools/fonts/upscale_buttons.py` enlarges the 2× atlas four more times
   with the Real-ESRGAN neural network (model `realesr-animevideov3`). The tool
   processes each glyph alone, with a transparent frame, so the ink does not
   spill into the next cell. Under the transparent pixels, the tool sets the
   color of the nearest ink, so the edge does not get darker. The result is
   `local/buttons/BUTTONS_PC_NXG_X4.png` (2048×1024).
3. The `full` level build (`ua/pipeline/buttons_hd.py`) shrinks this atlas by half (this is
   4× the atlas of our game). It puts each cell in the place of its glyph, by
   the glyph rectangle: center on center, then a shift of up to 4 pixels at 2×
   to the place where the cell, shrunk to 1×, is nearest to the game cell. If
   the mean error (RGBA, 0–255) is more than 16, the build stops.

The owner compared the options and chose Real-ESRGAN. A vector redraw did not
match the game style (thin outline, gloss). The models `realesrgan-x4plus` and
`x4plus-anime` gave ragged edges.

Mean error at 1× (2× original / x4 atlas):

| Glyph | Error | Glyph | Error |
|---|---|---|---|
| A | 11.5 / 8.5 | LT | 5.1 / 6.5 |
| B | 13.0 / 7.5 | RT | 5.4 / 7.1 |
| X | 9.7 / 5.1 | D-pad ×4 | 3.1–3.3 / 3.4–3.8 |
| Y | 9.3 / 10.3 | ◁ ▷ | 3.8 / 4.4–4.5 |
| LB | 3.5 / 4.1 | empty | 5.2 / 5.1 |
| RB | 3.4 / 4.2 | | |

The round buttons have the largest error, because the artist drew the 1× art
separately: the gloss and the shadow are already different in the 2× original.
For A, B, X and Y, the x4 atlas also goes through the "round buttons" step
below. The other glyphs of the x4 atlas against the 2× original: 0.8–4.8.

## Round buttons A, B, X, Y

After Real-ESRGAN, the tool processes the four round buttons (the first four
glyphs of the set) once more. The owner approved this step. The parameters are
in `assets/fonts/buttons.json`, section `round`; the file is the same in the
three repos.

1. Circle: the bounds of the pixels with alpha > 128 give the center and the
   radius r (the mean of the half-width and the half-height).
2. Letter: the bounds of the light pixels inside 0.75·r (alpha ≥ 200,
   HSV v > 170, s < 110) give the center of the letter.
3. The content is enlarged by a factor of 1 / (1 − 0.08) around the center of
   the circle. The letter goes to the center of the circle plus an optical
   correction in 2× pixels: A (0, 0), B (+2, 0), X (0, +6), Y (0, +1.5).
4. Alpha is multiplied by a smoothed disc of radius r, so the button edge is
   even and round.

The other glyphs do not change. The result matches the atlas that the owner
approved, pixel for pixel.

## Why the pixels are not in git

Repository rule ([approach.md](../approach.md)): git holds only our work, and the game assets are built from
your own copy of the game. The Real-ESRGAN atlas derives from an asset of
another game, so it lives in `local/buttons/`, and `manifests/inputs.json`
records its SHA-256. The tool is deterministic: two runs gave the
same file.

## How the plugin replaces the atlas

`BUTTONS_PC_PC.FNT` in the package has the same metrics and the 1× atlas. The
DDS header has the `UAHD` mark, k = 4 and slot 2 (`dwReserved1[0..2]`).
`native/asi/font_hd.h` has three slots: 0 is Font 1 (`UKRAINIAN/FONT_HD.DDS`),
1 is Font 2 (`UKRAINIAN/FONT2_HD.DDS`), 2 is the buttons
(`UKRAINIAN/BUTTONS_HD.DDS`, 1024×512, full mip chain). When the game creates a
texture with the mark, the plugin gives D3DX the large atlas and tells the game
the 1× size, so the UVs do not change.

## Check in the game

Without a gamepad, the game writes key names, so the test mode has a virtual
Xbox 360 gamepad. `VirtualPad=1` in `scripts/UKRAINIAN.test.ini` turns on three
things:

- DirectInput shows one more joystick, "XBOX 360 For Windows (Controller)"
  (VID 045E, PID 028E);
- XInput gamepad 0 is connected;
- the engine check "is this an XInput device?" (function `0x518560`, which
  looks for `IG_` through WMI) looks only at VID/PID in the test mode.

The buttons come from `scripts/screens/pad.txt`; `python tools/runtime/live.py
pad A` presses them without focus. After "A" on the first screen, the game
selects the gamepad and writes "Вибрати Ⓐ" and "Назад Ⓑ" in the menu.

Screenshot 2560×1440, the "Налаштування" menu, before and after:
`build/screens/buttons-indy.png` (the "before" frame is the same build with the
game `BUTTONS_PC_PC.FNT` without the mark). Plugin log:
`FONT HD: UKRAINIAN/BUTTONS_HD.DDS 1024x512 x4 texture for the 256x128 font atlas`.
