# Yakuza 0 stuck Pocket Circuit parts fix

Fixes Yakuza 0 (PC / Steam) saves where Pocket Circuit parts (tires, motors, gears, ...)
occupy slots in **Equipment > Weapon** or in the weapon box and can't be discarded.

## Usage

Requires Python 3. Your saves are in Steam's `remote` folder:

- Linux (Proton): `~/.local/share/Steam/userdata/<steam id>/638970/remote/`
- Windows: `C:\Program Files (x86)\Steam\userdata\<steam id>\638970\remote\`

Pass that folder to the script. It fixes every save in it (`SaveData*.sav` and
`SaveData*.clr`), in place:

```
python3 y0_fix_stuck_parts.py <save folder> --dry-run   # just report what it finds
python3 y0_fix_stuck_parts.py <save folder>             # fix all saves
```

Before changing anything, the script copies every file that needs fixing into a new folder
next to the save folder (for example `remote_backup_20261023-231500`) and checks the copies.
It never overwrites an existing backup and does nothing if a backup fails. Use
`--backup-dir PATH` to choose another backup location. Saves without stuck parts, and
other files in the folder, are left alone.

To fix one file instead, pass the file: it writes `<name>.fixed.sav` and leaves the original
alone (add `--in-place` to overwrite it, keeping a `.bak`).

### Loading the fixed save

Start the game and leave it running (at the title screen or in game), run the script (or
copy a fixed file over the save, keeping its name), then load that save in the game. This
is the flow that worked for us when copying a fixed file by hand; the folder mode of the
script does the same replacement but has not itself been tried in game. We haven't tested
replacing saves while the game is closed, where Steam Cloud might sync an older copy over
them, so disable Steam Cloud for the game if you do that.

## How it works

The save is an unencrypted file with fixed offsets and no checksum that we found. Each
inventory is an array of 16-byte item records; the first two bytes are the item ID.
Pocket Circuit parts belong only in Kiryu's own "Pocket Circuit" list, one record per part
type. The script scans every other inventory (item, weapon, gear, valuables and crafting
inventories and boxes, for both Kiryu and Majima) and zeroes any record whose ID is a
Pocket Circuit item. Zeroing a record is what the game does when you discard an item. No
other bytes are changed.

## Credits

- Yakuza 0 is (c) SEGA. The 140 Pocket Circuit item IDs in the script (`pokecir_*`: IDs
  `0x23c-0x293`, `0x3ad-0x3b5`, `0x3e0-0x3e9`, `0x436-0x44d`, `0x465-0x46d`) and their internal
  names come from the game's own item list (`item.uni` in `media/data/bootpar/boot.par`).
  This project is not affiliated with or endorsed by SEGA or RGG Studio.
- For the full item list (English names, types, limits) and a description of the save layout,
  see [apocalyptech/y0-cli-save](https://github.com/apocalyptech/y0-cli-save)
  ([`itemregistry.py`](https://github.com/apocalyptech/y0-cli-save/blob/main/y0/itemregistry.py),
  [`savegame.py`](https://github.com/apocalyptech/y0-cli-save/blob/main/y0/savegame.py)).
  This script contains none of that project's code; it was used as a reference.

## Caveats

- Tested on one Steam save (`Yakuza0.exe` SHA-256 `b3c6c144...`). Removing the stuck parts
  from the weapon inventory was confirmed in game. In that save there were also 8 stuck
  parts in Kiryu's weapon box, which the script removes but which have not been tested in
  game yet.
- Keep your own backup of the save folder too. Use at your own risk.

## License

[MIT](LICENSE)
