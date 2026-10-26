"""Apply native one/two-player menus and solo Mixed Match engine hooks."""
from pathlib import Path
import struct
from assemble65816 import assemble
from snes_disasm import offset
from build_rom import decode_tile, encode_tile
from normal_menu import build_normal_menu
from custom_menu import build_music_row

ROOT=Path(__file__).resolve().parents[1]


def apply(rom: bytearray, source: bytes) -> list[tuple[int,int]]:
    # Solo initialization copies this native blank tile over divider tile $2C8.
    if source[0x70000:0x70020]!=bytes(32):
        raise ValueError('Expected transparent native graphics tile at $8E8000')
    spans,labels=assemble((ROOT/'patches'/'single_player.asm').read_text())
    ranges=[]
    def put(off,data):
        rom[off:off+len(data)]=data;ranges.append((off,off+len(data)))
    def text(s):
        return b''.join(struct.pack('<H',0x2000 if c==' ' else 0x2100+(int(c) if c.isdigit() else ord(c)-55)) for c in s)
    def hook(pc,label,size=3,opcode=0x20):
        addr=labels[label];width=3 if opcode in (0x22,0x5c) else 2
        data=bytes([opcode])+(addr&((1<<(width*8))-1)).to_bytes(width,'little')
        assert len(data)<=size
        put(offset(pc),data+b'\xea'*(size-len(data)))
    for pc,data in spans.items():
        off=offset(pc)
        if source[off:off+len(data)]!=b'\xff'*len(data):
            raise ValueError(f'Extension space is not blank at {pc:06X}')
        put(off,data)

    hook(0x8AE474,'normal_init',5,0x22)
    hook(0x8ADF76,'custom_init',5,0x22)
    hook(0x8AE48E,'normal_input',6)
    put(offset(0x8AE494),b'\x60')
    hook(0x8ADF90,'custom_input',6)
    put(offset(0x8ADF96),b'\x60')
    hook(0x8AE454,'normal_draw')
    hook(0x8AE71D,'normal_initial_maps')
    hook(0x8ADF56,'custom_draw')
    hook(0x8ACF90,'mixed_input_two',10)
    hook(0x8ACFA3,'mixed_controls_two',9)
    hook(0x8ACFBE,'mixed_second',15)
    hook(0x8ACFD0,'mixed_finish')
    hook(0x8ACFAC,'mixed_pause')
    hook(0x8AD735,'mixed_timer_two',6,0x4c)
    hook(0x8AD8F0,'solo_results',4,0x5c)
    hook(0x8AD027,'mixed_init_two',9)
    hook(0x83DD41,'mixed_sprites',4,0x5c)
    hook(0x83DF60,'normal_second_marker')
    hook(0x808945,'solo_display')
    hook(0x808951,'solo_windows')
    hook(0x8AD03C,'solo_initial_maps')
    put(offset(0x8AD36E),struct.pack('<H',labels['solo_reload_init'] & 0xffff))

    # Pixel layout, graphics, and focus cells come from the same native assets.
    menu_map,graphics,highlights=build_normal_menu(source)
    put(0xb2000,menu_map)
    for pc,data in ((0x9D8000,graphics),(0x9C9100,highlights)):
        off=offset(pc)
        if source[off:off+len(data)]!=b'\xff'*len(data):
            raise ValueError(f'Normal menu extension space is not blank at ${pc:06X}')
        put(off,data)
    put(offset(labels['normal_font_length'])+1,struct.pack('<H',len(graphics)))
    put(offset(0x83DF75),b'\x57')
    put(offset(0x83DF8D),b'\x6f')
    put(offset(0x83DFA8),b'\x95')
    put(offset(0x83DFC3),b'\xb8')

    # Custom menu: keep the native frame, space the count row, and use the spare
    # space for music. PLAY TIME keeps a blank row above and below.
    base=0xAE800
    rows=[source[base+i*64:base+(i+1)*64] for i in range(32)]
    new=rows.copy()
    custom_rows={3:6,4:7,6:8,7:9,8:10,10:11,12:12,13:13,15:14,17:15,18:18,19:19,20:20,21:21}
    for row in range(3,22):new[row]=rows[5]
    for old,dest in custom_rows.items():new[dest]=rows[old]
    new[17]=build_music_row(source)
    put(base,b''.join(new))
    off=offset(0x8AE3B8)
    values=struct.unpack_from('<13H',source,off)
    put(off,struct.pack('<13H',*(custom_rows[v//64]*64+v%64 for v in values)))

    put(offset(0x9C9040),text('1 PLAYER GAME'))
    put(offset(0x9C9060),text('BGM1BGM2BGM3OFF '))
    result=bytearray(source[0xB3000:0xB3780])
    # One score column, no opponent labels, judgement, or winner comparison.
    for row in range(4,28):
        for col in range(20,29):struct.pack_into('<H',result,row*64+col*2,0x2000)
    for row in (4,21,22,23,24,25,26):
        for col in range(2,29):struct.pack_into('<H',result,row*64+col*2,0x2000)
    for row in (16,17):
        for col in range(10,29):struct.pack_into('<H',result,row*64+col*2,0x2000)
    result[4*64+18:4*64+44]=text('1 PLAYER GAME')
    result[24*64+20:24*64+42]=text('PRESS START')
    put(offset(0x9C9800),result)
    # Checker pixels also share five tiles with the status-panel borders. Keep
    # their beveled frames and clear only the outer three-pixel checker strip.
    # Include the interleaved P2 counterparts unchanged for one contiguous DMA.
    panel_graphics=bytearray(source[0x746c0:0x74800])
    for tile in (0x236,0x238,0x23a,0x23c,0x23e):
        pixels=decode_tile(source,tile,0x70000)
        for row in pixels:
            for x in range(5,8):
                if row[x] in (3,9):row[x]=0
        start=(tile-0x236)*32
        panel_graphics[start:start+32]=encode_tile(pixels)
    off=offset(0x9CB000)
    if source[off:off+len(panel_graphics)]!=b'\xff'*len(panel_graphics):
        raise ValueError('Solo panel graphics space is not blank at $9CB000')
    put(off,panel_graphics)
    # LEVEL and HEIGHT carry the same separator in their last text tile, using
    # a different palette from the metal frames. Preserve the first five pixels
    # (the label) and erase the entire three-pixel divider at its right edge.
    label_graphics=bytearray()
    for tile in (0x1a5,0x1b5):
        pixels=decode_tile(source,tile,0x70000)
        for row in pixels:row[5:]=[0,0,0]
        label_graphics.extend(encode_tile(pixels))
    off=offset(0x9CB140)
    if source[off:off+len(label_graphics)]!=b'\xff'*len(label_graphics):
        raise ValueError('Solo label graphics space is not blank at $9CB140')
    put(off,label_graphics)
    # Extend only decorative maps. Their native left halves remain byte-identical,
    # and the unused right halves become background texture, never another field.
    for stage,bg2_source,bg3_source,destination in (
        (1,0xAA000,0xAC000,0x9CC000),
        (3,0xAA800,0xAC800,0x9CD000),
        (5,0xAA000,0xAB800,0x9CE000),
    ):
        bg2=bytearray(source[bg2_source:bg2_source+0x800])
        bg3=bytearray(source[bg3_source:bg3_source+0x800])
        for row in range(32):
            for col in range(16,32):
                index=row*64+col*2
                if stage==3:
                    # The native two-by-two diamond texture and its color layer.
                    tile2=struct.unpack_from('<H',source,bg2_source+(8+row%2)*64+(col%2)*2)[0]
                    tile3=struct.unpack_from('<H',source,bg3_source+(8+row%4)*64+(col%2)*2)[0]
                else:
                    # Preserve the full maze's geometry, using its body palette
                    # instead of the blue palette belonging to the score strip.
                    tile2=(struct.unpack_from('<H',bg2,index)[0]&~0x1c00)|0x1400
                    tile3=struct.unpack_from('<H',source,bg3_source+10*64)[0]
                struct.pack_into('<H',bg2,index,tile2)
                struct.pack_into('<H',bg3,index,tile3)
        maps=bg2+bg3
        off=offset(destination)
        if source[off:off+len(maps)]!=b'\xff'*len(maps):
            raise ValueError(f'Solo background space is not blank at {destination:06X}')
        put(off,maps)
    return ranges
