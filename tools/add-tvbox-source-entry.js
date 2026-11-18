'use strict';
/* 把「阅读书架·TVBox配套源」（source 类）写进市场索引：
 *   node tools/add-tvbox-source-entry.js <version> <size> <md5> [changelog]
 * 包结构：source.json + spider/hipy/阅读书架TVBox.py（hipy py 源，指向 Legado Server Node 后端）
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const file = path.join(root, 'market.json');
const [version = '1.0.0', size = '0', md5 = '', customLog = ''] = process.argv.slice(2);

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const entry = {
  id: 'legado-tvbox-source',
  name: '阅读书架·TVBox配套源',
  author: 'JmwPower',
  desc: '配合「Legado Server (Node)」阅读后端使用的 TVBox / T3 配套 py 源（hipy 引擎）：'
    + '把书架搬进 TVBox 阅读，分类=书架视图（本地书架 / 我的书架 / 网络书架 / 分组），书=书架条目，'
    + '章节=剧集，正文按 novel:// 交付。重点支持本地书架——导入的 TXT / EPUB 由后端从本地缓存直出正文，'
    + '断网也能读；同时支持书源全网搜索与网络书籍。默认 http://127.0.0.1:8998，'
    + 'ext 可配 base / play_base / mode / timeout / hide / max_ep / shelf / scope。'
    + '需先启动 Legado Server (Node) 阅读后端；也可直接把 http://IP:8998/sub 填进 TVBox 订阅地址。',
  version,
  type: 'source',
  category: 'app',
  url: 'packages/legado-tvbox-source-' + version + '.zip',
  size: Number(size),
  md5,
  changelog: customLog || ('v' + version + '：首版，提供阅读书架 TVBox 配套 py 源。'
    + '本地书架（TXT/EPUB）正文由后端缓存直出、断网可读；支持书架分类、搜索、详情章节、'
    + 'novel:// / webview / direct 三种正文模式，以及封面 host 归一化（服务与 TVBox 不同机可用）。'),
  tags: ['书源', '阅读', '配套', '本地书架'],
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
