"""Composite fixed timer borders with the native background at their edges."""
import struct
from collections import deque

from build_rom import decode_tile, encode_tile
from timer import FONT_FIRST_TILE, PADDING_MAP_TILES, frame_pixels
from timer_padding import timer_layouts

# Only these cells contain frame pixels; the eight numeral cells stay dynamic.
BORDER_CELLS = tuple((y,x) for y in range(4) for x in range(6)
                     if y in (0,3) or x in (0,5))
COLOR_FIRST_TILE = 0x180
GOLD_PENS = {2:1,3:2,5:3,9:4}
GOLD_LEFT_PENS = {2:1,3:1,5:3,9:4}
GOLD_RIGHT_PENS = {2:1,3:3,5:4,9:5}


def gold_frame_pens(two=False,right=False):
    return (GOLD_RIGHT_PENS if right else GOLD_LEFT_PENS) if two else GOLD_PENS


def gold_background_pens(two=False):
    if not two:return {(5,p):i+5 for i,p in enumerate(range(9,16))}
    return ({(5,p):i+5 for i,p in enumerate((10,12,13,15))}
            |{(5,11):2}|{(6,p):p for p in (2,7,8,9,13,14,15)})


def gold_palette(source, two=False):
    """Use only pens unreferenced by the native foreground/background art."""
    palette=[0]*16
    for native,pen in GOLD_PENS.items():
        if two and native==3:continue
        palette[pen]=struct.unpack_from('<H',source,0x19460+native*2)[0]
    palette[4]=struct.unpack_from('<H',source,0x194a4)[0]
    for (bank,native),pen in gold_background_pens(two).items():
        if two and bank==6:continue
        palette[pen]=struct.unpack_from('<H',source,0x19400+(bank*16+native)*2)[0]
    return struct.pack('<8H',*palette[1:9]) if two else struct.pack('<16H',*palette)


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

    def metal_tile(pixels,attributes=0x3400):
        data=encode_tile(pixels)
        if data not in indices:
            n=next(available,None)
            if n is None:raise ValueError('Background composites exceed free timer tiles')
            indices[data]=n
            end=(n-FONT_FIRST_TILE+1)*32
            if end>len(graphics):
                start=0x70000+FONT_FIRST_TILE*32+len(graphics)
                graphics.extend(source[start:0x70000+(n+1)*32])
            graphics[end-32:end]=data
        return attributes|indices[data]

    color_used={e&1023 for base in (0xAB800,0xAC000,0xAC800)
                for e in struct.unpack_from('<1024H',source,base)}
    if color_used & set(range(COLOR_FIRST_TILE,0x200)):
        raise ValueError('Native BG3 maps use reserved masked-background characters')
    for base in (0xA8800,0xA9000,0xA9800,0xAA000,0xAA800):
        for e in set(struct.unpack_from('<1024H',source,base)):
            palette=(e>>10)&7
            forbidden=({5,6,7} if palette==0 else set(range(1,9)) if palette==4
                       else set(GOLD_RIGHT_PENS.values()) if palette==6 else set())
            if forbidden and any(p in forbidden for row in decode_tile(source,e&1023,0x70000) for p in row):
                raise ValueError('Native graphics use a reserved gold-edge palette pen')
    for base in (0xAB800,0xAC000,0xAC800):
        for e in set(struct.unpack_from('<1024H',source,base)):
            if any(((e>>10)&7)*4+p in (5,6,7)
                   for row in map_pixels(source,e,True) for p in row if p):
                raise ValueError('Native BG3 uses the gold shading palette')
    light,yellow=(struct.unpack_from('<H',source,0x19460+p*2)[0] for p in (2,3))
    if light-yellow!=0x4000:
        raise ValueError('Expected the native gold shades to differ by sixteen blue levels')
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
    for layout,(maps,doctors,col) in enumerate(timer_layouts(source,solo_maps)):
        color_map=bytearray(maps[1])
        for y in range(4):
            struct.pack_into('<6H',color_map,(23+y)*64+col*2,*([0x1ff]*6))
        for y,x in BORDER_CELLS:
            doctor=doctors[x//3]
            if doctor and x not in (0,5):
                entry=rf[(0 if y==0 else 6)+x]
            else:
                bg_entry=struct.unpack_from('<H',maps[0],(23+y)*64+(col+x)*2)[0]
                if not doctor and bg_entry&0x1c00!=0x1400:
                    raise ValueError('Silver background must share the native metal palette')
                background=map_pixels(source,bg_entry)
                ce=struct.unpack_from('<H',maps[1],(23+y)*64+(col+x)*2)[0]
                tint=map_pixels(source,ce,True)
                pixels=[];masked=[]
                gold=frame_pixels(source,True) if doctor else None
                background_pens=gold_background_pens(layout>=3)
                frame_pens=gold_frame_pens(layout>=3,x==5)
                shade_gold=doctor and layout>=3 and x==0
                for dy in range(8):
                    pixels.append([]);masked.append([])
                    for dx in range(8):
                        yy,xx=y*8+dy,x*8+dx
                        if doctor:
                            outside=(xx<2 or xx>=46) and 2<=yy<30
                            if outside:
                                pair=((bg_entry>>10)&7,background[dy][dx])
                                if pair not in background_pens:
                                    raise ValueError('Gold-edge background exceeds its reserved palette')
                                pixel=background_pens[pair]
                            else:pixel=frame_pens.get(gold[yy][xx],frame_pens[9])
                        else:
                            outside=mask[yy][xx]
                            pixel=background[dy][dx] if outside else frame[yy][xx]
                        pixels[-1].append(pixel)
                        if shade_gold:
                            if outside:
                                p=tint[dy][dx]
                                tint_index=((ce>>10)&7)*4+p if p else 0
                                if tint_index not in (15,31):
                                    raise ValueError('Unexpected gold-edge background tint')
                                masked[-1].append(1 if tint_index==15 else 2)
                            else:masked[-1].append(3 if gold[yy][xx]==3 else 0)
                        else:masked[-1].append(tint[dy][dx] if outside else 0)
                attributes=(0x3000 if x==0 else 0x3800) if layout>=3 else 0x3c00
                entry=metal_tile(pixels,attributes if doctor else 0x3400)
                tint_palette=(ce&0x2000)|0x400 if shade_gold else ce
                struct.pack_into('<H',color_map,(23+y)*64+(col+x)*2,color_tile(masked,tint_palette))
            records.extend(struct.pack('<H',entry))
        color_maps.append(bytes(color_map))
    right=struct.unpack('<16H',gold_palette(source))
    palettes=gold_palette(source)+gold_palette(source,True)+struct.pack('<4H',*right[1:5])
    return bytes(graphics),bytes(records),b''.join(colors),color_maps,palettes
