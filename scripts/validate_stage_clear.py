"""Compare real Dr. Mario stage-clear rainbow messages with native RGB pixels."""
import struct

from build_rom import OUTPUT,ROOT,SOURCE,decode_tile
from verify_menu import Emulator,DEFAULT_CORE
from validate_dr_clear import prepare_last_virus


def capture_clear(core,rom,custom,players,two=True,opponent=1,reference=None):
    from validate_single_player import menu,press,active,until
    from validate_timer import check_timer
    from validate_game_over import check_status_numbers,popup_mask
    source=SOURCE.read_bytes();patched=rom==OUTPUT
    glyphs={n:decode_tile(source,n,0x70000) for n in range(0x130,0x14A)}
    e=Emulator(core,rom)
    images={};colors={p:set() for p in players};holds={p:0 for p in players}
    masks=reference[0] if reference else None
    snapshots=reference[1] if reference else {}
    overlap=0;defeat_started=False
    name=('custom' if custom else 'normal')+('-two' if two else '-solo')
    try:
        menu(e,custom)
        if patched and two:press(e,7)
        press(e,3);active(e,1)
        stages={p:3 for p in players}
        if len(players)==1 and two:stages[1-players[0]]=3 if opponent=='game-over' else opponent
        for p,stage in stages.items():
            for target in range(3,stage+1,2):
                base=p*0x500
                e.write_memory(base+0x305,b'\x0b\x00');e.write_memory(base+0x316,b'\x01')
                until(e,lambda r:r[base+0x3f1]==target and r[base+0x305:base+0x307]==b'\x05\x01')
        e.run(4)
        baseline=e.memory()[0x1500:0x1540]
        for p in players:prepare_last_virus(e,p)
        for frame in range(900):
            r=e.memory()
            visible=[p for p in players if r[p*0x500+0x305:p*0x500+0x307]==b'\x0b\x02']
            if visible:
                picture=e.screenshot(ROOT/'custom'/'research'/'stage-clear-check.png')
                for p in visible:
                    holds[p]+=1
                    if holds[p]<=2:continue  # Native map/palette upload can follow logic by one frame.
                    left=32+p*128 if two else 96
                    if masks is None:
                        v=e.memory(3);opaque=[];ink=[]
                        for y in range(72):
                            for x in range(64):
                                entry=struct.unpack_from('<H',v,(11+y//8)*64+(4+p*16+x//8)*2)[0]
                                pixels=decode_tile(source,entry&1023,0x70000)
                                pen=pixels[7-y%8 if entry&0x8000 else y%8][7-x%8 if entry&0x4000 else x%8]
                                opaque.append(bool(pen));ink.append(pen==1)
                        assert sum(ink)>100
                        masks=(opaque,ink)
                    pixels=list(picture.crop((left,88,left+64,160)).getdata())
                    ink_colors={pixel for pixel,is_ink in zip(pixels,masks[1]) if is_ink}
                    assert len(ink_colors)==1, 'Stage-clear lettering has inconsistent colors'
                    color=ink_colors.pop();colors[p].add(color)
                    image=bytes(c for pixel,opaque in zip(pixels,masks[0]) if opaque for c in pixel)
                    if reference:
                        assert color in snapshots, f'Stage-clear ink is outside the native rainbow: {name}, P{p+1}, {opponent=}, {color=}'
                        assert image==snapshots[color], f'Stage-clear pixels differ from native: {name}, P{p+1}, {opponent=}'
                    else:
                        assert snapshots.setdefault(color,image)==image
                    if patched and holds[p]==32:
                        suffix='both' if len(players)==2 else f'p{p+1}-{opponent}'
                        picture.save(ROOT/'custom'/'validation'/f'{name}-dr-stage-clear-{suffix}.png')
                        check_timer(e)
                    if opponent=='game-over' and not defeat_started:
                        other=(1-p)*0x500
                        for row in range(1,17):e.write_memory(other+0x100+row*16+1,b'\x81'*8)
                        defeat_started=True
                if patched:
                    check_status_numbers(e,picture,baseline,glyphs,two)
                    if opponent=='game-over':
                        other=1-players[0];base=other*0x500
                        if r[base+0x305:base+0x307]==b'\x09\x02':
                            overlap+=1
                            if overlap>2:
                                popup=list(picture.crop((32+other*128,96,96+other*128,144)).getdata())
                                masked=bytes(c for pixel,opaque in zip(popup,popup_mask(source)) if opaque for c in pixel)
                                assert images.setdefault('game-over',masked)==masked, 'Stage-clear animation recolored the opponent Game Over popup'
            if all(r[p*0x500+0x3f1]==5 and r[p*0x500+0x305]==5 for p in players):break
            buttons=[]
            for p in range(2 if two else 1):
                clearing=p in players and r[p*0x500+0x3f1]==3 and r[p*0x500+0x305]<6
                if clearing or (opponent=='game-over' and defeat_started and p not in players):buttons.append(p)
            e.run(1,(5,) if 0 in buttons else (),(5,) if 1 in buttons else ())
        else:raise AssertionError(f'Real last-virus clear did not reach Tetris-A: {name}, {players=}, {opponent=}, '+
                                  str([(r[p*0x500+0x3f1],r[p*0x500+0x305:p*0x500+0x307].hex()) for p in players]))
        assert all(n>=90 for n in holds.values()), 'Stage-clear hold was skipped'
        # Both native victory handlers advance the shared index when clears
        # coincide. Keep that cadence; synchronized clears step by two colors.
        assert all(len(c)==(4 if len(players)==2 else 8) for c in colors.values()), f'Incomplete native rainbow cycle: {colors}'
        if opponent=='game-over':assert overlap>=20, 'Simultaneous Game Over/stage clear was not exercised'
        if patched:check_timer(e)
        return masks,snapshots
    finally:e.close()


def verify_stage_clear(core):
    reference=capture_clear(core,SOURCE,False,(0,))
    for custom in (False,True):
        capture_clear(core,OUTPUT,custom,(0,),False,reference=reference)
        for players,opponent in (((0,),1),((1,),1),((0,),5),((1,),5),((0,1),3),
                                 ((0,),'game-over'),((1,),'game-over')):
            capture_clear(core,OUTPUT,custom,players,opponent=opponent,reference=reference)
    print('PASS native stage-clear RGB pixels and all eight rainbow colors: solo, P1/P2/both, both routes, Tetris B/A opponents and simultaneous Game Over; HUD colors, timers and next-round reload intact')


if __name__=='__main__':verify_stage_clear(DEFAULT_CORE)
