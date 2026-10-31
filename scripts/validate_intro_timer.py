"""Check displayed clock updates throughout each visible round-introduction card."""
from build_rom import OUTPUT, ROOT
from snes_disasm import offset
from verify_menu import Emulator, DEFAULT_CORE
from timer_border import BORDER_CELLS


def expected_timer_map(rom,ram):
    left,right=(int.from_bytes(ram[a:a+2],'little') for a in (0x1ef6,0x1ef8))
    minutes,seconds=ram[0x40a],ram[0x409]
    bank=0x9c0000 if ram[0x1ef0] else 0x9e0000
    lf=offset(bank+0x9300)+left//32;rf=offset(bank+0x9300)+right//32
    mm=offset(bank+0xa000)+left+minutes*12
    ss=offset(bank+0xa800)+right+seconds*12
    result=bytearray(rom[lf:lf+6]+rom[rf+6:rf+12]
            +rom[mm:mm+6]+rom[ss:ss+6]+rom[mm+6:mm+12]+rom[ss+6:ss+12]
            +rom[lf+12:lf+18]+rom[rf+18:rf+24])
    p1=min((ram[0x3f1]-1)//2,2);p2=max(0,min((ram[0x8f1]-1)//2,2))
    key=3+p1*3+p2 if ram[0x1ef0] else p1
    base=offset(0x9c9400)+key*32
    for i,(y,x) in enumerate(BORDER_CELLS):
        if key==1 and y in (1,2) and x==5:continue
        result[(y*6+x)*2:(y*6+x+1)*2]=rom[base+i*2:base+i*2+2]
    return bytes(result)


def verify_intro_timer(core):
    from validate_single_player import menu,press,active
    rom=OUTPUT.read_bytes()
    for custom in (False,True):
        for two in (False,True):
            e=Emulator(core,OUTPUT)
            try:
                menu(e,custom)
                if two:press(e,7)
                press(e,3);active(e,1)
                for stage in (3,5):
                    e.write_memory(0x305,b'\x0b\x00');e.write_memory(0x316,b'\x01')
                    seen=0;changes=0;lag=0;previous=None
                    for frame in range(1000):
                        r=e.memory()
                        if r[0x3f1]==stage and r[0x305]==3 and r[0x306]==0:
                            seen+=1
                            assert r[0x6c:0x6e]==bytes((0,127)), 'Introduction card is still behind the wipe'
                            value=(r[0x40a],r[0x409])
                            if previous is not None and value!=previous:changes+=1
                            previous=value
                            v=e.memory(3);dest=int.from_bytes(r[0x1efa:0x1efc],'little')*2
                            actual=b''.join(v[dest+y*64:dest+y*64+12] for y in range(4))
                            lag=lag+1 if actual!=expected_timer_map(rom,r) else 0
                            assert lag<=2, f'Timer froze on GAME-{stage//2+1} card: {lag} frames behind {value}, custom={custom}, two={two}'
                            if seen==90:
                                prefix=('custom' if custom else 'normal')+('-two-player' if two else '-solo')
                                e.screenshot(ROOT/'custom'/'validation'/f'{prefix}-live-timer-intro-{stage}.png')
                        if r[0x3f1]==stage and r[0x305]==5:
                            assert seen>=100 and changes>=1, 'Skipped the native card or no real clock tick occurred'
                            break
                        e.run(1)
                    else:raise AssertionError('Round introduction did not reach gameplay')
            finally:e.close()
    print('PASS live introduction timer: both new rounds, normal/custom, solo/two-player, native clock ticks displayed within two frames throughout GAME-2/GAME-3 cards')


if __name__=='__main__':
    verify_intro_timer(DEFAULT_CORE)
