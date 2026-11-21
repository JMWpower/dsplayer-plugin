# DsPlayer 插件制作通用指导（AI 提示词模板）

> 状态：已实施 ｜ 最后更新：2026-11-16 ｜ 关联代码：lib/services/plugin_center/plugin_center.dart、lib/services/binary_plugin/、lib/services/plugin_market/、lib/services/jar_plugin/、plugins/README.md ｜ 本仓 ext/plugin_* 现有 9 个原生工程（mpv / qjs / python / ffmpeg / ijk / bytevc2 / agent / jar / bundle）+ 市场侧运行时包（nodejs / php / python-win / qjs-win / mpv-win / jar / magnet）

## 用法

本文是给 AI 的**通用提示词模板**：拿到任意新的开源项目，先判断形态，再按 DsPlayer 插件规范完成编译、打包和验证。使用时把「项目地址」替换为目标仓库即可。

文中全部 schema（plugin.json / server.json / source.json / live JSON / 市场条目 / action 协议）均已与 DsPlayer 当前代码逐项核对（基线 2026-11-16，核对文件见 §二）。若后续机制演进，**以 §二列出的代码与仓库为准修订本文**，不要凭旧记忆或其它 drpy 生态项目的习惯猜测。

---

你是一名熟悉 Android 交叉编译、Go/Node.js/Python/PHP 与 DsPlayer（智能规则聚合壳子）的高级开发者。

我有一个新的开源项目，希望把它制作成 DsPlayer 可安装或可导入的插件。

项目地址：
[在这里填写 GitHub 项目地址]

请先读取项目源码、README、构建脚本、许可证和 Releases，确认项目的运行方式，再决定应该使用哪一种 DsPlayer 插件形态。不要直接假设形态。

## 一、八种插件形态与判定特征

DsPlayer 消费侧（导入路由 `lib/services/plugin_center/plugin_center.dart` 的 `inspectImport`）按**包内特征**自动判定形态，优先级从高到低（整合包 > binary > server > source > jar > apkOnly > agentUI > so）。制作时必须让包的特征与目标形态严格一致：

| 形态 | 包形态 | 系统判定特征 | 典型用途 | 市场实例 |
|---|---|---|---|---|
| binary | zip | 包内 plugin.json `runtime:"binary"` | Go/C 编译的独立服务 | mediaProxy |
| binary-runtime | zip | 包内 plugin.json `runtime:"binary-runtime"` | nodejs/php/python 运行时 | nodejs、php、python |
| server | zip | zip 根部精确名 `server.json` | Node.js Web 服务 | danmu-api、lx-sync |
| source | zip | zip 根部 `source.json`，或顶层目录全属 `dr2/dr3/hipy/js/catLib` | 影视/音乐源文件 | demo-sources、catlib |
| live | **裸 JSON 文件**（非 zip） | 顶层 `lives` 是数组 | IPTV 电视源 | iptv-ccsh |
| apk | APK | 系统安装器直装；导入通道按 `installMode` 拒绝或分流 | 播放内核/引擎插件 | mpv、qjs、ijk、py |
| jar | zip | plugin.json `kind:"jar-spider"`，或包根有 `classes*.dex` **且非 APK**（无 AndroidManifest.xml，2026-11-16 起兜底排除 APK 载体） | TVBox JAR 爬虫引擎（DexClassLoader） | jar |
| so | zip | plugin.json `runtime:"native-lib"`（PC dll）或 `lib/<abi>/*.so`（Android） | so 载体插件/内核 | magnet、qjs-win、mpv-win |

另有 bundle（整合包安装器壳）只由本仓 `ext/plugin_bundle/` 构建，第三方不做。

**新插件一律用 §一.10 的 format:2 双字段清单**（载体+制品+能力位模型，docs/plugin/PLUGIN-MODEL-V2.md）：旧字段全保留（旧宿主照常安装）、v2 块声明能力与落盘位置——jar 1.2.0 / magnet 1.0.2 是现成实例。只写旧字段也完全可用（legacy 适配器永久兼容），v2 是给新宿主的显式声明。

### 1. binary：独立二进制服务插件

适用于 Go、Rust、C/C++ 编译出的单文件服务（第一个实例是 Go 的 mediaProxy）。

zip 结构：

```
plugin-name.zip
├── plugin.json
└── bin/
    └── plugin-android
```

plugin.json 字段全集（解析在 `lib/services/binary_plugin/binary_plugin_model.dart`，除 `name` 外均可选）：

```json
{
  "runtime": "binary",
  "name": "plugin-name",
  "title": "插件显示名称",
  "version": "1.0.0",
  "desc": "插件功能说明",
  "author": "作者",
  "installMode": "import",
  "params": "-port 5575",
  "env": { "KEY": "value" },
  "binaries": { "android": "bin/plugin-android" },
  "portField": "-port",
  "healthCheck": { "type": "http", "path": "/", "port": 5575, "timeoutMs": 3000 }
}
```

字段语义与硬约束：

- `runtime` 只有 `binary`（单服务）与 `binary-runtime`（运行时包）两个合法值，其他值整包解析失败。
- `name` **必填**，是落盘目录名（`files/plugins/<name>/`），必须合法路径段。
- `binaries` 的 key 是平台键（`android`/`win32`/`linux`）；value 是二进制相对路径，**先按 `bin/<value>` 查找、找不到再按包根裸名兜底**（兼容 drpy-node 的裸布局），容忍 `assets/` 前缀。落盘后恒为 `plugins/<name>/bin/<value>`。
- 二进制必须是真 ELF（魔数 `7F 45 4C 46`）或 PE（`MZ`），否则整包拒绝；包内任何条目路径含 `..` 拒绝。
- `params`/`env` 是包默认值，用户可在服务配置里改；启动时自动注入环境变量 `DS_PLUGIN_DIR`（指向插件落盘目录）。
- `portField`（如 `"-port"`）表示「从实际启动参数里解析该开关后面的数字作为端口」，**优先于** `healthCheck.port`。端口不自动分配，必须由参数显式给出。
- `healthCheck.type` 只支持 `http` / `tcp`；不声明 healthCheck 时「进程存活」即视为健康。

### 2. binary-runtime：运行时插件

适用于 Node.js / PHP / Python 等供服务包调用的解释器。它本身不启动业务服务，只提供运行环境，被服务以 `__plugin:<name>__` 占位符引用（见 §七）。

```json
{
  "runtime": "binary-runtime",
  "name": "nodejs",
  "title": "Node.js",
  "version": "1.0.0",
  "desc": "Node.js Android ARM64 运行时",
  "binaries": { "android": "node24-arm64" }
}
```

- 运行时包**整包解压**到 `files/plugins/<name>/`，覆盖安装时清旧产物但保留用户 `config.json`。
- Python 运行时包额外支持 `pyRuntime` 块（`pythonBin`/`shimFile`/`siteDir`/`examples`/`env`），供本体的「依赖管理」消费——实例见 `plugins/python-runtime/build_zip.py` 产出的包（musl CPython + `ld-musl-aarch64.so.1` 加载器 + sitecustomize DNS/CA shim）。
- PHP 运行时需同时提供 `bin/php` 与动态库目录 `libs/`（drpys 服务以 `PHP_PATH`/`LD_LIBRARY_PATH` 引用）。

### 3. server：进程服务包（Node.js / PHP 双运行时）

适用于需要由 DsPlayer 拉起进程的 Web 服务。安装后自动创建服务配置，
**`runtime` 字段分叉**（2026-10-16 EPG 服务批次新增 php 支持）：

| runtime | 可执行（自动拼 `__plugin:<名>__/bin/…`） | params 形态 | 解压落点 | 前置运行时插件 |
|---|---|---|---|---|
| 缺省 / `node` | `node24-arm64`（win32: `node.exe`；可用 manifest `executable` 覆盖） | `__sdcard__dsplayer/server/node/<workDir>/<entry>`（node 直跑入口文件） | `<sdcard>/dsplayer/server/node/` | `nodejs` |
| `php` | `php` | `-S 0.0.0.0:<port> <entry>`（php 内置服务器；entry=router.php，相对 workDir） | `<sdcard>/dsplayer/server/php/` | `php` |

- **php 形态必填 `port`**（`-S` 绑定端口即服务面），自动配 tcp 探活。
- manifest 新增可选 **`autoStart`**（布尔，缺省 false）：true 时服务配置建为
  自启（低频后端类如 EPG 服务适合——装完即可用）。
- 两种 runtime 的 `workDir` 都指向 **zip 内顶层目录**（解压端平铺落
  server/{node|php}，服务以 `server/{node|php}/<workDir>` 为 CWD）。
  zip 内必须含 workDir 顶层目录——PHP 文件直接平铺到 zip 根会落到
  `server/php/` 根、workDir 解析失败。

zip 结构（manifest 必须在**根部**、精确名 `server.json`，缺失整包拒绝）：

```
service-plugin.zip
├── server.json
└── danmu-api/
    ├── server.js
    ├── package.json
    └── node_modules/...
```

server.json 字段（解析在 `lib/services/plugin_market/market_manager.dart`；除 `workDir` 外均可选）：

```json
{
  "workDir": "danmu-api",
  "entry": "danmu_api/server.js",
  "port": 9321,
  "serviceName": "弹幕 API 服务",
  "version": "1.0.0",
  "desc": "弹弹play 协议弹幕服务"
}
```

- 解析端只消费 `workDir`（**必填**）/`entry`（缺省 `index.js`；php 形态建议 `router.php`）/`port`/`serviceName`（缺省用市场条目名）/`desc`/`version`/`runtime`（缺省 node）/`executable`（node 形态可覆盖二进制名；php 形态由 runtime 决定不得覆盖）/`autoStart`（可选布尔）。生态里常见的 `serviceId`、`healthType` 字段**不被解析**（健康检查固定 tcp；服务 id 自动生成），带上无害但别指望生效。
- `port > 0` 时自动配 tcp 探活；不声明或为 0 时只做进程存活检测（**php 形态必填 port**）。**端口不会自动分配**，程序内必须监听该固定端口。
- 全量解压到 `sdcard/dsplayer/server/{node|php}/`（按 runtime；覆盖式更新），`server.json` 本身不落盘。
- 服务默认不自启、不保活（`keepAlive` 恒 false；`autoStart` 可经 manifest 声明，缺省 false），用户也可在服务页手动开。

### 4. source：源码包

适用于 drpy 生态源文件（js/py）与引擎库。manifest `source.json` 在 zip 根部、**可选**，只有两个字段：

```json
{ "target": "dsplayer" }
```

或限制解压范围：

```json
{ "dirs": ["dr2", "js"] }
```

- `target` 缺省 `"spider"`：整包解压到 `sdcard/dsplayer/spider/`。设为 `"dsplayer"` 时落盘根上提一级到 `sdcard/dsplayer/`——**包内路径即 dsplayer 目录树**（`spider/dr3/…` 落源扫描位、`server/…` 落服务目录，可共存）。注意 target=dsplayer 需要较新版本本体，旧版 app 会把 spider/ 平铺成 spider/spider/ 导致扫不到。
- 顶层目录约定（与本地源扫描位一一对应）：`dr2/`（drpy2 规则源）、`dr3/`（drpy3 源）、`hipy/`（py 源）、`js/`（QJS 引擎 js 源）、`catLib/`（cat 生态引擎库，落 `sdcard/dsplayer/catLib/`，不进扫描树）。
- `_lib.` 前缀的文件视为依赖库，不成源。

### 5. live：电视源包

**裸 JSON 文件，不是 zip**（导入选择器选 `.json` 即走此通道）：

```json
{
  "lives": [
    { "name": "频道名称", "url": "播放地址", "ua": "请求UA", "epg": "节目单地址" }
  ]
}
```

- `url` 必填（空条目跳过）；该通道只认 JSON，不支持 m3u/txt 文本。
- 安装动作 = 写入电视配置 `liveProfiles`（按市场 id 整包替换）并把首个地址设为启用。

### 6. apk：APK 插件

适用于必须走 Android 系统安装器的插件：桥接式播放内核（IJK，dex 是载体，zip 导入会丢桥类）、Python 引擎（Chaquopy）等。APK **不能**改名塞进 binary 包的 bin 目录冒充二进制。

APK 内 `assets/plugin.json` 的真实字段（原生 `PluginMetaReader` **只认 `pluginVersion`，没有 `version` 回退**）：

```json
{
  "name": "qjs",
  "pluginVersion": "1.0.5",
  "component": "quickjs",
  "componentVersion": "19.0.0",
  "kind": "qjs-engine",
  "installMode": "import"
}
```

- `installMode: "apk"` = 仅允许系统安装器直装，应用内导入通道直接拒绝（IJK、python 引擎即此形态）；缺省 `"import"` = zip/APK 均可应用内导入落盘。
- `pluginVersion` 与 gradle `versionName` 必须**双处同步**——本仓 `ext/build-conventions` 的 `checkPluginVersion` task 在两处不一致时直接构建失败。
- APK 插件工程结构、`ext/build-conventions` 注入项（签名/useLegacyPackaging/abiFilters 基线 arm64-v8a）、桥接内核的 R8 keep 约定等，见 `docs/plugin/PLUGIN-DESIGN.md` 与 `docs/player/BRIDGE-KERNEL-DESIGN.md`——第三方自建 APK 插件前先读。

### 7. jar：JAR 爬虫引擎（dex 载体 zip，应用内直装）

适用于 TVBox 生态的 jar 爬虫引擎（`csp_` 源）。**不是 APK**：zip 内是 dex 载体，宿主在应用进程内用 `DexClassLoader` 加载，安装不跳系统安装器。

zip 结构（实例 `packages/jar-1.2.0.zip`）：

```
jar.zip
├── assets/plugin.json
├── classes.dex                     # 可多段 classes.dex / classes2.dex…（按数字序全量加载，classes.dex 必须第一）
└── lib/<abi>/<engine>.so           # 可选（源内 JS 引擎等）；安装按宿主 ABI 落 plugins/<name>/libs/
```

`assets/plugin.json`（1.2.0 起双字段，v2 块见 §一.10）：

```json
{
  "format": 2,
  "name": "DsPlayer JAR 爬虫引擎",
  "pluginVersion": "1.2.0",
  "kind": "jar-spider",
  "component": "jar",
  "componentVersion": "1.2.0",
  "installMode": "import",
  "abis": [],
  "artifacts": {
    "dex": {
      "modules": ["classes.dex"],
      "libs": { "android": ["lib/<abi>/libquickjs-android-wrapper.so"] }
    }
  },
  "provides": [{ "kind": "dex-spider", "id": "jar" }],
  "platforms": ["android"]
}
```

- 识别链：`kind:"jar-spider"`，或包根存在 `classes*.dex` **且包内无 `AndroidManifest.xml`**（APK 载体不进此通道，2026-11-16 修复——APK 走 §一.6/§一.8 的语义路由）→ `PluginImportKind.jarPack`（**先于 apkOnly/soPack 判定**）。
- 落盘：`<appSupport>/plugins/<name>/`（Android 与 PC 同根）；安装做「清旧 dex → 写新 dex → plugin.json → 释放桥」，升级不残留旧段。
- 运行面：宿主 MethodChannel `com.dsplayer/jar_spider` → 插件 `JarSpiderBridge` → `DexClassLoader`；`Spider`/`SpiderDebug` 接口面必须在**宿主 dex**（加固 jar payload loader 以 Application CL 为 parent），插件 dex 携带 okhttp/okio/gson 等 P1 依赖。
- `abis: []` = 全 ABI 不限制；包内 so 按宿主 ABI 安装，缺对应 ABI 不影响纯 dex 源。
- 开关：`Pref.jarPluginEnabled`（默认 true，插件中心卡片可关；关闭后 `JarSpiderRuntime` 直接拒绝，源检测标灰）。
- 卸载：删插件目录并释放桥/Spider 实例；已下载的用户 jar 缓存（`jar_cache/`）保留。

### 8. so：so 载体插件（Android so / PC dll）

适用于「一坨 native 库 + 宿主按路径加载」的插件，没有服务进程：

- Android so（例 `magnet`，1.0.2 起双字段）：`plugin.json` 在包根，`kind:"so"` + `abis` + `lib/<abi>/<libname>.so`：

```json
{
  "format": 2,
  "name": "magnet",
  "pluginVersion": "1.0.2",
  "kind": "so",
  "component": "anacrolix-torrent",
  "componentVersion": "1.53.3",
  "abis": ["arm64-v8a", "armeabi-v7a"],
  "artifacts": {
    "native": {
      "libs": {
        "android": {
          "arm64-v8a": "lib/<abi>/libmagnet.so",
          "armeabi-v7a": "lib/<abi>/libmagnet.so"
        }
      }
    }
  },
  "provides": [{ "kind": "native-lib", "id": "magnet" }],
  "platforms": ["android"]
}
```

- PC dll（例 `qjs-win` / `mpv-win`）：`runtime:"native-lib"` + `binaries: {"win32": "bin/xxx.dll"}`，宿主 FFI/dlopen 按路径加载，不建服务卡、不参与服务运行时选择。
- 识别：未命中前面形态时归 `soPack`；含 `.dll` 的包允许桌面导入（`windowsDll`），纯 Android so 包在 PC 提示「仅移动端」。
- 卸载：删插件目录；**已 dlopen 的 so 无法运行时卸载**——升级/卸载后需重启应用生效，卡片应给提示。
- 开关：可选（例 `Pref.magnetEnabled`）；关闭后能力位（如 `MagnetPluginManager.availableSync`）为 false，调用方回落。

### 9. 插件卡规范（所有可安装插件强制）

插件中心卡片是唯一管理面，新插件必须同时满足：

1. **卸载入口**：已安装态必须渲染「卸载」（`PluginCard.uninstall`）。files/so/jar 形态 = 应用内删插件目录；APK 形态 = 跳系统卸载页；确实不可卸（内置固化/无文件语义）时不渲染假按钮，且卡片文案要说明。
2. **开关必须真实**：有启停语义的插件必须 `enabled` 绑定持久化 Pref 键、`onToggle` 非空、并在执行链**真实门控**——只画一个 `onToggle:null` 的禁用 Switch 属规范违规（2026-11-16 JAR 插件实锤）。键范例：`jarPluginEnabled` / `magnetEnabled` / `pyPluginEnabled` / `qjsPluginEnabled`。
3. **卸载顺序**：先释放运行时（桥/进程/任务/句柄），再删目录；保留用户产物（jar 下载缓存、磁力已下载媒体、用户配置）。
4. **登记齐全**：新插件须同时登记 `PluginDescriptors.all`（探测/身份）、`PluginSpecs`（`lib/services/plugin_center/plugin_spec.dart`——卸载/开关/UiActions id 契约，`test/arch3/plugin_spec_contract_test.dart` 强制校验，漏配直接红灯）、`PluginCardsController`（卡片新动作）、UiActions 语义 id（`plugins.<id>.uninstall` / `plugins.<id>.toggle`，自动化禁坐标铁律）；`test/plugin_descriptor_coverage_test.dart` 会强制 marketId/市场条目对齐。
5. **文案诚实**：未安装/已停用/平台不支持三种状态要在 `statusLine` 区分，不要让用户把「开关关着」误认为「插件坏了」。

### 10. format:2 双字段清单（v2，新插件推荐）

机制收敛后的统一清单模型（docs/plugin/PLUGIN-MODEL-V2.md）：**包 = 载体 + 制品 + 能力位**。新包在旧字段**原样保留**的基础上追加 `format: 2` 块——旧宿主按旧字段安装（布局不变），新宿主优先读 v2 声明。

```json
{
  "format": 2,
  "...旧字段全保留（kind/pluginVersion/abis/installMode 等）": "",
  "artifacts": {
    "process": { "bin": {"android": "bin/node24"}, "health": {"type": "http", "path": "/", "port": 5575} },
    "native":  { "libs": {"android": {"arm64-v8a": "lib/<abi>/libmagnet.so"}} },
    "dex":     { "modules": ["classes.dex"], "libs": {"android": ["lib/<abi>/libw.so"]} },
    "content": { "kind": "source" },
    "web":     { "root": "www/" }
  },
  "provides": [{ "kind": "dex-spider", "id": "jar" }],
  "platforms": ["android"]
}
```

- `artifacts` 按需声明（一个包可含多种制品）：`process`（binary 形态）/ `native`（so/dll）/ `dex`（jar）/ `content`（source/server/live）/ `web`（agent-ui）。
- `native.libs` 两级形态：Map 形态显式 ABI → 路径；**数组形态**是共享模板（`"android": ["lib/<abi>/x.so"]`，多 ABI 同布局时用）。路径中 `<abi>` 占位**由安装器按宿主 ABI 展开**，解析层保真不展开。
- `provides[].kind` 词表：`process-service` / `process-runtime` / `native-lib`（带 id，如 `"id": "magnet"`）/ `dex-spider` / `source-pack` / `server-pack` / `live-pack` / `web-assets`——声明宿主应挂哪个消费适配器；未知 kind 向后兼容忽略。
- `platforms`：`android` / `win32`（预留 `linux`）。
- **双字段原则**：只加不改、旧字段原义不动；`format` 字段缺省 = 纯 legacy（永久兼容，不是过渡态）。
- 现成实例：jar 1.2.0（dex 制品）、magnet 1.0.2（native 制品）——市场包 `packages/jar-1.2.0.zip` / `packages/magnet-1.0.2.zip`，出包源 `ext/plugin_jar/app/src/main/assets/plugin.json` / `plugins/magnet/plugin.json`。

## 二、动手前先读的权威依据

不要只根据本模板动手，涉及 schema 细节时查以下位置（本仓 = DsPlayer 源码仓）：

- **官方插件市场**（唯一分发渠道）：GitHub `hjdhnx/dsplayer-plugin`，本地 clone `E:\gitwork\dsplayer-plugin`。重点看 `market.json`、`packages/`、`icons/`、`README.md` 条目表。
- **市场条目 schema 解析**：`lib/services/plugin_market/market_model.dart`（字段全集）、`market_manager.dart`（server/source/live 三类安装器 + md5/版本校验）。
- **导入路由**：`lib/services/plugin_center/plugin_center.dart` 的 `PluginImportKind` 与 `inspectImport`/`installFromFile`。
- **统一解析层（v2 双字段清单解析与制品/能力模型）**：`lib/services/plugin_core/plugin_blueprint.dart`（PackageBlueprint/ZipFeatures）、`plugin_manifest_legacy.dart`（旧清单 → Blueprint 适配器）、`plugin_manifest_v2.dart`（format:2 解析合并）；契约测试 `test/arch3/plugin_blueprint_contract_test.dart` 锁定 44 条市场条目 golden。
- **binary/运行时包**：`lib/services/binary_plugin/binary_plugin_model.dart`（字段解析）、`binary_plugin_manager.dart`（binaries 查找/魔数校验/落盘）、`service_model.dart`（`__plugin:` 占位符展开与依赖检查）。
- **源引擎与源类型**：`lib/models/t4/t4.dart`（sourceType）、`lib/services/site/site_service.dart`（导入判定）、`lib/services/qjs_plugin/`、`lib/services/drpy3/`、`lib/services/py_plugin/`。
- **jar 载体插件**：`lib/services/jar_plugin/`（运行时桥/缓存）、`ext/plugin_jar/`（Android 桥与 dex 打包）、`docs/plugin/JAR-SPIDER-PLUGIN-DESIGN.md`。
- **so 载体插件**：`lib/services/magnet/magnet_plugin_manager.dart`（Android so，市场 `magnet`）、`plugins/qjs-win/` 与 `plugins/mpv-win/`（PC dll，`native-lib`）。
- **插件卡与开关规范**：`lib/pages/plugins/widgets/plugin_card.dart`（统一卡片 UI）、`lib/pages/plugins/widgets/cards/engine_cards.dart`（各插件卡）、`lib/pages/plugins/widgets/cards/plugin_cards_controller.dart`（开关枚举/动作契约）。
- **action 动作协议**：`lib/models/t4/action_config.dart`、`lib/services/t4/action_result.dart`、`lib/pages/action/action_entry.dart`。
- **市场条目源登记处**（每条目怎么做的现成答案）：本仓 `plugins/README.md`（条目↔源位置对照表）与 `plugins/UPSTREAMS.md`（外部重打包类的上游与制作方法详解——Go 交叉编译、运行时打包的实例都在这）。
- **机制设计文档**：`docs/plugin/`（BINARY-PLUGIN-DESIGN / SERVICES-DESIGN / PLUGIN-MARKET-DESIGN / PLUGIN-BUNDLE-DESIGN / QJS-PLUGIN-DESIGN / PY-PLUGIN-DESIGN / DR3-QJS-ULTRA-MIGRATION 等）。**新插件优先按 [PLUGIN-MODEL-V2.md](plugin/PLUGIN-MODEL-V2.md) 的「载体+制品+能力位」模型设计清单**（旧八形态作为 legacy 兼容层继续可解析）。
- **打包脚本范式**：`plugins/demo-sources/build_zip.py`、`plugins/python-runtime/build_zip.py`、`tools/pack_danmu_zip.py`、`tools/pack_runtime_zip.py`、`tools/pack_binary_zip.py`。

第三方市场（如 `https://github.com/JMWpower/dsplayer-plugin`）只能作参考，schema 以官方仓库和上述代码为准。

## 三、项目分析要求

先分析目标项目并明确回答：

1. 使用什么语言；
2. 是否有可执行入口；
3. 是服务、命令行程序、库、Web 页面还是 Android App；
4. 是否支持 Android / ARM64（`arm64-v8a` 是 DsPlayer 插件体系唯一基线 ABI）；
5. 是否需要 CGO、JNI、FFmpeg、系统库或动态链接库；
6. 是否需要 Node.js / PHP / Python 运行时（server 包支持 node 与 php 两条路，见 §3）；
7. 是否有固定端口、是否支持自定义端口与绑定地址；
8. 是否需要可写数据目录、配置文件、Cookie、Token 或数据库；
9. 是否有健康检查接口；
10. 是否依赖外部命令；
11. 是否能以单文件形式运行；
12. Releases 中是否有可直接使用的 arm64 二进制；
13. Releases 中的 APK 是完整 App 还是可复用的插件；
14. 项目许可证是否允许重新打包和分发。

## 四、编译要求

编译型项目按实际语言选择方案。**目标 ABI 只有 arm64-v8a**（模拟器/其他 ABI 不在插件交付面）。

Go 项目优先纯静态交叉编译：

```
CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -ldflags="-s -w" -o dist/plugin/bin/plugin-android ./cmd/xxx
```

- `./cmd/xxx` 是目录时直接作为 package 构建，不要写成 `./cmd/xxx/main.go`（除非项目明确要求）；
- 多行命令反斜杠后不能有空格，优先给单行命令；
- 纯 Go 编译失败再考虑 NDK；用 CGO、SQLite 原生库、JNI 或 C/C++ 库时必须说明 NDK 与依赖要求；
- 实例：mediaProxy 的 Android 构建脚本 `scripts/build_goproxy.ps1`（见 `plugins/UPSTREAMS.md` §一）。

Android NDK 编译（C/C++/Rust）时确认：ABI 固定 arm64-v8a；最低 Android API（本体 minSdk 24，插件基线同）；动态链接器路径（bionic `/system/bin/linker64`；musl 动态链接必须随包带 `ld-musl-aarch64.so.1` 加载器并以它启动——python-runtime 包是现成范式）；是否需要 `libc++_shared.so`；能否静态链接（能则优先静态，省掉整个加载器问题）；是否需要额外 so。

so 库类插件（跨包 dlopen 形态）按 `plugin_qjs`/`plugin_fjs` 模式：jniLibs 放 `lib<name>.so` + 空壳 StubActivity，gradle 工程挂本仓 `ext/build-conventions`。多架构 so 优先用 GitHub Actions 构建（本仓铁律：本地不搭交叉编译环境）。

## 五、架构判断

不能仅因为两个文件都是 ARM64 就认为可以互换。用 `file` / `readelf -h` / `readelf -l` / `ldd` 确认：

- ELF 32 位还是 64 位（必须 64 位，`aarch64`）；
- 目标是 Android（bionic）还是 Linux（glibc/musl）；
- 动态链接器路径是否存在于 Android；
- 静态还是动态链接。

Releases 只有 `linux_arm64.tar.gz` / `.deb` / `.rpm` 时，不能直接声称能跑在 Android 上——glibc 动态链接的产物在 Android 上缺加载器必挂；musl 动态链接的产物需要随包分发 loader（§四）。反之，Releases 有 APK 也不代表它就是 DsPlayer 插件——必须核对包内 manifest（§一.6）。

## 六、启动参数与端口

确认目标程序的真实启动命令，binary 插件的 `params` 必须与之一致，不要凭空添加不支持的参数：

```
plugin-android server --port 5575      → "params": "server --port 5575"
plugin-android -port 5575              → "params": "-port 5575"，配 "portField": "-port"
node index.js --port 9321              → server 包 "entry": "index.js"（node 由运行时提供）
```

- 端口**不会**被 DsPlayer 自动分配：binary 包靠 `portField` 从参数解析（优先）或 `healthCheck.port`；server 包靠 server.json 的 `port`。探活方式二选一：`healthCheck.type=http` 探 HTTP 路径 / `tcp` 探端口；都不配则视为「进程活着就是健康」。
- 绑定地址优先 `127.0.0.1`（安全）；确需被局域网其他设备访问（投屏、DLNA、远程遥控）才用 `0.0.0.0`，并在插件说明里写明暴露面。
- 服务包运行时 = nodejs（缺省）或 php（manifest `runtime` 字段，2026-10-16 起）；Python 服务要么改造为被 nodejs 服务桥接（drpy-node 的 phpEnv.js 模式），要么编译成独立二进制走 binary 包。

## 七、数据目录、占位符与运行目录

- binary 包落盘 `files/plugins/<name>/`，启动时注入环境变量 `DS_PLUGIN_DIR` 指向该目录——**持久数据写这里**（用户 `config.json` 在覆盖安装时会被保留，其余产物会被新版清掉重建，别把数据混进 bin/）。
- server 包落盘 `sdcard/dsplayer/server/node/<workDir>/`，覆盖更新会整目录替换——持久数据必须写到包目录之外（如 `HOME` 指向的目录）或程序支持的环境变量指定目录。
- 配置路径时可用占位符（`lib/services/binary_plugin/service_model.dart` 展开规则）：`__plugin:<插件name>__` → 该插件落盘目录（依赖未安装时启动会明确报错）；`__sdcard__` → sdcard 路径前缀。
- 修改上游程序支持环境变量（`DATA_DIR`/`CONFIG_DIR`/`PORT`/`HOME`/`TMPDIR`）比在包里硬编码绝对路径好；不要假设工作目录语义，能显式传路径就显式传。

## 八、DNS、HTTPS 与 Android 兼容性

Android 插件进程常见故障：`lookup xxx on [::1]:53: connection refused`（读不到 `/etc/resolv.conf`）、TLS 证书校验失败（无系统 CA 信任路径）。检查并实测：

- DNS 是系统 resolver 还是语言自带 resolver；纯 Go resolver 默认读 resolv.conf 会挂，需回退 netgo 或显式配置上游；
- TLS 根证书：需随包带 `cacert.pem` 并设置 `SSL_CERT_FILE` 类环境变量（python-runtime 的 sitecustomize.py 是现成范式）；
- `HOME`/`TMPDIR` 已被宿主设置，程序应尊重它们。

不要只加一个环境变量就认为 DNS 已修复——必须在真机上实测域名解析和 HTTPS 请求。

## 九、数据源（drpy 生态）

如果项目本质是一个影视/音乐/漫画**源**，先按下表确定跑在哪个引擎上，再选格式与放置位置。**源格式与引擎强绑定，不能混用**：

| 源类型 | 判定 | 引擎/通道 | 依赖插件 | 源文件格式 |
|---|---|---|---|---|
| drpy3 | api 以 `-dr3.js` 结尾或路径含 `/dr3/` | QJS（qjs_ultra 换核后与 dr2 共用，fjs 已退役） | qjs | ESM |
| drpy2 | api URL 含 `drpy2` | QJS + 内置 drpy2.min.js 适配包 | qjs | var rule 规则 |
| cat 直连 | 内容含 `__jsEvalReturn` | QJS | qjs | 单文件 js |
| hipy/py | type==3 且 api 含 `.py` | Chaquopy 进程内 Python（Binder） | py（APK） | Python class Spider |
| drpys 服务源 | 普通 T4 HTTP 源指向服务地址 | nodejs 服务（HTTP ac 协议） | nodejs 运行时 | drpy-node js 源 |
| **web 源** | api 是 html 页面（`web://` / http / 本地 file://，type=3 html 分支） | WebView 整页渲染 + `window.ds`/`window.fm` 桥（req 免跨域/store/播放/导航/事件/接口配置管理） | 无 | 单个 HTML 页面（UI 即源），API 全表与样例见 [WEB-SOURCE-GUIDE.md](web/WEB-SOURCE-GUIDE.md) |
| cms | type 0/1 | 内置 CmsClient | 无 | — |

**可用性闸门**：dr2/dr3/cat 全部依赖 `plugin_qjs` 安装且启用（无 dr3 独立开关）；hipy 依赖 `plugin_python`（APK 直装）。做源包时在说明里写清依赖。

四类本地源有现成标准样例，**新源照抄结构**（全在 `plugins/demo-sources/spider/` 下）：

### A. drpy2（`spider/dr2/`，样例：百忙无果[官].js）

```js
/*
@header({
  searchable: 2, filterable: 1, quickSearch: 0,
  title: '百忙无果[官]',
  lang: 'dr2'
})
*/
var rule = {
    title: '...',
    host: '...',
    class_parse: async function () {},
    一级: async function () {},
    二级: async function () {},
    搜索: async function () {},
    lazy: async function () {},
    action: async function (action, value) {}
};
```

- 规则型 `var rule`，**不能单独作主模块**，运行时由内置 drpy2.min.js 装配；中文名钩子（`一级`/`二级`/`搜索`/`预处理`/`推荐`）真实生效；js 计算钩子用 `$js.toString(()=>{...})` 形态。

### B. drpy3（`spider/dr3/`，样例：百忙无果d3.js；写作指南 `assets/agent/drpy3-源写作指南.md`）

```js
/*
@header({ title: '...', lang: 'dr3', searchable: 2, filterable: 1, quickSearch: 0 })
*/
export default {
    meta: {},
    rule: {},
    async init(ctx, ext) {},
    async home(ctx, filter) {},
    async homeVod(ctx) {},
    async category(ctx, tid, pg, filter, extend) {},
    async detail(ctx, id, fullId) {},
    async play(ctx, flag, id, flags) {},
    async search(ctx, wd, quick, pg) {},
    async action(ctx, action, value) {},
    async proxy(ctx, params) {}
};
```

- ESM `export default`；**钩子必须在 export default 顶层**——写进 `rule:{}` 会静默走声明式 defaults（症状：六环节返回空、酷似网络问题）。`defineSource({...})` 只是恒等包装，可不用。
- 11 个钩子全 async、首参 `ctx`（含 `ctx.lib.{net,parse,crypto,text,utils,wasm}` 能力集），完整签名与 ctx 字段见写作指南。
- `rule` 声明式字段保留 drpy2 中文键（`一级`/`搜索`/`二级`/`lazy` 等），适合简单规则源；复杂逻辑直接写钩子。

### C. cat 直连（`spider/js/`，样例：云游戏cat.js）

```js
export function __jsEvalReturn() {
    return {
        init: function (cfg) { /* {stype:3, skey, sourceKey, ext} */ },
        home: function (filter) {},
        category: function (tid, pg, filter, extend) {},
        detail: function (id) {},
        search: function (key, quick, pg) {},
        play: function (flag, id, vipFlags) {},
        action: function (action, value) {}
    };
}
```

- 特征导出 `__jsEvalReturn` 工厂（`export default` 兜底）；`_lib.` 前缀 js 是依赖库；`import` 可引 `assets://js/lib/<file>` 协议的 catLib 库包（市场条目 catlib）。
- 选择器四件套 `pdfh/pdfa/pd/pdfl` 已由宿主注入，可直接用。

### D. hipy/py（`spider/hipy/`，样例：abts.py）

```python
class Spider(BaseSpider):   # 或不继承、自带全部方法
    def init(self, extend=""): ...
    def homeContent(self, filter): ...
    def homeVideoContent(self): ...
    def categoryContent(self, tid, pg, filter, extend): ...
    def detailContent(self, ids): ...
    def searchContent(self, key, quick, pg): ...
    def playerContent(self, flag, id, vipFlags): ...
    def localProxy(self, param): ...
```

- 十接口协议以 drpy-node `libs/hipy.js` 为基准；`@header` 注释提供元数据（title 等）。
- 注意 py 源有文件系统守卫（零存储权限 + 白名单），别在源里直接写任意路径 IO。

### E. drpys 服务源（nodejs）

- 源文件是 drpy-node 格式 js，放 `sdcard/dsplayer/server/node/drpy-node/spider/js/`（随 drpys 服务分发），由 nodejs 服务端扫描执行，DsPlayer 侧只按普通 T4 HTTP 源配置服务地址。
- 服务接口自带 query（如 `?pwd=`）是合法形态，客户端会**保留合并** site.api 自带 query。
- ⚠️ `spider/js/` 有两个消费方：`/sdcard/dsplayer/spider/js/` 由 QJS 内置引擎扫描（cat/js 源），`server/node/drpy-node/spider/js/` 由 drpys 服务扫描——source 包做本地源时落前者。

### F. 源的 JSON API 建议

如果项目原本只有 HTML 页面、要给源调用，优先增加稳定 JSON API（搜索/详情/播放/列表/健康检查），不要让源直接解析后台 HTML。

## 十、源动作协议（T4 action，真实清单）

源可以实现动作页（设置中心/登录/扫码等）。**以本仓实现为准，勿照抄其它 drpy 分支的习惯字段**（`lib/models/t4/action_config.dart`）：

- 下发形态三种：详情页 `more.actions` 声明 `[{name, action}]`；列表条目 `vod_tag:"action"`；`vod_id` 直接内联动作配置 JSON。
- 请求：`GET {api}?ac=action&action=<id>&value=<用户输入>`。
- 动作配置对象的键是 **`actionId`**（不是 `action`——`action` 键是响应里的链式字段）+ `type`。
- **type 全集**：`input` / `edit` / `multiInput` / `multiInputX` / `menu` / `select` / `msgbox` / `webview` / `browser` / `help`；另有文本直通预览（`__text_preview__`，text/markdown/pdf）。
- **二维码不是 type**：配置对象加 `qrcode` 字段（内容非空）即整个动作页切换为二维码展示形态。
- 常用字段：`id`（提交键名，缺省 `value`）、`button`（0-3 按钮位）、`selectData`（快选项）、`timeout`、`keep`、`imageUrl`、`multiSelect`、`column`、`selectedIndex`、`htmlMsg`、`url`、`textZoom`；multiInput 子项 `inputType`：0 文本 / 1 密码 / 2 数字 / 3 邮箱 / 4 URL。
- 响应分发：字符串 → toast；`.error` → 报错不关页；`.toast/.message/.msg`；`.action`（对象或 JSON 串）→ 链式打开新动作页；`actionId:"__keep__"` → 弹窗不关可续传；专项动作 `__copy__`（content）/`__detail__`（skey+ids 跳详情）/`__self_search__`（tid+name）/`__refresh_list__`。
- 没有 `refresh` 这个 type；要刷新列表用 `__refresh_list__` 专项响应。

登录态安全纪律（保留强制）：Cookie/Token/二维码会话属敏感信息，不进日志、不硬编码默认密码、Cookie 接口不暴露公网、二维码会话设过期时间；不绕过平台登录/验证码/付费/DRM。

## 十一、打包纪律

生成目录（示例以 binary 为例；server/source/live 按各自结构）：

```
mkdir -p dist/dsplayer/bin
# 放入 dist/dsplayer/plugin.json 与 dist/dsplayer/bin/plugin-android
chmod +x dist/dsplayer/bin/plugin-android
```

**统一用 Python zipfile 打包**（本仓所有 build_zip.py 的既定纪律）：

```python
import zipfile, os
FIXED_DATE = (2026, 1, 1, 0, 0, 0)  # 固定时间戳 → 同内容同 md5，可复现
with zipfile.ZipFile("dist/plugin-name-1.0.0.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk("dist/dsplayer"):
        for f in sorted(files):
            p = os.path.join(root, f)
            i = zipfile.ZipInfo(os.path.relpath(p, "dist"), FIXED_DATE)
            i.create_system = 3            # unix，保 UTF-8 文件名标志
            i.external_attr = (0o755 << 16) if p.endswith("plugin-android") else (0o644 << 16)
            with open(p, "rb") as fp:
                z.writestr(i, fp.read())
```

铁律：

- **禁用 7-Zip 打分发包**——它按本地代码页（GBK）写中文文件名且不带 UTF-8 flag，端内解压中文全乱码；含中文源名的包（source 类常见）必须 Python zipfile。
- zip **根部**直接是 manifest/plugin.json，不要套多余外层目录；
- 二进制路径与 manifest 声明一致；包内不残留旧二进制；
- 同一内容的包**固定 zip 时间戳**，保证 md5 可复现；
- 打包后自检：`unzip -l` 看清单、读回 manifest 确认内容与路径一致、`md5sum` 记录。

## 十二、市场索引与上架

官方市场 = GitHub 仓库 `hjdhnx/dsplayer-plugin`（结构：`market.json` + `packages/` + `icons/` + `README.md`）。market.json 顶层：`logo` / `name` / `desc` / `updatedAt` / `plugins[]`。

条目字段（解析在 `lib/services/plugin_market/market_model.dart`）：

```json
{
  "id": "plugin-name",
  "name": "插件名称",
  "version": "1.0.0",
  "url": "packages/plugin-name-1.0.0.zip",
  "type": "import",
  "category": "env",
  "icon": "icons/plugin-name.png",
  "size": 12345678,
  "author": "作者",
  "desc": "插件说明",
  "tags": ["binary"],
  "changelog": "首版",
  "md5": "32位hex",
  "minApp": "0.0.0"
}
```

- 必填四要素：`id` / `name` / `version` / `url`，缺一整条被丢弃；`type` 合法值 **5 个**：`import`（应用内静默导入）/ `apk`（系统安装器）/ `live` / `server` / `source`，未声明或非法值归 `import`。
- `category` 只有 `env`（运行时/环境类，默认）/ `app`（应用类）两值。
- `pkg` 是 **type=apk 专属**：第三方 APK 条目必须声明包名，否则市场 UI 永远判「未安装」。
- `md5` 声明即**强制校验**（不符拒装防篡改）；`size` 单位字节；`minApp` 不满足时条目置灰。
- `icon` 相对索引路径或绝对 URL；**换图必须换文件名**（客户端磁盘缓存按 URL 键控）。
- `platforms`（可选数组）：`["android"]` / `["win32"]`；缺省 = 全平台可见。PC 专用包（如 `python-win`/`qjs-win`）必须显式写 `win32`，Android 专用包（如 `magnet`、`jar`）写 `android`。
- `abis`（可选数组）：包内 so 支持的 ABI 列表（如 `["arm64-v8a","armeabi-v7a"]`）；空数组/缺省 = 纯 dex/资源包不限制。`minApp` 不满足时条目置灰（如 jar 1.1.0 要求宿主 1.1.6）。

上架流程（三条通用，缺一不可）：

1. 产物拷入市场仓库 `packages/`，**删除旧版本包**（git 历史留档）；文件名带版本号，**同名包绝不重传**（内容变化必升版本换文件名，否则 CDN 缓存导致 md5 假失败）；
2. `market.json` 更新 version/size/url/md5/changelog，刷顶层 `updatedAt`（它是客户端缓存新旧唯一判据）；同步 `README.md` 条目表（版本 + 包名）；
3. push 后拉 raw 复核（URL、md5、updatedAt）。

大体积 APK 可走 GitHub Release 分发：tag 约定 `<id>-<version>`、asset 名避开 `+` 和中文、条目 `url` 直接写绝对直链。

## 十三、验证要求

按 DsPlayer 本仓的调试口径执行（环境细节见仓内 `AGENTS.md`/`CLAUDE.md`）：

1. 构建成功、产物大小、`file`/`readelf` 架构与链接方式确认；
2. zip 清单与 manifest 内容自检（§十一）；
3. 真机安装验证（adb 在 `E:/Android/Sdk/platform-tools/adb.exe`；设备优先级：数据线真机 > 无线真机 > 模拟器；多设备 adb 命令必带 `-s <serial>`）：
   - binary/binary-runtime/server：插件页导入（或市场安装）→ 服务页起停 → 探活通过 → 浏览器/接口实测；
   - source：导入 → 源列表出现 → 首页/分类/详情/播放全链路点通；
   - live：导入 → 电视页频道加载；
   - apk：系统安装器直装 → 插件页探测到（probeLocal 计数正确）；
   - 所有形态：插件页卡片核对**已安装态有卸载入口**；有开关的插件必须实测「关 → 调用被拒/能力位回落 → 再开 → 恢复」，并核对 UiActions `plugins.<id>.toggle` / `plugins.<id>.uninstall` 可驱动；
4. 看日志优先 `adb logcat`，被 ROM 屏蔽（荣耀/华为）时用应用内导出：`am broadcast -a com.dsplayer.DEBUG --es action logpull` 后 `adb pull /sdcard/dsplayer/logs/`；
5. 语义化驱动 UI 用 UiActions id（`action list` 列出、`action tap <id>` 点击），**禁止坐标盲点**；
6. md5 三处对账一致：市场包 = 本地产物 = 索引声明；
7. 许可证与再分发要求确认。

当前环境没有 Android 设备时，必须明确说明「未完成真机验证」，不得声称插件已可用。

## 十四、最终输出格式

按以下结构回答：

1. 项目类型判断；
2. 选择的插件形态（§一 六选一）与判定依据；
3. 项目构建入口与编译命令；
4. manifest 全文（plugin.json / server.json / source.json / live JSON）；
5. 插件目录结构；
6. 打包命令（Python zipfile）；
7. 是否需要 runtime 依赖（nodejs/php/python 哪个）与依赖插件（qjs/py）；
8. 是否需要修改上游源码、改了什么；
9. 市场条目 JSON 与上架清单（md5/size/url/icon/README 表）；
10. 测试命令与真机验证结果；
11. 许可证注意事项；
12. 最终文件绝对路径；
13. 已完成验证 / 未完成验证与潜在风险。

不要只给理论方案：先检查 §二 的实际代码与仓库，再生成命令和文件。
