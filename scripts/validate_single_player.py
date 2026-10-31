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
    for index,row in enumerate((4,9,16,20)):
        border=struct.unpack_from('<H',vram,row*64+8)[0]
        selected=0x0800 if index==0 else 0x1000
        assert border&0x1c00==(selected if index==cursor else 0), 'Wrong normal-menu header highlighted'


def verify_navigation_sound(core):
    # Inspect the actual native SFX queue immediately after input. The title
    # and both menus use audio bank 3; navigation must enqueue the same effect.
    def event(e,button,port=0):
        e.run(30)
        assert e.memory()[0xc60:0xc64]==b'\xff'*4
        e.run(1,() if port else (button,),(button,) if port else ())
        queue=e.memory()[0xc60:0xc64]
        e.run(1)
        return queue

    for screen in ('title','normal','custom'):
        e=Emulator(core,OUTPUT)
        try:
            if screen=='title':
                e.run(600);press(e,3);e.run(120);press(e,5);press(e,3);e.run(120)
            else:menu(e,screen=='custom')
            assert e.memory()[0xc57]==3
            for button in (5,4):assert 2 in event(e,button), f'{screen}: P1 navigation sound missing'
            assert 2 not in event(e,4), f'{screen}: sound at a fixed upper boundary'
            if screen!='title':
                press(e,7);assert e.memory()[0x1ef0]==1
                for button in (5,4):assert 2 in event(e,button), f'{screen}: P1 two-player navigation silent'
                if screen=='custom':
                    for button in (5,4):assert 2 in event(e,button,1), 'Native P2 navigation sound changed'
        finally:e.close()
    print('PASS P1 up/down SFX matches Mixed Match title in both menus and player counts; native P2 sound intact')


def normal_menu_spacing(e, source):
    vram=e.memory(3)
    rom=OUTPUT.read_bytes()
    menu_tiles=[entry&0x3ff for entry in struct.unpack_from('<1024H',rom,0xb2000)]
    size=(max(menu_tiles)-0x280+1)*32
    assert vram[0x7000:0x7000+size]==rom[0xe8000:0xe8000+size], 'Normal menu graphics were not loaded'
    plane=[[0]*256 for _ in range(256)];cache={}
    for row in range(32):
        for col in range(32):
            entry=struct.unpack_from('<H',vram,row*64+col*2)[0];tile=entry&0x3ff
            if tile not in cache:cache[tile]=decode_tile(vram,tile,0x2000)
            pixels=cache[tile]
            if entry&0x4000:pixels=[line[::-1] for line in pixels]
            if entry&0x8000:pixels=pixels[::-1]
            for y,line in enumerate(pixels):plane[row*8+y][col*8:col*8+8]=line

    def bounds(x0,y0,x1,y1):
        # The font's last row contains only black shadow, not visible lettering.
        # Palette entries 2/3 are black; count the visible row for pixel gaps.
        ys=[y for y in range(y0,y1) if any(p not in (0,2,3) for p in plane[y][x0:x1])]
        return min(ys),max(ys)

    def native_row(row,col,width):
        tiles=[]
        for x in range(col,col+width):
            entry=struct.unpack_from('<H',source,0xb2000+row*64+x*2)[0];tile=entry&0x3ff
            pixels=decode_tile(source,tile-0x100,0x42000) if tile>=0x100 else decode_tile(source,tile,0x3e000)
            if entry&0x4000:pixels=[line[::-1] for line in pixels]
            if entry&0x8000:pixels=pixels[::-1]
            tiles.append(pixels)
        return [[p for tile in tiles for p in tile[y]] for y in range(8)]

    for old,width,y in ((4,10,71),(12,11,128),(18,14,163)):
        pixels=sum((native_row(row,4,width) for row in range(old,old+3)),[])[4:20]
        assert [line[32:32+width*8] for line in plane[y:y+16]]==pixels, 'Header pixels changed'
    for old,y in ((9,104),(16,150),(22,185)):
        assert [line[56:224] for line in plane[y:y+8]]==native_row(old,7,21), 'Choice glyph pixels changed'
    r=e.memory();end=int.from_bytes(r[0x1dc5:0x1dc7],'little')
    sprites=[r[i:i+4] for i in range(0x1900,end,4)]

    def sprite_bounds(group):
        ys=[]
        for obj in group:
            pixels=decode_tile(vram,obj[2]+(obj[3]&1)*256,0x8000)
            if obj[3]&0x80:pixels=pixels[::-1]
            ys.extend(obj[1]+y-7 for y,line in enumerate(pixels) if any(line))
        return min(ys),max(ys)

    p1=sprite_bounds(sprites[:8]);assert p1==(91,99)
    p2=sprite_bounds(sprites[8:16]) if r[0x1ef0] else None
    if p2:assert p2==(115,123)
    rows=[bounds(32,32,104,54),bounds(56,54,152,68),bounds(32,68,112,90),p1,
          bounds(56,102,200,114),p2,bounds(32,126,120,146),bounds(56,148,200,160),
          bounds(32,161,144,181),bounds(56,183,224,196)]
    assert rows[:3]==[(36,51),(58,64),(71,86)]
    for above,below,gap in zip(rows,rows[1:],(6,6,4,4,4,4,6,6,6)):
        if above is not None and below is not None:
            assert below[0]-above[1]-1==gap, f'Wrong normal-menu gap: {above} to {below}'
    assert r[0x1580:0x1588]==r[0x1500:0x1508], 'Focused header text palette changed'
    assert r[0x1588:0x158e]==r[0x1548:0x154e], 'Focused header border colors changed'
    assert r[0x1504:0x1508]==bytes(4), 'Black shadow colors changed'


def custom_speed_visibility(e):
    assert e.memory()[0x1ef0]==0
    old=e.memory()[0x1eb3:0x1eb4]
    p1=e.memory(3)[13*64+40:13*64+46]
    for speed,name in enumerate(('lo','med','hi')):
        e.write_memory(0x1eb3,bytes([speed]));e.run(3)
        assert e.memory(3)[13*64+48:13*64+54]==b'\x00\x20'*3, 'P2 speed letter survived in solo menu'
        assert e.memory(3)[13*64+40:13*64+46]==p1, 'P1 speed was damaged while hiding P2'
        e.screenshot(DEST/f'custom-solo-p2-speed-{name}.png')
    e.write_memory(0x1eb3,old);e.run(3)


def custom_music_layout(e,source):
    vram=e.memory(3)
    entries=struct.unpack_from('<32H',vram,17*64)
    r=e.memory();value=('BGM1','BGM2','BGM3','OFF ')[r[0x1ea9]]
    expected='MUSIC SELECT  '+value
    tiles=[0 if c==' ' else 0x100+(int(c) if c.isdigit() else ord(c)-55) for c in expected]
    assert [v&0x3ff for v in entries[7:25]]==tiles, 'Wrong compact music label/value'
    assert 7*8==256-25*8, 'Compact music row is not centered'
    for col in range(7,19):assert entries[col]&0x1c00==0, 'Music label color changed'
    for col in range(21,25):
        assert entries[col]&0x1c00==(0x0400 if r[0x1ef2]==7 else 0), 'Music value highlight is wrong'
    end=int.from_bytes(r[0x1dc5:0x1dc7],'little')
    assert not any(r[i+2:i+4]==b'\x60\x32' for i in range(0x1900,end,4)), 'Custom music arrow remained'
    assert entries[2]==entries[29]==0x2c0b, 'Music row damaged the menu frame'


def custom_count_layout(e):
    ram=e.memory();vram=e.memory(3)
    words=struct.unpack_from('<32H',vram,4*64)
    label=f'MODE SELECT {ram[0x1ef0]+1}PLAYER GAME'
    expected=[0 if c==' ' else 0x100+(int(c) if c.isdigit() else ord(c)-55) for c in label]
    assert [w&0x3ff for w in words[4:28]]==expected, 'Custom player row text/placement is wrong'
    assert words[3:4]+words[28:29]==(0x2000,)*2, 'Old player-row text remains'
    assert 4*8==256-28*8, 'Custom player row is not centered'
    for col in range(4,28):
        color=0x0400 if col==16 and ram[0x1ef2]==0 else 0
        assert words[col]&0x1c00==color, 'Only the focused player-count digit may be yellow'


def custom_menu_layout(e, source, two_players=False):
    custom_count_layout(e)
    vram=e.memory(3)
    # The original frame's lower corners and bottom must be back at rows 22/23.
    assert vram[22*64:24*64]==source[0xae800+22*64:0xae800+24*64]
    for row in (3,5,16,18,20):
        assert struct.unpack_from('<26H',vram,row*64+6)==(0x2000,)*26, 'Custom menu gap or spare area occupied'
    # Every moved setting must both accept input and redraw in its new location.
    fields=((8,0x1eaa),(9,0x1eac),(10,0x1eae),(12,0x1eb0),(13,0x1eb2),(15,0x1eb4),(19,0x1eb6))
    for index,(row,address) in enumerate(fields[:6] if two_players else fields):
        if two_players:
            assert e.memory()[0xc09]==index
            address+=1;col=24 if index==4 else 25
        else:
            press(e,5);col=14 if index==6 else 20 if index==4 else 21
            if index==6:press(e,5)  # Music is between the final level and time.
            assert e.memory()[0x1ef2]==(8 if index==6 else index+1)
        e.run(2)  # Native drawing and NMI upload follow input on later frames.
        custom_count_layout(e)
        start=row*64+col*2
        width=6 if row==13 else 4
        before_value=e.memory()[address];before_tiles=e.memory(3)[start:start+width]
        if two_players:e.run(1,(),(7,));e.run(1)
        else:press(e,7)
        e.run(2)
        assert e.memory()[address]!=before_value
        assert e.memory(3)[start:start+width]!=before_tiles, f'Custom setting {index} redrew at wrong position'
        if two_players:e.run(1,(),(6,));e.run(1)
        else:press(e,6)
        e.run(2)
        assert e.memory()[address]==before_value
        assert e.memory(3)[start:start+width]==before_tiles
        if two_players:e.run(1,(),(5,));e.run(1)
    if not two_players:
        e.screenshot(DEST/'custom-time-focused-menu.png')
        press(e,4);assert e.memory()[0x1ef2]==7
        e.run(2)
        custom_music_layout(e,source)
        native_settings=e.memory()[0x1eaa:0x1eb7]
        while e.memory()[0x1ea9]:press(e,6)
        for setting,name in enumerate(('bgm1','bgm2','bgm3','off')):
            if setting:press(e,7)
            e.run(3)
            assert e.memory()[0x1ea9]==setting
            custom_music_layout(e,source)
            assert e.memory()[0x1eaa:0x1eb7]==native_settings
            e.screenshot(DEST/f'custom-music-{name}-menu.png')
            if setting==0:e.screenshot(DEST/'custom-music-focused-menu.png')
        press(e,7);assert e.memory()[0x1ea9]==0
        e.run(3);custom_music_layout(e,source)
        press(e,6);assert e.memory()[0x1ea9]==3
        e.run(3);custom_music_layout(e,source)
        for _ in range(3):press(e,6)
        assert e.memory()[0x1ea9]==0
        for _ in range(7):press(e,4)
        assert e.memory()[0x1ef2]==0
        e.run(3);custom_count_layout(e)


def check_dr_exposed_background(e, picture):
    """Check the extended background against the original paired mosaic.

    This uses native repeating texture/color cells, not the generated maps,
    so a transparent old HUD tint cannot silently turn this strip gray.
    The foreground window ends at x=191; these pixels are all background.
    Aligned 64px cameras place this strip in even background column 16.
    """
    from timer_border import map_pixels
    source=SOURCE.read_bytes();ram=e.memory()
    for row in (*range(1,8),*range(11,15)):
        e2=struct.unpack_from('<H',source,0xaa800+(8+row%2)*64)[0]
        e3=struct.unpack_from('<H',source,0xac800+(8+row%4)*64)[0]
        main=map_pixels(source,e2);sub=map_pixels(source,e3,True)
        for y in range(8):
            for x in range(8):
                p,q=main[y][x],sub[y][x]
                a=struct.unpack_from('<H',ram,0x1500+(((e2>>10)&7)*16+p)*2)[0]
                b=struct.unpack_from('<H',ram,0x1500+(((e3>>10)&7)*4+q)*2)[0] if q else 0
                r,g,blue=(max(0,((a>>s)&31)-((b>>s)&31)) for s in (0,5,10))
                expected=(r*255//31,(g*2+(g>>4))*255//63,blue*255//31) if e.pixel_format==2 else tuple(v*255//31 for v in (r,g,blue))
                assert picture.getpixel((192+x,row*8+y))==expected, f'Extended Dr. Mario background differs from native mosaic at {(192+x,row*8+y)}'


def background_capture(e, stage, path):
    # Verify that both full decorative maps reached VRAM, including their side
    # extensions, rather than just changing window masks around the old maps.
    start={1:0xe4000,3:0xe5000,5:0xe6000}[stage]
    ram=e.memory()
    foreground_shift=64 if stage==3 else 80
    background_shift=foreground_shift
    assert ram[0x1ef3]==foreground_shift, 'Wrong solo sprite/window displacement'
    assert int.from_bytes(ram[0x4f:0x51],'little')==(-foreground_shift)&0xffff
    for off in (0x53,0x57):
        assert int.from_bytes(ram[off:off+2],'little')==(-background_shift)&0xffff, 'Solo background camera moved'
    # The timer locally replaces BG2 and its BG3 color layer at the bottom.
    expected=bytearray(OUTPUT.read_bytes()[start:start+0x1000])
    actual=bytearray(e.memory(3)[0x800:0x1800])
    from validate_timer import timer_column
    col=timer_column(e.memory())
    for row in range(23,27):
        for base in (0,0x800):
            off=base+row*64+col*2
            expected[off:off+12]=actual[off:off+12]
    assert actual==expected
    assert e.memory(3)[0x7900:0x7920]==bytes(32), 'Solo checkerboard divider returned'
    # Check the embedded pieces as rendered graphics, not just the standalone
    # separator tile. All panel/frame pixels outside the strip must survive.
    vram=e.memory(3);source=SOURCE.read_bytes()
    # Anchor the complete native P1 decorative half to the original phase
    # assets. Comparing only with our generated maps can hide a wrong source
    # selection (Type A uses $959800; Type B uses $95A000).
    native_bg2={1:0xaa000,3:0xaa800,5:0xa9800}[stage]
    native_bg3={1:0xac000,3:0xac800,5:0xab800}[stage]
    for layer,base in ((0x800,native_bg2),(0x1000,native_bg3)):
        reference=source[base:base+0x800]
        for row in range(32):
            for x in range(16):
                if 23<=row<28 and col<=x<col+7:continue
                offset=row*64+x*2
                assert vram[layer+offset:layer+offset+2]==reference[offset:offset+2], f'Solo phase {stage} changed native background at layer {layer:x}, row {row}, column {x}'
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
    if stage==3:
        from validate_solo_art import check_dr_frame_edges
        check_dr_exposed_background(e,picture)
        check_dr_frame_edges(e,picture)
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
    verify_navigation_sound(core)
    from validate_custom_repeat import verify_custom_repeat
    verify_custom_repeat(core)
    from validate_timer import verify_timer
    from validate_solo_art import verify_native_dr_reference
    verify_native_dr_reference(core)
    verify_timer(core)
    from validate_timer import verify_additional_shadow_layouts
    verify_additional_shadow_layouts(core)
    from validate_intro_timer import verify_intro_timer
    verify_intro_timer(core)
    from validate_results import verify_results
    verify_results(core)
    from validate_transition import verify_solo_transition
    verify_solo_transition(core)
    from validate_dr_clear import verify_dr_clear
    verify_dr_clear(core)
    from validate_game_over import verify_game_over
    verify_game_over(core)
    for custom in (False,True):
        prefix='custom' if custom else 'normal'
        e=Emulator(core,OUTPUT)
        try:
            menu(e,custom)
            assert e.memory()[0x1ef0]==0
            if not custom:
                normal_menu_focus(e,0)
                normal_menu_spacing(e,source)
            e.screenshot(DEST/f'{prefix}-one-player-menu.png')
            if custom:
                custom_speed_visibility(e)
                custom_menu_layout(e,source)
            press(e,7);assert e.memory()[0x1ef0]==1
            if not custom:
                e.run(2);normal_menu_spacing(e,source)
            e.screenshot(DEST/f'{prefix}-two-player-menu.png')
            if custom:custom_menu_layout(e,source,True)
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
            until(e,lambda r:r[0xbaf]==0x31 and r[0x305]==7 and r[0x306]==1)
            e.run(2)
            assert e.memory()[0x805]==0, 'Timer started an inactive P2 end state'
            assert not e.memory()[0x34]&0x80, 'Obsolete solo window HDMA leaked into results'
            assert e.memory()[0x1efe]==0 and not e.memory()[0x34]&0x60, 'Timer padding HDMA leaked into results'
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
            assert not e.memory()[0x34]&0x80, 'Obsolete solo window HDMA leaked into two-player play'
            assert e.memory()[0x1efe]==0 and not e.memory()[0x34]&0x60, 'Gold timer bands leaked into Tetris'
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
            press(e,3);e.run(120)
            assert e.memory()[0x1ef0]==0, 'Reopening menu retained two-player selection'
            press(e,6);assert e.memory()[0x1ef0]==0
            press(e,3);active(e,1)
            assert not any(e.memory()[0x600:0xa00]), 'Old opponent state survived solo restart'
            print(f'PASS {prefix}: count toggle, solo controls, P2 inert, pause, '
                  'Tetris/Dr. Mario/Tetris, expiry/results, title return, two-player controls')
        finally:e.close()

    # An entire one-minute custom session runs without accelerated RAM edits.
    e=Emulator(core,OUTPUT)
    try:
        menu(e,True)
        for _ in range(8):press(e,5)
        for _ in range(4):press(e,6)
        assert e.memory()[0x1eb6]==1
        e.screenshot(DEST/'custom-one-minute-settings.png')
        press(e,3);active(e,1)
        for _ in range(100):
            e.run(60)
            if e.memory()[0xbaf]==0x31 and e.memory()[0x305]==7 and e.memory()[0x306]==1:break
        else:raise AssertionError('Natural one-minute session did not finish')
        e.screenshot(DEST/'natural-one-minute-results.png')
        print('PASS custom one-minute session through natural timer expiry (no RAM edits)')
    finally:e.close()

    # Global NMI hooks must leave the two standalone game modes visually intact.
    for name,choose in (('tetris',None),('dr-mario',7)):
        pictures=[]
        gameplay_vram=[]
        for rom,prefix in ((SOURCE,'original-'),(OUTPUT,'')):
            e=Emulator(core,rom)
            try:
                e.run(600);press(e,3);e.run(120)
                if choose is not None:press(e,choose)
                press(e,3);e.run(120);press(e,3);e.run(120)
                pictures.append(e.screenshot(DEST/f'{prefix}standalone-{name}.png'))
                # Start standalone play as well: its decorative maps and all
                # graphics must retain their native bytes. Live pill/virus RNG
                # can differ with CPU timing, so do not compare the board pixels.
                press(e,3);e.run(120);press(e,3);e.run(120)
                gameplay_vram.append(e.memory(3))
                e.screenshot(DEST/f'{prefix}standalone-{name}-play.png')
            finally:e.close()
        assert ImageChops.difference(*pictures).getbbox() is None, f'Standalone {name} changed'
        for start,end in ((0x800,0x1800),(0x2000,0x10000)):
            assert gameplay_vram[0][start:end]==gameplay_vram[1][start:end], f'Standalone {name} background/graphics changed'
    print('PASS standalone Tetris and Dr. Mario menu captures and gameplay background/graphics')
    assert SOURCE.read_bytes()==source
    print('PASS deterministic build, checksum, original ROM intact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core',type=Path,default=Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
    verify(p.parse_args().core)
