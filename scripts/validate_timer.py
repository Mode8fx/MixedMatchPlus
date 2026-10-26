"""Check the actual rendered countdown, its native font, and both play layouts."""
import struct

from build_rom import OUTPUT, ROOT, SOURCE, decode_tile
from verify_menu import Emulator


def timer_column(ram):
    return 13 if ram[0x1ef0] else (14 if ram[0x3f1] == 3 else 13)


def check_timer(e, minutes=None, seconds=None):
    r=e.memory();v=e.memory(3);source=SOURCE.read_bytes()
    minutes=r[0x40a] if minutes is None else minutes
    seconds=r[0x409] if seconds is None else seconds
    col=timer_column(r)
    # Reconstruct BG2 from uploaded graphics, checking source glyph pixels,
    # exact centering, opaque backing, and the two subscreen cutouts.
    pixels=[]
    for row in range(23,27):
        line=[[] for _ in range(8)]
        for x in range(col,col+6):
            entry=struct.unpack_from('<H',v,0x800+row*64+x*2)[0]
            assert entry&0x3c00==0x2400, 'Timer priority/palette incorrect'
            glyph=decode_tile(v,entry&0x3ff,0x2000)
            for y in range(8):line[y].extend(glyph[y])
            assert struct.unpack_from('<H',v,row*64+x*2)[0]==0, 'Divider crosses timer'
            assert struct.unpack_from('<H',v,0x1000+row*64+x*2)[0]==0x1ff, 'Timer color cutout lost'
        pixels.extend(line)
    assert all(all(p for p in row) for row in pixels), 'Transparent timer backing'
    for i,n in ((0,minutes//10),(1,minutes%10),(3,seconds//10),(4,seconds%10)):
        native=decode_tile(source,0x130+n,0x70000)+decode_tile(source,0x140+n,0x70000)
        actual=[row[4+i*8:12+i*8] for row in pixels[8:24]]
        assert actual==[[p or 3 for p in row] for row in native], 'Timer uses the wrong digit/font'
    assert v[0xbff0:0xc000]==bytes(16), 'BG3 transparent tile was not loaded'
    expected_x=104 if r[0x1ef0] else 184
    shift=0 if r[0x1ef0] else (72 if r[0x3f1]==3 else 80)
    assert col*8+shift==expected_x
    picture=e.screenshot(ROOT/'custom'/'research'/'timer-check.png')
    # The native white and shadow must remain white/black after color math,
    # including the center divider column in a two-player game.
    for y in range(8,24):
        for x in range(4,44):
            assert picture.getpixel((expected_x+x,184+y))==((255,255,255) if pixels[y][x]==1 else (0,0,0)), 'Timer digits tinted or obscured'
    return picture.crop((expected_x,184,expected_x+48,216))


def verify_timer(core):
    from validate_single_player import menu,press,active,until
    dest=ROOT/'custom'/'validation'
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
                    prefix=('custom' if custom else 'normal')+('-two-player' if two else '-solo')
                    e.screenshot(dest/f'{prefix}-timer-stage-{stage}.png')
                    if two and stage!=1:
                        # Exercise independently transitioning opponents too.
                        e.write_memory(0x805,b'\x0b\x00');e.write_memory(0x816,b'\x01')
                        until(e,lambda r:r[0x8f1]==stage and r[0x805]==5 and r[0x806]==1)
                        e.run(4);check_timer(e)
                # 00:00 remains legible through the native end-of-time sequence.
                e.write_memory(0x408,bytes((0,0,0)));e.run(4);check_timer(e,0,0)
                e.screenshot(dest/f'{prefix}-timer-zero.png')
                until(e,lambda r:r[0xbaf]==0x31)
            finally:e.close()
    print('PASS rendered timer: original white 8x16 font, all minute/second digits, both layouts/routes, 10:00 rollover, pause, independent stage transitions, 00:00/expiry')
