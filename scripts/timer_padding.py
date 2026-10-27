"""Restore native backgrounds on the four scanlines outside the gold frame."""
import struct


def build_padding(source, solo_maps, frames):
    phases=(1,3,5)
    bg2={n:source[b:b+0x800] for n,b in ((1,0xAA000),(3,0xAA800),(5,0xA9800))}
    bg3={n:source[b:b+0x800] for n,b in ((1,0xAC000),(3,0xAC800),(5,0xAB800))}
    layouts=[(solo_maps[n],(n==3,n==3),14 if n==3 else 13) for n in phases]
    for left in phases:
        for right in phases:
            maps=[]
            for layer in (bg2,bg3):
                maps.append(b''.join(layer[left][y*64:y*64+32]+layer[right][y*64+32:(y+1)*64]
                                     for y in range(32)))
            layouts.append((maps,(left==3,right==3),13))
    data=bytearray();descriptors=bytearray()
    silver=struct.unpack_from('<12H',frames)
    # BG2 map base $1800, BG3 map base $8800 (VRAM byte addresses). The
    # latter's two live rows occupy four reserved, unreferenced font tiles.
    destinations=(0xEE0,0xF40,0x46E0,0x4740)
    for maps,doctors,col in layouts:
        record=bytearray()
        for layer in range(2):
            for edge,row in enumerate((23,26)):
                words=list(struct.unpack_from('<32H',maps[layer],row*64))
                for x in range(6):
                    if not doctors[x//3]:
                        words[col+x]=silver[edge*6+x] if layer==0 else 0x1FF
                record.extend(struct.pack('<32H',*words))
        for offset,destination in zip(range(0,256,64),destinations):
            # Native VRAM queue: DMAP/BBAD, source/bank, count, VMADD, VMAIN.
            descriptors.extend(struct.pack('<HHBHHB',0x1801,0xF000+len(data)+offset,
                                           0x9C,64,destination,0x80))
        data.extend(record)
    assert len(data)==0xC00 and len(descriptors)==480
    # Channel 6, mode 1: BG2SC/BG3SC. Counts include HDMA first-line timing.
    bands=bytes.fromhex('7f 04 08 40 04 08 02 0c 44 1c 04 08 02 0c 44 11 04 08 00')
    return bytes(data),bytes(descriptors),bands
