# -*- coding: utf-8 -*-
"""heal 的回归测试（全用合成 docx，不含真实论文或库数据）。

1) 生成合成基线；
2) 人为制造「域尾掉进下一段」：把段末那个域的 </w:r> 搬到下一段开头；
3) 跑 heal_xml；
4) 断言：跨段域 1 → 0，域数不变，逐段文字与基线一致，XML 合法。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lxml import etree                        # noqa: E402
from make_fixture import build                # noqa: E402
from zotdocx.analyze import Document          # noqa: E402
from zotdocx.docxfile import Docx, DOC       # noqa: E402
from zotdocx.heal import END, RUN_OPEN, field_spans, heal_xml  # noqa: E402

PARA = re.compile(r'<w:p(?: [^>]*)?>')
PPR = re.compile(r'<w:pPr>.*?</w:pPr>', re.S)


def inject(xml):
    """把第一个段的域的 end run 搬到下一段开头。"""
    spans = [(a, b) for a, b in field_spans(xml) if xml[b:b + 6] == '</w:p>']
    assert spans, '没有段末的域可注入'
    rs, re_ = spans[0]
    b = xml.rindex(END, rs, re_)
    rs2 = [m.start() for m in RUN_OPEN.finditer(xml, 0, b)][-1]
    run = xml[rs2:re_]
    rest = xml[:rs2] + xml[re_:]
    close = rest.index('</w:p>', rs2)
    m = PARA.search(rest, close)
    m2 = PPR.match(rest, m.end())
    ins = m2.end() if m2 else m.end()
    return rest[:ins] + run + rest[ins:]


def load(path):
    with Docx(path) as z:
        return z.text(DOC)


def texts(xml):
    return Document(xml.encode('utf-8')).para_text


def main():
    os.makedirs(os.path.join(HERE, 'fixtures'), exist_ok=True)
    base = build(os.path.join(HERE, 'fixtures', 'synthetic.docx'))
    xml0 = load(base)
    n_fields0 = len(Document(xml0.encode('utf-8')).fields)

    xml1 = inject(xml0)
    d1 = Document(xml1.encode('utf-8'))
    cross1 = sum(1 for f in d1.items() if f.cross)
    print(f'注入后：域 {len(d1.fields)}，跨段引注 {cross1}')
    assert cross1 >= 1

    xml2, rep = heal_xml(xml1)
    etree.fromstring(xml2.encode('utf-8'))
    d2 = Document(xml2.encode('utf-8'))
    cross2 = sum(1 for f in d2.items() if f.cross)
    print(f'heal：收回域尾 {rep["moved"]}，同步编号 {rep["synced"]}，问题 {rep["problems"]}')
    print(f'修复后：域 {len(d2.fields)}，跨段引注 {cross2}')
    assert cross2 == 0, 'heal 没修干净'
    assert len(d2.fields) == n_fields0, '域数变了'

    t0, t2 = texts(xml0), texts(xml2)
    assert len(t0) == len(t2), f'段落数变了 {len(t0)} -> {len(t2)}'
    bad = [i for i, (a, b) in enumerate(zip(t0, t2)) if a != b]
    if bad:
        for i in bad[:5]:
            print(f'  段{i}: 基线 {t0[i]!r}')
            print(f'        修复 {t2[i]!r}')
        raise AssertionError('修复改动了正文文字')
    print('段落文字：逐段一致')

    # ---- 第二项：域内编号与显示不一致 ----
    xml3 = xml0.replace('"plainCitation":"[1]"', '"plainCitation":"[9]"', 1)
    assert xml3 != xml0, '没造出编号不一致的样本'
    xml4, rep4 = heal_xml(xml3)
    d4 = Document(xml4.encode('utf-8'))
    pc = d4.items()[0].plain_citation
    print(f'编号同步：收回域尾 {rep4["moved"]}，同步 {rep4["synced"]}，修后 plainCitation={pc!r}')
    assert rep4['synced'] == 1 and pc == '[1]', '编号没同步回来'

    print('PASS')


if __name__ == '__main__':
    main()
