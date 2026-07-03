#!/usr/bin/env python3
# Copyright (c) 2026 Nordic Semiconductor ASA
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
"""Inject Wi-Fi LMAC/UMAC ROM patch blobs into zephyr.bin and zephyr.hex.

The patch binaries are GPL-licensed and position-dependent (absolute ARM
MRAM address references); they MUST reside at lmac_origin / umac_origin.

zephyr.bin is modified BEFORE imgtool signs the image so that
zephyr.signed.bin carries the patch bytes at the correct binary offsets.
When MCUboot performs a slot1 -> slot0 swap the patches land at exactly
lmac_origin / umac_origin in MRAM.

zephyr.hex receives the patches at the same absolute MRAM addresses and
serves as the combined factory programming image.

No imgtool change is needed: origins are ~960 KB into slot0, far beyond
the MCUboot header zone (bytes 0..ROM_START_OFFSET-1) that check_header()
inspects.
"""

import argparse
import sys
from pathlib import Path


def parse_int(value: str) -> int:
    return int(value, 0)


def inject_bin(app_bin: Path, patch_bin: Path, origin: int,
               code_base: int, name: str) -> None:
    data = patch_bin.read_bytes()
    offset = origin - code_base

    if offset < 0:
        sys.exit(f"ERROR: {name} origin 0x{origin:X} < code_base 0x{code_base:X}.")

    app = bytearray(app_bin.read_bytes())

    # Extend if linker section is NOBITS (not materialised in binary by objcopy).
    required = offset + len(data)
    if required > len(app):
        app.extend(bytes(required - len(app)))

    region = app[offset:offset + len(data)]
    if any(b not in (0x00, 0xFF) for b in region):
        sys.exit(f"ERROR: non-empty bytes at {name} region "
                 f"(bin offset 0x{offset:X}).  Already patched?")

    app[offset:offset + len(data)] = data
    app_bin.write_bytes(bytes(app))
    print(f"  {name}: {len(data)} B at bin offset 0x{offset:X}  (MRAM 0x{origin:X})")


def inject_hex(app_hex: Path, patch_bin: Path, origin: int, name: str) -> None:
    try:
        from intelhex import IntelHex
    except ImportError:
        sys.exit("ERROR: intelhex is required.  pip install intelhex")

    data = patch_bin.read_bytes()
    ih = IntelHex(str(app_hex))
    ih.puts(origin, data)
    ih.write_hex_file(str(app_hex))
    print(f"  {name}: {len(data)} B -> HEX at MRAM 0x{origin:X}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--app-bin",   required=True, type=Path)
    ap.add_argument("--app-hex",   type=Path)
    ap.add_argument("--code-base", required=True, type=parse_int,
                    help="slot0_partition start address (CODE_BASE)")
    ap.add_argument("--lmac-bin",    type=Path)
    ap.add_argument("--lmac-origin", type=parse_int)
    ap.add_argument("--umac-bin",    type=Path)
    ap.add_argument("--umac-origin", type=parse_int)
    args = ap.parse_args()

    if args.lmac_bin is None and args.umac_bin is None:
        sys.exit("ERROR: at least one of --lmac-bin / --umac-bin must be given.")
    if args.lmac_bin is not None and args.lmac_origin is None:
        sys.exit("ERROR: --lmac-bin requires --lmac-origin.")
    if args.umac_bin is not None and args.umac_origin is None:
        sys.exit("ERROR: --umac-bin requires --umac-origin.")

    print("inject_wifi_patch.py:")

    if args.lmac_bin is not None:
        inject_bin(args.app_bin, args.lmac_bin,
                   args.lmac_origin, args.code_base, "LMAC")
    if args.umac_bin is not None:
        inject_bin(args.app_bin, args.umac_bin,
                   args.umac_origin, args.code_base, "UMAC")

    if args.app_hex is not None:
        if args.lmac_bin is not None:
            inject_hex(args.app_hex, args.lmac_bin, args.lmac_origin, "LMAC")
        if args.umac_bin is not None:
            inject_hex(args.app_hex, args.umac_bin, args.umac_origin, "UMAC")


if __name__ == "__main__":
    main()
