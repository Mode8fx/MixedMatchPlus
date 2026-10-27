"""Check the actual rendered countdown, its native font, and both play layouts."""
import struct

from build_rom import OUTPUT, ROOT, SOURCE, decode_tile
from verify_menu import Emulator
from timer import frame_pixels, FONT_FIRST_TILE, GLYPH_X, font_colors


def timer_column(ram):
    return 13 if ram[0x1ef0] else (14 if ram[0x3f1] == 3 else 13)


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
    if padding:
        entry=struct.unpack_from('<H',v,0x8800+row*64+column*2)[0]
        dy=7-dy if entry&0x8000 else dy;dx=7-dx if entry&0x4000 else dx
        off=0xa000+(entry&1023)*16+dy*2
        p=((v[off]>>(7-dx))&1)|(((v[off+1]>>(7-dx))&1)<<1)
        if p:sub=struct.unpack_from('<H',r,0x1500+(((entry>>10)&7)*4+p)*2)[0]
    red,green,blue=(max(0,((main>>shift)&31)-((sub>>shift)&31)) for shift in (0,5,10))
    if pixel_format==2:
        return red*255//31,(green*2+(green>>4))*255//63,blue*255//31
    return red*255//31,green*255//31,blue*255//31


def verify_native_frame_tiles(source):
    # Independent source-tile anchors: whole corners/connectors must survive,
    # rather than being reconstructed from a single sampled column.
    metal=frame_pixels(source,False);gold=frame_pixels(source,True)
    assert all(row[:24]==row[24:][::-1] for row in metal), 'Tetris frame halves are not mirrored'
    for tile,x,y in ((0x231,24,0),(0x232,32,0),(0x231,24,24),(0x232,32,24)):
        original=decode_tile(source,tile,0x70000)
        assert [row[x:x+8] for row in metal[y:y+8]]==[[p or 3 for p in row] for row in original], 'Native metal connector was cropped/redrawn'
    for tile,x,y,flip in ((0x37,0,0,False),(0x37,40,0,True),(0x4A,0,24,False),(0x4A,40,24,True),(0x49,0,8,False)):
        original=decode_tile(source,tile,0x70000)
        if flip:original=[row[::-1] for row in original]
        for dy,row in enumerate(original):
            for dx,p in enumerate(row):
                if p:assert gold[y+dy-2][x+dx]==p, 'Native gold corner/bevel did not move up two pixels'
    assert all(p==8 for row in gold[:2]+gold[30:] for p in row), 'Old gold frame/padding survived the move'
    assert gold[2][8:40]==[2]*32, 'Gold top edge is not aligned with the silver horizontal edge'
    assert all(p!=3 for p in metal[2][8:40]), 'Silver horizontal edge moved'
    assert gold[29][8:40]==[7]*32, 'Gold bottom edge is not aligned with the silver frame'


def check_timer(e, minutes=None, seconds=None):
    r=e.memory();v=e.memory(3);source=SOURCE.read_bytes()
    minutes=r[0x40a] if minutes is None else minutes
    seconds=r[0x409] if seconds is None else seconds
    col=timer_column(r)
    styles=timer_styles(r)
    # Reconstruct BG2 from uploaded graphics, checking source glyph pixels,
    # exact centering, opaque backing, and the two subscreen cutouts.
    pixels=[]
    for row in range(23,27):
        line=[[] for _ in range(8)]
        for x in range(col,col+6):
            entry=struct.unpack_from('<H',v,0x800+row*64+x*2)[0]
            doctor=styles[(x-col)//3]
            assert entry&0x3c00==(0x2c00 if doctor else 0x3400), 'Wrong player/game timer style'
            glyph=decode_tile(v,entry&0x3ff,0x2000)
            if entry&0x4000:glyph=[row[::-1] for row in glyph]
            for y in range(8):line[y].extend(glyph[y])
            assert struct.unpack_from('<H',v,row*64+x*2)[0]==0, 'Divider crosses timer'
            assert struct.unpack_from('<H',v,0x1000+row*64+x*2)[0]==0x1ff, 'Timer color cutout lost'
        pixels.extend(line)
    assert all(all(p for p in row) for row in pixels), 'Transparent timer backing'
    native_frames=[frame_pixels(source,doctor) for doctor in styles]
    for y in range(32):
        for x in range(48):
            if y<8 or y>=24 or x<8 or x>=40:
                assert pixels[y][x]==native_frames[x//24][y][x], 'Native timer frame art incorrect'
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
    expected_x=104 if r[0x1ef0] else 184
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
    verify_native_frame_tiles(source)
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
                        if not two and tile in (0x2c8,0x236,0x238,0x23a,0x23c,0x23e):continue
                        assert vram[0x2000+tile*32:0x2000+(tile+1)*32]==source[0x70000+tile*32:0x70000+(tile+1)*32], 'Timer upload damaged native decorative graphics'
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
                        left=104 if two else 184
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
    print('PASS rendered timer: native 8x16 font and silver/gold frame art/colors, all four player-stage combinations, both solo styles, minute/second digits, both routes, rollover, pause, transitions, expiry')
