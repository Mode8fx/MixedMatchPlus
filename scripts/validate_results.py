"""Compare solo score reveals against the unchanged native two-player sequence."""
import struct

from build_rom import OUTPUT, ROOT, SOURCE
from verify_menu import Emulator, DEFAULT_CORE


def custom_exit_flash(core):
    """Measure the original Custom Game exit prompt and native upload delay."""
    from validate_single_player import menu
    e=Emulator(core,SOURCE);phases={}
    try:
        menu(e,True)
        for _ in range(80):
            r=e.memory()
            assert r[0xbaf]==0x32
            picture=e.screenshot(ROOT/'custom'/'research'/'custom-exit-flash-check.png')
            shown=any(picture.getpixel((x,y))==(255,255,255)
                      for y in range(208,216) for x in range(48,208))
            phase=r[0x1df0]
            assert phases.setdefault(phase,shown)==shown, 'Native Custom Game flash changed between cycles'
            e.run(1)
    finally:e.close()
    assert len(phases)==40 and sum(phases.values())==20
    return phases


def check_results_flash(e,phases,prefix,played):
    prompt=OUTPUT.read_bytes()[0xe1030:0xe1054];blank=b'\x00\x20'*18
    start,end=24*64+14,24*64+50
    baseline=e.memory(3);captured=set()
    for _ in range(120):
        r=e.memory();v=e.memory(3)
        assert r[0x305:0x307]==b'\x07\x01', 'Flashing changed the results input state'
        shown=phases[r[0x316]]
        assert v[start:end]==(prompt if shown else blank), 'Results flash differs from Custom Game timing'
        assert v[:start]+v[end:0x780]==baseline[:start]+baseline[end:0x780], 'Prompt flash changed another results tile'
        picture=e.screenshot(ROOT/'custom'/'research'/'results-flash-check.png')
        rendered=any(picture.getpixel((x,y))==(255,255,255)
                     for y in range(192,200) for x in range(56,200))
        assert rendered==shown, 'Rendered results prompt differs from Custom Game flash'
        if shown not in captured:
            suffix='complete' if shown else 'prompt-hidden'
            picture.save(ROOT/'custom'/'validation'/f'{prefix}-results-{played}-{suffix}.png')
            captured.add(shown)
        e.run(1)
    assert captured=={False,True}


def verify_results(core):
    from validate_single_player import menu,press,active,until
    source=SOURCE.read_bytes();reference={};phases=custom_exit_flash(core)
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
                                    assert r[0x1060e:0x10632]==b'\x00\x20'*18, 'PRESS START BUTTON appeared before results finished'
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
                        check_results_flash(e,phases,prefix,played)
                        # Exercise START while hidden and while visible; both
                        # retain the native return-to-title behavior.
                        until(e,lambda r:all(phases[(r[0x316]+n)%40]==bool(played) for n in range(3)))
                    press(e,3);until(e,lambda r:r[0xbaf]==0x33 and r[0x32]==15)
                finally:e.close()
    print('PASS solo results: native reveals/input timing, borders, centered scores, NO-PLAY/totals; 20-on/20-off prompt matches original Custom Game pixels over three cycles, START works shown/hidden, both routes')


if __name__=='__main__':
    verify_results(DEFAULT_CORE)
