---
title: FAQ
description: Antivirus flags dinput8.dll or the .asi file, the game is still in English, saves, other game versions, switching back to English — answers to common questions about the Ukrainian localization.
---

## Is there an English translation?

No — the game is already in English. This project translates it **into Ukrainian**. The English version of this site exists so that modders and curious players outside Ukraine can read how the localization works.

## My antivirus flags `dinput8.dll` or `UKRAINIAN.asi`. Is it a virus?

No, but the reaction is understandable. `dinput8.dll` is [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) by ThirteenAG, an open-source plugin loader used by thousands of PC game mods. The game looks for the system library `dinput8.dll` and finds this one first, in its own folder; the loader then picks up `*.asi` plugins from the `scripts/` folder. Our `UKRAINIAN.asi` serves Ukrainian text, fonts and textures from `UKRAINIAN.uap` while the game runs, without writing anything to the game files.

That exact technique — a stand-in library next to the EXE that hooks into the game process — is often flagged as suspicious by antivirus heuristics, even when the code is harmless.

How to check for yourself:

1. Download only from this project’s [GitHub Releases](https://github.com/DrSmile444/lego-indiana-jones-ua/releases).
2. Compare the checksum with `SHA256SUMS` from the same release:

   ```powershell
   Get-FileHash .\lego-indiana-jones-ua-1.1.10.zip -Algorithm SHA256
   ```

3. The plugin source code and build scripts are open in the [repository](https://github.com/DrSmile444/lego-indiana-jones-ua).

If the antivirus has already quarantined a file, add the game folder to its exclusions and unpack the archive again.

## I unpacked everything, but the game is still in English

- Check that `dinput8.dll` and the `scripts/` folder sit **next to `LEGOIndy.exe`**, not in a nested folder such as `lego-indiana-jones-ua-1.1.10/`.
- The game language must be English — the localization replaces exactly that.
- Your antivirus may have silently removed `dinput8.dll` or the `.asi` file — see the question above.
- On Steam Deck, if the translation doesn’t appear, add the launch option `WINEDLLOVERRIDES="dinput8=n,b" %command%` — see [installation](/lego-indiana-jones-ua/en/install/#steam-deck).

## Will it break my saves?

No. The localization changes neither the EXE, nor the DAT archives, nor your saves: the translation is injected into memory while the game runs. After uninstalling, your saves work as before.

## Does it work with GOG or other versions?

It is verified on the Steam version for Windows and on Steam Deck. GOG has not been tested yet — if you try it, [let us know](/lego-indiana-jones-ua/en/feedback/) how it went. Console versions are not supported.

## Does it work with other mods?

Yes. The package only adds its own files (`scripts/UKRAINIAN.*`) and uses the standard ASI Loader, so it runs alongside other ASI plugins. It doesn’t repack or replace game archives, so there are no file conflicts with other mods.

## How do I switch back to English?

Delete the localization files — see [“Uninstalling”](/lego-indiana-jones-ua/en/install/#uninstalling). There is no need to reinstall the game.

## Why «круглики», «Бонуси», «Валєра» and «Пластун»?

We translated so that the game sounds natural in Ukrainian rather than like a calque. Studs became «круглики» (kruhlyky, “little round ones”) and the Extras menu became «Бонуси» (Bonuses) rather than “Cheats”, the Jungle Guide became «Валєра» (Valera) and the Boy Scout became «Пластун» (Plastun, the Ukrainian word for a scout). Every decision is explained in [cultural adaptations](/lego-indiana-jones-ua/en/adaptations/), and all terms are in the [glossary](/lego-indiana-jones-ua/en/glossary/).

## Is this an official translation?

No. It is an unofficial fan project, not affiliated with the LEGO Group, Lucasfilm, TT Games or Warner Bros. You need your own legal copy of the game.

## I found a mistake in the translation

Thank you! Here’s [how to report it](/lego-indiana-jones-ua/en/feedback/).
