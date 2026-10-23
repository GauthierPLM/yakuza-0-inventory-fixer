# Yakuza 0 stuck Pocket Circuit parts fix

Fixes a Yakuza 0 (PC / Steam) save where Pocket Circuit parts (tires, motors, gears, ...)
occupy slots in **Equipment > Weapon** or in the weapon box and can't be discarded.

## Usage

Requires Python 3.

1. Back up your save folder:
   `<Steam>/userdata/<steam id>/638970/remote/`
   (On Linux with Proton: `~/.local/share/Steam/userdata/<steam id>/638970/remote/`.)
2. Run the script on the slot you want to fix:

   ```
   python3 y0_fix_stuck_parts.py SaveData0002.sav --dry-run   # see what it finds
   python3 y0_fix_stuck_parts.py SaveData0002.sav             # writes SaveData0002.fixed.sav
   ```

3. Replace the save with the fixed file. This is the method that worked for us:
   1. Start the game and leave it running (at the title screen or in game).
   2. Copy the fixed file over the save in the `remote` folder, renamed to the original
      name (for example `SaveData0002.sav`).
   3. Load that save in the game. It loads the fixed version.

   Replacing the file while the game is running avoided any need to disable Steam Cloud
   for us. We haven't tested replacing it while the game is closed, where Steam Cloud
   might sync an older copy over it, so disable Steam Cloud for the game if you do that.

Options: `--output PATH`, `--in-place`, `--dry-run`, `--extra-id 0xNNN` (also remove records
with this item ID).

## How it works

The save is an unencrypted file with fixed offsets and no checksum that we found. Each
inventory is an array of 16-byte item records; the first two bytes are the item ID, which is
the item's index in the game's item list (`item.uni` inside `media/data/bootpar/boot.par`).
The inventory layout is documented by
[apocalyptech/y0-cli-save](https://github.com/apocalyptech/y0-cli-save).

Pocket Circuit parts belong only in Kiryu's own "Pocket Circuit" list (offset `0xD86C`, one
record per part type). The script scans every other inventory (item, weapon, gear, valuables
and crafting inventories and boxes, for both Kiryu and Majima) and zeroes any record whose
ID is one of the game's 140 Pocket Circuit items (`pokecir_*`: IDs `0x23c-0x293`,
`0x3ad-0x3b5`, `0x3e0-0x3e9`, `0x436-0x44d`, `0x465-0x46d`). Zeroing the record is what the
game does itself when you discard an item. No other bytes are changed.

## Caveats

- Tested on one Steam save (`Yakuza0.exe` SHA-256 `b3c6c144...`). Removing the stuck parts
  from the weapon inventory was confirmed in game. In that save there were also 8 stuck
  parts in Kiryu's weapon box, which the script removes but which have not been tested in
  game yet.
- Always keep a backup. Use at your own risk.
