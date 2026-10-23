#!/usr/bin/env python3
"""Remove stuck Pocket Circuit parts from Yakuza 0 and Yakuza 0 Director's Cut (PC/Steam) saves.

Some saves end up with Pocket Circuit car parts (tires, motors) occupying slots in
Equipment > Weapon and in the weapon box. They can't be discarded in game. This script
zeroes those records in the save file, which is what the game itself does when you
discard an item. Your real Pocket Circuit part list is not touched.

Usage:
    # Fix every save in a folder, in place. Each file that needs fixing is backed up first,
    # into a new folder next to the save folder (e.g. remote_backup_20261023-231500).
    python3 y0_fix_stuck_parts.py ~/.local/share/Steam/userdata/<id>/638970/remote

    # Same, but only report what would change (nothing is written, no backup is made)
    python3 y0_fix_stuck_parts.py <save folder> --dry-run

    # Fix a single file: writes SaveData0002.fixed.sav and leaves the original alone
    python3 y0_fix_stuck_parts.py SaveData0002.sav
    python3 y0_fix_stuck_parts.py SaveData0002.sav --in-place   # overwrite, keeping a .bak

Save locations:
    Yakuza 0:
        <Steam>/userdata/<steam id>/638970/remote/
    Yakuza 0 Director's Cut:
        %APPDATA%\\SEGA\\Yakuza0_DirectorsCut\\Steam\\<steam id>\\
        (Proton: <Steam>/steamapps/compatdata/2988580/pfx/drive_c/users/steamuser/
         AppData/Roaming/Sega/Yakuza0_DirectorsCut/Steam/<steam id>/)

Credits: Yakuza 0 is (c) SEGA. The item IDs below come from the game's own item list
(item.uni in media/data/bootpar/boot.par; identical in Director's Cut). This project is not
affiliated with SEGA or RGG Studio. For the full item list (names, types, limits) and the save
layout, see https://github.com/apocalyptech/y0-cli-save (y0/itemregistry.py, y0/savegame.py).
The Director's Cut save format (original save body behind an enlarged header) is from
https://github.com/kamikazziee/Yakuza0-DirectorsCutSaveConverter.
"""

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

# Yakuza 0 saves start with "YZFH" and are 167720 bytes. Director's Cut saves start with
# "YZF2": the same data, but with an extra DC_EXT_SIZE bytes inserted after the first
# BASE_HEADER_SIZE bytes, so every inventory offset below moves by DC_EXT_SIZE.
SAVE_SIZE = 167720
BASE_HEADER_SIZE = 0x38
DC_EXT_SIZE = 0xC0
FORMATS = {
    b"YZFH": ("Yakuza 0", SAVE_SIZE, 0),
    b"YZF2": ("Director's Cut", SAVE_SIZE + DC_EXT_SIZE, DC_EXT_SIZE),
}
# The game's item list has 1148 entries (IDs 0-1147); any larger ID means we are misreading.
MAX_ITEM_ID = 1147

# Save layout (see also github.com/apocalyptech/y0-cli-save, which documents it).
# Items are 16-byte records; the first 2 bytes (little endian) are the item ID.
RECORD_SIZE = 16

# (label, offset in a Yakuza 0 save, number of slots). Kiryu's own "Pocket Circuit" list at 0xD86C is where
# these parts belong, so it is not scanned. Everything else must not contain any.
INVENTORIES = [
    ("Kiryu item inventory", 0x7AAC, 20),
    ("Kiryu valuables", 0x7D3C, 25),
    ("Kiryu item box", 0x836C, 200),
    ("Kiryu weapon box", 0x9C6C, 200),
    ("Kiryu gear box", 0xB56C, 200),
    ("Kiryu weapon inventory", 0xCE6C, 15),
    ("Kiryu gear inventory", 0xD04C, 15),
    ("Majima item inventory", 0x7BEC, 20),
    ("Majima valuables", 0x805C, 25),
    ("Majima item box", 0x8FEC, 200),
    ("Majima weapon box", 0xA8EC, 200),
    ("Majima gear box", 0xC1EC, 200),
    ("Majima weapon inventory", 0xCF5C, 15),
    ("Majima gear inventory", 0xD13C, 15),
    ("Majima crafting materials", 0xD22C, 96),
]

# Every Pocket Circuit item in Yakuza 0 (c) SEGA: item IDs and internal names from the game's
# item list (item.uni in boot.par, all names "pokecir_*"). For the complete item list see
# https://github.com/apocalyptech/y0-cli-save/blob/main/y0/itemregistry.py
# None of these belong anywhere except Kiryu's own Pocket Circuit list.
PARTS = {
    0x23c: "r_motor", 0x23d: "t_motor", 0x23e: "motor_m",
    0x23f: "motor_ht", 0x240: "motor0", 0x241: "wheel0",
    0x242: "wheel1", 0x243: "wheel_test", 0x244: "wheel2",
    0x245: "gear0", 0x246: "battery0", 0x247: "pole0",
    0x248: "mass_dumper0", 0x249: "bumper0", 0x24a: "wheel_sp",
    0x24b: "roller_p", 0x24c: "roller_pg", 0x24d: "roller_a",
    0x24e: "roller_ap", 0x24f: "motor_power_01", 0x250: "motor_power_02",
    0x251: "motor_power_03", 0x252: "motor_power_04", 0x253: "motor_power_05",
    0x254: "motor_speed_01", 0x255: "motor_speed_02", 0x256: "motor_speed_03",
    0x257: "motor_speed_04", 0x258: "motor_speed_05", 0x259: "motor_middle_01",
    0x25a: "motor_middle_02", 0x25b: "motor_middle_03", 0x25c: "motor_middle_04",
    0x25d: "motor_middle_05", 0x25e: "motor_torque_01", 0x25f: "motor_torque_02",
    0x260: "motor_idaten_01", 0x261: "motor_idaten_02", 0x262: "slick_t_01",
    0x263: "slick_t_02", 0x264: "slick_t_03", 0x265: "slick_t_04",
    0x266: "slick_t_05", 0x267: "sponge_t_01", 0x268: "sponge_t_02",
    0x269: "sponge_t_03", 0x26a: "sponge_t_04", 0x26b: "sponge_t_05",
    0x26c: "spike_t_01", 0x26d: "spike_t_02", 0x26e: "spike_t_03",
    0x26f: "spike_t_04", 0x270: "spike_t_05", 0x271: "lowheight_t_01",
    0x272: "lowheight_t_02", 0x273: "lowheight_t_03", 0x274: "lowheight_t_04",
    0x275: "lowheight_t_05", 0x276: "barrel_t_01", 0x277: "barrel_t_02",
    0x278: "barrel_t_03", 0x279: "barrel_t_04", 0x27a: "barrel_t_05",
    0x27b: "gear_power_01", 0x27c: "gear_power_02", 0x27d: "gear_power_03",
    0x27e: "gear_power_04", 0x27f: "gear_power_05", 0x280: "gear_middle_01",
    0x281: "gear_middle_02", 0x282: "gear_middle_03", 0x283: "gear_middle_04",
    0x284: "gear_middle_05", 0x285: "gear_nomal_01", 0x286: "gear_nomal_02",
    0x287: "gear_nomal_03", 0x288: "gear_nomal_04", 0x289: "gear_nomal_05",
    0x28a: "gear_dash_01", 0x28b: "gear_dash_02", 0x28c: "gear_dash_03",
    0x28d: "gear_dash_04", 0x28e: "gear_dash_05", 0x28f: "gear_hsg_01",
    0x290: "gear_hsg_02", 0x291: "gear_hsg_03", 0x292: "gear_hsg_04",
    0x293: "gear_hsg_05", 0x3ad: "battery_tough", 0x3ae: "battery_speed",
    0x3af: "battery_light", 0x3b0: "battery_power", 0x3b1: "gear_hsp_01",
    0x3b2: "gear_hsp_02", 0x3b3: "gear_hsp_03", 0x3b4: "gear_hsp_04",
    0x3b5: "gear_hsp_05", 0x3e0: "roller_gum_01", 0x3e1: "stay_01",
    0x3e2: "stay_02", 0x3e3: "stay_03", 0x3e4: "suspenrion_01",
    0x3e5: "suspenrion_02", 0x3e6: "suspenrion_03", 0x3e7: "suspension_01",
    0x3e8: "suspension_02", 0x3e9: "suspension_03", 0x436: "roller_gum_02",
    0x437: "roller_gum_03", 0x438: "roller_gum_04", 0x439: "roller_gum_05",
    0x43a: "roller_hg_01", 0x43b: "roller_hg_02", 0x43c: "roller_hg_03",
    0x43d: "roller_hg_04", 0x43e: "roller_hg_05", 0x43f: "roller_hgsp_01",
    0x440: "roller_hgsp_02", 0x441: "roller_hgsp_03", 0x442: "roller_hgsp_04",
    0x443: "roller_hgsp_05", 0x444: "roller_double_01", 0x445: "roller_double_02",
    0x446: "roller_double_03", 0x447: "roller_double_04", 0x448: "roller_double_05",
    0x449: "roller_speed_01", 0x44a: "roller_speed_02", 0x44b: "roller_speed_03",
    0x44c: "roller_speed_04", 0x44d: "roller_speed_05", 0x465: "sticker_a",
    0x466: "sticker_b", 0x467: "sticker_c", 0x468: "sticker_d",
    0x469: "body_full_01", 0x46a: "body_race_01", 0x46b: "body_aero_01",
    0x46c: "body_spr_01", 0x46d: "body_mty_01",
}


SAVE_PATTERNS = ("SaveData*.sav", "SaveData*.clr")


def find_stuck(data, ids, shift):
    """Return the stuck records, or None if the data doesn't look like the expected layout."""
    found = []
    for label, base, count in INVENTORIES:
        for index in range(count):
            offset = base + shift + index * RECORD_SIZE
            item_id = int.from_bytes(data[offset:offset + 2], "little")
            if item_id > MAX_ITEM_ID:
                return None
            if item_id in ids:
                found.append((label, index, offset, item_id))
    return found


def load_save(path):
    """Return (bytes, offset shift, game name), or None (with a message) if not a known save."""
    data = bytearray(path.read_bytes())
    fmt = FORMATS.get(bytes(data[:4]))
    if fmt is None or len(data) != fmt[1]:
        expected = ", ".join(f"{magic.decode()} with {size} bytes ({name})"
                             for magic, (name, size, _) in FORMATS.items())
        print(f"{path}: not a known Yakuza 0 save (expected {expected}; "
              f"got {bytes(data[:4])!r} with {len(data)} bytes)")
        return None
    return data, fmt[2], fmt[0]


def scan(path, data, ids, shift, game):
    found = find_stuck(data, ids, shift)
    if found is None:
        print(f"{path}: unrecognised {game} save layout (item IDs out of range), skipping")
        return None
    if not found:
        print(f"{path}: no stuck Pocket Circuit parts found ({game})")
        return found
    print(f"{path}: found {len(found)} stuck record(s) ({game})")
    for label, index, offset, item_id in found:
        print(f"  {label}, slot {index + 1:3d} at {offset:#x}: pokecir_{ids[item_id]} (id {item_id:#x})")
    return found


def clear_records(data, found):
    for _, _, offset, _ in found:
        data[offset:offset + RECORD_SIZE] = bytes(RECORD_SIZE)


def write_in_place(path, data):
    """Replace the file atomically so a crash can't leave a half-written save."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(data)
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def default_backup_dir(folder):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = folder.resolve()
    return folder.parent / f"{folder.name}_backup_{stamp}"


def fix_folder(folder, ids, dry_run, backup_dir):
    paths = sorted({p for pattern in SAVE_PATTERNS for p in folder.glob(pattern) if p.is_file()})
    if not paths:
        sys.exit(f"No SaveData*.sav / SaveData*.clr files found in {folder}")

    todo = []
    for path in paths:
        loaded = load_save(path)
        if loaded is None:
            continue
        data, shift, game = loaded
        found = scan(path, data, ids, shift, game)
        if found:
            todo.append((path, data, found))

    if not todo:
        print("Nothing to fix.")
        return
    if dry_run:
        print(f"Dry run: {len(todo)} file(s) would be fixed. Nothing was written.")
        return

    # Back everything up before touching any save.
    backup_dir = backup_dir or default_backup_dir(folder)
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path, _, _ in todo:
        target = backup_dir / path.name
        if target.exists():
            sys.exit(f"Refusing to overwrite existing backup {target}. Nothing was changed.")
        shutil.copy2(path, target)
        if target.read_bytes() != path.read_bytes():
            sys.exit(f"Backup of {path} could not be verified. Nothing was changed.")
    print(f"Backed up {len(todo)} file(s) to {backup_dir}")

    for path, data, found in todo:
        clear_records(data, found)
        write_in_place(path, data)
        print(f"Fixed {path} ({len(found)} record(s) removed)")


def fix_file(path, ids, dry_run, in_place, output):
    loaded = load_save(path)
    if loaded is None:
        sys.exit(1)
    data, shift, game = loaded
    found = scan(path, data, ids, shift, game)
    if found is None:
        sys.exit(1)
    if not found or dry_run:
        return
    clear_records(data, found)
    if in_place:
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.exists():
            sys.exit(f"Refusing to overwrite existing backup {backup}. Nothing was changed.")
        shutil.copy2(path, backup)
        print(f"Backup written to {backup}")
        write_in_place(path, data)
        print(f"Fixed save written to {path}")
    else:
        out = output or path.with_suffix(".fixed.sav")
        out.write_bytes(data)
        print(f"Fixed save written to {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("path", type=Path,
                        help="a save folder (fixes every save in it, in place, with backups) "
                             "or a single SaveData000N.sav file")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--backup-dir", type=Path,
                        help="folder mode: where to put the backups "
                             "(default: <save folder>_backup_<timestamp> next to the save folder)")
    parser.add_argument("--in-place", action="store_true",
                        help="single file mode: overwrite the file (a .bak copy is kept)")
    parser.add_argument("-o", "--output", type=Path,
                        help="single file mode: where to write the fixed save")
    parser.add_argument("--extra-id", type=lambda s: int(s, 0), action="append", default=[],
                        metavar="ID", help="also remove records with this item ID (e.g. 0x265)")
    args = parser.parse_args()

    ids = dict(PARTS)
    for extra in args.extra_id:
        ids.setdefault(extra, f"item_{extra:#x}")

    if args.path.is_dir():
        if args.in_place or args.output:
            parser.error("--in-place and --output are for single files; "
                         "folders are always fixed in place, with a backup first")
        fix_folder(args.path, ids, args.dry_run, args.backup_dir)
    elif args.path.is_file():
        if args.backup_dir:
            parser.error("--backup-dir is only for folders")
        fix_file(args.path, ids, args.dry_run, args.in_place, args.output)
    else:
        sys.exit(f"{args.path} does not exist")


if __name__ == "__main__":
    main()
