#!/usr/bin/env python

import sys
import os

def decrypt(input):
    output = ''
    size = len(input)
    a = (((size & 1) << 6) | ((size & 2) << 3) | (size & 4)) ^ 0xab
    for c in input:
      output += chr(a ^ ord(c))
      a = ((a & 0x7f) << 1 | (a & 0x80) >> 7) ^ ord(c)
    return output

def encrypt(input):
    output = ''
    size = len(input)
    a = (((size & 1) << 6) | ((size & 2) << 3) | (size & 4)) ^ 0xab
    for c in input:
      output += chr(a ^ ord(c))
      a = ((a & 0x7f) << 1 | (a & 0x80) >> 7) ^ ord(output[-1])
    return output

if len(sys.argv) <> 2 or sys.argv[1] not in ('-e','-d'):
    print 'Usage: goocrypt -d  (decrypt files)'
    print '       goocrypt -e  (encrypt files)'
    sys.exit(1)
if sys.argv[1] == '-d': what, ext_in, ext_out = 'decrypting', '.bin', '.txt'
if sys.argv[1] == '-e': what, ext_in, ext_out = 'encrypting', '.txt', '.bin'

found = 0
for dirname in [ 'properties', 'res' ]:
    for (path, dirs, files) in os.walk(dirname):
        for name in files:
            if name.endswith(ext_in):
                found += 1
                path_in  = os.path.join(path, name)
                path_out = os.path.join(path, name[:-len(ext_in)]) + ext_out
                input = file(path_in, "rb").read()
                print "%s %s\n => %s"% (what, path_in, path_out)
                if what == 'decrypting': output = decrypt(input)
                if what == 'encrypting': output = encrypt(input)
                file(path_out, "wb").write(output)

if not found:
    print 'No files found! (Did you run from the World Of Goo directory?)'
else:
    print found, 'files processed'