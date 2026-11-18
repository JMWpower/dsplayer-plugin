'use strict';
/* 把「阅读源·Node聚合」配套源（source 类）写进市场索引：
 *   node tools/add-source-entry.js <version> <size> <md5>
 * 包结构：source.json + spider/hipy/阅读源Node聚合.py（py 源，指向本机 Node 服务）
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const file = path.join(root, 'market.json');
const [version = '1.0.0', size = '0', md5 = ''] = process.argv.slice(2);

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const entry = {
  id: 'legado-node-source',
  name: '阅读源·Node聚合配套源',
  author: '江湖',
  desc: '配合「阅读源·Node聚合」服务使用的 py 书源（hipy 引擎）：一个源看全部乐读书源，'
    + '分类=书源、书=条目、正文按 novel:// 交付，数据全部走本机 Node 服务（默认 http://127.0.0.1:13000）。'
    + '需先安装同市场的服务包，服务没起来时源不可用。',
  version,
  type: 'source',
  category: 'app',
  url: 'packages/legado-node-source-' + version + '.zip',
  size: Number(size),
  md5,
  changelog: 'v' + version + '：首个版本，提供阅读配套 py 源（novel:// 正文），与阅读源·Node聚合服务成对使用。',
  tags: ['书源', '阅读', '配套'],
  icon: 'icons/legado.png',
  platforms: ['android', 'win32'],
};

const idx = data.plugins.findIndex((p) => p.id === entry.id);
if (idx >= 0) {
  data.plugins[idx] = { ...data.plugins[idx], ...entry };
  console.log('更新已有条目 #' + idx);
} else {
  data.plugins.push(entry);
  console.log('追加新条目，共 ' + data.plugins.length + ' 条');
}

const now = new Date();
const pad = (n) => String(n).padStart(2, '0');
const off = -now.getTimezoneOffset() / 60;
const stamp = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate())
  + 'T' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds())
  + (off >= 0 ? '+' : '-') + pad(Math.abs(off)) + ':00';
data.updatedAt = stamp;

fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
console.log('updatedAt = ' + stamp);
console.log('条目：' + entry.id + ' / ' + entry.name + ' / v' + entry.version + ' / ' + entry.url);
