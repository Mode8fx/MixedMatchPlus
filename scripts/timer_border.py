"""Composite the silver timer's cleared outer padding with native backgrounds."""
import struct
from collections import deque

from build_rom import decode_tile, encode_tile
from timer import FONT_FIRST_TILE, PADDING_MAP_TILES, frame_pixels
from timer_padding import timer_layouts

# Only these cells contain frame pixels; the eight numeral cells stay dynamic.
BORDER_CELLS = tuple((y,x) for y in range(4) for x in range(6)
                     if y in (0,3) or x in (0,5))
COLOR_FIRST_TILE = 0x180


def silver_clear_mask(source):
    """Expose native decoration outside the rails and original corner art."""
    frame=frame_pixels(source)
    mask=[[False]*48 for _ in range(32)]
    pending=deque((y,x) for y in range(32) for x in range(48)
                  if y in (0,31) or x in (0,47))
    while pending:
        y,x=pending.popleft()
        if not (0<=y<32 and 0<=x<48) or mask[y][x] or frame[y][x]!=3:
            continue
        mask[y][x]=True
        pending.extend(((y-1,x),(y+1,x),(y,x-1),(y,x+1)))
    return mask


def map_pixels(source, entry, color=False):
    if color:
        off=0x4E000+(entry&1023)*16
        pixels=[[sum(((source[off+y*2+p]>>(7-x))&1)<<p for p in range(2))
                 for x in range(8)] for y in range(8)]
    else:
        pixels=decode_tile(source,entry&1023,0x70000)
    if entry&0x8000:pixels=pixels[::-1]
    if entry&0x4000:pixels=[row[::-1] for row in pixels]
    return pixels


def build_border(source, solo_maps, graphics, frames, minutes, seconds):
    used={e&1023 for base in (0xA8800,0xA9000,0xA9800,0xAA000,0xAA800)
          for e in struct.unpack_from('<1024H',source,base)}
    words=[e for data in (frames,minutes,seconds)
           for e in struct.unpack('<'+'H'*(len(data)//2),data) if e!=0xffff]
    used.update(e&1023 for e in words)
    available=iter(n for n in range(FONT_FIRST_TILE,0x400)
                   if n not in used and n not in PADDING_MAP_TILES
                   and (n<0x200 or n>=0x2cf))
    graphics=bytearray(graphics)
    indices={bytes(graphics[(n-FONT_FIRST_TILE)*32:(n-FONT_FIRST_TILE+1)*32]):n
             for n in {e&1023 for e in words}}

    def metal_tile(pixels):
        data=encode_tile(pixels)
        if data not in indices:
            n=next(available,None)
            if n is None:raise ValueError('Silver background composites exceed free timer tiles')
            indices[data]=n
            end=(n-FONT_FIRST_TILE+1)*32
            if end>len(graphics):
                start=0x70000+FONT_FIRST_TILE*32+len(graphics)
                graphics.extend(source[start:0x70000+(n+1)*32])
            graphics[end-32:end]=data
        return 0x3400|indices[data]

    color_used={e&1023 for base in (0xAB800,0xAC000,0xAC800)
                for e in struct.unpack_from('<1024H',source,base)}
    if color_used & set(range(COLOR_FIRST_TILE,0x200)):
        raise ValueError('Native BG3 maps use reserved masked-background characters')
    colors=[];color_indices={}

    def color_tile(pixels,palette):
        data=encode_tile(pixels)[:16]
        if data==bytes(16):return 0x1ff
        if data not in color_indices:
            n=COLOR_FIRST_TILE+len(colors)
            if n>=0x1ff:raise ValueError('Masked backgrounds exceed free BG3 characters')
            color_indices[data]=n;colors.append(data)
        return (palette&0x3c00)|color_indices[data]

    mask=silver_clear_mask(source);frame=frame_pixels(source)
    records=bytearray();color_maps=[]
    rf=struct.unpack_from('<12H',frames,32)
    for maps,doctors,col in timer_layouts(source,solo_maps):
        color_map=bytearray(maps[1])
        for y in range(4):
            struct.pack_into('<6H',color_map,(23+y)*64+col*2,*([0x1ff]*6))
        for y,x in BORDER_CELLS:
            doctor=doctors[x//3]
            if doctor:
                # Gold side cells contain no numeral pixels.
                if y in (0,3):entry=rf[(0 if y==0 else 6)+x]
                else:
                    off=0x400+(y-1)*6+(0 if x==0 else 4)
                    entry=struct.unpack_from('<H',minutes if x==0 else seconds,off)[0]
            else:
                bg_entry=struct.unpack_from('<H',maps[0],(23+y)*64+(col+x)*2)[0]
                if bg_entry&0x1c00!=0x1400:
                    raise ValueError('Silver background must share the native metal palette')
                background=map_pixels(source,bg_entry)
                ce=struct.unpack_from('<H',maps[1],(23+y)*64+(col+x)*2)[0]
                tint=map_pixels(source,ce,True)
                pixels=[];masked=[]
                for dy in range(8):
                    pixels.append([background[dy][dx] if mask[y*8+dy][x*8+dx]
                                   else frame[y*8+dy][x*8+dx] for dx in range(8)])
                    masked.append([tint[dy][dx] if mask[y*8+dy][x*8+dx] else 0
                                   for dx in range(8)])
                entry=metal_tile(pixels)
                struct.pack_into('<H',color_map,(23+y)*64+(col+x)*2,color_tile(masked,ce))
            records.extend(struct.pack('<H',entry))
        color_maps.append(bytes(color_map))
    return bytes(graphics),bytes(records),b''.join(colors),color_maps
