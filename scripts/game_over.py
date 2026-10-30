"""Keep the native Dr. Mario popup colors separate from timer composites."""
import struct

from build_rom import decode_tile


# Only these palette-1 pens change. Native HUD digits keep their existing
# white face (1) and black shadow (3), which the popup can share unchanged.
POPUP_PENS = (2,4,8,12)
POPUP_FRAME_TILES = (0xBC,0xBD,0xBE,0xCC,0xCD,0xCE)
POPUP_TEXT_TILES = tuple(range(0xC0,0xC8))


def build_popup(source, tile):
    # The initial maps omit live HUD digits, which use palette 1, pens 1/3.
    # Share their native white/black; place the blue shades in separate pens.
    frame_pens={0:0,2:1,6:2,7:8,8:4}
    text_pens={1:3,2:12}
    for pen,bank,native in ((1,4,2),(3,6,1)):
        shared=source[0x19420+pen*2:0x19422+pen*2]
        if shared!=source[0x19400+(bank*16+native)*2:0x19402+(bank*16+native)*2]:
            raise ValueError('Popup must preserve native HUD white/black colors')
    for n in range(0x130,0x14A):
        if any(p not in (0,1,3) for row in decode_tile(source,n,0x70000) for p in row):
            raise ValueError('Native live HUD digits use reserved popup colors')
    records=bytearray()
    for n in range(0xBC,0xD0):
        frame=n in POPUP_FRAME_TILES
        if not frame and n not in POPUP_TEXT_TILES:
            records.extend(bytes(4));continue
        pens=frame_pens if frame else text_pens
        pixels=decode_tile(source,n,0x70000)
        if any(p not in pens for row in pixels for p in row):
            raise ValueError('Unexpected native Game Over popup pixels')
        entry=tile([[pens[p] for p in row] for row in pixels],0x0400)
        records.extend(struct.pack('<HH',(0x1000 if frame else 0x1800)|n,entry))
    for dest,bank,native in ((1,4,2),(2,4,6),(8,4,7),(4,4,8),(3,6,1),(12,6,2)):
        color=struct.unpack_from('<H',source,0x19400+(bank*16+native)*2)[0]
        records.extend(struct.pack('<HH',(16+dest)*2,color))
    assert len(records)==0x68
    return bytes(records)
