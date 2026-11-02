---
title: Install & uninstall
description: "How to install the Ukrainian localization of LEGO Indiana Jones: The Original Adventures — unpack the ZIP next to LEGOIndy.exe. How to verify checksums, set it up on Steam Deck and remove the translation completely."
---

The localization is a ZIP archive that you unpack straight into the game folder. It overwrites nothing: the original game files, `LEGOIndy.exe`, the DAT archives and your saves stay exactly as they were. The translation is injected into memory when the game starts.

:::note[The translation is Ukrainian]
Installing this package switches the game’s English text to **Ukrainian**. There is no English text to install — the game is already in English.
:::

## Requirements

- **LEGO Indiana Jones: The Original Adventures** for PC (Windows). Verified on the Steam version.
- Game language set to **English** (the Steam default): the localization replaces the English text specifically.
- The `lego-indiana-jones-ua-1.1.10.zip` archive from [GitHub Releases](https://github.com/DrSmile444/lego-indiana-jones-ua/releases).

| Game version | Status |
|---|---|
| Steam (Windows) | ✅ verified |
| Steam Deck | ✅ verified |
| GOG | ❔ not verified |

## Installation

1. **Download** the latest ZIP from [GitHub Releases](https://github.com/DrSmile444/lego-indiana-jones-ua/releases) (or with the button on the [home page](/lego-indiana-jones-ua/en/)).
2. **Open the game folder.** In Steam: right-click the game → “Manage” → “Browse local files”. Usually it is
   `C:\Program Files (x86)\Steam\steamapps\common\LEGO Indiana Jones The Original Adventures`.
3. **Unpack the archive into that folder**, next to `LEGOIndy.exe`. Afterwards it should contain:

   ```text
   LEGOIndy.exe
   dinput8.dll          ← ASI plugin loader
   scripts/
     UKRAINIAN.asi      ← the localization plugin
     UKRAINIAN.uap      ← resource package: text, fonts, textures
     UKRAINIAN/         ← plugin support files
   ```

4. **Launch the game** as usual. The main menu should now be in Ukrainian, with the new logo.

:::tip[Already using other ASI mods?]
If the game folder already has a `dinput8.dll` from Ultimate ASI Loader, keep yours: our plugin only needs the `scripts/` folder to be loaded. Copy just the contents of `scripts/`.
:::

## Verifying the archive (optional)

Every release on GitHub ships a `SHA256SUMS` file with checksums. In PowerShell:

```powershell
Get-FileHash .\lego-indiana-jones-ua-1.1.10.zip -Algorithm SHA256
```

The value must match the line for that file in `SHA256SUMS`. On Linux or Steam Deck: `sha256sum -c SHA256SUMS`.

## Steam Deck

Verified by the author on version 1.1.10. Installation is the same: unpack the archive into the game folder (Steam → ⚙ → “Manage” → “Browse local files” in Desktop Mode). If the game still starts in English, Proton did not load `dinput8.dll`. In that case open the game’s Properties → “Launch Options” and add

```text
WINEDLLOVERRIDES="dinput8=n,b" %command%
```

Proton reports the system language as English (United States). Starting with 1.1.10 the translation covers that locale as well, so nothing else needs to be configured.

## Updating

Close the game and unpack the new archive into the same folder, replacing the files. There is no need to remove the old version first.

## Uninstalling

Close the game and delete from the game folder:

- `scripts/UKRAINIAN.asi`
- `scripts/UKRAINIAN.uap`
- the `scripts/UKRAINIAN/` folder
- `dinput8.dll` — **only if** you have no other ASI mods that need it.

Don’t delete the whole `scripts/` folder if it contains files from other mods. The game will start in English again, and your saves keep working as before.

Something went wrong? See the [FAQ](/lego-indiana-jones-ua/en/faq/) or [get in touch](/lego-indiana-jones-ua/en/feedback/).
