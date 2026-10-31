"""Isolate Dr. Mario's animated stage-clear lettering from the timer palette."""
import struct

from build_rom import decode_tile


CLEAR_PENS = (4,8,12)  # Palette 0; preserve live HUD face/shadow pens 1/3.
CLEAR_TEXT_TILES = (*range(0xD0,0xE0),*range(0xE6,0xEA))


def build_stage_clear(source, tile):
    pens={1:4,2:8,11:12}  # Animated ink, off-white paper, pink frame edge.
    records=bytearray()
    for n in range(0xD0,0xEA):
        if n not in CLEAR_TEXT_TILES:
            records.extend(bytes(4));continue
        pixels=decode_tile(source,n,0x70000)
        if any(p not in pens for row in pixels for p in row):
            raise ValueError('Unexpected native stage-clear lettering pixels')
        entry=tile([[pens[p] for p in row] for row in pixels],0)
        records.extend(struct.pack('<HH',0x1800|n,entry))
    for dest,native in ((8,2),(12,11)):
        color=struct.unpack_from('<H',source,0x194c0+native*2)[0]
        records.extend(struct.pack('<HH',dest*2,color))
    assert len(records)==0x70
    return bytes(records)
