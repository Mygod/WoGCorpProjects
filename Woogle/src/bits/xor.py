#!/usr/bin/env python
import sys, zlib, struct

if len(sys.argv) > 1:
  text = open(sys.argv[1]).read()
  if sys.argv[1][-4:] == ".bin" or sys.argv[1][-4:] == ".dat":
    size = len(text)

    a = (((size & 1) << 6) | ((size & 2) << 3) | (size & 4)) ^ 0xab
    for c in text:
      sys.stdout.write(chr(a ^ ord(c)))
      a = ((a & 0x7f) << 1 | (a & 0x80) >> 7) ^ ord(c)

#    a = (((size & 1) << 6) | ((size & 2) << 3) | (size & 4)) ^ 0xffffffab
#    for c in text:
#      sys.stdout.write(chr((a ^ ord(c)) & 0xff))
#      a = ((a & ~0xff) | (a << 1 | (a & 0x80) >> 7) & 0xff) ^ ord(c)
  elif sys.argv[1][-11:] == ".png.binltl":
    # repack .png.binltl files into png
    width, height, size, fullsize = struct.unpack("<HHII", text[:12])
    data = zlib.decompress(text[12:12+size])
    side = 1
    while side < width or side < height:
      side *= 2
    assert fullsize == side * side * 4
    image = ""
    # images are stored as a square, so crop the image data
    for line in range(height):
      # 00 filter type byte for png
      image += "\x00" + data[line*side*4:(line*side + width)*4]
    # output png
    sys.stdout.write("\x89\x50\x4E\x47\x0D\x0A\x1A\x0A")
    def chunk(type, data):
      check = type + data
      sys.stdout.write(struct.pack(">I", len(data)))
      sys.stdout.write(check)
      sys.stdout.write(struct.pack(">I", zlib.crc32(check) & 0xffffffff))
    chunk("IHDR", struct.pack(">II", width, height) + "\x08\x06\x00\x00\x00")
    chunk("IDAT", zlib.compress(image, 9))
    chunk("IEND", "")
  else:
    sys.stdout.write(text)

