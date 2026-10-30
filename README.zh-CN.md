# zotdocx

[![tests](https://github.com/HbS66-pro/zotdocx/actions/workflows/tests.yml/badge.svg)](https://github.com/HbS66-pro/zotdocx/actions/workflows/tests.yml)

[English](README.md) | **中文**

正文里删掉一条引用，全文编号都变了，可表格、图题、表注里的 `[12]` 还是旧号——这是 Zotero 在 Word 里最容易出错的地方。

`zotdocx` 直接修 `.docx` 里的引用域：只动这一个文件，不碰你的文献库，也不重新排版。

任何 Zotero 样式都能用。其中 `renumber` 和 `lift` 只对数字制有意义——GB/T 7714、IEEE、Nature、Vancouver 以及其它编号制 CSL 样式——因为它们排的是编号；著者-出版年样式（APA、Harvard）没有编号可排，这两个命令跳过，`status`、`heal`、`repair` 照常可用。

## 快速开始

```bash
pip install zotdocx
zotdocx demo
```

`demo` 在当前目录生成 `demo.docx`（合成文档，两个引注域，几处故意留的毛病），然后打印一次只读体检和一次 `renumber` 干跑：

```
demo.docx
  部件 7 个；document.xml 0.00 MB
  样式 未记录

域      3 = 引注 2 + 书目 1 + 其他 0
        跨段落：引注 0 · 书目 0
        位置：正文 2
条目    2 个
编号   显示 1–2；同条目多编号 0；单条目编号不符 2；多条目编号不符 0
纯文本 正文 1 · 表格 1 · 表注图注 1 · 图题表题 1
```

换成自己的稿子：

```bash
zotdocx status 论文.docx          # 只读体检；有问题时退出码 1
zotdocx renumber 论文.docx        # 干跑，只打印会改什么
zotdocx renumber 论文.docx --apply
```

## 处理的问题

- 引注域跨段落，域尾落在下一段
- 域内编号与页面显示的编号不一致
- 编号顺序与实际引用顺序不符
- 正文中的纯文本引用（`[3]`、`[12,13]`）未上宏
- 引用域指向的条目已从文献库删除（断链）
- Zotero 刷新时报「无法删除范围」

## 命令

| 命令 | 功能 |
|---|---|
| `demo` | 生成合成示例文档并检查一遍 |
| `status` | 检查域结构、条目、编号与纯文本引用分布 |
| `heal` | 修复跨段落引注域，对齐域内编号与显示编号 |
| `renumber` | 按首次引用顺序重排编号，同步表格、图题、表注中的纯文本数字 |
| `lift` | 将正文中的纯文本引用补为活域 |
| `repair` | 按 item key 或题名重新连接断链引用 |
| `patch` | 检查或打上「无法删除范围」的补丁 |

## 安装

```bash
pip install zotdocx
```

需要 Python 3.9 及以上，唯一依赖是 `lxml`。从源码装用 `pip install .`。

`repair` 和 `status` 的断链检查需要 `zotero.sqlite`，按这个顺序找：`--zotero-db`、环境变量 `ZOTERO_DB`、`~/Zotero/zotero.sqlite`。都没找到时，文档内的检查照常做，断链检查跳过。

## 使用

写入类命令默认只干跑，加 `--apply` 才落盘：

```bash
zotdocx heal     稿件.docx            # 只打印将要修改的内容
zotdocx heal     稿件.docx --apply    # 写入，原文件备份为 *.bak_<时间戳>
zotdocx lift     稿件.docx --apply --out 新文件.docx
```

`status` 发现问题时退出码为 1，无问题为 0；用法错误和文件错误为 2。

## 处理范围

- 仅替换 docx 包内的 `word/document.xml`，其他部件逐字节保留。
- 表格、图题、表注中的编号保持纯文本，`renumber` 只同步数字，不转为活域。
- 图题表题、表注、参考文献标题同时识别中英文写法（图 / 表 / 注 / 参考文献，Table / Figure / Note / References）。
- 文献库只读，查询前复制到临时目录。
- 不修改正文文字，不排版，不做定稿处理。

## 限制

- 仅支持数字型 CSL 样式。著者-出版年样式没有编号可排。
- 仅在 Windows 与 Word 环境验证。
- 编号被拆分为多个 run 时不处理，列在输出中。
- `repair` 仅依据 item key 与完整题名匹配，无法匹配时报告，不作推测。
- `patch` 会改写 Zotero `omni.ja` 里的 `integration.js`。需要对 Zotero 目录的写权限；找不到 `setText` 的常见写法时直接停下，不改任何东西。

## 测试

```bash
python tests/run_all.py
```

测试使用测试进程内生成的合成文档（中英文各一份），不含真实论文或文献库内容。同一套测试在 GitHub Actions 上跑 Python 3.9、3.11、3.13。

## 高级：Zotero 集成补丁

如果 Zotero 报**「无法删除范围」**、引注域反复损坏，原因在 Zotero 一侧，不在文档里：

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto --apply
```

它先备份 `omni.ja`，改写里面的 `integration.js`，重建并自检通过后才替换原文件。加进去的片段是本项目自己的 MIT 代码，不携带 Zotero 代码。细节、上标代价和手工兜底见 [docs/integration-patch.zh-CN.md](docs/integration-patch.zh-CN.md)。它改的是 Zotero 而不是文档，Zotero 升级会把它覆盖掉。

## 许可

MIT 协议，见 [LICENSE](LICENSE)。
