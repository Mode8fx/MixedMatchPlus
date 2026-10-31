"""Composite fixed timer borders with the native background at their edges."""
import struct

from build_rom import decode_tile, encode_tile
from timer import FONT_FIRST_TILE, PADDING_MAP_TILES, frame_pixels, DOCTOR_GRAY_PENS, SOLO_FRAME_PENS
from timer_padding import timer_layouts
from game_over import POPUP_PENS, build_popup
from timer_shadow import shadow_mask, shadow_tint_cell, SHADOW_CELLS

# Only these cells contain frame pixels; the eight numeral cells stay dynamic.
BORDER_CELLS = tuple((y,x) for y in range(4) for x in range(6)
                     if y in (0,3) or x in (0,5))
COLOR_FIRST_TILE = 0x180
GOLD_PENS = SOLO_FRAME_PENS
GOLD_LEFT_PENS = {2:1,3:1,4:1,5:3,9:4}
GOLD_RIGHT_PENS = {2:1,3:3,4:6,5:4,9:5}
# Subtract from the light-gold pen to retain the original orange RGB.
ORANGE_SUBTRACT = 0x58E0


def gold_frame_pens(two=False,right=False):
    return (GOLD_RIGHT_PENS if right else GOLD_LEFT_PENS) if two else GOLD_PENS


def gold_background_pens(two=False):
    if not two:return {(5,p):i+7 for i,p in enumerate(range(9,16))}
    return ({(5,p):i+5 for i,p in enumerate((10,12,13,15))}
            |{(5,11):2,(5,9):4}|{(6,p):p for p in (2,7,8,9,13,14,15)})


def gold_palette(source, two=False):
    """Composite colors; the native popup is relocated to its own spare pens."""
    palette=[0]*16
    frame_pens=GOLD_LEFT_PENS if two else GOLD_PENS
    for native,pen in frame_pens.items():
        if two and native in (3,4):continue
        off=(0x194a0+DOCTOR_GRAY_PENS[native]*2 if native in DOCTOR_GRAY_PENS
             else 0x194a4 if native==9 else 0x19460+native*2)
        palette[pen]=struct.unpack_from('<H',source,off)[0]
    for (bank,native),pen in gold_background_pens(two).items():
        if two and bank==6:continue
        palette[pen]=struct.unpack_from('<H',source,0x19400+(bank*16+native)*2)[0]
    if not two:
        palette[14]=0
        palette[15]=struct.unpack_from('<H',source,0x19506)[0]
    return struct.pack('<8H',*palette[1:9]) if two else struct.pack('<16H',*palette)


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


def build_border(source, solo_maps, graphics, frames, minutes, seconds, two_mode, color_state):
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
            forbidden=({5,6,7} if palette==0 else set(POPUP_PENS) if palette==1 else set(range(1,9)) if palette==4
                       else set(GOLD_RIGHT_PENS.values()) if palette==6 else set())
            if forbidden and any(p in forbidden for row in decode_tile(source,e&1023,0x70000) for p in row):
                raise ValueError('Native graphics use a reserved gold-edge palette pen')
    for base in (0xAB800,0xAC000,0xAC800):
        for e in set(struct.unpack_from('<1024H',source,base)):
            if any(((e>>10)&7)*4+p in (5,6,7,*(16+n for n in POPUP_PENS))
                   for row in map_pixels(source,e,True) for p in row if p):
                raise ValueError('Native BG3 uses the gold shading palette')
    light,yellow=(struct.unpack_from('<H',source,0x19460+p*2)[0] for p in (2,3))
    if light-yellow!=0x4000:
        raise ValueError('Expected the native gold shades to differ by sixteen blue levels')
    orange=struct.unpack_from('<H',source,0x19468)[0]
    if light-orange!=ORANGE_SUBTRACT:
        raise ValueError('Expected the native orange shading difference')
    if source[0x1941e:0x19420]!=source[0x1943e:0x19440]:
        raise ValueError('Expected matching native background tints 15/31')
    colors,color_indices=color_state

    def color_tile(pixels,palette):
        data=encode_tile(pixels)[:16]
        if data==bytes(16):return 0x1ff
        if data not in color_indices:
            n=COLOR_FIRST_TILE+len(colors)
            if n>=0x1ff:raise ValueError('Masked backgrounds exceed free BG3 characters')
            color_indices[data]=n;colors.append(data)
        return (palette&0x3c00)|color_indices[data]

    records=bytearray();color_maps=[];shadow_maps=[]
    for layout,(maps,doctors,col) in enumerate(timer_layouts(source,solo_maps)):
        two=layout>=3
        if two!=two_mode:
            records.extend(bytes(32));color_maps.append(bytes(0x800))
            shadow_maps.append(bytes(0x800));continue
        art=[frame_pixels(source,doctor,two) for doctor in doctors]
        shadow=shadow_mask(source,doctors,two,maps,col)
        shadow_map=bytearray(maps[1])
        # Also retain shadow-only versions of the compact gold bottom cells:
        # the alternate map exposes their last scanline below the frame.
        for y,x in (*SHADOW_CELLS,*((3,x) for x in range(6))):
            tint,attributes=shadow_tint_cell(source,maps,shadow,doctors,two,col,y,x)
            struct.pack_into('<H',shadow_map,(23+y)*64+(col+x)*2,color_tile(tint,attributes))
        color_map=bytearray(maps[1])
        for y,x in SHADOW_CELLS:
            off=(23+y)*64+(col+x)*2
            color_map[off:off+2]=shadow_map[off:off+2]
        for y in range(4):
            struct.pack_into('<6H',color_map,(23+y)*64+col*2,*([0x1ff]*6))
        for y,x in BORDER_CELLS:
            doctor=doctors[x//3]
            bg_entry=struct.unpack_from('<H',maps[0],(23+y)*64+(col+x)*2)[0]
            if not doctor and bg_entry&0x1c00!=0x1400:
                raise ValueError('Silver background must share the native metal palette')
            background=map_pixels(source,bg_entry)
            ce=struct.unpack_from('<H',maps[1],(23+y)*64+(col+x)*2)[0]
            tint,tint_attributes=shadow_tint_cell(source,maps,shadow,doctors,two,col,y,x)
            pixels=[];masked=[]
            frame=art[x//3]
            background_pens=gold_background_pens(two)
            frame_pens=gold_frame_pens(two,x>=3)
            shade_gold=doctor and two and x<3
            for dy in range(8):
                pixels.append([]);masked.append([])
                for dx in range(8):
                    yy,xx=y*8+dy,x*8+dx
                    pixel_frame=frame[yy][xx]
                    # Compact gold has no artwork on these scanlines. HDMA
                    # selects the original maps there, preserving native tint
                    # palettes that do not fit alongside the gold shading.
                    if doctor and two and yy in (0,1,31):pixel_frame=9
                    outside=pixel_frame is None
                    if outside:
                        background_pixel=background[dy][dx]
                        pair=((bg_entry>>10)&7,background_pixel)
                        if doctor:
                            if pair not in background_pens:
                                raise ValueError(f'Gold-edge background exceeds its reserved palette: {pair}')
                            pixel=background_pens[pair]
                        else:pixel=background_pixel
                    else:pixel=frame_pens[pixel_frame] if doctor else pixel_frame
                    pixels[-1].append(pixel)
                    if shade_gold:
                        if outside:
                            p=tint[dy][dx]
                            tint_index=((tint_attributes>>10)&7)*4+p if p else 0
                            if tint_index not in (0,15,31):raise ValueError(f'Unexpected P1 gold-edge background tint {tint_index} at {layout,y,x,dy,dx}')
                            masked[-1].append(1 if tint_index else 0)
                        else:masked[-1].append({3:3,4:2}.get(pixel_frame,0))
                    else:masked[-1].append(tint[dy][dx] if outside else 0)
            attributes=(0x3000 if x<3 else 0x3800) if two else 0x3c00
            entry=metal_tile(pixels,attributes if doctor else 0x3400)
            tint_palette=(ce&0x2000)|0x400 if shade_gold else tint_attributes
            struct.pack_into('<H',color_map,(23+y)*64+(col+x)*2,color_tile(masked,tint_palette))
            records.extend(struct.pack('<H',entry))
        color_maps.append(bytes(color_map))
        shadow_maps.append(bytes(shadow_map))
    right=[struct.unpack_from('<H',source,0x19460+n*2)[0] for n in (2,3,5)]
    right.extend((struct.unpack_from('<H',source,0x194a4)[0],
                  struct.unpack_from('<H',source,0x19468)[0]))
    palettes=gold_palette(source)+gold_palette(source,True)+struct.pack('<5H',*right)
    popup=build_popup(source,metal_tile) if two_mode else b''
    return bytes(graphics),bytes(records),b''.join(colors),color_maps,palettes,popup,shadow_maps
