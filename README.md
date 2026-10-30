# zotdocx

[![tests](https://github.com/HbS66-pro/zotdocx/actions/workflows/tests.yml/badge.svg)](https://github.com/HbS66-pro/zotdocx/actions/workflows/tests.yml)

**English** | [中文](README.zh-CN.md)

`zotdocx` repairs Zotero citation fields inside a `.docx`. It edits the file only: it does not touch the Zotero library, and it does not re-typeset the document.

It works with any Zotero citation style. `renumber` and `lift` only apply to numeric styles — GB/T 7714, IEEE, Nature, Vancouver and any other numbered CSL style — because they reorder numbers; author–date styles such as APA or Harvard have no numbers to reorder, so those two are skipped. `status`, `heal` and `repair` work with any style.

## Quick start

```bash
pip install zotdocx
zotdocx demo
```

`demo` writes `demo.docx` into the current directory — a synthetic document with two citation fields and a few known defects — then prints a read-only report and a dry run of `renumber`:

```
demo.docx
  部件 7 个；document.xml 0.00 MB
  样式 未记录

域      3 = 引注 2 + 书目 1 + 其他 0
        跨段落：引注 0 · 书目 0
        位置：正文 2
条目    2 个
编号   显示 1–2；同条目多编号 0；单条目编号不符 2；多条目编号不符 0
上标   数字制引注 2 个：整条上标 2 · 整条非上标 0 · 域内混排 0
纯文本 正文 1 · 表格 1 · 表注图注 1 · 图题表题 1
```

Then point it at your own file:

```bash
zotdocx status 论文.docx          # read-only report; exit code 1 if something is off
zotdocx renumber 论文.docx        # dry run, prints what would change
zotdocx renumber 论文.docx --apply
```

The console output is in Chinese; numbers, exit codes and `--json` are the stable interface for scripts.

## What it fixes

- Citation fields split across paragraphs, with the field end in the next paragraph
- Numbers stored in a field that disagree with the numbers shown on the page
- Numbering that does not follow the order of first citation
- Plain-text citations in the body (`[3]`, `[12,13]`) that are not live fields
- Citation fields pointing to items removed from the library (broken links)
- Zotero's "Cannot delete range" error when refreshing

## Commands

| Command | What it does |
|---|---|
| `demo` | Write a synthetic sample document and check it |
| `status` | Report field structure, item count, numbering consistency, superscript state, plain-text citations |
| `heal` | Repair cross-paragraph citation fields; align stored and displayed numbers |
| `renumber` | Renumber by first citation and sync plain-text numbers in tables, captions and notes |
| `lift` | Turn plain-text citations in the body into live fields |
| `repair` | Relink broken citations by item key or title |
| `patch` | Check, or apply, the workaround for Zotero's "Cannot delete range" |

## Install

```bash
pip install zotdocx
```

Python 3.9 or later; the only dependency is `lxml`. From a checkout, `pip install .`.

`repair`, and the broken-link part of `status`, need `zotero.sqlite`. It is looked up in this order: `--zotero-db`, the `ZOTERO_DB` environment variable, then `~/Zotero/zotero.sqlite`. If none is found, the document-side checks still run and the broken-link check is skipped.

## Usage

Write commands are dry runs until `--apply` is given:

```bash
zotdocx heal     manuscript.docx            # print what would change
zotdocx heal     manuscript.docx --apply    # write, original backed up as *.bak_<timestamp>
zotdocx lift     manuscript.docx --apply --out new.docx
```

Exit code is 1 when `status` finds a problem, 0 otherwise, and 2 for usage or file errors.

## Scope

- Only `word/document.xml` is replaced; every other part of the package is preserved byte for byte.
- Numbers in table cells, captions and notes stay plain text; `renumber` syncs the digits and never turns them into fields.
- Caption, note and bibliography headings are recognised in both Chinese (图 / 表 / 注 / 参考文献) and English (Table / Figure / Note / References).
- The Zotero database is opened read-only, from a temporary copy.
- No wording changes, no layout, no conversion to a final plain-text manuscript.

## Limitations

- Numeric CSL styles only. Author–date styles have no numbers to reorder.
- Verified on Windows with Word only.
- Citations split across several runs are reported, not lifted.
- `repair` matches by item key or exact title; anything else is reported, never guessed.
- `patch` rewrites `integration.js` inside Zotero's `omni.ja`. It needs write access to the Zotero directory, and it stops without touching anything if `setText` is not where it expects.
- `patch` also flattens body citation numbers, because it drops the `\super` control word. The Word-side macro in [docs/word-superscript.md](docs/word-superscript.md) puts the superscript back; `status` reports how many citation fields still lack it.

## Tests

```bash
python tests/run_all.py
```

Tests run against synthetic documents built in the test process, in Chinese and English. No real manuscript or library content is included. The same suite runs on GitHub Actions for Python 3.9, 3.11 and 3.13.

## Advanced: Zotero integration patch

If Zotero reports **Cannot delete range** and citation fields keep breaking, the cause is on the Zotero side, not in the document:

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto --apply
```

`patch` backs up `omni.ja`, rewrites the `integration.js` inside it, and verifies the rebuilt package before replacing the original. The snippet it adds is this project's own MIT JavaScript; no Zotero code is shipped. Details, the superscript trade-off and the manual fallback are in [docs/integration-patch.md](docs/integration-patch.md). It modifies Zotero rather than the document, and a Zotero update overwrites it.

Because the patched write path is plain text, body citation numbers come out flat. The Word-side macro in [docs/word-superscript.md](docs/word-superscript.md) sets them back to superscript, and keeps them there while you refresh. `zotdocx status` tells you where the document stands:

```
上标   数字制引注 32 个：整条上标 32 · 整条非上标 0 · 域内混排 0
```

## License

MIT, see [LICENSE](LICENSE).
