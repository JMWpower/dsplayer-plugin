# -*- coding: utf-8 -*-
"""把 source 类插件目录打成市场包。

source 类包结构（与 apps 端 sdcard 布局一致）：
    source.json                       {"target": "dsplayer"}
    spider/hipy/<名称>.py             py 源（hipy 引擎）
    spider/html/<名称>.html           HTML 网页源
    server/node/drpy-node/spider/js/  drpy JS 源

用法：
    python make_source_package.py <源目录> <输出 zip>
例：
    python make_source_package.py .build-source packages/legado-node-source-1.0.0.zip

要点：
  * 条目路径一律用 `/`（PS 5.1 的 ZipFile::CreateFromDirectory 会写 `\\`，别用）
  * source.json 排在第一条
  * UTF-8 文件名（中文源名）由 zipfile 自动置 UTF-8 flag，Android 端可正常解压
"""
import hashlib
import os
import sys
import zipfile


def collect(src):
    items = []
    for root, _dirs, files in os.walk(src):
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src).replace("\\", "/")
            items.append((rel, full))
    # source.json 优先，其余按路径排序
    items.sort(key=lambda it: (it[0] != "source.json", it[0]))
    return items


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    if not os.path.isdir(src):
        print("源目录不存在:", src)
        return 2
    if not os.path.isfile(os.path.join(src, "source.json")):
        print("缺少 source.json:", src)
        return 3

    os.makedirs(os.path.dirname(out), exist_ok=True)
    items = collect(src)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, full in items:
            zf.write(full, rel)

    raw = open(out, "rb").read()
    print("输出:", out)
    print("条目:", len(items))
    for rel, _full in items:
        print("  -", rel)
    print("size:", len(raw))
    print("md5 :", hashlib.md5(raw).hexdigest())

    with zipfile.ZipFile(out) as zf:
        bad = [n for n in zf.namelist() if "\\" in n]
        print("反斜杠条目:", bad if bad else "无")
        print("首条目:", zf.namelist()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
