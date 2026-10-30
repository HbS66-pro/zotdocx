# Word 侧配套宏：引用号补上标

`zotdocx patch` 把 Zotero 的正文引文改成纯文本写入，`\super` 被一并剥掉——「无法删除范围」不再出现，代价是正文引用号变成平排。这个宏负责把上标补回来。

它只处理域代码里含 `ZOTERO_ITEM` 的引注域。参考文献表（`CSL_BIBLIOGRAPHY`）只统计、绝不改动，所以文献条目编号不会被误设成上标。

只有跑过 `zotdocx patch` 的文档需要它。没打过补丁的文档，引用号本来就是 Zotero 用 `\super` 排的上标，跑这个宏只会把已经是上标的再设一遍，无害也无必要。

## 两种用法

| 方式 | 装什么 | 什么时候补 |
|---|---|---|
| 手动 | 只要标准模块 `ZoteroFix.bas` | 定稿前按 `Alt+F8` 跑一次 |
| 自动 | 加上类模块 `WordEvents.cls` 和 `ThisDocument` 里的 `AutoExec` | 每 5 秒巡检一次，缺上标就补，刷新完不用管 |

手动版更简单，但每刷新一次引用就要重跑一次宏。自动版装一次，之后随便刷新。

## 安装（写进 Normal.dotm，全局生效）

装之前：备份 `%APPDATA%\Microsoft\Templates\Normal.dotm`，并关掉所有 Word 窗口。

1. 打开 Word，按 `Alt+F11` 进 VBA 编辑器。
2. 左侧工程树里右键 `Normal` → **插入 → 模块**，把 `docs/macros/ZoteroFix.bas` 的全部内容粘进去。
3. 右键 `Normal` → **插入 → 类模块**，把 `docs/macros/WordEvents.cls` 的内容粘进去；在属性窗口（`F4`）把类模块的名字改成 `WordEvents`。
4. 双击工程树里的 `ThisDocument`，把 `docs/macros/ThisDocument.txt` 的内容粘进去。
5. 按 `Ctrl+S` 或直接关掉 VBA 编辑器，Word 会问是否保存到 Normal.dotm，选**是**。
6. 重启 Word。

只想要手动版的话，第 1–2 步做完就够了，跳过 3–6。

**用粘贴，不要用「导入文件」**：`.bas` 是 UTF-8，VBE 的导入按系统编码读，中文注释会乱码。

## 它做什么

- `ZoteroFixCitationsSuper`：把当前文档里每个 `ZOTERO_ITEM` 域的 `Result.Font.Superscript` 设为 `True`，只对还不是上标的动手。手动版就是它。
- `ZoteroFixTick`：每 5 秒看一次当前文档，发现任何一个引注域缺上标，就把全部引注域扫一遍。自动版靠它。
- `ZoteroFixNow`：立刻补一次，不弹窗。
- `ZoteroCitationList`：把每个引用域的文字和上标状态打到立即窗口（`Ctrl+G`），排查用。
- `ZoteroFixStop`：停掉巡检。

## 为什么「刷新也不用管」

手动版只在跑的那一刻生效：刷新之后如果引用号又变回平排，再跑一次。自动版省掉这个判断——巡检每 5 秒看一次当前文档，发现缺上标就补，所以你刷新完什么都不用做，看到的始终是上标。

## 怎么验证

```bash
zotdocx status 论文.docx
```

看「上标」那行：

```
上标   数字制引注 32 个：整条上标 32 · 整条非上标 0 · 域内混排 0
```

整条非上标为 0，说明都补回来了。域内混排不为 0，通常是域结果里还有别的 run（比如引用后面跟着页码），需要人看一眼。

`--json` 里是 `superscript: {numeric, all, none, mixed}`，方便写进脚本。

## 关掉或卸载

- 临时停巡检：VBE 立即窗口（`Ctrl+G`）里执行 `ZoteroFixStop`。
- 恢复巡检：重启 Word，或执行 `WordEventsKick`。
- 彻底卸载：`Alt+F11` 删掉 `ZoteroFix` 模块和 `WordEvents` 类模块，清空 `ThisDocument`，保存 Normal.dotm。

## 注意

- Normal.dotm 是全局模板，装进去之后对这台机器上所有文档生效。它只改 `ZOTERO_ITEM` 域的格式，不碰正文文字。
- 宏需要被允许运行：文件 → 选项 → 信任中心 → 宏设置。Normal.dotm 位于受信任位置，通常无需额外设置。
- 换机器、重装 Office 后要重装一次。
