"""Compare solo Dr. Mario HUD/background pixels with the original scene."""
import struct

from build_rom import SOURCE,OUTPUT,ROOT
from timer_border import map_pixels
from timer_shadow import FRAME_SHADOW_ENABLED


def check_dr_exposed_background(e, picture):
    """Check the extension against original repeating cells, independently
    of the generated maps. The strip at x=192..199 is background column 16.
    """
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


def check_dr_frame_edges(e,picture):
    """Resolve all three original layers, preserving their native pairings.

    These rectangles include the complete LEVEL/VIRUS gap, score left edge,
    and pipes above SCORE. They exclude animated pills, viruses and HUD digits.
    Every pixel is taken from its original position, without palette swaps.
    """
    check_dr_exposed_background(e,picture)
    source=SOURCE.read_bytes();ram=e.memory()
    for left,top,right,bottom in ((88,56,125,88),(0,0,72,4),(0,8,8,32)):
        for row in range(top//8,(bottom+7)//8):
            for col in range(left//8,(right+7)//8):
                fg,bg,tint=(struct.unpack_from('<H',source,base+row*64+col*2)[0]
                            for base in (0xa9000,0xaa800,0xac800))
                front,back,sub=map_pixels(source,fg),map_pixels(source,bg),map_pixels(source,tint,True)
                for y in range(max(0,top-row*8),min(8,bottom-row*8)):
                    for x in range(max(0,left-col*8),min(8,right-col*8)):
                        # Blue well tiles animate during defeat/restart; only
                        # their opaque native BG1 rim is static artwork.
                        if not front[y][x] and (bg>>10)&7==4:continue
                        if front[y][x]:
                            main=struct.unpack_from('<H',ram,0x1500+(((fg>>10)&7)*16+front[y][x])*2)[0]
                            shade=0  # Native BG1 does not use subtraction.
                        else:
                            p,q=back[y][x],sub[y][x]
                            main=struct.unpack_from('<H',ram,0x1500+((((bg>>10)&7)*16+p) if p else 0)*2)[0]
                            shade=struct.unpack_from('<H',ram,0x1500+(((tint>>10)&7)*4+q)*2)[0] if q else 0
                        r,g,b=(max(0,((main>>s)&31)-((shade>>s)&31)) for s in (0,5,10))
                        expected=((r*255//31,(g*2+(g>>4))*255//63,b*255//31)
                                  if e.pixel_format==2 else tuple(v*255//31 for v in (r,g,b)))
                        sx,sy=64+col*8+x,row*8+y
                        assert picture.getpixel((sx,sy))==expected, f'Solo Dr. Mario differs from original native scene at {(sx,sy)}'


def verify_native_dr_reference(core):
    """Compare real emulator screenshots with the untouched two-player ROM."""
    from PIL import Image,ImageChops
    from verify_menu import Emulator
    from validate_single_player import menu,press,active

    source=SOURCE.read_bytes()
    for custom in (False,True):
        pictures=[]
        for rom,label in ((SOURCE,'original'),(OUTPUT,'patched')):
            e=Emulator(core,rom)
            try:
                menu(e,custom);press(e,3);active(e,1)
                e.write_memory(0x305,b'\x0b\x00');e.write_memory(0x316,b'\x01')
                active(e,3);e.run(4);press(e,3)
                path=ROOT/'custom'/'validation'/f'dr-native-{custom}-{label}.png'
                pictures.append(e.screenshot(path))
            finally:e.close()
        original,patched=pictures
        count=0
        for y in range(224):
            for x in range(125):
                bg=struct.unpack_from('<H',source,0xaa800+(y//8)*64+(x//8)*2)[0]
                # Native blue well cells contain independently seeded pills
                # and viruses. The new timer is an intentional addition.
                timer_bottom=224 if FRAME_SHADOW_ENABLED else 216
                if (bg>>10)&7==4 or (x>=104 and 184<=y<timer_bottom):continue
                assert original.getpixel((x,y))==patched.getpixel((x+64,y)), f'Original-ROM Dr. Mario scene mismatch at {(x+64,y)}, custom={custom}'
                count+=1
        for box in ((88,56,125,88),(0,0,72,4),(0,8,8,32)):
            shifted=(box[0]+64,box[1],box[2]+64,box[3])
            assert ImageChops.difference(original.crop(box),patched.crop(shifted)).getbbox() is None
        comparison=Image.new('RGB',(512,448))
        comparison.paste(original.crop((0,0,128,224)).resize((256,448),Image.Resampling.NEAREST),(0,0))
        comparison.paste(patched.crop((64,0,192,224)).resize((256,448),Image.Resampling.NEAREST),(256,0))
        comparison.save(ROOT/'custom'/'validation'/f'dr-native-original-vs-patched-{custom}.png')
        print(f'PASS original emulator reference: {count} native Dr. Mario background/HUD pixels, custom={custom}')
