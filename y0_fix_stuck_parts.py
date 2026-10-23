#!/usr/bin/env python3
"""Remove stuck Pocket Circuit parts from a Yakuza 0 (PC/Steam) save file.

Some saves end up with Pocket Circuit car parts (tires, motors) occupying slots in
Equipment > Weapon and in the weapon box. They can't be discarded in game. This script
zeroes those records in the save file, which is what the game itself does when you
discard an item. Your real Pocket Circuit part list is not touched.

By default the original file is left untouched and a fixed copy is written next to it.

Usage:
    python3 y0_fix_stuck_parts.py SaveData0002.sav              # writes SaveData0002.fixed.sav
    python3 y0_fix_stuck_parts.py SaveData0002.sav --dry-run    # only report what would change
    python3 y0_fix_stuck_parts.py SaveData0002.sav --in-place   # overwrite, keeping a .bak copy

Save location with Steam:
    <Steam>/userdata/<steam id>/638970/remote/SaveData000N.sav
Turn off Steam Cloud for the game and back up that folder before replacing a save.
"""

import argparse
import shutil
import sys
from pathlib import Path

SAVE_SIZE = 167720
MAGIC = b"YZFH"

# Save layout (see also github.com/apocalyptech/y0-cli-save, which documents it).
# Items are 16-byte records; the first 2 bytes (little endian) are the item ID.
RECORD_SIZE = 16

# (label, offset, number of slots). Kiryu's own "Pocket Circuit" list at 0xD86C is where
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

# Every Pocket Circuit item in the game (item.uni in boot.par: all names "pokecir_*").
# None of them belong in a weapon slot.
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


def find_stuck(data, ids):
    found = []
    for label, base, count in INVENTORIES:
        for index in range(count):
            offset = base + index * RECORD_SIZE
            item_id = int.from_bytes(data[offset:offset + 2], "little")
            if item_id in ids:
                found.append((label, index, offset, item_id))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("save", type=Path, help="path to a SaveData000N.sav file")
    parser.add_argument("-o", "--output", type=Path, help="where to write the fixed save")
    parser.add_argument("--in-place", action="store_true",
                        help="overwrite the input file (a .bak copy is kept)")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--extra-id", type=lambda s: int(s, 0), action="append", default=[],
                        metavar="ID", help="also remove records with this item ID (e.g. 0x265)")
    args = parser.parse_args()

    data = bytearray(args.save.read_bytes())
    if data[:4] != MAGIC or len(data) != SAVE_SIZE:
        sys.exit(f"{args.save} does not look like a Yakuza 0 save "
                 f"(expected magic {MAGIC!r} and {SAVE_SIZE} bytes, got {bytes(data[:4])!r} and {len(data)} bytes)")

    ids = dict(PARTS)
    for extra in args.extra_id:
        ids.setdefault(extra, f"item_{extra:#x}")

    found = find_stuck(data, ids)
    if not found:
        print("No stuck Pocket Circuit parts found. Nothing to do.")
        return

    print(f"Found {len(found)} stuck record(s):")
    for label, index, offset, item_id in found:
        print(f"  {label}, slot {index + 1:3d} at {offset:#x}: pokecir_{ids[item_id]} (id {item_id:#x})")

    if args.dry_run:
        return

    for _, _, offset, _ in found:
        data[offset:offset + RECORD_SIZE] = bytes(RECORD_SIZE)

    if args.in_place:
        backup = args.save.with_suffix(args.save.suffix + ".bak")
        shutil.copy2(args.save, backup)
        out = args.save
        print(f"Backup written to {backup}")
    else:
        out = args.output or args.save.with_suffix(".fixed.sav")
    out.write_bytes(data)
    print(f"Fixed save written to {out}")


if __name__ == "__main__":
    main()
