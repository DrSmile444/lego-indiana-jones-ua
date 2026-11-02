# How the translation was built

This page explains how the Ukrainian localization was made: where the words
come from, who did what, how every string was checked and why some decisions
are the way they are. Technical details are in
[architecture.md](architecture.md) and in the [research](research/fonts.md)
section.

## In short

- The translation is not a machine-translation pass. Every string was
  translated in the context of where it appears in the game, checked against
  the glossary and proofread by the author.
- The technical side (formats, memory addresses, the plugin) was researched
  from scratch: there are no official tools for translating the game.
- The AI assistant was a tool for research and drafts. Decisions,
  proofreading and in-game testing are the author's.
- Nothing is claimed without verification: if something has not been
  checked, that is stated explicitly.

## Who did what

The project was made by one person with AI assistants (Claude Code, Codex).
We say so openly: it is honest, and it is how we managed to get, in a few
weeks, from "the game doesn't know the letter ї" to a complete translation.

| Author | AI assistant |
|---|---|
| The project idea and every decision: what to translate, how to install, what to release | Research into the `.FNT`, UAP, DDS and save formats |
| Glossary and dictionary, cultural adaptations («Валєра» (Valera), «Пластун» (Plastun), «круглики» (kruhlyky — the studs currency)) | Finding addresses and functions in the game's memory, analyzing crash dumps |
| Proofreading every string, style and terminology edits | Unpacking resources, texture inventory, OCR |
| Testing in the live game: playthroughs, screenshots, bug hunting | Translation drafts based on the glossary and context |
| Graphics: the logo, texture lettering, manual glyph tuning | Tools: builders, DXT encoders, tests, the plugin |
| Identifying the Franklin Gothic Medium font and its render parameters | Documenting the research and checks |

An important consequence: almost all of the font bugs described in
[fonts.md](research/fonts.md) were found by the author in the live game.
Automated byte-level checks did not see them.

## The path of a single string

```text
 String ID         where it is in game      glossary             translation
 ┌────────┐       ┌──────────────┐       ┌────────────┐       ┌──────────┐
 │ 151    │──────>│ character    │──────>│ team-      │──────>│ «Валєра» │
 │ Jungle │       │ shop, short  │       │ approved?  │       │          │
 │ Guide  │       │ name         │       │ yes/no     │       │          │
 └────────┘       └──────────────┘       └────────────┘       └────┬─────┘
                                                                   │
                         ┌─────────────────────┐       ┌───────────v──────┐
                         │ live check in the   │<──────│ author proofread:│
                         │ game: fits, font,   │       │ style, gender,   │
                         │ context             │       │ tokens [..], %d  │
                         └─────────────────────┘       └──────────────────┘
```

1. **ID.** Every `ENGLISH.TXT` line has a numeric ID, `TRC.CSV` rows have
   text labels, and the PC menu has its own IDs. The translation is stored by
   ID in `translations/*.json`; the repository contains no complete English
   game files, and the structure of the strings (IDs, service tokens) is
   described by the index in `index/`.
2. **Context.** Where the string appears: a menu, a hint, a name in the shop,
   a level title. That determines length, grammatical gender, case and tone.
   For example, "Posted" in the game is a parcel status, so it becomes
   «Відправлено» ("sent"), not «Опубліковано» ("published").
3. **Glossary.** `translations/glossary.json` holds names, artifacts, places,
   game terms and a confidence level for each: `high`, `medium`,
   `low-proposal`, `team-approved`.
4. **Translation.** The AI assistant prepared a draft from the glossary and
   context; the author accepted, edited or rewrote it.
5. **Proofreading.** The author checked style and terminology. The automated
   check (`python -m ua validate`) makes sure no IDs, service tokens `[...]`
   or `%d` are lost and that every character exists in the font.
6. **Live check.** The string has to be seen in the game: does it fit, is it
   cut off, does every letter render correctly.

## Glossary and sources

- **The official Ukrainian dub** of the trilogy (ICTV, TV+ studio): «У
  пошуках втраченого ковчега» (*Raiders of the Lost Ark*), «Храм Долі»
  (*Temple of Doom*), «Останній хрестовий похід» (*The Last Crusade*).
- **Ukrainian Wikipedia**: names of characters, artifacts and places (Меріон
  Ревенвуд — Marion Ravenwood, Малюк — Short Round, Салла — Sallah, Беллок —
  Belloq, Ковчег Заповіту — the Ark of the Covenant, палац Панкот — Pankot
  Palace).
- **There are no Ukrainian translations of Indiana Jones books**, so this is
  not a skipped step but an empty niche.
- **No established Ukrainian terminology for LEGO games** (Studs, Free Play,
  Minikit) could be found publicly. Such terms are reasoned proposals and are
  marked as such in the glossary.
- Third-party Cyrillic localizations were **not used** as a translation
  source. Technically, the only thing used was the atlas of a third-party
  Cyrillic font patch, as the base for Font 1.

Cultural adaptations are described separately: [research/cultural-adaptations.md](research/cultural-adaptations.md).

## How it was tested

**The live game.** Browser automation is no help for a native Win32 game.
The test loop looked like this: close the game → update the files → launch
through Steam → reach the right screen → screenshot → compare. For fonts,
the author temporarily replaced «Нова гра» ("New Game") with a test string
containing all eight new letters side by side, to see them in one word.

**Process memory.** A separate tool reads the memory of the running game
(without changing anything) and confirms that our strings are really there:
598/598 main strings, 194/194 CSV values, 38/38 PC strings.

**Tests.** Formats, the string index, font structure, the baseline, the
runtime targeting characters, the x86 editor adapters, DDS replacement on the
original containers, behavior without a UAP and with a corrupted UAP.

**Game integrity.** After installation and rollback, the SHA-256 of the EXE
and DAT files must match the original.

**Honest status.** Every version stated separately what had been verified and
what had not. For example, a full start-to-finish playthrough is not yet
complete, which is why the feedback channels are on the first screen of the
README.

## From 0.1.0 to 1.1.10

| Version | What was discovered or done |
|---|---|
| 0.1.0 | All the text and 8 letters in the main font; the game had to be unpacked |
| 0.1.1–0.1.2 | The logo and 9 textures with lettering |
| 0.1.3 | Fixed Font 2 and the baseline of the gamepad icons |
| 0.1.4 | The PC menu from the EXE via pointer replacement in memory |
| 0.1.5 | Editorial pass: «круглики» (kruhlyky — studs), «Бонуси» (Extras), hints |
| 0.1.6–0.1.7 | UAP: the original DAT files stay, the package shrank from 182 MB to 2 MB |
| 0.1.8 | The official Ultimate ASI Loader and an ASI plugin |
| 0.1.9 | Cultural adaptations of names |
| 0.1.10 | Targeting reticle, UTF-8 in the editor, «Форелька» (Forelka) and «Льоля» (Lolia) as custom character names |
| 1.1.10 | First public release, new reproducible repository |

Details of every version are in [CHANGELOG.md](../../CHANGELOG.md).

## Principles worth keeping

- **Do not modify game files on disk.** Everything is substituted in memory,
  and deleting three files restores the original.
- **Do not ship game resources.** Git holds only our text, our graphics
  layers and our glyphs; complete resources are built from your own copy of
  the game.
- **Verify before changing.** The plugin checks the EXE, the function bytes
  and the package; at the slightest mismatch it does nothing.
- **A hypothesis is not a fact.** Several early assumptions (loose files on
  top of DAT, a "magic" value in the FNT header, the plugin being to blame for
  the pause before cutscenes) were disproved by experiments. A conclusion is
  written down only after it has been verified.
