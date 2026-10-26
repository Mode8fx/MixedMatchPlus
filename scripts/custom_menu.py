"""Build the compact Custom Game music label and value field."""
import struct


def build_music_row(source: bytes) -> bytes:
    # An 18-cell row is centered at x=128; the value aligns with P1's settings.
    label='MUSIC SELECT  BGM1'
    row=bytearray(source[0xae800+5*64:0xae800+6*64])
    for index,char in enumerate(label):
        tile=0x2000 if char==' ' else 0x2100+(int(char) if char.isdigit() else ord(char)-55)
        struct.pack_into('<H',row,(7+index)*2,tile)
    return bytes(row)
