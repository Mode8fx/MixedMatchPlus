"""Verify/capture emulator frames with an installed SNES libretro core; needs Pillow.

Default: capture the patched Mixed Match title screen.
Use --check to check the preview, title menu, and both menu destinations.
Example: python scripts/verify_menu.py --sequence 600 start:1 120
Joypad names: b, y, select, start, up, down, left, right, a, x, l, r.
Numbers are frames with no buttons; button:frames holds that button.
"""

import argparse
import ctypes as C
from pathlib import Path

from PIL import Image, ImageChops

from build_rom import (OUTPUT, ROOT, SOURCE, PREVIEW_GFX_BASE, PREVIEW_MAP_OFFSET,
                       PREVIEW_TILES, build_rom)


SELECT_SEQUENCE = ["600", "start:1", "120"]
MENU_SEQUENCE = SELECT_SEQUENCE + ["down:1", "1", "start:1", "120"]


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                ("size", C.c_size_t), ("meta", C.c_char_p)]


class Emulator:
    def __init__(self, core: Path, rom: Path):
        self.core = C.CDLL(str(core.resolve()))
        self.pixel_format = 0
        self.buttons = set()
        self.buttons_two = set()
        self.frame = None
        self.directory = str((ROOT / "output").resolve()).encode()
        self.callbacks = []

        def environment(cmd, data):
            if cmd == 10:  # SET_PIXEL_FORMAT
                self.pixel_format = C.cast(data, C.POINTER(C.c_int))[0]
                return self.pixel_format in (0, 1, 2)
            if cmd in (9, 31):  # GET_SYSTEM_DIRECTORY / GET_SAVE_DIRECTORY
                C.cast(data, C.POINTER(C.c_char_p))[0] = self.directory
                return True
            if cmd == 18:  # GET_VARIABLE_UPDATE
                C.cast(data, C.POINTER(C.c_bool))[0] = False
                return True
            return False

        def video(data, width, height, pitch):
            if data and data != C.c_void_p(-1).value:
                self.frame = (C.string_at(data, pitch * height), width, height, pitch)

        def input_state(port, device, index, button):
            return int(device == 1 and ((port == 0 and button in self.buttons)
                                       or (port == 1 and button in self.buttons_two)))

        callbacks = (
            ("environment", C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p), environment),
            ("video_refresh", C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t), video),
            ("audio_sample", C.CFUNCTYPE(None, C.c_int16, C.c_int16), lambda l, r: None),
            ("audio_sample_batch", C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t), lambda data, frames: frames),
            ("input_poll", C.CFUNCTYPE(None), lambda: None),
            ("input_state", C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint), input_state),
        )
        for name, callback_type, function in callbacks:
            callback = callback_type(function)
            self.callbacks.append(callback)
            setter = getattr(self.core, "retro_set_" + name)
            setter.argtypes = [callback_type]
            setter(callback)

        self.core.retro_init()
        self.rom_buffer = C.create_string_buffer(rom.read_bytes())
        info = GameInfo(str(rom.resolve()).encode(), C.cast(self.rom_buffer, C.c_void_p),
                        len(self.rom_buffer) - 1, None)
        self.core.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        if not self.core.retro_load_game(C.byref(info)):
            raise RuntimeError("Core could not load ROM")
        self.core.retro_set_controller_port_device(0, 1)
        self.core.retro_set_controller_port_device(1, 1)
        self.core.retro_get_memory_data.argtypes = [C.c_uint]
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.argtypes = [C.c_uint]
        self.core.retro_get_memory_size.restype = C.c_size_t

    def run(self, frames: int, buttons=(), buttons_two=()):
        self.buttons = set(buttons)
        self.buttons_two = set(buttons_two)
        for _ in range(frames):
            self.core.retro_run()

    def memory(self, kind=2):
        size = self.core.retro_get_memory_size(kind)
        if not size:
            raise RuntimeError("Core does not expose this RAM; use the Snes9x core for validation")
        return C.string_at(self.core.retro_get_memory_data(kind), size)

    def write_memory(self, address: int, data: bytes, kind=2):
        size = self.core.retro_get_memory_size(kind)
        if address < 0 or address + len(data) > size:
            raise ValueError("Memory write outside exposed RAM")
        C.memmove(self.core.retro_get_memory_data(kind) + address, data, len(data))

    def screenshot(self, path: Path):
        if self.frame is None:
            raise RuntimeError("Core produced no video")
        raw, width, height, pitch = self.frame
        if self.pixel_format == 1:
            picture = Image.frombytes("RGB", (width, height), raw, "raw", "BGRX", pitch)
        else:
            rgb = bytearray()
            for y in range(height):
                row = memoryview(raw)[y * pitch:y * pitch + width * 2].cast("H")
                for value in row:
                    if self.pixel_format == 2:
                        r, g, b = value >> 11, (value >> 5) & 63, value & 31
                        rgb.extend((r * 255 // 31, g * 255 // 63, b * 255 // 31))
                    else:
                        r, g, b = (value >> 10) & 31, (value >> 5) & 31, value & 31
                        rgb.extend((r * 255 // 31, g * 255 // 31, b * 255 // 31))
            picture = Image.frombytes("RGB", (width, height), bytes(rgb))
        path.parent.mkdir(parents=True, exist_ok=True)
        picture.save(path)
        return picture

    def close(self):
        self.core.retro_unload_game()
        self.core.retro_deinit()


def capture(core: Path, rom: Path, sequence: list[str], path: Path):
    names = "b y select start up down left right a x l r".split()
    emulator = Emulator(core, rom)
    try:
        for action in sequence:
            if ":" in action:
                button, frames = action.split(":")
                emulator.run(int(frames), [names.index(button)])
            else:
                emulator.run(int(action))
        picture = emulator.screenshot(path)
        print(f"Captured: {path}")
        return picture
    finally:
        emulator.close()


def check(core: Path):
    original = SOURCE.read_bytes()
    patched = OUTPUT.read_bytes()
    assert patched == build_rom(original) == build_rom(original), "Build differs"
    allowed = set(range(0x7FDC, 0x7FE0)) | set(range(0xB8D96, 0xB8DAC))
    allowed.update(range(PREVIEW_MAP_OFFSET, PREVIEW_MAP_OFFSET + 12))
    for tile in PREVIEW_TILES:
        offset = PREVIEW_GFX_BASE + tile * 32
        allowed.update(range(offset, offset + 32))
    from single_player import apply
    for start,end in apply(bytearray(original), original):
        allowed.update(range(start,end))
    changed = {i for i, (a, b) in enumerate(zip(original, patched)) if a != b}
    assert changed <= allowed, "Unexpected changes outside labels/checksum"
    scenarios = (
        ("game-select", SELECT_SEQUENCE + ["down:1", "120"], (48, 208, 96, 212)),
        ("game-select-dim", SELECT_SEQUENCE, (48, 208, 96, 212)),
        ("mixed-match-menu", MENU_SEQUENCE, (88, 176, 176, 184)),
    )
    for name, sequence, label_bounds in scenarios:
        pictures = [capture(core, rom, sequence,
                            ROOT / "custom" / "validation" / f"{prefix}{name}.png")
                    for rom, prefix in ((SOURCE, "original-"), (OUTPUT, ""))]
        difference = ImageChops.difference(*pictures)
        if label_bounds:
            assert difference.getbbox(), f"{name} did not change"
            # Only CUSTOM GAME may differ; GAME START and the cursor stay intact.
            difference.paste((0, 0, 0), label_bounds)
            assert difference.getbbox() is None, f"Unrelated {name} pixels changed"
        else:
            assert difference.getbbox() is None, f"{name} behavior changed"
    assert SOURCE.read_bytes() == original, "Original ROM changed"
    print(f"PASS: repeatable build, {len(changed)} changed bytes, title/preview labels localized, original ROM intact")
    from validate_single_player import verify
    verify(core)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=Path(
        "C:/RetroBat/emulators/retroarch/cores/snes9x_libretro.dll"))
    parser.add_argument("--rom", type=Path, default=OUTPUT)
    parser.add_argument("--sequence", nargs="+", default=MENU_SEQUENCE)
    parser.add_argument("--capture", type=Path, default=ROOT / "custom" / "validation" / "mixed-match-menu.png")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check(args.core)
    else:
        capture(args.core, args.rom, args.sequence, args.capture)


if __name__ == "__main__":
    main()
