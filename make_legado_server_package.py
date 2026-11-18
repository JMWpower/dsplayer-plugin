#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 legado-server-node 的 DsPlayer server 插件包。

源目录默认取同级的 legado-server-main/server-node，产出：
  .build-legado-server/server.json             （manfiest，zip 根部）
  .build-legado-server/legado-server-node/*    （workDir，整目录解压到 server/node/）
  packages/legado-server-node-<version>.zip

与仓库既有 make_package.py 同纪律：POSIX 路径分隔符、server.json 首条目、
中文文件名 UTF-8 flag、末尾打印 size/md5 供 market.json 对账。

分发包内 better-sqlite3 被替换为基于 node:sqlite 的纯 JS 兼容实现，
避免 Android arm64 无法加载 Windows 原生 .node，源码与编译产物零改动。
"""
import hashlib
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, '.build-legado-server')
PKGS = os.path.join(HERE, 'packages')
VERSION = sys.argv[1] if len(sys.argv) > 1 else '1.0.0'
SRC = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath(
    os.path.join(HERE, '..', 'legado-server-main', 'server-node'))
WEB = os.path.abspath(os.path.join(SRC, '..', 'web', 'dist'))
OUT = os.path.join(PKGS, 'legado-server-node-%s.zip' % VERSION)
WORK = os.path.join(STAGE, 'legado-server-node')

SERVER_JSON = {
    "workDir": "legado-server-node",
    "entry": "dist/index.js",
    "port": 8998,
    "serviceName": "Legado Server · Node 阅读后端",
    "version": VERSION,
    "runtime": "node",
    "autoStart": True,
    "desc": "Legado Server 的 Node.js 移植版（Fastify + SQLite）：自带 Web 阅读前端、书架与本地书（TXT/EPUB 导入、封面直出）、书源规则池、Z-Library 图书馆，以及 TVBox/CMS 订阅接口（书架分类/搜索/章节/novel:// 正文），默认端口 8998。包内 sqlite 为 node:sqlite 纯 JS 实现，无原生模块，Android/Windows 通用。需先安装 nodejs 运行时插件（Node >= 22.5）；配合市场「阅读书架·TVBox配套源」使用，或把 http://IP:8998/sub 直接填进 TVBox 订阅地址。数据目录写到包外的 legado-server-data/，覆盖升级不丢书。",
}

CONFIG_YAML = """# Legado Server (Node) · DsPlayer 服务插件预置配置
# 环境变量优先级更高；本文件存在即代表已完成初始化，服务会直接启动。
server.host: 0.0.0.0
server.port: 8998
# 数据目录放在 workDir 之外：覆盖式更新只替换 legado-server-node/，
# 书架、本地书、封面缓存等用户数据不会随升级丢失。
data.dir: ../legado-server-data
cache.manga.max_gb: 10
cache.manga.max_global_fetches: 6
cache.manga.prefetch: true
cache.manga.gc: true
cache.audio.max_gb: 20
cache.audio.max_global_fetches: 3
cache.audio.prefetch: true
cache.audio.gc: true
cover.self_heal: true
"""

SHIM_INDEX = """'use strict';
// 分发包专用：把 better-sqlite3 的同步 API 映射到 Node 内置 node:sqlite。
// 目的：Android arm64 的 node24 运行时无法加载 Windows 编译的 .node 原生模块。
const { DatabaseSync } = require('node:sqlite');

class Statement {
  constructor(db, sql) { this.stmt = db.prepare(sql); }
  get(...params) { return this.stmt.get(...params); }
  all(...params) { return this.stmt.all(...params); }
  run(...params) {
    const r = this.stmt.run(...params);
    return { changes: Number(r.changes), lastInsertRowid: r.lastInsertRowid };
  }
}

class Database {
  constructor(path) { this.db = new DatabaseSync(path); }
  pragma(text) { this.db.exec('PRAGMA ' + text); return undefined; }
  exec(sql) { this.db.exec(sql); return this; }
  prepare(sql) { return new Statement(this.db, sql); }
  close() { this.db.close(); }
  transaction(fn) {
    const db = this.db;
    return (...args) => {
      db.exec('BEGIN');
      try {
        const result = fn(...args);
        db.exec('COMMIT');
        return result;
      } catch (e) {
        db.exec('ROLLBACK');
        throw e;
      }
    };
  }
}

module.exports = Database;
module.exports.default = Database;
module.exports.Database = Database;
module.exports.Statement = Statement;
"""

SHIM_PKG = {
    "name": "better-sqlite3",
    "version": "11.10.0",
    "main": "index.js",
    "type": "commonjs",
    "description": "DsPlayer 分发包内的 node:sqlite 同步兼容层（无原生模块）",
}

DEPLOY_DOC = """# Legado Server (Node) · DsPlayer 服务插件部署说明

## 安装

1. 在市场先安装 **nodejs 运行时插件**（需 Node >= 22.5，Android 运行时的
   node24-arm64 已满足），再安装本服务包。
2. 服务默认不自启；`server.json` 已声明 autoStart，装完在服务页确认一次即可。
   启动后监听 **8998**（tcp 探活同端口）。

## 访问

- Web 阅读前端：`http://<设备IP>:8998/`
- TVBox 订阅地址：`http://<设备IP>:8998/sub`（可直接填进 TVBox，不装 py 源也能用）
- 配套 py 源：市场「阅读书架·TVBox配套源」「阅读源·Node聚合配套源」，
  默认指向 `http://127.0.0.1:8998`；服务与 TVBox 不同机时用 ext 的
  `base` / `play_base` 指向设备 IP。

## 数据目录

预置 `config/config.yaml` 把 `data.dir` 指向 `../legado-server-data`（包目录之外）。
覆盖升级只替换 `legado-server-node/`，书架、本地书、封面缓存不会丢失。
如需自定义，设置环境变量 `LEGADO_DATA_DIR` / `LEGADO_PORT` / `LEGADO_WEB_DIR`
（环境变量优先于 config.yaml）。

## 关于 sqlite

上游使用 `better-sqlite3` 原生模块，但 Android arm64 无法加载为 Windows 编译的
`.node` 文件。本分发包把 `node_modules/better-sqlite3` 换成了基于 Node 内置
`node:sqlite` 的纯 JS 同步兼容层（`pragma` / `exec` / `prepare` / `transaction`
/ `get` / `all` / `run`），跨平台零原生依赖，能直接读写既有 SQLite/WAL 数据文件。
**包内已自带全部依赖，不要执行 npm install**（会覆盖兼容层）。

## 目录

```
legado-server-node/
├── server.json            ← 实际在 zip 根部（平铺到 server/node/ 时不落盘）
├── dist/                  编译后的服务端 JS（入口 dist/index.js）
├── web-dist/              阅读前端构建产物
├── config/config.yaml     预置配置（保证首次启动即监听 8998）
├── node_modules/          生产依赖（含 sqlite 兼容层）
├── package.json
└── 部署说明.md
```
"""

# 这些是 devDependencies 或 better-sqlite3 原生模块专用依赖，分发包不需要
EXCLUDE_TOP = {
    'typescript', '@types', '.bin', 'better-sqlite3',
    'bindings', 'file-uri-to-path', 'detect-libc', 'github-from-package',
    'prebuild-install', 'node-gyp-build', 'expand-template', 'mkdirp-classic',
    'napi-build-utils', 'simple-get', 'tunnel-agent',
}


def copytree_filtered(src, dst, exclude):
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if name in exclude:
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s) and not os.path.islink(s):
            shutil.copytree(s, d, symlinks=True)
        elif os.path.isfile(s):
            shutil.copy2(s, d)


def main():
    for p in (os.path.join(SRC, 'dist', 'index.js'), os.path.join(WEB, 'index.html')):
        if not os.path.isfile(p):
            print('缺少必要产物：%s' % p)
            return 1
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(WORK)

    shutil.copytree(os.path.join(SRC, 'dist'), os.path.join(WORK, 'dist'))
    shutil.copytree(WEB, os.path.join(WORK, 'web-dist'))
    copytree_filtered(os.path.join(SRC, 'node_modules'),
                      os.path.join(WORK, 'node_modules'), EXCLUDE_TOP)

    shim = os.path.join(WORK, 'node_modules', 'better-sqlite3')
    os.makedirs(shim)
    with open(os.path.join(shim, 'index.js'), 'w', encoding='utf-8') as f:
        f.write(SHIM_INDEX)
    with open(os.path.join(shim, 'package.json'), 'w', encoding='utf-8') as f:
        json.dump(SHIM_PKG, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.join(WORK, 'config'))
    with open(os.path.join(WORK, 'config', 'config.yaml'), 'w', encoding='utf-8') as f:
        f.write(CONFIG_YAML)

    with open(os.path.join(SRC, 'package.json'), encoding='utf-8') as f:
        pkg = json.load(f)
    pkg['version'] = VERSION
    pkg['engines'] = {'node': '>=22.5.0'}
    pkg['scripts'] = {'start': 'node dist/index.js'}
    with open(os.path.join(WORK, 'package.json'), 'w', encoding='utf-8') as f:
        json.dump(pkg, f, ensure_ascii=False, indent=2)
    shutil.copy2(os.path.join(SRC, 'package-lock.json'),
                 os.path.join(WORK, 'package-lock.json'))
    with open(os.path.join(WORK, '部署说明.md'), 'w', encoding='utf-8') as f:
        f.write(DEPLOY_DOC)
    with open(os.path.join(STAGE, 'server.json'), 'w', encoding='utf-8') as f:
        json.dump(SERVER_JSON, f, ensure_ascii=False, indent=2)

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

    raw = open(OUT, 'rb').read()
    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
    print('file    =', OUT)
    print('size    =', len(raw))
    print('md5     =', hashlib.md5(raw).hexdigest())
    print('entries =', len(names))
    print('backslash entries =', len([n for n in names if '\\' in n]))
    print('head    =', ', '.join(names[:6]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
