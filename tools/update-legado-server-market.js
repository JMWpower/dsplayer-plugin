'use strict';
/* 本批次上架：Legado Server (Node) 服务包 + 两个 TVBox 源包加 [书] 标签重发。
 *   node tools/update-legado-server-market.js
 * size/md5 直接从 packages/ 中的 zip 计算，避免手工传参对不上账。
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = path.join(__dirname, '..');
const file = path.join(root, 'market.json');

function packageInfo(name) {
  const p = path.join(root, 'packages', name);
  const raw = fs.readFileSync(p);
  return { url: 'packages/' + name, size: raw.length, md5: crypto.createHash('md5').update(raw).digest('hex') };
}

const SVR = packageInfo('legado-server-node-1.0.0.zip');
const SRC = packageInfo('legado-node-source-1.0.1.zip');
const TVB = packageInfo('legado-tvbox-source-1.0.1.zip');

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const upsert = (entry) => {
  const i = data.plugins.findIndex((p) => p.id === entry.id);
  if (i >= 0) data.plugins[i] = { ...data.plugins[i], ...entry };
  else data.plugins.push(entry);
  return i >= 0 ? '更新' : '新增';
};

const serverEntry = {
  id: 'legado-server-node',
  name: 'Legado Server · Node阅读后端',
  author: 'JmwPower',
  desc: 'Legado Server 的 Node.js 移植版（Fastify + SQLite）：自带 Web 阅读前端、书架与本地书（TXT/EPUB 导入、封面直出）、书源规则池、Z-Library 图书馆，以及 TVBox/CMS 订阅接口（书架分类 / 搜索 / 章节 / novel:// 正文），默认端口 8998。包内 sqlite 为基于 Node 内置 node:sqlite 的纯 JS 实现，无原生模块，Android / Windows 通用；数据目录写在包外，覆盖升级不丢书。需先安装 nodejs 运行时插件（Node >= 22.5）。配合市场「阅读书架·TVBox配套源」使用，或把 http://IP:8998/sub 直接填进 TVBox 订阅地址。',
  version: '1.0.0',
  type: 'server',
  category: 'app',
  ...SVR,
  changelog: 'v1.0.0：首个上架版本。Legado Server (Node) 阅读后端服务包，含 Web 前端、书架 / 本地书、Z-Library 图书馆与 TVBox/CMS 接口（默认 8998）。分发包内把 better-sqlite3 换成 node:sqlite 纯 JS 兼容层，去掉原生模块依赖，Android arm64 与 Windows 均可直接运行；预置 config.yaml 保证装完即监听，数据目录落在包外。',
  tags: ['服务', '阅读', '书架', 'TVBox'],
  icon: 'icons/legado.png',
  platforms: ['android', 'win32'],
};

const sourcePatch = (id, info, pyName, extra) => ({
  id,
  version: '1.0.1',
  ...info,
  changelog: 'v1.0.1：py 源文件名加 [书] 标签（' + pyName + '），TVBox 壳子按标签归入阅读类规则；功能与 v1.0.0 完全一致。' + extra
    + '升级后请手动删除旧的无标签同名源，避免列表里出现重复条目。',
});

const sourceDescTail = ' v1.0.1 起 py 源文件名带 [书] 标签（TVBox 壳子据此归入阅读类）。';

console.log('server :', SVR.size, SVR.md5);
console.log('source :', SRC.size, SRC.md5);
console.log('tvbox  :', TVB.size, TVB.md5);

console.log(upsert(serverEntry), serverEntry.id);

const patchSrc = sourcePatch('legado-node-source', SRC, '阅读源Node聚合[书].py', '');
const iSrc = data.plugins.findIndex((p) => p.id === patchSrc.id);
data.plugins[iSrc] = { ...data.plugins[iSrc], ...patchSrc, desc: data.plugins[iSrc].desc.replace(/\s*$/, '') + sourceDescTail };
console.log('更新', patchSrc.id, '→ v1.0.1');

const patchTvb = sourcePatch('legado-tvbox-source', TVB, '阅读书架TVBox[书].py', '配套服务包「Legado Server · Node阅读后端」已同步上架。');
const iTvb = data.plugins.findIndex((p) => p.id === patchTvb.id);
data.plugins[iTvb] = { ...data.plugins[iTvb], ...patchTvb, desc: data.plugins[iTvb].desc.replace(/\s*$/, '') + sourceDescTail };
console.log('更新', patchTvb.id, '→ v1.0.1');

const now = new Date();
const pad = (n) => String(n).padStart(2, '0');
const off = -now.getTimezoneOffset() / 60;
data.updatedAt = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate())
  + 'T' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds())
  + (off >= 0 ? '+' : '-') + pad(Math.abs(off)) + ':00';

fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
console.log('updatedAt =', data.updatedAt, '| 条目数 =', data.plugins.length);
