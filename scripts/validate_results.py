"""Compare solo score reveals against the unchanged native two-player sequence."""
from pathlib import Path
import struct

from build_rom import OUTPUT, ROOT, SOURCE
from verify_menu import Emulator


def verify_results(core):
    from validate_single_player import menu,press,active,until
    source=SOURCE.read_bytes();reference={}
    for custom in (False,True):
        for played in (0,2):
            for two in (True,False):
                e=Emulator(core,OUTPUT)
                try:
                    menu(e,custom)
                    if two:press(e,7)
                    press(e,3);active(e,1)
                    if played:
                        for phase in (3,5):
                            e.write_memory(0x305,b'\x0b\x00');e.write_memory(0x316,b'\x01');active(e,phase)
                        e.write_memory(0x416,(1234).to_bytes(4,'little'))
                        e.write_memory(0x41a,(5678).to_bytes(4,'little'))
                    e.write_memory(0x270,(9000 if played else 17).to_bytes(4,'little'))
                    e.write_memory(0x408,b'\x00'*3)
                    until(e,lambda r:r[0xbaf]==0x31 and r[0x305]==1)
                    events=[];prior=(False,)*4
                    prefix=('custom' if custom else 'normal')+('-two-player' if two else '-solo')
                    for frame in range(600):
                        r=e.memory();v=e.memory(3);col=12 if two else 16
                        values=[struct.unpack_from('<7H',v,row*64+col*2) for row in (6,9,12,18)]
                        visible=tuple(any((x&1023) not in (0,0x177,0x187) for x in row) for row in values)
                        if frame>=4:
                            assert visible in tuple((True,)*n+(False,)*(4-n) for n in range(5)), 'Results revealed out of order/all at once'
                            assert v[27*64:28*64]==source[0xb3000+27*64:0xb3000+28*64], 'Results bottom border was cut off'
                            if visible!=prior:
                                assert sum(visible)==sum(prior)+1, 'Multiple result rows appeared together'
                                events.append((frame,visible))
                                if not two:e.screenshot(ROOT/'custom'/'validation'/f'{prefix}-results-{played}-reveal-{len(events)}.png')
                            prior=visible
                            if not two:
                                for row in (6,7,9,10,12,13,18,19):
                                    assert struct.unpack_from('<4H',v,row*64+24)==(0x2000,)*4, 'Results retained uncentered score fragments'
                                if r[0x305]<7:
                                    assert r[0x10614:0x1062a]==b'\x00\x20'*11, 'PRESS START appeared before results finished'
                        if r[0x305]==7 and r[0x306]==1:
                            assert len(events)==4 and visible==(True,)*4
                            assert int.from_bytes(r[0x412:0x416],'little')==(15912 if played else 17), 'Incorrect staged score total'
                            e.run(2)
                            e.screenshot(ROOT/'custom'/'validation'/f'{prefix}-results-{played}-complete.png')
                            break
                        # Native results ignore START until the reveal ends.
                        e.run(1,(3,) if frame==110 else ())
                    else:raise AssertionError('Results did not reach input state')
                    if two:reference[custom,played]=(events,frame,values)
                    else:
                        native_events,native_ready,native_values=reference[custom,played]
                        assert events==native_events and frame==native_ready, 'Solo reveal timing differs from native two-player results'
                        assert [[n&1023 for n in row] for row in values]==[[n&1023 for n in row] for row in native_values], 'Solo score/NO-PLAY digits differ from native results'
                        prompt=e.memory(3)[24*64+20:24*64+42]
                        assert prompt==OUTPUT.read_bytes()[0xe1080:0xe1096], 'Missing final PRESS START prompt'
                    press(e,3);until(e,lambda r:r[0xbaf]==0x33 and r[0x32]==15)
                finally:e.close()
    print('PASS solo results: four reveals and input timing match native two-player results, complete border throughout, centered placeholders/scores, NO-PLAY, totals and title return, both routes')


if __name__=='__main__':
    verify_results(Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
