# dsplayer-plugin

DsPlayer 插件市场仓库：`market.json` 为市场索引（在线安装入口），`packages/` 存放插件包，`icons/` 存放条目图标，`check_market.py` 为发版前对账闸门（在仓库根目录执行）。

市场地址（DsPlayer 内添加）：

```
https://raw.githubusercontent.com/JMWpower/dsplayer-plugin/main/market.json
```

### 环境（env）

| 条目 | id | 版本 | type | 包 |
|---|---|---|---|---|
| 多聚听书 | `duoju-ting` | 1.9.3 | import | `duoju-ting.zip` |
| 多聚网盘（安卓） | `duojupan` | 1.6.1 | import | `duojupan-1.6.1.zip` |
| TG短剧库 | `tgdrama` | 1.45.2 | import | `tgdrama-1.45.2.zip` |

### 应用（app）

| 条目 | id | 版本 | type | 包 |
|---|---|---|---|---|
| MusicK音乐 | `musick-api` | 1.0.0 | server | `music_api-main.zip` |
| 多聚聚合-node版 | `djnode` | 1.0.0 | server | `djnode-1.0.0.zip` |
| MusicK音乐配套源 | `musick-source` | 1.2.1 | source | `musick-source.zip` |
| 多聚听书配套源 | `duoju-ting-source` | 1.9.1 | source | `duoju-ting-source.zip` |
| 豆瓣盘搜 | `douban-pansou` | 1.1.1 | source | `douban-pansou-1.1.1.zip` |
| 炫彩主页web源 | `my-home` | 1.0.15 | source | `my-home-1.0.15.zip` |
| TG短剧库配套源 | `tgdrama-source` | 1.0.0 | source | `tgdrama-source.zip` |
| 阅读图书馆·Node | `legado-server-node` | 1.3.0 | server | `legado-server-node-1.3.0.zip` |
| 阅读源·Node聚合 | `legado-node` | 3.0.0 | server | `legado-node-3.0.0.zip` |
| 阅读源·Node聚合配套源 | `legado-node-source` | 1.1.0 | source | `legado-node-source-1.1.0.zip` |

### 已下架（暂不显示）

以下包仍保留在 `packages/`，登记在 `market.json` 顶层 `hidden` 数组里（闸门跳过孤儿判定），市场列表不显示。要重新上架：把它们移出 `hidden` 并补回对应条目与 README 行。

`duoju-lite-green.zip` · `duojupan-win-1.6.1.zip` · `lanmei-lite-1.0.18.zip` · `djduanju.zip` · `drpy-node-2.0.7.zip` · `legado-tvbox-source-1.0.1.zip` · `legado-server-node-1.0.0.zip`
