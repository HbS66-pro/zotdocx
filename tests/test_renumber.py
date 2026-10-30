# -*- coding: utf-8 -*-
"""renumber 的回归测试（合成 docx）。

构造：两个单条目域的显示号故意对调（[2] / [1]），表格、表注、图题里各放一个
纯文本编号，参考文献表里放两条条目序号。

断言：
  * 正文域按首次被引顺序改回 [1] / [2]；
  * 域内 plainCitation 同步；
  * 表格 / 表注 / 图题里的纯文本编号按映射同步；
  * 参考文献表里的条目序号**不动**。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lxml import etree                    # noqa: E402
from make_fixture import build            # noqa: E402
from zotdocx.analyze import Document, TABLE, NOTE, CAPTION, BIBLIO  # noqa: E402
from zotdocx.docxfile import Docx, DOC   # noqa: E402
from zotdocx.renumber import renumber_xml  # noqa: E402


def main():
    path = build(os.path.join(HERE, 'fixtures', 'synthetic_swapped.docx'), swapped=True)
    with Docx(path) as z:
        xml0 = z.text(DOC)

    d0 = Document(xml0.encode('utf-8'))
    print('改前：域显示', [f.display for f in d0.items()])
    print('      纯文本', [(p.text, p.ctx) for p in d0.plains])
    assert [f.display for f in d0.items()] == ['[2]', '[1]']

    xml1, rep = renumber_xml(xml0)
    etree.fromstring(xml1.encode('utf-8'))
    d1 = Document(xml1.encode('utf-8'))

    print('改后：域显示', [f.display for f in d1.items()])
    print('      纯文本', [(p.text, p.ctx) for p in d1.plains])
    print('      映射', rep['mapping'], '改动域', rep['fields'], '纯文本', rep['plain'])

    assert [f.display for f in d1.items()] == ['[1]', '[2]'], '正文编号没纠正'
    assert [f.plain_citation for f in d1.items()] == ['[1]', '[2]'], 'plainCitation 没同步'
    assert rep['mapping'] == {2: 1, 1: 2}, f'映射不对：{rep["mapping"]}'

    by_ctx = {}
    for p in d1.plains:
        by_ctx.setdefault(p.ctx, []).append(p.text)
    print('      按语境', {k: v for k, v in by_ctx.items()})
    assert not by_ctx.get(BIBLIO), '文献表编号被改了'
    assert '[1] Fixture A' in xml1 and '[2] Fixture B' in xml1, '书目域里的条目序号被改了'
    # 表格原 [2] → [1]；表注原 [1] → [2]；图题原 [1] → [2]
    assert by_ctx.get(TABLE) == ['[1]'], f'表格没同步：{by_ctx.get(TABLE)}'
    assert by_ctx.get(NOTE) == ['[2]'], f'表注没同步：{by_ctx.get(NOTE)}'
    assert by_ctx.get(CAPTION) == ['[2]'], f'图题没同步：{by_ctx.get(CAPTION)}'
    assert rep['fields'] == 2

    print('PASS')


if __name__ == '__main__':
    main()
