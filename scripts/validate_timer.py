"""Check the actual rendered countdown, its native font, and both play layouts."""
import struct

from build_rom import OUTPUT, ROOT, SOURCE, decode_tile
from verify_menu import Emulator
from timer import frame_pixels, FONT_FIRST_TILE, GLYPH_X, font_colors
from timer_border import silver_clear_mask, map_pixels, gold_frame_pens
from timer_padding import timer_layouts


def timer_column(ram):
    return 13


def timer_screen_x(ram):
    return 104 if ram[0x1ef0] else (176 if ram[0x3f1]==3 else 184)


def timer_styles(ram):
    left=ram[0x3f1]==3
    return left,ram[0x8f1]==3 if ram[0x1ef0] else left


def displayed_timer_pixel(r,v,col,x,y,pixel_format=2):
    """Read the selected BG2/BG3 maps, including the four background bands."""
    padding=r[0x1efe] and y in (0,1,30,31)
    row,dy=divmod(184+y,8);column=col+x//8;dx=x%8
    entry=struct.unpack_from('<H',v,(0x1800 if padding else 0x800)+row*64+column*2)[0]
    glyph=decode_tile(v,entry&1023,0x2000)
    p=glyph[7-dy if entry&0x8000 else dy][7-dx if entry&0x4000 else dx]
    main=struct.unpack_from('<H',r,0x1500+(((entry>>10)&7)*16+p if p else 0)*2)[0]
    sub=0
    entry=struct.unpack_from('<H',v,(0x8800 if padding else 0x1000)+row*64+column*2)[0]
    dy=(184+y)%8;dx=x%8
    dy=7-dy if entry&0x8000 else dy;dx=7-dx if entry&0x4000 else dx
    off=0xa000+(entry&1023)*16+dy*2
    p=((v[off]>>(7-dx))&1)|(((v[off+1]>>(7-dx))&1)<<1)
    if p:sub=struct.unpack_from('<H',r,0x1500+(((entry>>10)&7)*4+p)*2)[0]
    red,green,blue=(max(0,((main>>shift)&31)-((sub>>shift)&31)) for shift in (0,5,10))
    if pixel_format==2:
        return red*255//31,(green*2+(green>>4))*255//63,blue*255//31
    return red*255//31,green*255//31,blue*255//31


def verify_frame_design(source):
    clear=silver_clear_mask(source)
    assert all(clear[0]) and all(clear[31]), 'Outer padding is not cleared'
    assert all(clear[y][x] for y in range(9,23) for x in (0,47)), 'Black side padding remains'
    assert not any(clear[y][x] for y in range(8,24) for x in range(8,40)), 'Background mask cuts into the numerals'
    for doctor in (False,True):
        frame=frame_pixels(source,doctor)
        body=9 if doctor else 3
        assert all(row==row[::-1] for row in frame), 'Timer frame is not horizontally symmetric'
        for x in range(10,38):
            assert [y for y in range(2,8) if frame[y][x]!=body]==[2,3,4], 'Top rail is not exactly three pixels'
            assert [y for y in range(24,30) if frame[y][x]!=body]==[27,28,29], 'Bottom rail is not exactly three pixels'
        for y in range(9,23):
            expected=[2,3,4,43,44,45]
            assert [x for x in range(48) if frame[y][x] not in ((body,8) if doctor else (body,))]==expected, 'Side rails are not exactly three pixels'
        assert not any(frame[y][x]!=body for y in range(9,23) for x in range(8,40)), 'Frame intrudes into the numerals'
        for y in (2,3):
            assert frame[y][16]!=frame[y+1][16], 'Bevel gradient lost a shade'
        if doctor:
            assert frame==frame[::-1], 'Gold frame is not vertically symmetric'
            assert all(all(p==8 for p in frame[y]) for y in (0,1,30,31)), 'Gold frame protrudes into background bands'
        else:
            # Reassemble the ORIGINAL source tiles independently of the frame
            # builder. The 8x8 corner crosses tile boundaries; all colors,
            # including its original dark edge, must survive unchanged.
            flat=decode_tile(source,0x232,0x70000)
            top=decode_tile(source,0x236,0x70000)
            top_side=decode_tile(source,0x238,0x70000)
            bottom=decode_tile(source,0x23c,0x70000)
            bottom_side=decode_tile(source,0x23a,0x70000)
            for dy in range(8):
                tr=flat[dy+1][6:]+top[dy+1][:6] if dy<7 else [0,0]+top_side[0][:6]
                br=[0,0]+bottom_side[dy+6][:6] if dy<2 else flat[dy-2][6:]+bottom[dy-2][:6]
                assert frame[dy+1][39:47]==[p or 3 for p in tr], 'Top native corner was recolored, scaled or moved'
                assert frame[dy+23][39:47]==[p or 3 for p in br], 'Bottom native corner was recolored or scaled'
            assert [y for y in range(8) if frame[y][39]!=body]==[1,2,3,4,5], 'Top connector is not five pixels'
            assert [y for y in range(24,32) if frame[y][39]!=body]==[26,27,28,29,30], 'Bottom connector is not five pixels'
            assert all(frame[8][x]==15 for x in range(42,47)), 'Five-pixel side connector changed'
    # Count the actual visible art, including corner caps rather than padding.
    widths=[]
    for doctor in (False,True):
        frame=frame_pixels(source,doctor);void=8 if doctor else 3
        columns=[x for x in range(48) if any(row[x]!=void for row in frame)]
        assert (min(columns),max(columns))==((2,45) if doctor else (1,46)), 'Timer does not have the requested inset'
        widths.append(max(columns)-min(columns)+1)
    assert widths==[46,44], 'Timer widths do not match the requested sizes'


def check_timer(e, minutes=None, seconds=None):
    r=e.memory();v=e.memory(3);source=SOURCE.read_bytes()
    minutes=r[0x40a] if minutes is None else minutes
    seconds=r[0x409] if seconds is None else seconds
    col=timer_column(r)
    styles=timer_styles(r)
    clear=silver_clear_mask(source)
    # Reconstruct BG2 from uploaded graphics, checking source glyph pixels,
    # exact centering, opaque backing, and the two subscreen cutouts.
    pixels=[]
    for row in range(23,27):
        line=[[] for _ in range(8)]
        for x in range(col,col+6):
            entry=struct.unpack_from('<H',v,0x800+row*64+x*2)[0]
            doctor=styles[(x-col)//3]
            edge_attributes=(0x3000 if x==col else 0x3800) if r[0x1ef0] else 0x3c00
            attributes=(edge_attributes if x in (col,col+5) else 0x2c00) if doctor else 0x3400
            assert entry&0x3c00==attributes, 'Wrong player/game timer style'
            glyph=decode_tile(v,entry&0x3ff,0x2000)
            if entry&0x4000:glyph=[row[::-1] for row in glyph]
            for y in range(8):line[y].extend(glyph[y])
            assert struct.unpack_from('<H',v,row*64+x*2)[0]==0, 'Divider crosses timer'
            ce=struct.unpack_from('<H',v,0x1000+row*64+x*2)[0]
            assert ce==0x1ff or 0x180<=ce&1023<0x1ff, 'Timer color cutout lost'
        pixels.extend(line)
    native_frames=[frame_pixels(source,doctor) for doctor in styles]
    for y in range(32):
        for x in range(48):
            if y<8 or y>=24 or x<8 or x>=40:
                doctor=styles[x//24]
                outside=(x<2 or x>=46 or y in (0,1,30,31)) if doctor else clear[y][x]
                if not outside:
                    pixel=pixels[y][x]
                    expected=native_frames[x//24][y][x]
                    if doctor and x//8 in (0,5):
                        expected=gold_frame_pens(bool(r[0x1ef0]),x//8==5)[expected]
                    assert pixel==expected, 'Native timer frame art incorrect'
    for i,n in ((0,minutes//10),(1,minutes%10),(3,seconds//10),(4,seconds%10)):
        native=decode_tile(source,0x130+n,0x70000)+decode_tile(source,0x140+n,0x70000)
        actual=[row[GLYPH_X[i]:GLYPH_X[i]+7] for row in pixels[8:24]]
        ink,shadow,body=font_colors(styles[i//3])
        assert len({ink,shadow,body})==3, 'Timer drop shadow disappeared into face/background'
        assert actual==[[ink if p==1 else shadow if p==3 else body for p in row[:7]] for row in native], f'Timer lost native glyph/drop-shadow pixels: clock={minutes}:{seconds:02}, glyph={i}, two={r[0x1ef0]}, styles={styles}, queued={r[0x1dc0:0x1dc2].hex()}, key={r[0x1efc:0x1eff].hex()}'
    # The colon also has a two-pixel right/down cast shadow, with its pixels
    # using the appropriate player style on either side of the center seam.
    for y in range(16):
        for x in range(4):
            ink,shadow,body=font_colors(styles[(22+x)//24])
            expected=ink if y in (4,5,10,11) and x<2 else shadow if y in (6,7,12,13) and x>=2 else body
            assert pixels[y+8][22+x]==expected, 'Colon shadow/face is incorrect'
    assert r[0x1572:0x1574]==source[0x194a4:0x194a6], 'Gold timer paper differs from native HUD paper'
    assert r[0x1574:0x1576]==source[0x19506:0x19508], 'Gold timer shadow differs from native Dr. Mario shadow'
    assert r[0x1560:0x1572]==source[0x19460:0x19472] and r[0x1576:0x1580]==source[0x19476:0x19480], 'Native gold frame palette was changed'
    assert v[0xbff0:0xc000]==bytes(16), 'BG3 transparent tile was not loaded'
    rom=OUTPUT.read_bytes()
    if r[0x1ef0]:
        assert r[0x1582:0x1592]==rom[0xe1620:0xe1630], 'Gold left-edge palette pens were not loaded'
        actual=b''.join(r[a:a+2] for a in (0x15c2,0x15c6,0x15c8,0x15ca))
        assert actual==rom[0xe1630:0xe1638], 'Gold right-edge palette pens were not loaded'
        if any(styles):
            assert r[0x150a:0x150c]==r[0x151e:0x1520], 'Gold background tint 15 is stale'
            assert r[0x150c:0x150e]==r[0x153e:0x1540], 'Gold background tint 31 is stale'
            assert r[0x150e:0x1510]==b'\x00\x40', 'Gold yellow-shade subtraction changed'
    else:
        assert r[0x15e0:0x1600]==rom[0xe1600:0xe1620], 'Solo gold-edge palette was not loaded'
    expected_x=timer_screen_x(r)
    shift=0 if r[0x1ef0] else (72 if r[0x3f1]==3 else 80)
    assert col*8+shift==expected_x
    picture=e.screenshot(ROOT/'custom'/'research'/'timer-check.png')
    # Verify every actual screen pixel against the native frame palette, so
    # checkerboard/subscreen color subtraction cannot damage either half.
    assert bool(r[0x1efe])==any(styles), 'Background-band HDMA does not follow frame styles'
    assert not r[0x34]&0x20, 'Timer padding must not enable scroll-register HDMA'
    for y in range(32):
        for x in range(48):
            expected=displayed_timer_pixel(r,v,col,x,y,e.pixel_format)
            assert picture.getpixel((expected_x+x,184+y))==expected, f'Timer frame/background tinted or obscured at {(x,y)}'
            if styles[x//24] and 2<=x<46 and 2<=y<30 and (y<8 or y>=24 or x<8 or x>=40):
                color=native_frames[x//24][y][x]
                word=struct.unpack_from('<H',r,0x1560+color*2)[0]
                red,green,blue=((word>>shift)&31 for shift in (0,5,10))
                native_rgb=(red*255//31,(green*2+(green>>4))*255//63,blue*255//31) if e.pixel_format==2 else (red*255//31,green*255//31,blue*255//31)
                assert picture.getpixel((expected_x+x,184+y))==native_rgb, 'Gold bevel/paper differs from its original native RGB colors'
    # Independently reconstruct the unmodified native background at every
    # removed exterior pixel, including the pixels around the native silver corners.
    solo_maps={n:(OUTPUT.read_bytes()[base:base+0x800],b'')
               for n,base in ((1,0xe4000),(3,0xe5000),(5,0xe6000))}
    for n,base in ((1,0xac000),(3,0xac800),(5,0xab800)):
        bg3=bytearray(source[base:base+0x800])
        for yy in range(32):
            for xx in range(16,32):
                ce=struct.unpack_from('<H',source,base+(8+yy%4)*64+(xx%2)*2)[0] if n==3 else struct.unpack_from('<H',source,base+10*64)[0]
                struct.pack_into('<H',bg3,yy*64+xx*2,ce)
        solo_maps[n]=(solo_maps[n][0],bytes(bg3))
    maps,_,_=timer_layouts(source,solo_maps)[r[0x1efc]]
    for y in range(32):
        for x in range(48):
            outside=(x<2 or x>=46 or y in (0,1,30,31)) if styles[x//24] else clear[y][x]
            if not outside:continue
            values=[]
            for layer in (0,1):
                entry=struct.unpack_from('<H',maps[layer],(23+y//8)*64+(col+x//8)*2)[0]
                p=map_pixels(source,entry,bool(layer))[y%8][x%8]
                palette=((entry>>10)&7)*(4 if layer else 16)
                values.append(struct.unpack_from('<H',r,0x1500+(palette+p if p else 0)*2)[0] if p or not layer else 0)
            rgb=[max(0,((values[0]>>shift)&31)-((values[1]>>shift)&31)) for shift in (0,5,10)]
            expected=(rgb[0]*255//31,(rgb[1]*2+(rgb[1]>>4))*255//63,rgb[2]*255//31) if e.pixel_format==2 else tuple(c*255//31 for c in rgb)
            assert picture.getpixel((expected_x+x,184+y))==expected, f'Cleared silver padding does not match native background at {(x,y)}'
    if any(styles):
        index=r[0x1efc]
        for i,destination in enumerate((0x1dc0,0x1e80,0x8dc0,0x8e80)):
            start=0xe7000+index*256+i*64
            assert v[destination:destination+64]==OUTPUT.read_bytes()[start:start+64], 'Wrong restored background rows'
        for half,doctor in enumerate(styles):
            if doctor:
                # A native decorative strip has multiple shades; the old
                # opaque black backing cannot satisfy this visual check.
                colors={picture.getpixel((expected_x+half*24+x,184+y))
                        for x in range(24) for y in (0,1,30,31)}
                assert len(colors)>3, 'Black bars remain outside the gold frame'
    return picture.crop((expected_x,184,expected_x+48,216))


def verify_timer(core):
    from validate_single_player import menu,press,active,until
    dest=ROOT/'custom'/'validation'
    source=SOURCE.read_bytes()
    verify_frame_design(source)
    native_tiles={entry&0x3ff for base in (0xA8800,0xA9000,0xA9800,0xAA000,0xAA800)
                  for entry in struct.unpack_from('<1024H',source,base)
                  if FONT_FIRST_TILE<=entry&0x3ff<0x300}
    for custom in (False,True):
        for two in (False,True):
            e=Emulator(core,OUTPUT)
            try:
                menu(e,custom)
                if two:press(e,7)
                if custom:
                    for _ in range(8):press(e,5)
                    # The native custom range is 1..30 minutes, not just 1..9.
                    for _ in range(30):press(e,7)
                    assert e.memory()[0x1eb6]==30
                press(e,3);active(e,1);e.run(4)
                press(e,3);assert e.memory()[0x304]==0x40
                for minutes,seconds in [(n,0) for n in range(31)]+[(0,n) for n in range(60)]:
                    e.write_memory(0x408,bytes((29,seconds,minutes)));e.run(4)
                    check_timer(e,minutes,seconds)
                e.write_memory(0x408,bytes((59,0,10)));e.run(2)
                before=check_timer(e,10,0);clock=e.memory()[0x408:0x40b]
                e.run(60)
                assert clock==e.memory()[0x408:0x40b], 'Pause did not freeze native timer'
                assert list(before.getdata())==list(check_timer(e,10,0).getdata())
                press(e,3);e.run(60)
                assert e.memory()[0x409:0x40b]==bytes((59,9)), '10:00 to 09:59 rollover incorrect'
                e.run(2);check_timer(e,9,59)
                for stage in (1,3,5):
                    if stage!=1:
                        e.write_memory(0x305,b'\x0b\x00');e.write_memory(0x316,b'\x01')
                        active(e,stage);e.run(4)
                    check_timer(e)
                    vram=e.memory(3)
                    for tile in native_tiles:
                        # Existing solo cleanup intentionally edits these shared
                        # divider/frame tiles after the font load; its pixel
                        # invariants are checked by background_capture().
                        if not two and tile in (0x1a5,0x1b5,0x2c8,0x236,0x238,0x23a,0x23c,0x23e):continue
                        assert vram[0x2000+tile*32:0x2000+(tile+1)*32]==source[0x70000+tile*32:0x70000+(tile+1)*32], f'Timer upload damaged native decorative character {tile:03x}'
                    prefix=('custom' if custom else 'normal')+('-two-player' if two else '-solo')
                    e.screenshot(dest/f'{prefix}-timer-stage-{stage}.png')
                    if two and stage!=1:
                        # Exercise independently transitioning opponents too.
                        e.write_memory(0x805,b'\x0b\x00');e.write_memory(0x816,b'\x01')
                        until(e,lambda r:r[0x8f1]==stage and r[0x805]==5 and r[0x806]==1)
                        e.run(4);check_timer(e)
                        e.screenshot(dest/f'{prefix}-timer-stage-{stage}-both.png')
                    if stage==3:
                        # Exercise the second template bank at its boundaries,
                        # with both halves gold (including the 30-minute limit).
                        press(e,3);assert e.memory()[0x304]==0x40
                        # Switching maps for four complete scanlines must not
                        # alter either playfield or the surrounding decoration.
                        before=e.screenshot(ROOT/'custom'/'research'/'padding-enabled.png')
                        e.write_memory(0x1ef4,b'\x00');e.run(2)
                        without=e.screenshot(ROOT/'custom'/'research'/'padding-disabled.png')
                        left=timer_screen_x(e.memory())
                        for y in (184,185,214,215):
                            for x in range(256):
                                if not left<=x<left+48:
                                    assert before.getpixel((x,y))==without.getpixel((x,y)), f'Background-band switch changed native graphics at {(x,y)}, two={two}'
                        e.write_memory(0x1ef4,b'\x01');e.run(4)
                        clock=e.memory()[0x408:0x40b]
                        for mm,ss in ((30,59),(10,0),(0,0),(9,59),(1,8),(23,45)):
                            e.write_memory(0x408,bytes((29,ss,mm)));e.run(4)
                            check_timer(e,mm,ss)
                        e.write_memory(0x408,clock);e.run(32);press(e,3);e.run(4)
                # 00:00 remains legible through the native end-of-time sequence.
                e.write_memory(0x408,bytes((0,0,0)));e.run(4);check_timer(e,0,0)
                e.screenshot(dest/f'{prefix}-timer-zero.png')
                until(e,lambda r:r[0xbaf]==0x31)
            finally:e.close()
    print('PASS rendered timer: native 8x16 font and symmetric silver/gold frames/colors, all four player-stage combinations, both solo styles, minute/second digits, both routes, rollover, pause, transitions, expiry')
