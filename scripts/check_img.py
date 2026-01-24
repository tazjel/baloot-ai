
import struct
import os

def get_png_dimensions(file_path):
    with open(file_path, 'rb') as f:
        data = f.read(24)
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return "Not a PNG"
        w, h = struct.unpack('>LL', data[16:24])
        return w, h

print(get_png_dimensions('c:/Users/MiEXCITE/Projects/baloot-ai/frontend/public/cards.png'))
