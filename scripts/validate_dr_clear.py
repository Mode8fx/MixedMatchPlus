"""Clear a real last virus and verify solo backgrounds throughout victory."""
from pathlib import Path

from build_rom import OUTPUT, ROOT
from verify_menu import Emulator


def verify_dr_clear(core, rom=OUTPUT):
    from validate_single_player import menu,press,active
    for custom in (False,True):
        e=Emulator(core,rom)
        try:
            menu(e,custom);press(e,3);active(e,1)
            # Skip the unrelated first stage, then set up a real four-color
            # match. The engine must lock a capsule and clear the last virus;
            # no Dr. Mario state, camera, PPU or DMA registers are forced.
            e.write_memory(0x305,b'\x0b\x00');e.write_memory(0x316,b'\x01')
            active(e,3);e.run(4)
            for row in range(1,17):e.write_memory(0x100+row*16+1,bytes(8))
            e.write_memory(0x201,bytes((0x83,3,3,3)))
            e.write_memory(0x3e7,b'\x01');e.write_memory(0x367,bytes((0,0,1)))
            picture=e.screenshot(ROOT/'custom'/'research'/'dr-clear-start.png')
            regions=((0,0,64,224),(232,0,256,224))
            expected=[picture.crop(box).tobytes() for box in regions]
            states=set();victory=0;cleared=False;closed_frames=0;bounds=None
            from validate_transition import check_solo_wipe
            for frame in range(900):
                r=e.memory();state=(r[0x3f1],r[0x305],r[0x306]);states.add(state)
                picture=e.screenshot(ROOT/'custom'/'research'/'dr-clear-check.png')
                bounds=check_solo_wipe(e,picture,bounds)
                if bounds==(64,191) and state[0] in (3,5):
                    prefix='custom' if custom else 'normal'
                    direction='closing' if state[0]==3 else 'opening'
                    picture.save(ROOT/'custom'/'validation'/f'{prefix}-solo-type-a-{direction}-wipe.png')
                if state[0]==3:
                    if state[1]!=11 or state[2]<3:
                        for box,pixels in zip(regions,expected):
                            assert picture.crop(box).tobytes()==pixels, f'Background shook during last-virus clear: frame {frame}, state {state}, route {custom}'
                    if state[1]==11:
                        cleared |= r[0x3e7]==0 and r[0x328]>=1
                        victory+=1
                        if victory==60:
                            from validate_transition import timer_visible
                            timer_visible(e,picture)
                            prefix='custom' if custom else 'normal'
                            picture.save(ROOT/'custom'/'validation'/f'{prefix}-solo-last-virus-victory.png')
                if state[0]==5 and state[1]==1 and bounds[0]>bounds[1]:
                    closed_frames+=1
                    if closed_frames==12:
                        prefix='custom' if custom else 'normal'
                        picture.save(ROOT/'custom'/'validation'/f'{prefix}-solo-type-a-closed-wipe.png')
                if state[0]==5 and state[1]==5:
                    assert any(phase==3 and status==6 for phase,status,sub in states)
                    assert victory>=180 and cleared, 'Skipped native last-virus victory'
                    assert closed_frames>=20, 'Dr. Mario-to-Tetris reload was not covered by the full-screen wipe'
                    assert not any(r[0x600:0xa00]), 'Last-virus clear activated P2'
                    break
                e.run(1,(5,) if state[0]==3 and state[1]<6 else ())
            else:raise AssertionError('Last-virus clear did not reach Tetris-A')
        finally:e.close()
    print('PASS native last-virus clear: backgrounds stay fixed through victory and the next Tetris stage starts, both solo routes, P2 inactive')


if __name__=='__main__':
    verify_dr_clear(Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
