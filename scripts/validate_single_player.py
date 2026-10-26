"""Exercise solo/two-player menus, controls, stage changes, pause and results.

The stage-completion and timer-expiry checks write only emulator RAM to accelerate
the native end-of-stage/end-of-time states. No cheats are included in the ROM.
"""
import argparse
from hashlib import sha256
from pathlib import Path
import struct
from PIL import ImageChops

from build_rom import OUTPUT, ROOT, SOURCE, SOURCE_SHA256, build_rom, decode_tile
from verify_menu import Emulator

DEST=ROOT/'custom'/'validation'


def press(e, button, frames=1):
    e.run(frames,[button]);e.run(1)


def menu(e, custom=False):
    e.run(600);press(e,3);e.run(120);press(e,5);press(e,3);e.run(120)
    if custom:press(e,5)
    press(e,3);e.run(120)


def until(e, predicate, limit=1200):
    for _ in range(limit):
        if predicate(e.memory()):return
        e.run(1)
    raise AssertionError('Timed out waiting for native game state')


def active(e,stage):
    until(e,lambda r:r[0x3f1]==stage and r[0x305]==5 and r[0x306]==1)


def normal_menu_focus(e, cursor):
    assert e.memory()[0x1ef1]==cursor
    vram=e.memory(3)
    for index,row in enumerate((4,8,14,19)):
        border=struct.unpack_from('<H',vram,row*64+8)[0]
        assert border&0x1c00==(0x0800 if index==cursor else 0), 'Wrong normal-menu header highlighted'


def background_capture(e, stage, path):
    # Verify that both full decorative maps reached VRAM, including their side
    # extensions, rather than just changing window masks around the old maps.
    start={1:0xe4000,3:0xe5000,5:0xe6000}[stage]
    assert e.memory(3)[0x800:0x1800]==OUTPUT.read_bytes()[start:start+0x1000]
    assert e.memory(3)[0x7900:0x7920]==bytes(32), 'Solo checkerboard divider returned'
    # Check the embedded pieces as rendered graphics, not just the standalone
    # separator tile. All panel/frame pixels outside the strip must survive.
    vram=e.memory(3);source=SOURCE.read_bytes()
    for tile in (0x236,0x238,0x23a,0x23c,0x23e):
        original=decode_tile(source,tile,0x70000)
        cleaned=decode_tile(vram,tile,0x2000)
        for old,new in zip(original,cleaned):
            assert new[:5]==old[:5], 'Status-panel border was damaged'
            assert new[6:]==[0,0], 'Embedded checkerboard divider remained'
            assert new[5]==(0 if old[5] in (3,9) else old[5]), 'Panel bevel or divider incorrect'
    for tile in (0x1a5,0x1b5):
        original=decode_tile(source,tile,0x70000)
        cleaned=decode_tile(vram,tile,0x2000)
        for old,new in zip(original,cleaned):
            assert new[:5]==old[:5], 'LEVEL/HEIGHT label was damaged'
            assert new[5:]==[0,0,0], 'Checkerboard remained beside LEVEL/HEIGHT'
    if stage in (1,5):
        # Audit the whole separator column, including all text and frame tiles,
        # so a tile omitted from the individual graphics checks cannot hide it.
        for row in range(32):
            entry=struct.unpack_from('<H',vram,row*64+30)[0]
            pixels=decode_tile(vram,entry&0x3ff,0x2000)
            for line in pixels:
                edge=line[:2] if entry&0x4000 else line[6:]
                assert edge==[0,0], f'Foreground remained at divider row {row}'
    picture=e.screenshot(path)
    for bounds in ((0,0,64,224),(224,0,256,224)):
        side=picture.crop(bounds)
        lit=sum(pixel!=(0,0,0) for pixel in side.getdata())
        assert lit>side.width*side.height*0.6, 'Black margin remained beside solo field'


def verify(core):
    source=SOURCE.read_bytes();patched=OUTPUT.read_bytes()
    assert sha256(source).hexdigest()==SOURCE_SHA256
    assert patched==build_rom(source)==build_rom(source)
    complement,checksum=struct.unpack_from('<HH',patched,0x7fdc)
    assert complement^checksum==0xffff and sum(patched)&0xffff==checksum
    DEST.mkdir(parents=True,exist_ok=True)
    for custom in (False,True):
        prefix='custom' if custom else 'normal'
        e=Emulator(core,OUTPUT)
        try:
            menu(e,custom)
            assert e.memory()[0x1ef0]==0
            if not custom:normal_menu_focus(e,0)
            e.screenshot(DEST/f'{prefix}-one-player-menu.png')
            press(e,7);assert e.memory()[0x1ef0]==1
            e.screenshot(DEST/f'{prefix}-two-player-menu.png')
            press(e,6);assert e.memory()[0x1ef0]==0
            if not custom:
                for cursor,address,name in ((1,0x1ea6,'handicap'),(2,0x1ea8,'time'),(3,0x1ea9,'music')):
                    press(e,5);normal_menu_focus(e,cursor)
                    before=e.memory()[address]
                    press(e,7);assert e.memory()[address]!=before
                    press(e,6);assert e.memory()[address]==before
                    assert e.memory()[0x1ef0]==0
                    e.screenshot(DEST/f'normal-{name}-focused-menu.png')
                for _ in range(3):press(e,4)
                normal_menu_focus(e,0)
            press(e,3);active(e,1)
            assert e.memory()[0x8f1]==0
            background_capture(e,1,DEST/f'{prefix}-solo-tetris.png')

            # P2 controls cannot move, rotate, drop, or pause a solo game.
            p2=e.memory()[0x600:0xa00]
            e.run(30,(),(3,5,6,8));r=e.memory()
            assert r[0x600:0xa00]==p2 and r[0x304]==0
            start_x=r[0x326]
            e.run(8,(6,));assert e.memory()[0x326]!=start_x
            e.run(40)
            press(e,3);assert e.memory()[0x304]==0x40
            before=e.memory()[0x408:0x40b];e.run(40)
            assert e.memory()[0x408:0x40b]==before
            e.screenshot(DEST/f'{prefix}-solo-paused.png')
            press(e,3);assert e.memory()[0x304]==0

            # Enter each native completion state; exercise the original wipe,
            # graphics reload, countdown, next-game rules and controller logic.
            for old,new,name in ((1,3,'dr-mario'),(3,5,'tetris-final')):
                e.write_memory(0x305,b'\x0b\x00')
                e.write_memory(0x316,b'\x01')
                active(e,new)
                e.run(30)
                assert e.memory()[0x8f1]==0
                background_capture(e,new,DEST/f'{prefix}-solo-{name}.png')
            # Known binary scores verify the native stage sum and digit rendering.
            e.write_memory(0x416,(1234).to_bytes(4,'little'))
            e.write_memory(0x41a,(5678).to_bytes(4,'little'))
            e.write_memory(0x270,(9000).to_bytes(4,'little'))
            e.write_memory(0x408,b'\x00\x00\x00')
            until(e,lambda r:r[0xbaf]==0x31 and r[0x305]==4)
            e.run(2)
            assert e.memory()[0x805]==0, 'Timer started an inactive P2 end state'
            assert int.from_bytes(e.memory()[0x412:0x416],'little')==15912
            e.screenshot(DEST/f'{prefix}-solo-results.png')
            press(e,3)
            until(e,lambda r:r[0xbaf]==0x33 and r[0x32]==15)
            e.run(2)
            e.screenshot(DEST/f'{prefix}-returned-to-title.png')
            # The same ROM must return cleanly to genuine two-player play.
            if custom:press(e,5)
            press(e,3);e.run(120);press(e,7);assert e.memory()[0x1ef0]==1
            press(e,3);active(e,1)
            until(e,lambda r:r[0x8f1]==1 and r[0x805]==5)
            old_x=e.memory()[0x826];e.run(8,(),(6,))
            assert e.memory()[0x826]!=old_x
            assert e.memory(3)[0x7900:0x7920]==source[0x75900:0x75920], 'Two-player divider changed'
            assert e.memory(3)[0x66c0:0x6800]==source[0x746c0:0x74800], 'Two-player panel graphics changed'
            for tile in (0x1a5,0x1b5):
                assert decode_tile(e.memory(3),tile,0x2000)==decode_tile(source,tile,0x70000), 'Two-player label graphics changed'
            e.screenshot(DEST/f'{prefix}-two-player-tetris.png')
            # Finish a two-player round using the original result sequence, then
            # switch back to solo; no old opponent state may survive the restart.
            e.write_memory(0x408,b'\x00\x00\x00')
            until(e,lambda r:r[0xbaf]==0x31 and r[0x305]==7 and r[0x306]==1)
            e.screenshot(DEST/f'{prefix}-two-player-results.png')
            press(e,3)
            until(e,lambda r:r[0xbaf]==0x33 and r[0x32]==15)
            if custom:press(e,5)
            press(e,3);e.run(120);press(e,6);assert e.memory()[0x1ef0]==0
            press(e,3);active(e,1)
            assert not any(e.memory()[0x600:0xa00]), 'Old opponent state survived solo restart'
            print(f'PASS {prefix}: count toggle, solo controls, P2 inert, pause, '
                  'Tetris/Dr. Mario/Tetris, expiry/results, title return, two-player controls')
        finally:e.close()

    # An entire one-minute custom session runs without accelerated RAM edits.
    e=Emulator(core,OUTPUT)
    try:
        menu(e,True)
        for _ in range(7):press(e,5)
        for _ in range(4):press(e,6)
        assert e.memory()[0x1eb6]==1
        e.screenshot(DEST/'custom-one-minute-settings.png')
        press(e,3);active(e,1)
        for _ in range(100):
            e.run(60)
            if e.memory()[0xbaf]==0x31 and e.memory()[0x305]==4:break
        else:raise AssertionError('Natural one-minute session did not finish')
        e.screenshot(DEST/'natural-one-minute-results.png')
        print('PASS custom one-minute session through natural timer expiry (no RAM edits)')
    finally:e.close()

    # Global NMI hooks must leave the two standalone game modes visually intact.
    for name,choose in (('tetris',None),('dr-mario',7)):
        pictures=[]
        for rom,prefix in ((SOURCE,'original-'),(OUTPUT,'')):
            e=Emulator(core,rom)
            try:
                e.run(600);press(e,3);e.run(120)
                if choose is not None:press(e,choose)
                press(e,3);e.run(120);press(e,3);e.run(120)
                pictures.append(e.screenshot(DEST/f'{prefix}standalone-{name}.png'))
            finally:e.close()
        assert ImageChops.difference(*pictures).getbbox() is None, f'Standalone {name} changed'
    print('PASS standalone Tetris and Dr. Mario menu regression captures')
    assert SOURCE.read_bytes()==source
    print('PASS deterministic build, checksum, original ROM intact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core',type=Path,default=Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
    verify(p.parse_args().core)
