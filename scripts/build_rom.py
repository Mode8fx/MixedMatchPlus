"""Build MixedMatchPlus from the untouched USA ROM (Python 3, no dependencies)."""

from hashlib import sha256
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "original_roms" / "Tetris & Dr. Mario (USA).sfc"
OUTPUT = ROOT / "output" / "Tetris & Dr. Mario (USA) - MixedMatchPlus.sfc"
SOURCE_SHA256 = "3cdebbd8adc4bb6773a7995f542fdac49adefca71cba583255a1c1bf37ac3946"
PREVIEW_GFX_BASE = 0x78000
PREVIEW_TILES = (0x14C, 0x14D, 0x14E, 0x15E, 0x15F, 0x16F)
PREVIEW_MAP_OFFSET = 0xBDE8C


def text_tiles(text: str) -> bytes:
    """Encode this screen's 16-bit BG entries: A=$010A, space=$0000."""
    return b"".join(
        struct.pack("<H", 0 if char == " " else 0x100 + ord(char) - 55)
        for char in text
    )


def decode_tile(rom: bytes, tile: int, base: int = PREVIEW_GFX_BASE) -> list[list[int]]:
    """Read an 8x8 SNES 4bpp tile."""
    offset = base + tile * 32
    data = rom[offset:offset + 32]
    return [[sum(((data[plane // 2 * 16 + y * 2 + plane % 2] >> (7 - x)) & 1)
                 << plane for plane in range(4)) for x in range(8)] for y in range(8)]


def encode_tile(pixels: list[list[int]]) -> bytes:
    data = bytearray(32)
    for y, row in enumerate(pixels):
        for x, color in enumerate(row):
            for plane in range(4):
                data[plane // 2 * 16 + y * 2 + plane % 2] |= (
                    (color >> plane & 1) << (7 - x))
    return bytes(data)


def patch_preview(rom: bytearray, source: bytes) -> None:
    # Reuse the miniature's proportional lettering, including its native shadows.
    game = [[p for tile in (0x15C, 0x15D, 0x16C, 0x16D, 0x16E)
             for p in decode_tile(source, tile)[y]] for y in range(4)]
    glyphs = {char: [row[x:x + width] for row in game]
              for char, x, width in (("G", 0, 4), ("A", 4, 4), ("M", 8, 5),
                                     ("E", 13, 3), ("S", 18, 4), ("T", 22, 3))}
    glyphs["O"] = [row[:4] for row in decode_tile(source, 0x14C)[:4]]
    # C comes from the Tetris preview's VS COM; remap its shadow to Mixed Match's.
    vs_com = [[p for tile in (0xB3, 0xB4, 0xB5)
               for p in decode_tile(source, tile)[y]] for y in range(4, 8)]
    glyphs["C"] = [[8 if p == 3 else p for p in row[10:14]] for row in vs_com]
    # U is absent from the existing miniature labels. Sample the game's full font
    # at half size, keeping the same foreground and shadow palette indices.
    font_u = decode_tile(source, ord("U") - 55, 0x42000)
    glyphs["U"] = [[8 if font_u[y][x] == 3 else font_u[y][x] for x in (0, 2, 4, 6)]
        for y in (0, 2, 4, 6)]
    glyphs[" "] = [[0, 0] for _ in range(4)]
    label = [[p for char in "CUSTOM GAME" for p in glyphs[char][y]]
             for y in range(4)]

    expected = struct.pack("<6H", 0x94C, 0x94D, 0x94E, 0, 0, 0)
    if source[PREVIEW_MAP_OFFSET:PREVIEW_MAP_OFFSET + 12] != expected:
        raise ValueError("Unexpected original game-select preview tilemap")
    for tile in PREVIEW_TILES[3:]:
        offset = PREVIEW_GFX_BASE + tile * 32
        if any(source[offset:offset + 32]):
            raise ValueError(f"Preview tile {tile:#x} is not blank")
        entries = struct.unpack_from("<1024H", source, 0xBD800)
        if any(entry & 0x3FF == tile for entry in entries):
            raise ValueError(f"Preview tile {tile:#x} is already referenced")
    for index, tile in enumerate(PREVIEW_TILES):
        pixels = [[row[x] if x < len(row) else 0
                   for x in range(index * 8, index * 8 + 8)] for row in label]
        pixels += [[0] * 8 for _ in range(4)]
        offset = PREVIEW_GFX_BASE + tile * 32
        rom[offset:offset + 32] = encode_tile(pixels)
    rom[PREVIEW_MAP_OFFSET:PREVIEW_MAP_OFFSET + 12] = struct.pack(
        "<6H", *(0x800 | tile for tile in PREVIEW_TILES))


def build_rom(source: bytes) -> bytes:
    if sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the original, unheadered 1 MiB USA ROM; SHA-256 differs.")
    rom = bytearray(source)
    for offset, old, new in (
        (0xB8D96, "OPTION     ", "CUSTOM GAME"),
    ):
        expected, replacement = text_tiles(old), text_tiles(new)
        if rom[offset:offset + len(expected)] != expected:
            raise ValueError(f"Unexpected original menu tiles at {offset:#x}.")
        rom[offset:offset + len(expected)] = replacement

    patch_preview(rom, source)
    from single_player import apply
    apply(rom, source)

    # The checksum/complement pair always contributes $01FE to the byte sum.
    rom[0x7FDC:0x7FE0] = bytes.fromhex("ff ff 00 00")
    checksum = sum(rom) & 0xFFFF
    struct.pack_into("<HH", rom, 0x7FDC, checksum ^ 0xFFFF, checksum)
    assert len(rom) == len(source)
    assert sum(rom) & 0xFFFF == checksum
    return bytes(rom)


def main() -> None:
    source = SOURCE.read_bytes()
    result = build_rom(source)
    if OUTPUT.resolve().is_relative_to((ROOT / "original_roms").resolve()):
        raise ValueError("Output must not be inside original_roms.")
    if OUTPUT.resolve() == SOURCE.resolve() or (OUTPUT.exists() and OUTPUT.samefile(SOURCE)):
        raise ValueError("Output must not overwrite the original ROM.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(result)
    print(f"Created: {OUTPUT}")
    print(f"SHA-256: {sha256(result).hexdigest()}")
    print(f"SNES checksum: ${struct.unpack_from('<H', result, 0x7FDE)[0]:04X}")


if __name__ == "__main__":
    main()
