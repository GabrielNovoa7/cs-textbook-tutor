from pathlib import Path
import struct
import pymupdf
root = Path(__file__).resolve().parents[1]
doc = pymupdf.open(root / 'desktop/icon.svg')
image = doc[0].get_pixmap().tobytes('png')
(root / 'desktop/icon.png').write_bytes(image)
header = struct.pack('<HHH', 0, 1, 1)
entry = struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(image), 22)
(root / 'desktop/icon.ico').write_bytes(header + entry + image)
