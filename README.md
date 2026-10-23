# Yakuza 0 stuck Pocket Circuit parts fix

Fixes Yakuza 0 and Yakuza 0 Director's Cut (PC / Steam) saves where Pocket Circuit parts
(tires, motors, gears, ...) occupy slots in **Equipment > Weapon** or in the weapon box and
can't be discarded.

## Usage

Requires Python 3. Pass the folder that holds your saves; the script fixes every save in it
(`SaveData*.sav` and `SaveData*.clr`), in place:

```
python3 y0_fix_stuck_parts.py <save folder> --dry-run   # just report what it finds
python3 y0_fix_stuck_parts.py <save folder>             # fix all saves
```

Save folders:

| Game | Windows | Linux (Proton) |
|------|---------|----------------|
| Yakuza 0 | `C:\Program Files (x86)\Steam\userdata\<steam id>\638970\remote\` | `~/.local/share/Steam/userdata/<steam id>/638970/remote/` |
| Yakuza 0 Director's Cut | `%APPDATA%\SEGA\Yakuza0_DirectorsCut\Steam\<steam id>\` | `~/.local/share/Steam/steamapps/compatdata/2988580/pfx/drive_c/users/steamuser/AppData/Roaming/Sega/Yakuza0_DirectorsCut/Steam/<steam id>/` |

The script recognises both games' saves by their header, so a folder can hold either kind.
Anything it doesn't recognise (such as `system.sys`) is left alone.

Before changing anything, the script copies every file that needs fixing into a new folder
next to the save folder (for example `remote_backup_20261023-231500`) and checks the copies.
It never overwrites an existing backup and does nothing if a backup fails.

### Loading the fixed save

Start the game and leave it running (at the title screen or in game), run the script (or
copy a fixed file over the save, keeping its name), then load that save in the game. This
is the flow that worked for us when copying a fixed file by hand; the folder mode of the
script does the same replacement but has not itself been tried in game. We haven't tested
replacing saves while the game is closed, where Steam Cloud might sync an older copy over
them, so disable Steam Cloud for the game if you do that.

### Converting to Director's Cut

If you plan to convert a Yakuza 0 save to Director's Cut (for example with
[this converter](https://github.com/kamikazziee/Yakuza0-DirectorsCutSaveConverter)), **fix the
Yakuza 0 save first, then convert it**. The conversion copies the stuck parts along with
everything else, but a save that was fixed before conversion converts cleanly.

## Command line options

```
python3 y0_fix_stuck_parts.py [options] path
```

| Option | Applies to | Description |
|--------|-----------|-------------|
| `path` | both | A **folder**: every `SaveData*.sav` / `SaveData*.clr` in it is fixed in place, with a backup first. Or a single **save file**: a fixed copy is written next to it (see below). |
| `--dry-run` | both | Only report which stuck parts were found. Nothing is written and no backup is made. |
| `--backup-dir PATH` | folder | Put the backups in `PATH` instead of `<save folder>_backup_<timestamp>` (next to the save folder). The folder is created if needed. If a file with the same name is already there, the script stops without changing anything. |
| `--in-place` | file | Overwrite the file instead of writing a copy. A `<file>.bak` backup is made first; if it already exists, the script stops. |
| `-o PATH`, `--output PATH` | file | Write the fixed copy to `PATH` instead of `<file>.fixed.sav`. |
| `--extra-id ID` | both | Also remove records with this item ID (decimal or hex, e.g. `0x265`). Can be given several times. The 140 Pocket Circuit IDs are always included. |
| `-h`, `--help` | | Show the built-in help. |

`--in-place` and `-o` are rejected with a folder (folders are always fixed in place), and
`--backup-dir` is rejected with a single file.

Exit codes: `0` on success (including "nothing to fix"), `1` if the script stopped because of
an error (a single file that isn't a recognised save, a backup conflict, no saves in the
folder), `2` for invalid options. In folder mode, files that aren't recognised saves are
reported and skipped without failing.

Examples:

```
# Preview, then fix, every save in a folder
python3 y0_fix_stuck_parts.py ~/.local/share/Steam/userdata/123456/638970/remote --dry-run
python3 y0_fix_stuck_parts.py ~/.local/share/Steam/userdata/123456/638970/remote

# Keep the backups somewhere specific
python3 y0_fix_stuck_parts.py <save folder> --backup-dir ~/y0-backups

# One file: writes SaveData0002.fixed.sav and leaves SaveData0002.sav alone
python3 y0_fix_stuck_parts.py SaveData0002.sav

# One file, overwriting it (SaveData0002.sav.bak is kept)
python3 y0_fix_stuck_parts.py SaveData0002.sav --in-place
```

## How it works

The save is an unencrypted file with fixed offsets and no checksum that we found. Each
inventory is an array of 16-byte item records; the first two bytes are the item ID.
Pocket Circuit parts belong only in Kiryu's own "Pocket Circuit" list, one record per part
type. The script scans every other inventory (item, weapon, gear, valuables and crafting
inventories and boxes, for both Kiryu and Majima) and zeroes any record whose ID is a
Pocket Circuit item. Zeroing a record is what the game does when you discard an item. No
other bytes are changed.

**Director's Cut:** a Director's Cut save is a Yakuza 0 save with a different header: the
magic changes from `YZFH` to `YZF2` and 0xC0 extra bytes are inserted after the first 0x38
bytes, so every offset moves by 0xC0 (the file is 167,912 bytes instead of 167,720). The
Director's Cut item list is identical to Yakuza 0's, so the same IDs apply. The script
refuses a file whose size doesn't match its header or whose item IDs fall outside the game's
item range, rather than guessing at an unknown layout.

## Credits

- Yakuza 0 is (c) SEGA. The 140 Pocket Circuit item IDs in the script (`pokecir_*`: IDs
  `0x23c-0x293`, `0x3ad-0x3b5`, `0x3e0-0x3e9`, `0x436-0x44d`, `0x465-0x46d`) and their internal
  names come from the game's own item list (`item.uni` in `media/data/bootpar/boot.par`).
  This project is not affiliated with or endorsed by SEGA or RGG Studio.
- For the full item list (English names, types, limits) and a description of the save layout,
  see [apocalyptech/y0-cli-save](https://github.com/apocalyptech/y0-cli-save)
  ([`itemregistry.py`](https://github.com/apocalyptech/y0-cli-save/blob/main/y0/itemregistry.py),
  [`savegame.py`](https://github.com/apocalyptech/y0-cli-save/blob/main/y0/savegame.py)).
- The Director's Cut save format (header size, extension size, file layout) comes from
  [kamikazziee/Yakuza0-DirectorsCutSaveConverter](https://github.com/kamikazziee/Yakuza0-DirectorsCutSaveConverter),
  a converter from Yakuza 0 saves to Director's Cut saves.
- This script contains none of those projects' code; they were used as references.

## Caveats

- Tested on one Yakuza 0 Steam save (`Yakuza0.exe` SHA-256 `b3c6c144...`). Removing the stuck
  parts from the weapon inventory and from the weapon box was confirmed in game.
- A corrupted Yakuza 0 save keeps its stuck parts when it is converted to Director's Cut.
  Converting a save that was fixed first gives a clean Director's Cut save (confirmed). The
  script's own Director's Cut support, for cleaning a save that is already converted, follows
  the layout used by the converter above and has only been tested on files built the same way,
  not on a real Director's Cut save.
- Keep your own backup of the save folder too. Use at your own risk.

## License

[MIT](LICENSE)
