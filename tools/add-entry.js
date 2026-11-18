'use strict';
/* 把 legado-node 条目写进市场索引：node tools/add-entry.js <version> <size> <md5> [changelog] */
const fs = require('fs');
const path = require('path');
const os = require('os');

const root = path.join(__dirname, '..');
const file = path.join(root, 'market.json');
const [version = '2.0.0', size = '0', md5 = '', customLog = ''] = process.argv.slice(2);

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const entry = {
  id: 'legado-node',
  name: '阅读源·Node聚合',
  author: '江湖',
  desc: '把本地 sources.json 里的乐读书源聚合成一份 HTML 规则书源（/legado_html.json，阅读器直接导入），'
    + '自带管理面板（浏览内容 / 源管理 / 源仓库三页签，内置 yiove、yuancang.cc、yckceo.com 三个书源仓库一键导入）'
    + '与 T3/T4/正文接口，默认端口 13000，无第三方依赖。需先安装 nodejs 运行时插件。',
  version,
  type: 'server',
  category: 'app',
  url: 'packages/legado-node-' + version + '.zip',
  size: Number(size),
  md5,
  changelog: customLog || ('v' + version + '：书源状态徽章 + 「检测全部」体检（空内容不再无解释）；导入后自动检测并提示原因；'
    + '修复请求头全角连字符导致的 Cannot convert argument to a ByteString；JS 规则源明确报错而不是静默空白；书库默认挑可用源。'),
  tags: ['服务', '书源', '聚合'],
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
