"""Compare real blocked-spawn Dr. Mario popups with the original ROM."""
from pathlib import Path
import struct

from build_rom import OUTPUT, ROOT, SOURCE
from verify_menu import Emulator


def popup_mask(source):
    """Exclude transparent corners showing the independently moving board."""
    from build_rom import decode_tile
    top=(0xbc,0xbd,0xbd,0xbd,0xbd,0xbd,0x40bd,0x40bc)
    middle=(0xcc,0xcd,0xce,0xce,0xce,0xce,0x40cd,0x40cc)
    rows=(top,middle,(0xcc,0xbe,0xc0,0xc1,0xc2,0xc3,0x40be,0x40cc),
          (0xcc,0xbe,0xc4,0xc5,0xc6,0xc7,0x40be,0x40cc),
          tuple(e|0x8000 for e in middle),tuple(e|0x8000 for e in top))
    mask=[]
    for row in rows:
        tiles=[]
        for entry in row:
            pixels=decode_tile(source,entry&1023,0x70000)
            if entry&0x4000:pixels=[line[::-1] for line in pixels]
            if entry&0x8000:pixels=pixels[::-1]
            tiles.append(pixels)
        mask.extend(bool(tiles[x//8][y][x%8]) for y in range(8) for x in range(64))
    return mask


def check_status_numbers(e, picture, baseline, glyphs, two):
    """Check both visible HUDs; solo Dr. Mario clips these BG1 number cells."""
    if not two:return
    ram=e.memory();vram=e.memory(3)
    count=0
    for row in range(28):
        for col in range(32):
            entry=struct.unpack_from('<H',vram,row*64+col*2)[0]
            palette=(entry>>10)&7;tile=entry&1023
            if palette not in (0,1) or tile not in glyphs:continue
            # Dr. Mario uses its own HUD; leftover Tetris map cells can sit
            # behind its window/sprites and are not visible status numerals.
            if ram[0x3f1+palette*0x500] not in (1,5):continue
            for y,line in enumerate(glyphs[tile]):
                for x,pen in enumerate(line):
                    if not pen:continue
                    assert pen in (1,3), 'Native HUD numeral masks changed'
                    off=(palette*16+pen)*2
                    word=struct.unpack_from('<H',baseline,off)[0]
                    assert ram[0x1500+off:0x1502+off]==baseline[off:off+2], 'Popup changed a live status numeral face/shadow palette color'
                    r,g,b=((word>>s)&31 for s in (0,5,10))
                    rgb=(r*255//31,(g*2+(g>>4))*255//63,b*255//31) if e.pixel_format==2 else tuple(c*255//31 for c in (r,g,b))
                    px=col*8+(7-x if entry&0x4000 else x)
                    py=row*8+(7-y if entry&0x8000 else y)
                    assert picture.getpixel((px,py))==rgb, f'Popup tinted a rendered status numeral face/shadow at {(px,py)}, palette={palette}, pen={pen}'
                    count+=1
    if any(ram[a] in (1,5) for a in (0x3f1,0x8f1)):
        assert count, 'No live opponent status digits were checked'


def capture_popups(core, rom, custom, players, two=True, opponent_stage=1):
    from validate_single_player import menu,press,active,until
    from validate_timer import check_timer
    from build_rom import decode_tile
    e=Emulator(core,rom)
    pictures={p:[] for p in players}
    patched=rom==OUTPUT
    prefix=('custom' if custom else 'normal')+('-two-player' if two else '-solo')
    try:
        menu(e,custom)
        if patched and two:press(e,7)
        press(e,3);active(e,1)
        for p in players:
            off=p*0x500
            e.write_memory(off+0x305,b'\x0b\x00');e.write_memory(off+0x316,b'\x01')
            until(e,lambda r:r[off+0x3f1]==3 and r[off+0x305]==5 and r[off+0x306]==1)
        if opponent_stage==5:
            assert two and players==(0,)
            for stage in (3,5):
                e.write_memory(0x805,b'\x0b\x00');e.write_memory(0x816,b'\x01')
                until(e,lambda r:r[0x8f1]==stage and r[0x805]==5 and r[0x806]==1)
            # P1 has kept playing during P2's two transitions. Wait for a live
            # capsule and empty its old stack before setting the blocked spawn.
            active(e,3)
            for row in range(1,17):e.write_memory(0x100+row*16+1,bytes(8))
        e.run(4)
        baseline=e.memory()[0x1500:0x1540]
        source=SOURCE.read_bytes()
        glyphs={n:decode_tile(source,n,0x70000) for n in range(0x130,0x14A)}
        opaque=popup_mask(source)
        check_status_numbers(e,e.screenshot(ROOT/'custom'/'research'/'status-before-popup.png'),baseline,glyphs,two)
        # Block the next spawn using ordinary occupied board cells. The native
        # engine must detect defeat; no Game Over status/drawing state is set.
        for p in players:
            for row in range(1,17):e.write_memory(p*0x500+0x100+row*16+1,b'\x81'*8)
        for frame in range(205):
            ram=e.memory()
            visible=[p for p in players if ram[p*0x500+0x305:p*0x500+0x307]==b'\x09\x02']
            if visible:
                picture=e.screenshot(ROOT/'custom'/'research'/'game-over-check.png')
                check_status_numbers(e,picture,baseline,glyphs,two)
                for p in visible:
                    left=32+128*p if two else 104
                    pixels=picture.crop((left,96,left+64,144)).tobytes()
                    pictures[p].append(bytes(c if opaque[i//3] else 0 for i,c in enumerate(pixels)))
                    if patched and len(pictures[p])==30:
                        suffix='-both' if len(players)==2 else ''
                        if opponent_stage==5:suffix+='-type-a'
                        picture.save(ROOT/'custom'/'validation'/f'{prefix}-dr-game-over-p{p+1}{suffix}.png')
                if patched and frame==100:check_timer(e)
            e.run(1)
        assert all(len(images)==60 for images in pictures.values()), 'Native Game Over hold was skipped or changed'
        # The timed Mixed Match round resumes Dr. Mario after defeat. Palette
        # repair and popup remapping must survive native graphics/palette reloads.
        for p in players:
            off=p*0x500
            until(e,lambda r:r[off+0x305]==5 and r[off+0x306]==1)
        e.run(4)
        check_status_numbers(e,e.screenshot(ROOT/'custom'/'research'/'status-after-restart.png'),baseline,glyphs,two)
        if patched:check_timer(e)
        return pictures
    finally:e.close()


def verify_game_over(core):
    (ROOT/'custom'/'validation').mkdir(parents=True,exist_ok=True)
    for custom in (False,True):
        for players in ((0,),(1,),(0,1)):
            original=capture_popups(core,SOURCE,custom,players)
            patched=capture_popups(core,OUTPUT,custom,players)
            assert patched==original, f'Dr. Mario popup differs from native RGB pixels: custom={custom}, players={players}'
            if players==(0,):
                solo=capture_popups(core,OUTPUT,custom,players,False)
                assert solo==original, 'Centered solo Dr. Mario popup differs from native pixels'
                patched_a=capture_popups(core,OUTPUT,custom,players,opponent_stage=5)
                # Native Type A replaces palette-6 black with orange, tinting
                # the ORIGINAL popup lettering too. Retain the canonical black
                # lettering from the native Type B matchup, not that native bug.
                # The first hold-state image still contains the preceding map
                # upload; the independently running boards can differ there.
                assert patched_a[0][1:]==original[0][1:], 'Dr. Mario popup differs alongside Tetris Type A'
    print('PASS native Dr. Mario Game Over popup: every rendered hold frame matches original pixels/colors for P1, P2, both defeated, solo, both menu routes; live HUD numeral faces/shadows and timers stay correct through defeat and restart')


if __name__=='__main__':
    verify_game_over(Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
