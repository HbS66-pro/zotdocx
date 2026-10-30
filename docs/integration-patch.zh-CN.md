# Zotero 集成补丁

`zotdocx patch` 会检查 `<Zotero 程序目录>/app/omni.ja`，并能把你**自己改好**的
`integration.js` 写回去。它不携带 Zotero 代码，不加 `--apply` 不会改动任何文件。

要用的片段是本目录下的 [`zotero-plaintext-fix.js`](zotero-plaintext-fix.js)，
下面是完整的三步。

## 什么情况下用

有些 Word 环境里，Zotero 删不掉它插入 RTF 块时多出来的段落标记，于是报
**「无法删除范围」**：刷新引用、插入新引用都会失败，引注域反复损坏。

GB/T 7714、IEEE、Nature、Vancouver 这类数字制样式正是走 RTF 路径的，所以坏的
是正文引注；著者-出版年样式一般不受影响。

## 这个片段做什么

Zotero 的 Word 集成有两种写法：RTF 块和纯文本。片段拦截即将写入的文本，当它是
一个纯编号（`\super [n]\nosupersub{}`）时，剥掉 RTF 外壳，改写成纯文本。没有
RTF 块插入，事后就没有东西要删。参考文献表仍走原来的 RTF 路径。

代价：`\super` 被一并剥掉，正文引用号失去上标。可以在 Word 里补回上标，或者按
目标样式的要求接受平排编号。

## 三步

先把 Word 关掉。

### 1. 取出 integration.js

```powershell
$omni = "$env:ProgramFiles\Zotero\app\omni.ja"
Copy-Item $omni "$env:TEMP\omni.zip" -Force
Expand-Archive "$env:TEMP\omni.zip" "$env:TEMP\omni" -Force
```

要改的文件是 `$env:TEMP\omni\chrome\content\zotero\xpcom\integration.js`。

### 2. 改它

用文本编辑器打开：

- 找到 `setText` 实现，作为第一条语句加上

  ```js
  text = _zoteroPlainCitationFix(text);
  ```

- 把 `zotero-plaintext-fix.js` 里从 `function` 到文件末尾的内容追加到文件末尾

### 3. 写回去

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --patched "$env:TEMP\omni\chrome\content\zotero\xpcom\integration.js"
```

不加 `--apply` 是干跑。加 `--apply` 时会在原处留一份 `omni.ja.bak_<时间戳>`
备份，只替换那一个条目，重建后自检，然后由你重启 Zotero 生效。

写 `Program Files` 需要管理员权限的终端。

## 复查、撤销、重打

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero"
```

会打印包大小和补丁标记在不在。要撤销，把 `omni.ja.bak_<时间戳>` 覆盖回 `omni.ja`。

Zotero 升级会覆盖 `omni.ja`，升级后先复查一次，标记没了就重做第 3 步。
