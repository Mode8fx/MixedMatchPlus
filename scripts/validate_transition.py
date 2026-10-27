"""Exercise a real Tetris line clear and inspect the solo wipe frame by frame."""
from pathlib import Path
from build_rom import OUTPUT, ROOT
from verify_menu import Emulator
from validate_timer import displayed_timer_pixel


def timer_visible(e,picture):
    """Compare the actual displayed panel with its current VRAM/CGRAM pixels."""
    r=e.memory();v=e.memory(3)
    col=14 if r[0x1ef3]==72 else 13
    for row in range(23,27):
        for x in range(6):
            for y in range(8):
                for dx in range(8):
                    rgb=displayed_timer_pixel(r,v,col,x*8+dx,(row-23)*8+y,e.pixel_format)
                    actual=picture.getpixel((184+x*8+dx,row*8+y))
                    assert actual==rgb, f'Timer clipped/tinted during solo wipe at {(184+x*8+dx,row*8+y)}: {actual} != {rgb}'


def check_solo_wipe(e,picture,previous=None):
    """Every layer, including decoration/timer, must stay inside the opening.

    Allow the current/previous counter envelope because RAM can be one logic
    update ahead of the rendered frame. At a stable closed opening the whole
    image must be black, with no exception for any scanline or UI element.
    """
    r=e.memory();bounds=(r[0x6c]*2,r[0x6d]*2+1)
    left,right=bounds
    if previous is not None:left,right=min(left,previous[0]),max(right,previous[1])
    if left>right:
        assert picture.getbbox() is None, 'Solo map loading or timer leaked through the fully closed wipe'
    else:
        for box in ((0,0,left,224),(right+1,0,256,224)):
            if box[2]>box[0]:assert picture.crop(box).getbbox() is None, f'Solo screen/timer leaked outside wipe bounds {left}..{right}'
    assert not r[0x34]&0x80, 'Obsolete timer window HDMA is still enabled'
    return bounds


def verify_solo_transition(core):
    from validate_single_player import menu,press,active
    dest=ROOT/'custom'/'validation'
    for custom in (False,True):
        e=Emulator(core,OUTPUT)
        try:
            menu(e,custom);press(e,3);active(e,1);e.run(4)
            # Test-only board setup. The engine must lock a real piece, find
            # the completed row, decrement the objective and enter victory.
            # No phase/state or DMA/window variables are written by this test.
            for row in range(2,22):e.write_memory(0x100+row*16+1,bytes(10))
            e.write_memory(0x251,b'\x01'*10)
            e.write_memory(0x328,b'\x01')
            prefix='custom' if custom else 'normal'
            closed_frames=0;prior=None;states=set();bounds=None
            for frame in range(1100):
                r=e.memory();state=(r[0x3f1],r[0x305],r[0x306]);states.add(state)
                picture=e.screenshot(ROOT/'custom'/'research'/'solo-wipe-check.png')
                bounds=check_solo_wipe(e,picture,bounds)
                if bounds==(64,191) and state[0] in (1,3):
                    direction='closing' if state[0]==1 else 'opening'
                    picture.save(dest/f'{prefix}-solo-{direction}-wipe.png')
                if state[0]==3 and state[1]==1 and r[0x6c]>r[0x6d] and prior==state:
                    assert picture.getbbox() is None, 'Full-screen solo wipe did not conceal the map reload and timer'
                    if closed_frames==12:picture.save(dest/f'{prefix}-solo-closed-wipe.png')
                    closed_frames+=1
                if state[0]==3 and state[1]==5:
                    e.run(4)
                    assert r[0x328]==0 and closed_frames>=20
                    timer_visible(e,e.screenshot(ROOT/'custom'/'research'/'solo-wipe-open.png'))
                    assert any(phase==1 and status==7 for phase,status,sub in states), 'Skipped the native line-clear animation'
                    assert any(phase==1 and status==11 for phase,status,sub in states), 'Skipped native victory'
                    e.screenshot(dest/f'{prefix}-solo-natural-dr-mario.png')
                    assert not any(e.memory()[0x600:0xa00]), 'Solo wipe activated P2'
                    break
                prior=state
                e.run(1,(5,) if state[0]==1 and state[1]<9 else ())
            else:raise AssertionError('Natural line clear did not reach Dr. Mario')
        finally:e.close()
    print('PASS real Tetris line-clear route: full-screen solo wipe covers backgrounds and timer, map reload stays fully black, Dr. Mario opens cleanly, P2 inactive')


if __name__=='__main__':
    verify_solo_transition(Path('C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll'))
