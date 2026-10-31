"""Render the normal Mixed Match menu at explicit pixel positions."""
import struct

from build_rom import decode_tile, encode_tile, text_tiles


def build_normal_menu(source: bytes) -> tuple[bytes, bytes, bytes]:
    """Return the tilemap, extra graphics, and (map offset, focus index) table.

    Gaps count rows between visible pixels, including beveled header borders
    but excluding black text shadows. P1/P2 occupy y=91..99 and 115..123.
    """
    base=0xb2000
    rows=[source[base+i*64:base+(i+1)*64] for i in range(32)]
    new=rows.copy()
    for row in range(4,24):new[row]=rows[7]

    # PLAYERS stays in its original position, with the original border colors.
    for row,data in (
        (4,struct.pack('<9H',0x2024,*([0x2025]*7),0x6024)),
        (5,struct.pack('<H',0x2026)+text_tiles('PLAYERS',0x2000)+struct.pack('<H',0x6026)),
        (6,struct.pack('<9H',0xa024,*([0xa025]*7),0xe024)),
    ):
        line=bytearray(new[row]);line[8:8+len(data)]=data;new[row]=bytes(line)

    canvas=[[0]*256 for _ in range(256)]
    roles={}

    def blit(pixels,x,y,focus=0):
        for dy,line in enumerate(pixels):
            for dx,pixel in enumerate(line):
                if not pixel:continue
                px=x+dx;py=y+dy
                if canvas[py][px]:raise ValueError('Normal menu elements overlap')
                canvas[py][px]=pixel
                if focus:
                    cell=(py//8,px//8)
                    if roles.get(cell,focus)!=focus:raise ValueError('Two headers share a tile')
                    roles[cell]=focus

    def native(entry):
        tile=entry&0x3ff
        pixels=decode_tile(source,tile-0x100,0x42000) if tile>=0x100 else decode_tile(source,tile,0x3e000)
        if entry&0x4000:pixels=[line[::-1] for line in pixels]
        if entry&0x8000:pixels=pixels[::-1]
        return pixels

    def native_rows(start,count,col,width):
        pixels=[]
        for row in range(start,start+count):
            tiles=[native(struct.unpack_from('<H',rows[row],c*2)[0]) for c in range(col,col+width)]
            pixels.extend([[p for tile in tiles for p in tile[y]] for y in range(8)])
        return pixels

    label='1 2  PLAYERS'
    glyphs=[[[0]*8 for _ in range(8)] if c==' ' else native(0x100+(int(c) if c.isdigit() else ord(c)-55)) for c in label]
    blit([[p for glyph in glyphs for p in glyph[y]] for y in range(8)],56,58)
    for original,width,y,focus in ((4,10,71,1),(12,11,128,2),(18,14,163,3)):
        blit(native_rows(original,3,4,width)[4:20],32,y,focus)
    for original,y in ((9,104),(16,150),(22,185)):
        blit(native_rows(original,1,7,21),56,y)

    graphics=bytearray();tiles={};highlights=bytearray()
    for row in range(32):
        line=bytearray(new[row])
        for col in range(32):
            pixels=[p[col*8:col*8+8] for p in canvas[row*8:row*8+8]]
            encoded=encode_tile(pixels)
            if not any(encoded):continue
            if encoded not in tiles:
                tiles[encoded]=0x280+len(graphics)//32
                graphics.extend(encoded)
            struct.pack_into('<H',line,col*2,0x2000|tiles[encoded])
            if (row,col) in roles:highlights.extend(struct.pack('<HB',row*64+col*2,roles[row,col]))
        new[row]=bytes(line)
    highlights.extend(b'\xff\xff')
    if len(graphics)>0x1000:raise ValueError('Normal-menu graphics exceed spare VRAM')
    # Palette 4 combines white lettering with native animated focus borders.
    # These original 4bpp maps do not otherwise use that palette; BG3 is 2bpp.
    for off in (0xb2000,0xab000):
        if any(v&0x3ff and (v>>10)&7==4 for v in struct.unpack_from('<1024H',source,off)):
            raise ValueError('Normal menu uses the reserved focus palette')
    return b''.join(new),bytes(graphics),bytes(highlights)
