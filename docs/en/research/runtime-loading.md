# Loading the translation at runtime: from an unpacked game to ASI

This page describes how the translation gets into the game, which engine
functions were found for this, and how the delivery method evolved from 0.1.0
to 1.1.10. For the overall picture of the modules, see
[architecture.md](../architecture.md).

## Stage 1: an unpacked game (0.1.0–0.1.5)

The project's early hypothesis: the game reads files from `STUFF/TEXT/` on
top of `GAME.DAT`. The first attempt to install the translation that way
changed nothing. The actual behavior: the engine reads plain files **only
when the corresponding DAT is missing from disk**. So the early versions
required unpacking all four DAT files into the game folder (tens of thousands
of files, several gigabytes), renaming the archives to
`*.DAT.original_backup` and laying the translation on top. The package
weighed 182 MB, and installation was inconvenient and risky.

## Stage 2: UAP and read interception (0.1.6–0.1.7)

The idea: keep the original DAT files and serve the needed files to the engine
from memory. To do that, the functions of the resource subsystem were found by
disassembly (addresses for the Steam EXE with image base `0x400000`):

| VA | Role |
|---|---|
| `0x6B44F0` | open a resource: from DAT or by file path |
| `0x6B46D0` | existence check |
| `0x6B4750` | size by path |
| `0x6B7440` | load a whole resource (with a direct DAT read branch) |
| `0x6B0250` | size of an open resource |
| `0x6AA040` | open a memory buffer as a resource (memory stream) |
| `0x6B55A0` | read |
| `0x6B04C0` | seek |
| `0x6B38F0` | close |

The plugin places x86 detours on these functions. For known paths
(`STUFF/TEXT/ENGLISH.TXT`, fonts, credits) it creates **the engine's own
memory stream** over the data from the UAP, so the game reads them with its
own functions. All other resources pass through a trampoline to the original
code.

Two findings without which this would not have worked:

- **The CSV was read bypassing the open call.** A prototype with three hooks
  already showed Ukrainian main text and font, but `TRC.CSV` stayed in
  English. The cause was a separate direct DAT read branch in `0x6B7440`. A
  dedicated hook was added for that function.
- **Size off by one byte.** The engine's memory stream stores an inclusive
  end, and `0x6B0250` returns `end − start`. For our buffers the size is
  corrected to the length of the UAP entry; other handles are left alone.

The engine has a pool of 20 slots for buffer streams. If the pool is
exhausted, the plugin logs it and falls back to the stock open.

Version 0.1.7 added DDS replacement in the read buffer (function `0x6B55A0`,
stolen instructions `51 8B 44 24 08`). Details are in [textures.md](textures.md).

### Safeguards

Before making any change, the plugin checks:

- the SHA-256 of `LEGOIndy.exe` (`c12f7348…332e5e5fd`);
- the prologue bytes of every function it hooks;
- the SHA-256 of every UAP entry.

If anything at all does not match, the translation is not enabled and the
game runs as the original. This is covered by tests with a missing and a
corrupted UAP: all six functions and 76 PC pointers stay unchanged.

## Stage 3: the ASI plugin (0.1.8 onward)

In 0.1.6–0.1.7 our `dinput8.dll` was a proxy library: it provided the
DirectInput exports, loaded the system library and forwarded calls to it.
The downside: the translation could not coexist with another mod that also
needs `dinput8.dll`.

Since 0.1.8, `dinput8.dll` is the official, unmodified
[Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader)
9.7.4, and the translation is the `scripts/UKRAINIAN.asi` plugin. Before
choosing it, we checked the code of the v9.7.4 tag specifically, not the
master branch README:

- after loading an ASI, the loader calls the undecorated `InitializeASI`
  export;
- with the default `DontLoadFromDllMain=1`, plugin startup is deferred until
  calls from the game, and the loader accounts for the Steam `.bind`
  protection section.

Our plugin:

- only records its module handle in `DllMain`; all the work happens in
  `InitializeASI`;
- initializes exactly once via `InitOnceExecuteOnce`, even if another mod
  calls `InitializeASI` again;
- pins itself in memory until the process exits, because the game's tables
  and the trampolines reference its code and data;
- looks for `UKRAINIAN.uap` next to itself, not in the working directory;
- writes its log to `scripts/legoindy-ua-pc.log`;
- imports only `KERNEL32` and `bcrypt` (SHA-256) and exports only
  `InitializeASI`.

| 0.1.8 check | Result |
|---|---|
| Main text in memory | 598/598 |
| CSV in memory | 194/194 |
| PC strings | 38/38; 76 source and 38 active pointers |
| UAP streams (read/size/seek/EOF/close, 32 reopenings) | 21/21 |
| A second, independent ASI | loaded and ran alongside ours |
| Repeated `InitializeASI` call | one initialization |
| UAP missing or corrupted | original game |
| Unknown EXE | skipped without patches |

### Compatibility with other mods

ASI removes the conflict over the `dinput8.dll` name, but not every conflict:

- `ENGLISH.TXT`, `TRC.CSV` and the fonts from the UAP are replaced as
  **whole files**. Text mods (for example, Archeologist Edition changes names
  in `english.txt`) will need merging.
- A mod that changes the same DDS takes priority: the plugin will not
  recognize the changed pixels and will skip the replacement.
- Loose files in `CHARS/` or `LEVELS/` have no effect while the DAT files are
  active; such mods need an unpacked game or a redirector.
- Any change to the EXE on disk, including an LAA patch, changes its SHA-256,
  and the plugin disables itself.

Combinations with third-party mod packs have not been tested live.

## System language: English (United Kingdom) or English (United States)

While testing on the Steam Deck, the author noticed that some text stayed in
English, even though the same package worked fully on a Windows PC. The cause
turned out to be neither memory addresses nor Proton as such.

- `LEGOIndy.exe` determines the language via `GetUserDefaultLangID`. The
  binary separately contains `stuff\text\american.txt`.
- For English (United States), the game first reads `ENGLISH.TXT` and then
  `AMERICAN.TXT` on top of it. This is an overlay of only 18 lines with
  American spelling ("Artifact", "Theater", the shovel hints and so on). In
  addition, the game takes the AMERICAN column of `TRC.CSV` (all the save and
  load dialogs, "Press a key or controller button…") and
  `AMERICAN_CREDITS.TXT` instead of our credits.
- Proton on the Steam Deck runs as en-US by default. On the author's PC the
  system language is different, so the game picked the British variant and
  everything was translated. The launch option `LANG=en_GB.UTF-8` did not help
  on the Deck, so it does not affect language selection under Proton.

**Fix (1.1.10):** the plugin serves any file that is in the package, so the
native code did not need to change. The translated `AMERICAN.TXT` and
`AMERICAN_CREDITS.TXT` were added to `UKRAINIAN.uap`, and `TRC.CSV` gets the
translation in both English columns, ENGLISH and AMERICAN. The templates of
the American files are taken once from the extracted game
(`manifests/game-files.json`); in future releases they will already be in the
baseline package. The ESRB rating badge on the American splash screen was
deliberately not repainted: it is the rating organization's mark. The text of
the screen itself (T2748) is translated.

## A diagnostic lesson: the pause before cutscenes

After switching to UAP, the author noticed a pause of about 15 seconds before
cutscenes. Suspicion logically fell on the plugin. Control runs showed
otherwise:

1. Without `UKRAINIAN.asi` the pause remained.
2. Without `dinput8.dll` (the process using the system `DINPUT8.dll`) the
   pause remained.
3. A comparison with the Steam depot manifest revealed 279 missing files from
   the `audio` folder (883 MB: cutscene OGGs, music). They had been removed by
   mistake by an old migration script from the unpacked-game era.

After the audio was restored (Steam integrity check), cutscenes worked
normally again and the translation was put back. The conclusion that became
part of the process: the developer installation tools verify the checksums of
the game files that must not be touched (EXE, DAT, `binkw32.dll`, the
`audio` folder) before and after copying.

For quick testing during that diagnosis there was a mode for automatically
completing cutscenes (following an open community guide, the predicate at
`0x6A0250` was changed). It remained an experiment and is not part of the
release.

The full evidence is in the author's research archive.
