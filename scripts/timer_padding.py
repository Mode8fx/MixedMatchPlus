"""Restore native backgrounds above/below the compact two-player gold frame."""
import struct


def timer_layouts(source, solo_maps):
    phases=(1,3,5)
    bg2={n:source[b:b+0x800] for n,b in ((1,0xAA000),(3,0xAA800),(5,0xA9800))}
    bg3={n:source[b:b+0x800] for n,b in ((1,0xAC000),(3,0xAC800),(5,0xAB800))}
    layouts=[(solo_maps[n],(n==3,n==3),13) for n in phases]
    for left in phases:
        for right in phases:
            maps=[]
            for layer in (bg2,bg3):
                maps.append(b''.join(layer[left][y*64:y*64+32]+layer[right][y*64+32:(y+1)*64]
                                     for y in range(32)))
            layouts.append((maps,(left==3,right==3),13))
    return layouts


def build_padding(source, solo_maps, borders, color_maps):
    from timer_border import BORDER_CELLS
    layouts=timer_layouts(source,solo_maps)
    data=bytearray();descriptors=bytearray()
    # BG2 map base $1800, BG3 map base $8800 (VRAM byte addresses). The
    # latter's two live rows occupy four reserved, unreferenced font tiles.
    destinations=(0xEE0,0xF40,0x46E0,0x4740)
    for index,(maps,doctors,col) in enumerate(layouts):
        record=bytearray()
        for layer in range(2):
            for edge,row in enumerate((23,26)):
                words=list(struct.unpack_from('<32H',maps[layer],row*64))
                for x in range(6):
                    if index>=3 and doctors[x//3]:continue
                    if layer==0:
                        cell=BORDER_CELLS.index((0 if edge==0 else 3,x))
                        words[col+x]=struct.unpack_from('<H',borders,index*32+cell*2)[0]
                    else:
                        words[col+x]=struct.unpack_from('<H',color_maps[index],row*64+(col+x)*2)[0]
                record.extend(struct.pack('<32H',*words))
        for offset,destination in zip(range(0,256,64),destinations):
            # Native VRAM queue: DMAP/BBAD, source/bank, count, VMADD, VMAIN.
            descriptors.extend(struct.pack('<HHBHHB',0x1801,0xF000+len(data)+offset,
                                           0x9C,64,destination,0x80))
        data.extend(record)
    assert len(data)==0xC00 and len(descriptors)==480
    # Channel 6, mode 1: BG2SC/BG3SC. Counts include HDMA first-line timing.
    bands=bytes.fromhex('7f 04 08 40 04 08 02 0c 44 1d 04 08 01 0c 44 11 04 08 00')
    return bytes(data),bytes(descriptors),bands
