"""Compare held custom-setting input with the unchanged native P2 handler."""
from pathlib import Path

from build_rom import OUTPUT
from verify_menu import Emulator


def verify_custom_repeat(core):
    from validate_single_player import menu,press
    fields=((0x1eaa,5,0,10),(0x1eac,2,0,5),(0x1eae,15,1,30),
            (0x1eb0,10,0,20),(0x1eb2,1,0,2),(0x1eb4,5,0,10))
    native_traces=[];repeat_frames=None
    for two in (True,False):
        e=Emulator(core,OUTPUT)
        try:
            menu(e,True)
            if two:press(e,7)
            for index,(address,start,minimum,maximum) in enumerate(fields):
                press(e,5);e.run(3)
                e.write_memory(address,bytes((start,start)))
                trace=[]
                for button,frames in ((7,240),(6,240)):
                    e.run(3)
                    changes=[];before=e.memory()[address+1 if two else address]
                    for frame in range(frames):
                        e.run(1,(button,),(button,))
                        r=e.memory();value=r[address]
                        assert minimum<=value<=maximum, 'Held input exceeded native bounds'
                        if two:
                            assert value==r[address+1], f'P1/P2 hold cadence differs: setting {index}, direction {button}, frame {frame}: {value} != {r[address+1]}'
                            if value!=before:changes.append(frame)
                            before=value
                        else:
                            assert r[address+1]==start, 'Solo held input changed P2 settings'
                        trace.append(value)
                    assert e.memory()[address]==(maximum if button==7 else minimum)
                    if two and index==0 and button==7:
                        repeat_frames=changes
                        assert len(changes)>=4, 'Native P2 hold input did not repeat'
                if two:
                    native_traces.append(trace)
                    e.run(2);e.run(1,(),(5,));e.run(1)
                else:assert trace==native_traces[index], 'Solo repeats differ from native P2'
            # Music and play time are shared P1 rows. Use the native repeat
            # event positions rather than imposing a new delay/rate.
            e.run(3);press(e,5)
            assert e.memory()[0x1ef2]==7
            e.write_memory(0x1ea9,b'\x00')
            for button in (7,6):
                e.run(3);value=e.memory()[0x1ea9]
                for frame in range(28):
                    if frame in repeat_frames:value=(value+(1 if button==7 else -1))%4
                    e.run(1,(button,))
                    assert e.memory()[0x1ea9]==value, 'Held music input lost native repeat cadence/wrap'
            e.run(3);press(e,5)
            assert e.memory()[0x1ef2]==8
            for button,start,limit in ((7,29,30),(6,2,1)):
                e.run(3);e.write_memory(0x1eb6,bytes((start,)))
                for frame in range(40):e.run(1,(button,))
                assert e.memory()[0x1eb6]==limit, 'Held play-time input lost native bounds'
            # Menu navigation retains its existing one-row-per-press behavior.
            e.run(3);e.run(60,(4,));assert e.memory()[0x1ef2]==7
        finally:e.close()
    print('PASS Custom Game held left/right: P1 matches native P2 frame-for-frame across all six fields, solo/P2 isolation, music wrapping, time bounds and single-press navigation')


if __name__=='__main__':
    verify_custom_repeat(Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
