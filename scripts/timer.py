"""Build a centered MM:SS panel from the native 8x16 status-number font."""
import struct

from build_rom import decode_tile, encode_tile


def build_timer(source):
    # BG1/BG2 share graphics at VRAM $2000. $8000..$9FFF is unused in Mixed
    # Match, before BG3 at $A000 and OBJ at $C000. Deduplicate half-glyph pairs
    # so all 31 minute values and 60 second values fit in those 256 tiles.
    for base in (0xA8800,0xA9000,0xA9800,0xAA000,0xAA800):
        if any(entry&0x3ff>=0x300 for entry in struct.unpack_from('<1024H',source,base)):
            raise ValueError('Mixed Match already uses reserved BG1/BG2 timer tiles')
    tiles = []
    indices = {}

    def tile(pixels):
        data = encode_tile(pixels)
        if data not in indices:
            indices[data] = 0x300 + len(tiles)
            tiles.append(data)
        return 0x2400 | indices[data]  # BG2 high priority, native number palette 1

    digits = [decode_tile(source, 0x130 + n, 0x70000)
              + decode_tile(source, 0x140 + n, 0x70000) for n in range(10)]
    colon = [[3] * 8 for _ in range(16)]
    for y in (4, 5, 10, 11):
        colon[y][2:4] = [1, 1]

    def panel(minutes, seconds):
        canvas = [[3] * 48 for _ in range(32)]  # opaque black stops the divider
        for x in range(48):
            canvas[0][x] = canvas[31][x] = 2
        for row in canvas:
            row[0] = row[47] = 2
        glyphs = [digits[minutes // 10], digits[minutes % 10], colon,
                  digits[seconds // 10], digits[seconds % 10]]
        for i, glyph in enumerate(glyphs):
            for y, row in enumerate(glyph):
                canvas[y + 8][4 + i * 8:12 + i * 8] = [p or 3 for p in row]
        return [[tile([r[x:x + 8] for r in canvas[y:y + 8]])
                 for x in range(0, 48, 8)] for y in range(0, 32, 8)]

    frame = panel(0, 0)
    minutes = [entry for n in range(31) for row in panel(n, 0)[1:3]
               for entry in row[:3]]
    seconds = [entry for n in range(60) for row in panel(0, n)[1:3]
               for entry in row[3:]]
    if len(tiles) > 256:
        raise ValueError(f'Timer needs {len(tiles)} tiles; only 256 are reserved')
    words = lambda values: struct.pack('<' + 'H' * len(values), *values)
    return (b''.join(tiles), words(frame[0] + frame[3]),
            words(minutes), words(seconds))
