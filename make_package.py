#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 .build/ 打成 packages/legado-node-<version>.zip（POSIX 路径分隔符，服务包结构）。"""
import hashlib
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, '.build')
PKGS = os.path.join(HERE, 'packages')
VERSION = sys.argv[1] if len(sys.argv) > 1 else '2.0.0'
OUT = os.path.join(PKGS, 'legado-node-%s.zip' % VERSION)

if os.path.exists(OUT):
    os.remove(OUT)

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.write(os.path.join(STAGE, 'server.json'), 'server.json')
    for root, dirs, files in os.walk(STAGE):
        dirs.sort()
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, STAGE).replace('\\', '/')
            if rel == 'server.json':
                continue
            z.write(p, rel)

size = os.path.getsize(OUT)
md5 = hashlib.md5(open(OUT, 'rb').read()).hexdigest()
with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
bad = [n for n in names if '\\' in n]
print('file    =', OUT)
print('size    =', size)
print('md5     =', md5)
print('entries =', len(names))
print('backslash entries =', len(bad))
print('head    =', ', '.join(names[:6]))
