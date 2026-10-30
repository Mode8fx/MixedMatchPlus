"""Build the supplied PNG timer frames and native 8x16 status-number font."""
import struct
from functools import lru_cache
from pathlib import Path

from PIL import Image

from build_rom import decode_tile, encode_tile

FONT_FIRST_TILE = 0x150
STYLE_STRIDE = 0x400
GLYPH_X = (8,15,22,26,33)
# Alternate BG3 map rows share these otherwise unused character slots. They
# are selected as map data on the three scanlines outside compact gold frames.
PADDING_MAP_TILES = {0x36E,0x36F,0x374,0x375}


def font_colors(doctor=False):
    # Keep the source font's separate face and offset-shadow masks.
    return (8,10,9) if doctor else (2,15,3)


def snes_color(rgb):
    """Round artwork RGB to the SNES's five bits per channel."""
    return sum(((c*31+127)//255)<<shift for c,shift in zip(rgb,(0,5,10)))


# Abstract frame pens. Solo gold's gray trim uses these only in static border
# cells, which get a composite palette; the live numeral cells retain palette 3.
DOCTOR_GRAY_PENS = {11:12,12:11,13:15,14:10}


def frame_colors(source, doctor=False):
    base=0x19460 if doctor else 0x194a0
    colors=dict(enumerate(struct.unpack_from('<16H',source,base)))
    if doctor:
        colors[9]=struct.unpack_from('<H',source,0x194a4)[0]
        for pen,native in DOCTOR_GRAY_PENS.items():
            colors[pen]=struct.unpack_from('<H',source,0x194a0+native*2)[0]
    return colors


@lru_cache(maxsize=3)
def frame_art(doctor=False,two=False):
    """Read the supplied PNG at native size, without resampling its pixels."""
    name=f'timer-drmario-{2 if two else 1}p.png' if doctor else 'timer-tetris.png'
    with Image.open(Path(__file__).parent/'assets'/name) as original:
        image=original.convert('RGBA')
    size=(44,29) if doctor and two else (46,31)
    if image.size!=size:raise ValueError(f'{name}: expected {size}, got {image.size}')
    x0,y0=(2,2) if doctor and two else (1,1)
    canvas=[[None]*48 for _ in range(32)]
    for y in range(image.height):
        for x in range(image.width):
            r,g,b,a=image.getpixel((x,y))
            if a not in (0,255):raise ValueError(f'{name}: partial alpha is unsupported')
            if a and (r,g,b)!=(255,0,255):
                canvas[y+y0][x+x0]=snes_color((r,g,b))
    return tuple(tuple(row) for row in canvas)


def frame_pixels(source, doctor=False, two=False):
    colors=frame_colors(source,doctor)
    # Prefer the existing body/rail pens when duplicate native colors exist.
    pens={colors[p]:p for p in ((3,9,10,11,12,13,15) if not doctor else (2,3,4,5,6,7,9,11,12,13,14))}
    try:return [[None if p is None else pens[p] for p in row] for row in frame_art(doctor,two)]
    except KeyError as error:raise ValueError(f'Timer PNG color ${error.args[0]:04X} has no native palette match') from error


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
        canvas = [[(9 if doctor else 3) if p is None else p for p in row]
                  for row in frame_pixels(source,doctor)]
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
