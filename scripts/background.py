"""Build full-width decorative maps from the original Mixed Match artwork."""
import struct


def build_solo_backgrounds(source):
    result={}
    for phase,b2,b3 in ((1,0xAA000,0xAC000),(3,0xAA800,0xAC800),(5,0xA9800,0xAB800)):
        bg2=bytearray(source[b2:b2+0x800]);bg3=bytearray(source[b3:b3+0x800])
        for row in range(32):
            for col in range(16,32):
                off=row*64+col*2
                if phase==3:
                    # Extend both layers of the native repeating mosaic.
                    e=struct.unpack_from('<H',source,b2+(8+row%2)*64+(col%2)*2)[0]
                    ce=struct.unpack_from('<H',source,b3+(8+row%4)*64+(col%2)*2)[0]
                else:
                    # Keep the maze geometry, using its gray body palette
                    # instead of the blue palette of the unused P2 field.
                    e=(struct.unpack_from('<H',source,b2+off)[0]&~0x1c00)|0x1400
                    ce=struct.unpack_from('<H',source,b3+10*64)[0]
                struct.pack_into('<H',bg2,off,e);struct.pack_into('<H',bg3,off,ce)
        result[phase]=(bytes(bg2),bytes(bg3))
    return result
