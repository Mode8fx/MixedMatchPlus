"""Build matching metal timer frames and the native 8x16 status-number font."""
import struct

from build_rom import decode_tile, encode_tile

FONT_FIRST_TILE = 0x150
STYLE_STRIDE = 0x400
GLYPH_X = (8,15,22,26,33)
# Alternate BG3 map rows share these otherwise unused character slots. They
# are selected as map data only on the four scanlines outside the gold frame.
PADDING_MAP_TILES = {0x36E,0x36F,0x374,0x375}


def font_colors(doctor=False):
    # Keep the source font's separate face and offset-shadow masks.
    return (8,10,9) if doctor else (2,15,3)


def tetris_corner_pixels(source, bottom=False):
    """The native right-hand 8x8 corner, including its original shading.

    A corner crosses three source tiles. Its five-pixel connector has the
    native three-pixel rail centered on it. No scaling or recoloring is used.
    """
    left=decode_tile(source,0x232,0x70000)
    corner=decode_tile(source,0x23C if bottom else 0x236,0x70000)
    side=decode_tile(source,0x23A if bottom else 0x238,0x70000)
    if bottom:
        return [[0,0]+side[y][:6] for y in (6,7)]+[
            left[y][6:]+corner[y][:6] for y in range(6)]
    return [left[y][6:]+corner[y][:6] for y in range(1,8)]+[[0,0]+side[0][:6]]


def frame_pixels(source, doctor=False):
    """Three-pixel rails, with unmodified native corners on the silver frame."""
    bevel=(2,3,5) if doctor else (9,10,13)
    body=9 if doctor else 3
    outside=8 if doctor else 3
    canvas=[[outside]*48 for _ in range(32)]
    left,right=(0,47) if doctor else (3,44)
    for y in range(2,30):
        for x in range(left,right+1):
            depth=min(x-left,right-x,y-2,29-y)
            canvas[y][x]=bevel[depth] if depth<3 else body
    if not doctor:
        # Original top corner: y=1..8. Translate the original bottom corner
        # down one pixel to y=23..30 so both rails share the gold frame's
        # y=2..4 / 27..29 positions. Mirror only the left-hand copies.
        for bottom,y in ((False,1),(True,23)):
            pixels=tetris_corner_pixels(source,bottom)
            for dy,row in enumerate(pixels):
                canvas[y+dy][38:46]=[p or body for p in row]
                canvas[y+dy][2:10]=[p or body for p in row[::-1]]
    return canvas


def build_timer(source):
    # Reuse unreferenced HUD-font/decorative slots and $300..$3FF. Dynamic
    # capsule/virus and Tetris-board tiles ($000..$03F/$200..) stay untouched.
    # Preserve all interleaved native graphics in the contiguous DMA span.
    used = set()
    for base in (0xA8800,0xA9000,0xA9800,0xAA000,0xAA800):
        entries = struct.unpack_from('<1024H',source,base)
        used.update(entry & 0x3ff for entry in entries)
        if any(entry&0x3ff>=0x300 for entry in entries):
            raise ValueError('Mixed Match already uses reserved BG1/BG2 timer tiles')
        for entry in entries:
            if entry&0x1c00==0xc00:
                if any(p in (9,10) for row in decode_tile(source,entry&0x3ff,0x70000) for p in row):
                    raise ValueError('Native frame palette already uses timer paper/shadow slots')
    if used & PADDING_MAP_TILES:
        raise ValueError('Native graphics use the alternate timer color-map slots')
    available = [n for n in range(FONT_FIRST_TILE,0x400)
                 if n not in used and n not in PADDING_MAP_TILES
                 and (n<0x200 or n>=0x2cf)]
    tiles = []
    indices = {}

    def tile(pixels, doctor):
        data = encode_tile(pixels)
        if data not in indices:
            mirrored=encode_tile([row[::-1] for row in pixels])
            if mirrored in indices:
                return (0x2C00 if doctor else 0x3400) | indices[mirrored] | 0x4000
            if len(tiles) == len(available):
                raise ValueError(f'Timer exceeds {len(available)} available tiles')
            indices[data] = available[len(tiles)]
            tiles.append(data)
        return (0x2C00 if doctor else 0x3400) | indices[data]

    digits = [decode_tile(source, 0x130 + n, 0x70000)
              + decode_tile(source, 0x140 + n, 0x70000) for n in range(10)]
    if any(row[7] for glyph in digits for row in glyph):
        raise ValueError('Expected the native digits to have a blank eighth column')
    digits=[[row[:7] for row in glyph] for glyph in digits]
    colon = [[0] * 4 for _ in range(16)]
    for y in (6,7,12,13):colon[y][2:4]=[3,3]
    for y in (4, 5, 10, 11):
        colon[y][:2] = [1, 1]

    def panel(minutes, seconds, doctor):
        canvas = frame_pixels(source,doctor)
        ink,shadow,body = font_colors(doctor)
        glyphs = [digits[minutes // 10], digits[minutes % 10], colon,
                  digits[seconds // 10], digits[seconds % 10]]
        for i, glyph in enumerate(glyphs):
            for y, row in enumerate(glyph):
                x=GLYPH_X[i]
                canvas[y + 8][x:x+len(row)] = [ink if p==1 else shadow if p==3 else body for p in row]
        return [[tile([r[x:x + 8] for r in canvas[y:y + 8]],doctor)
                 for x in range(0, 48, 8)] for y in range(0, 32, 8)]

    words = lambda values: struct.pack('<' + 'H' * len(values), *values)
    frames, minutes, seconds = [], [], []
    for doctor in (False,True):
        frame = panel(0,0,doctor)
        frames.append(words(frame[0]+frame[3]).ljust(0x20,b'\xff'))
        minutes.append(words([v for n in range(31) for row in panel(n,0,doctor)[1:3]
                              for v in row[:3]]))
        seconds.append(words([v for n in range(60) for row in panel(0,n,doctor)[1:3]
                              for v in row[3:]]))
    last = available[len(tiles)-1]
    graphics = bytearray(source[0x70000+FONT_FIRST_TILE*32:0x70000+(last+1)*32])
    for n,data in zip(available,tiles):
        off=(n-FONT_FIRST_TILE)*32
        graphics[off:off+32]=data
    return (bytes(graphics),b''.join(frames),
            minutes[0].ljust(STYLE_STRIDE,b'\xff')+minutes[1],
            seconds[0].ljust(STYLE_STRIDE,b'\xff')+seconds[1])
