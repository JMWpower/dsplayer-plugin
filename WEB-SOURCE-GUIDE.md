# Web 源开发指南（fm / ds 桥 API 参考）

> 状态：已实施 ｜ 最后更新：2026-11-17 ｜ 关联代码：lib/services/web/web_ds_js.dart（注入脚本，API 唯一事实源）、lib/services/web/web_bridge.dart（Dart 侧分发）、lib/pages/web/web_pane.dart（env 构造）
> 读者：写 Web 源的开发者（可直接把本文 + 样例丢给 AI 代写）。机制设计背景见 [WEB-SOURCE-DESIGN.md](WEB-SOURCE-DESIGN.md) 与 [WEB-FM-FULL-COMPAT-DESIGN.md](WEB-FM-FULL-COMPAT-DESIGN.md)；本文只讲「页面里能调什么、怎么调」。

## 〇、Web 源是什么

一个**普通 HTML 页面**就是源：接口配置里站点的 `api` 指向一个 html 地址（或 `web://` 前缀 URL / 本地 `file://` 路径），`type=3` 家族的 html 分支。壳子用 WebView 整页渲染你的页面，并在页面任何脚本运行前注入 `ds.js`——你由此拿到 `window.ds`（DsPlayer 规范 API）与 `window.fm`（webhtv/fongmi 兼容 API，两者同注册表），页面自身负责首页/分类/详情/搜索的 UI 与数据抓取，播放、导航、存储等设备能力全走桥。

**api 三种形态**：`http(s)://…`（在线页面直载）/ `web://域名或完整URL`（在线形态的语义前缀，裸域名自动补 https）/ `file://` 或裸本地路径（本地源包，走网关 /file 通道，相对资源同源可解析）。本地扫描位 `spider/html/`（源码包顶层目录，见 plugin-build.md §一.4）。

最小可跑源（本地放一个 html，配置 api 指向它即可）：

```html
<!DOCTYPE html>
<html><body>
<button onclick="fm.play('https://example.com/video.mp4','测试')">播放</button>
<script>
// 页面自己的代码；ds/fm 已在文档开始前注入，无需引 SDK
</script>
</body></html>
```

## 一、就绪机制（写代码前必读）

- `ds.js` 在 `AT_DOCUMENT_START` 注入，**早于你页面的任何脚本**——head 里可直接用 `window.fm` 判定环境（存在即运行在 DsPlayer 内，webhtv 生态叫 fm-native）。
- 就绪事件 `dsready` / `fmsdk`（同名双发）：同步派发一次 + DOMContentLoaded 补发一次——**在 body 末尾 addEventListener 也能收到**，无需排队技巧。
- 桥传输是异步 Promise；页面脚本无需 ES6+ 之外假设（注入脚本自身 ES5，老 WebView 内核可跑；页面可以用现代语法，取决于目标设备 WebView）。
- `window.fongmiBridge === window.fm`、`window.fongmiClient = {isLeanback, mode}`（leanback=TV 形态）——fongmi 生态页面零改动探测。

## 二、ds 规范 API（`window.ds`）

| API | 签名 | 说明 |
|---|---|---|
| `ds.env` | 属性 | 环境快照（字段表见 §六；theme/viewport 等随事件增量更新） |
| `ds.version` | 属性 | 壳子版本号 |
| `ds.req(url, opt)` | `Promise<{ok,status,headers,url,cookies,body,error?}>` | **免跨域 HTTP**（CORS 由壳子原生网络栈豁免）。opt 全量表与网络口径见 §2.1。业务失败（4xx/5xx）**不 reject**——resolve 里 `ok:false`，自己判（`if(!r\|\|!r.ok)return`）。仅桥层崩溃才 reject |
| `ds.res(url, opt)` | 同步返回 string | 资源代理 URL（`/mediaProxy` 路径）：`<img src=ds.res(pic,{Referer:'…'})>` 解决图片防盗链 |
| `ds.store.get/set/remove(k, v?, ns?)` / `keys(ns)` | Promise | 键值持久存储（按源隔离，ns 可再分域；v 任意 JSON 值） |
| `ds.play(spec)` | Promise | 播放（spec 见 §五） |
| `ds.openVod(vod)` | Promise | 推壳子原生详情页（vod 对象，字段同 §五 spec 超集） |
| `ds.tab(name)` / `ds.back()` | Promise | 切壳子底部 tab / 返回 |
| `ds.search(kw)` | Promise | 跳壳子搜索页并预填关键词 |
| `ds.external(url)` | Promise | 系统浏览器打开 |
| `ds.toast(msg)` / `ds.clipboard.get/set` / `ds.fullscreen(bool)` / `ds.setTitle(t)` | Promise | UI 杂项（toast 有速率闸 1s 3 条，超出静默丢弃） |
| `ds.device()` / `ds.site()` / `ds.config()` / `ds.history()` / `ds.viewport()` | Promise | 信息域：设备 / 当前源身份 / 壳子配置 / 观看历史（fm.history 同源，字段见 §四）/ 视口 |
| `ds.on(name, cb)` / `ds.off` | 返回取消函数 | 事件订阅（事件表见 §七） |
| `ds.profiles.list/add/apply/remove/refresh` | Promise | **接口配置（profile）管理**——页面管理壳子订阅配置的唯一通道：`add(url, name?)` 添加订阅、`apply(id)` 应用即刷新、`refresh(id?)` 重拉。配置助手类页面（样例 `配置助手.html`）即以此构建 |

### 2.1 ds.req 参数表与网络口径（写请求前必读）

| opt | 类型 | 说明 |
|---|---|---|
| `method` | string | GET/POST/PUT/DELETE…，缺省 GET |
| `headers` | object | 自定义请求头；**`User-Agent` 合法且生效，会覆盖 dart:io 默认 UA**；头名大小写不敏感 |
| `body` | string | 原始 body 直传（不序列化）；与 `data` 同现时 `body` 优先 |
| `data` | object | GET 时拼 query；非 GET 按 `postType` 序列化 |
| `postType` | string | `json`（缺省）/ `form` / `form-data` |
| `responseType` | string | `text`（缺省）/ `json` / `base64`（取二进制内容的唯一方式） |
| `credentials` | string | `'include'` = 注入该 URL 域在 WebView 里的会话 Cookie；显式 `Cookie` 头优先 |
| `redirect` | number | 0 = 不跟随重定向（缺省跟随，最多 5 跳） |
| `timeout` | number | 秒，缺省 20，**60s 硬顶** |

返回 `{ok,status,headers,url,cookies,body,error?}`：`ok` 语义同 fetch（`status < 400`）；`cookies` 是该响应的 `set-cookie` 数组（`headers` 里同时保留合并形态）；`body` 按 `responseType` 解码。

**网络栈口径**（决定「为什么浏览器能开、壳子里 403」）：

- `ds.req` 由**壳子原生 HTTP 栈**发出（dart:io `HttpClient`，不是 WebView、不是系统 Dio）——没有 CORS 限制，但**也不带 WebView 的 TLS 指纹/Cookie**（Cookie 见 `credentials`）。
- **UA 确实生效**：页面 `headers` 里传什么就发什么，会替换 dart:io 默认的 `Dart/x (dart:io)`。
- **非法头值会被静默丢弃**：头名/头值含换行、控制字符时该头不会发出且不报错——「传了头但服务端没收到」先怀疑这个，用 `fm.ext.log` 打实际值核对。
- **系统 HTTP 代理不会自动生效**：`ds.req` 缺省 `DIRECT`，不读 Android Wi-Fi 代理，也不读 `http_proxy` 环境变量。
- **全局 VPN（TUN 模式）是透明的**：VPN 在系统路由层接管，`ds.req` / WebView / 播放器内核都会自动走，无需任何代码。「Clash 只开 7890 代理端口」不算全局 VPN，那种情况 `ds.req` 不会走代理。
- **页面里的 `<img>/<video>` 不经过 `ds.req`**：它们由 WebView 直接加载，UA/Referer/代理设置与 `ds.req` 无关；防盗链图片用 `ds.res()` 或自己拼代理 URL。

#### 403 / 反爬：UA 不是万能钥匙（2026-11-17 实锤）

站点对「非浏览器 TLS 指纹」做机器人判定时（典型是 Cloudflare：403 且 body 含 `Just a moment` / `challenge-platform`），**改 UA、补 `sec-ch-ua`/`sec-fetch-*` 都救不了**——判定在 TLS/客户端特征层，不在请求头。别继续堆头，按下面选路：

1. 先看**响应体**（`r.body`）区分是 CF 挑战页还是站点自己的 403 文案；只看 status 会误判。
2. 站点有可用 CORS 代理/反代（页面里已有 `DEF_PROXY` 之类）→ **所有形态都走它**，不要按客户端形态分支。
3. 没有代理可用 → 让用户开**全局 VPN（TUN）**或换出口节点；壳子侧没有「自动换 TLS 指纹」的能力。

**最常见的走弯路写法**（本次实锤）：

```js
// ❌ 浏览器里走代理、进了壳子反而直连 —— 壳子里必 403
function proxied(u){ if (isNative() || !DEF_PROXY) return u; return DEF_PROXY + u; }

// ✅ 网络通路与客户端形态无关：所有形态一视同仁
function proxied(u){
  if (!USE_PROXY || !DEF_PROXY) return u;
  return String(u).indexOf(DEF_PROXY) === 0 ? u : DEF_PROXY + u;
}
```

`isNative()`（`window.fm.req` 是否存在）只能判断「有没有 fm 桥能力」（比如要不要用 `fm.vodInline`），**不能用来判断网络能不能直连**——原生栈只是没有 CORS 限制，TLS 指纹/出口 IP 该被拦还是被拦。代理类源必须在壳子里真机验证一次，不能只测浏览器。

## 三、fm 兼容 API（`window.fm`，webhtv/fongmi 对标）

与 `ds` 同注册表，多数量值兼容 webhtv 契约——**已有 webhtv/fongmi 页面零改动可跑**（标杆验证：bilibili.html）。

| API | 对应 ds | 差异点 |
|---|---|---|
| `fm.req(url, opt)` | `ds.req` | 直转 |
| `fm.cache.get/set/del(k, v?, ns?)` + `remove`（别名） | `ds.store` | del/remove 双名 |
| `fm.res(u, opt)` | `ds.res` | 走 `/webResource` 路径（fm 生态用 `indexOf('/webResource')` 探测网关基址——形态不能变） |
| `fm.play(uri, title, opt?)` | `ds.play` | 参数拍平形态；opt：`{pic, wallPic(忽略), headers, format}` |
| `fm.vodInline(spec)` | `ds.openVod` | spec 直推（vod_play_url/episodes） |
| `fm.vod(siteKey, vodId, title?, pic?, opt?)` | — | **原生详情链路**：壳子现拉该站点详情页（与 fm.history 的增益字段 siteKey/vodId 配合可复原回放） |
| `fm.search(kw, {direct?})` | `ds.search` | direct=true 直搜不过预填 |
| `fm.openVod() / openLive() / openKeep() / openSetting()` | `ds.tab` 族 | 打开壳子对应页面 |
| `fm.back() / reload()` | `ds.back` / — | reload 重载当前源页 |
| `fm.history() / device() / site() / config()` | `ds.*` | 同源（信息域函数式，禁挂子方法——webhtv 红线） |
| `fm.stat()` | — | 播放会话快照：`{state, speed, duration, position, url, title, artist, artwork}`（state：1 无会话 / 2 paused / 3 playing / 6 buffering；时长/位置单位秒） |
| `fm.ctrl(action)` | — | 播放控制：`play/pause/stop/prev/next/loop/replay`（未知动作明错） |
| `fm.preloadArtwork(pic)` | — | 封面预取（LRU 缓存 64 文件/50MB，无回调保证） |
| `fm.pan.check(items)` / `fm.pan.play(spec)` | — | 网盘降级：http 直链→转 fm.play；`magnet:`/`ed2k:`→拉起 IDM+；quark/uc/aliyun 等网盘类型→unsupported 明错 + toast（无网盘驱动） |
| `fm.check(spec)` | `fm.pan.play` 别名 | |
| `fm.ui.setChrome/restoreChrome/setToolbar` | — | no-op（接受并 resolve，防页面 catch 刷错误）；`fm.ui.getViewport()` 真实 |
| `fm.ext.info() / log(msg, data?) / toast(msg)` | — | 扩展域：环境信息 / 落壳子日志 / toast |
| `fm.magnetReady` | 属性（bool） | **磁力插件能力位**：装了磁力插件才 true，随 `dsmagnet` 事件动态更新——磁力集推壳子还是降级剪贴板由此判（独狼样例 §4.8） |
| `fm.on/off(n, cb)` | `ds.on/off` | fm* 事件名走同一注册表 |

## 四、fm.history 返回字段（观看历史）

`[{key, vodPic, vodName, vodRemarks, vodFlag, createTime, opening, ending, position, duration, episodeUrl, revSort, revPlay, speed, scale, cid, siteKey, episodeIndex, lineIndex}]`——60 天窗口、time 降序、500 条截断；`siteKey/episodeIndex/lineIndex` 是 DsPlayer 增益字段，配合 `fm.vod(siteKey, vodId)` 可一键复原回放。`opening/ending` 为片头/片尾跳过秒数。

## 五、播放链（最重要的一个 API）

`ds.play(spec)` / `fm.play` / `fm.vodInline` / `ds.openVod` 底层同一条「spec → 壳子详情页」链，spec 四形态**按优先级**：

```js
// ① 多线路（推荐：CMS 类黑白双源一键全量推送）
ds.play({
  vod_name: '片名', vod_pic: '封面', type_name: '分类',
  vod_remarks: '更新至12集',
  lines: [
    { name: '线路一', episodes: [{ name: '第1集', url: 'https://…/1.m3u8' }] },
    { name: '线路二', episodes: [{ name: '第1集', url: 'https://…/1.mp4' }] },
  ],
});

// ② 单线路多集
ds.play({ vod_name: '片名', episodes: [{ name: '第1集', url: '…' }] });

// ③ 单集直链（fm.play 的规范形态）
ds.play({ url: 'https://…/1.mp4', title: '第1集', pic: '封面?' });

// ④ CMS 原生串（懂 vod_play_url 格式的页面用）
ds.play({ vod_name: '片名', vod_play_from: '线路名', vod_play_url: '第1集$https://…#第2集$https://…' });
```

- `headers`（如 `{Referer:'…', 'User-Agent':'…'}`）传 spec 顶层或 opt：带 headers 的 http 直链在详情页会被**自动包 /webResource 代理**（防盗链直链可直接播）。
- ⚠️ **相对分片 m3u8 与 headers 互斥**：传了 `headers` 的直链会被包成 `/webResource?url=…`，播放器看到的 playlist 地址是 `http://127.0.0.1:<port>/webResource?...`。如果该 m3u8 用**相对路径分片**（如 `video0.jpeg`、`seg-1.ts`），相对解析会落到 `127.0.0.1` 而不是源站，整集分片全 404。规则：
  - 直链需要 headers（防盗链）→ 传 headers 让壳子包代理；此时 m3u8 里**所有分片/子清单都必须是绝对地址**（HLS 相对 URI 以包含它的 playlist 地址为基址，被包一层后基址就变成了 127.0.0.1）。
  - 自己已经套了反代/代理（URL 形如 `https://你的代理/https://源站/…`）→ **不要再传 headers**，否则壳子会二次包装，相对分片必挂。
- 分片后缀不可信：遇到过 `.jpeg` 实际是 MPEG-TS（首字节 `0x47`）的反爬伪装——Exo/MPV 按内容嗅探能正常播，别按后缀自行判「不是视频」。
- `resolve: true` 的 episode 是「哨兵集」——url 先占位，进详情页时页面经 webresolve 回查换真实地址（异步解析源用，样例见独狼影视聚合）。
- 推送有 1s 窗节流（防路由轰炸）：同签名 1 秒内重复推送静默丢弃。

## 六、ds.env 字段表

| 字段 | 类型 | 说明 |
|---|---|---|
| `version / platform / isTv / isDesktop / fullscreen` | str/bool | 壳子版本 / `android`\|`windows` / TV 形态 / 桌面 / 当前全屏态 |
| `theme` | `{mode, primary, isDark}` | 跟随壳子主题；dstheme 事件增量更新 |
| `safeInsets` / `viewport` / `keyboardBottom` | px 值 | 安全区/视口/键盘高度（dsviewport 事件增量更新） |
| `source` | `{key, name, scope}` | 当前源身份 |
| `gwPort / gwTok` | int/str | 本地网关端口与令牌（拼代理 URL 已由 ds.res/fm.res 代劳，一般不用直接碰） |
| `magnet` | bool | 磁力插件就绪（= fm.magnetReady） |
| `fontScale` | double | 系统字体缩放 |

## 七、事件表（`ds.on` / `fm.on` / DOM addEventListener 三通道同发）

| 事件 | 时机 | payload |
|---|---|---|
| `dsready` / `fmsdk` | 桥就绪（同步 + DOMContentLoaded 双发） | — |
| `dstheme` | 壳子切主题 | `{theme}` |
| `dsviewport` / `fmviewport` | 视口/安全区变化（含 resize） | `{safeInsets?, viewport?, keyboardBottom?}` |
| `dsforeground` / `fmresume` | 回前台 | `{time, pausedMs?}`（fmresume 带后台停留时长） |
| `dsbackground` / `fmpause` | 退后台 | `{time}` |
| `dsfullscreen` | 进/出全屏 | `{value}` |
| `dsmagnet` | 磁力插件装/卸 | `{ready}` |
| `fmurlchange` | SPA 路由变化（pushState/replaceState/popstate/hashchange 全 hook） | `{url}` |
| `dsback`（仅 DOM） | 用户按返回键 | cancelable——`e.preventDefault()` = 页面自消化（弹层先关一层） |

## 八、CSS 变量（documentElement 上常驻）

安全区：`--ds-safe-{top,bottom,left,right}`（`--fm-safe-*` 同值）；主题：`--ds-theme-primary`、`--ds-dark`（'1'/'0'）、`--ds-font-scale`；fm 全量：`--fm-chrome-mode`（恒 edge）、`--fm-status-bar-height`、`--fm-web-height`、`--fm-web-width`（resize 自动更新）、`--fm-navigation-bar-height`、`--fm-keyboard-bottom`、`--fm-system-bars-hidden`。

```css
.nav { padding-top: var(--fm-status-bar-height, 0px); }
body[data-dark] { /* ds.dark 时手动切 */ }
```

## 九、限制与守卫（行为边界，写页面前知道少踩坑）

- `ds.req` 业务失败不 reject（见 §二）；**没有** fetch/DOM parser 之外的浏览器外能力，页面自己带解析逻辑。
- `ds.req` 走原生 HTTP 栈（不是 WebView/fetch）：没有 CORS，但也没有 WebView 的 Cookie/TLS 指纹；`credentials:'include'` 才带该域 Cookie（见 §2.1）。
- 系统 HTTP 代理不生效（`ds.req` 缺省 DIRECT）；**全局 VPN（TUN）透明生效**——「Clash 只开代理端口」不等于全局 VPN。
- 页面里的 `<img>/<video>` 由 WebView 直接加载，`ds.req` 的 headers/代理与它们无关；防盗链资源用 `ds.res()` 或代理 URL。
- 头值含换行/控制字符会被静默丢弃（不报错），排查见 §2.1。
- toast 速率闸 1s 3 条；路由类动作（openVod/play/search/tab）1s 同签名节流。
- 网盘域是降级实现：只有 http 直链与磁力（拉 IDM+）真实可用，quark/uc/aliyun 等类型明错。
- 首屏 350/900ms 非用户交互的自动聚焦会被强制 blur（防站方自动弹 IME 顶起导航）——搜索框聚焦请放在用户事件回调里。
- Cookie 与主窗互通；「新窗口打开」的多开窗口里桥能力全量可用（经 webwin 通道转发主引擎，见 WEB-WINDOW-DESIGN.md）。

## 十、样例索引（plugins/demo-sources/spider/html/，装 demo-sources 源码包即得）

| 文件 | 学什么 |
|---|---|
| `bilibili.html` | **标杆**：webhtv 生态页面零改动可跑的实证（fm.req/cache/play 全用） |
| `Web源演示.html` | 入门演示（卡片墙 + 各 API 用法） |
| `fm-selftest.html` | **fm API 自验页**（28 断言全 PASS = 桥健康；开发时先跑它） |
| `配置助手.html` | `ds.profiles` 五方法管理接口订阅的完整应用 |
| `独狼影视聚合.html` | 便携 WebHome 聚合：多站聚合 + 磁力能力位降级（magnetReady）+ 哨兵 resolve |
| `gm-probe.web.json` + `gm-probe.js` | 源清单 + 引擎探针（web 源的 json 配对形态） |
| `wbbb1.web.json` + `wbbb1.js` | 同上（歪比巴卜 booster） |

## 十一、开发与调试

1. 本地起页：HTML 放 `sdcard/dsplayer/spider/html/`（或打源码包），接口配置站点 api 填 `file:///sdcard/dsplayer/spider/html/你的页.html`（源码包形态见 plugin-build.md §一.4）。
2. 自验：先开 `fm-selftest.html` 全 PASS 再调自己的页面。
3. 看日志：`adb logcat -s flutter` 过滤 `[WEB]`（桥错误带 `ds.<ns>.<method> error:`）。
4. 页面内调试：`fm.ext.log('tag', data)` 落壳子日志；`fm.ext.toast()` 快速打点。
5. 真机自动化回归：UiActions id（`web.url.edit` / `web.reload` / `web.fullscreen` 等，`action list` 可见）。

## 十二、常见故障排查（按现象）

| 现象 | 先查 |
|---|---|
| 列表空 + `HTTP 403`，UA 已设置 | 站点机器人判定（典型 Cloudflare）：看 `r.body` 是否 `Just a moment`；不要继续堆 UA/头；需要代理就让所有形态都走代理（§2.1） |
| 浏览器能开、壳子里 403 | `proxied()` 是否按 `isNative()` 分支（§2.1）；native 路径是否真机验证过 |
| 接口正常但图片裂图/403 | 图片是 WebView `<img>` 直连，不经 `ds.req`；改用 `ds.res()` 或代理 URL（§2.1、§九） |
| 播放分片请求打到 `127.0.0.1` | 相对分片 m3u8 + spec `headers` 二次包装（§五） |
| 播放器报格式不支持，但地址是 `.jpeg` | 可能是伪装的 MPEG-TS 分片；让内核嗅探，别按后缀判死（§五） |
| `ds.req` 的头「传了没生效」 | 头值含换行/控制字符被静默丢弃，或头名带空格（§2.1） |
| `req` 返回 4xx 但页面没进错误分支 | `ds.req` 业务失败不 reject，必须自判 `r.ok`（§二） |
| 开了代理/VPN 仍 403 | 代理是「规则/分流」而非全局；分应用代理排除了壳子；出口节点本身被拦（§2.1） |
