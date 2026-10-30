# Zotero 集成补丁

`zotdocx patch` 会读出 `<Zotero 程序目录>/app/omni.ja`、改写里面的
`integration.js`，自检通过后把包写回去。它不携带 Zotero 代码：加进去的片段是本项目
自己的 MIT 代码（`zotdocx/data/plaintext-fix.js`）。

## 什么情况下用

有些 Word 环境里，Zotero 删不掉它插入 RTF 块时多出来的段落标记，于是报
**「无法删除范围」**：刷新引用、插入新引用都会失败，引注域反复损坏。

GB/T 7714、IEEE、Nature、Vancouver 这类数字制样式正是走 RTF 路径的，所以坏的
是正文引注；著者-出版年样式一般不受影响。

## 它改了哪两处

`integration.js` 里只动两个地方：

1. `setText` 开头加一行调用 —— `<参数> = _zoteroPlainCitationFix(<参数>);`
2. 文件末尾追加片段

对渲染成纯编号的引用（`\super [n]\nosupersub{}`），片段改写成纯文本、不加 RTF 外壳。
没有 RTF 块插入，事后就没有东西要删。参考文献表仍走原来的 RTF 路径。

代价：`\super` 被一并剥掉，正文引用号失去上标。可以在 Word 里补回上标，或者按目标
样式的要求接受平排编号。

## 怎么跑

先把 Zotero 和 Word 关掉。

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto
```

不加 `--apply` 只报告会改什么。要写：

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto --apply
```

`--apply` 会在原处留一份 `omni.ja.bak_<时间戳>` 备份，只替换那一个条目，其余部件逐字节
保留，重建后先自检再落盘。重启 Zotero 生效。

写 `Program Files` 需要管理员权限的终端。

## 它停下来的时候

两种情况 `--auto` 会拒绝，不会硬改：

- 找不到 `setText` 的常见写法（Zotero 版本差异）—— 文件保持原样；
- 已经有补丁标记 —— 确实要重打就加 `--force`。

第一种情况可以手工打，再把改好的文件喂回去：

1. 把 `app/omni.ja` 复制到可写目录，改名成 zip 后解压；
2. 在 `setText` 第一条语句位置加上调用，再把 `zotdocx/data/plaintext-fix.js` 里从
   `function` 到末尾的内容追加到文件末尾；
3. `zotdocx patch --zotero-dir "C:\Program Files\Zotero" --patched <改好的 integration.js> --apply`

## 复查、撤销、重打

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero"
```

会打印包大小和补丁标记在不在。要撤销，把 `omni.ja.bak_<时间戳>` 覆盖回 `omni.ja`。

Zotero 升级会覆盖 `omni.ja`，升级后先复查，标记没了就重跑一次 `--auto --apply`。
