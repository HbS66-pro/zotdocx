# -*- coding: utf-8 -*-
"""英文文档的段落语境识别与 lift 边界（全用合成稿）。

断言：
  * Table 1 / Figure 2 图题表题、Note: 表注、References 标题都能认出来；
  * lift 只动正文里的纯文本引用，图题、表注、表格单元格、参考文献表一律不碰；
  * 上宏前后每段可见文字不变。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from make_fixture import build                                        # noqa: E402
from zotdocx.analyze import (BIBLIO, BODY, CAPTION, NOTE, TABLE,      # noqa: E402
                             Document)
from zotdocx.docxfile import DOC, Docx                                # noqa: E402
from zotdocx.lift import lift_xml                                     # noqa: E402


def main():
    path = os.path.join(HERE, 'fixtures', 'en.docx')
    build(path, plain_body=True, lang='en')
    with Docx(path) as z:
        xml = z.text(DOC)
    doc = Document(xml.encode('utf-8'))

    want = {
        'Synthetic paragraph one': BODY,
        'Table 1': CAPTION,
        'Figure 2': CAPTION,
        'Note:': NOTE,
        'References': BIBLIO,
    }
    seen = {}
    for i, t in enumerate(doc.para_text):
        for key in want:
            if t.startswith(key):
                seen[key] = doc.para_ctx[i]
    for key, ctx in want.items():
        assert seen.get(key) == ctx, f'{key!r} 判成了 {seen.get(key)!r}，应为 {ctx}'

    new_xml, rep = lift_xml(xml)
    assert len(rep['lifted']) == 2, f'只该上宏正文两处，实际 {rep["lifted"]}'
    for text, para in rep['lifted']:
        assert doc.para_ctx[para] == BODY, f'{text} 在段{para}，语境是 {doc.para_ctx[para]}'

    after = Document(new_xml.encode('utf-8'))
    assert after.para_text == doc.para_text, '上宏前后可见文字不一致'
    for i, ctx in enumerate(doc.para_ctx):
        if ctx != BODY:
            assert after.para_text[i] == doc.para_text[i]

    print(f'语境识别 {len(want)} 项通过；上宏 {len(rep["lifted"])} 处，均落在正文')
    print('PASS')


if __name__ == '__main__':
    main()
