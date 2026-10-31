"""Build the compact Custom Game music label and value field."""
from build_rom import text_tiles


def build_music_row(source: bytes) -> bytes:
    # An 18-cell row is centered at x=128; the value aligns with P1's settings.
    label=text_tiles('MUSIC SELECT  BGM1',0x2000)
    row=bytearray(source[0xae800+5*64:0xae800+6*64])
    row[14:14+len(label)]=label
    return bytes(row)
