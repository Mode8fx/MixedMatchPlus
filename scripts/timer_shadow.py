"""Draw timer shadows in the game's native BG3 subtraction layer."""
import struct

from timer import frame_pixels


# Retain the native shadow renderer for later experiments. Change to True and
# rebuild to restore the frame cast and its extra foreground cutout row.
FRAME_SHADOW_ENABLED = False


SHADOW_DX = SHADOW_DY = 8
SHADOW_WIDTH, SHADOW_HEIGHT = 56,40
SHADOW_CELLS = tuple((y,6) for y in range(4))+tuple((4,x) for x in range(7))


def shadow_mask(source, doctors, two, maps, col):
    if not FRAME_SHADOW_ENABLED:
        return [[False]*SHADOW_WIDTH for _ in range(SHADOW_HEIGHT)]
    frames=[frame_pixels(source,doctor,two) for doctor in doctors]
    def opaque(x,y):
        return 0<=x<48 and 0<=y<32 and frames[x//24][y][x] is not None
    mask=[]
    for y in range(SHADOW_HEIGHT):
        row=[]
        for x in range(SHADOW_WIDTH):
            entry=struct.unpack_from('<H',maps[0],(23+y//8)*64+(col+x//8)*2)[0]
            # Native blue interiors/shadows and gold bottle frames stay in
            # front of this cast, as do the BG1 board and falling sprites.
            covered=((entry>>10)&7) in (4,6)
            row.append(opaque(x-SHADOW_DX,y-SHADOW_DY) and not opaque(x,y) and not covered)
        mask.append(row)
    return mask


def shadow_tint_cell(source, maps, mask, doctors, two, col, y, x):
    """Use pen 3, as in the native board/LEVEL/SCORE cast-shadow tiles.

    Dr. Mario's native shadow connectors use palette 3, with pen 1 for
    exposed mosaic pixels and pen 3 for the cast. Tetris retains the local
    tint palette, including the original gray seam/connector palettes.
    """
    from timer_border import map_pixels
    off=(23+y)*64+(col+x)*2
    entry=struct.unpack_from('<H',maps[1],off)[0]
    pixels=map_pixels(source,entry,True)
    if not any(mask[y*8+dy][x*8+dx] for dy in range(8) for dx in range(8)):
        return pixels,entry
    doctor=doctors[int(col+x>=16)] if two else doctors[0]
    attributes=entry&0x3c00
    if doctor:
        # This is the exact palette/remapping used by native $0D06/$0D07
        # shadow edges. Pens 13 and 21 are identical native mosaic colors.
        remap={0:0,9:1,13:1,21:1,15:3,31:3}
        palette=(entry>>10)&7
        for dy in range(8):
            for dx in range(8):
                p=pixels[dy][dx]
                index=palette*4+p if p else 0
                if index not in remap:raise ValueError(f'Unexpected Dr. Mario shadow-edge tint {index}')
                pixels[dy][dx]=remap[index]
        attributes=(entry&0x2000)|0x0c00
    for dy in range(8):
        for dx in range(8):
            if mask[y*8+dy][x*8+dx]:pixels[dy][dx]=3
    return pixels,attributes
