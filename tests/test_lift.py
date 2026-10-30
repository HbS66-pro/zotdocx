# -*- coding: utf-8 -*-
"""lift 的回归测试（合成 docx）。

构造：正文两段里各有一个纯文本引用 run（[1] 和 [1,2]），文档别处已有
对应条目的单条目活域。

断言：
  * 域数 +2（单条目一个、合并条目一个）；
  * 上宏后段落的可见文字没变；
  * 合并出来的域里 citationItems 有 2 个、position 为 0/1、id 与 uris 一一对应；
  * 表格 / 表注 / 图题里的纯文本一个都没被上宏（域数只增 2）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lxml import etree                     # noqa: E402
from make_fixture import build             # noqa: E402
from zotdocx.analyze import Document, BODY, TABLE, NOTE, CAPTION  # noqa: E402
from zotdocx.docxfile import Docx, DOC     # noqa: E402
from zotdocx.lift import lift_xml          # noqa: E402


def main():
    path = build(os.path.join(HERE, 'fixtures', 'synthetic_plain.docx'), plain_body=True)
    with Docx(path) as z:
        xml0 = z.text(DOC)

    d0 = Document(xml0.encode('utf-8'))
    plain0 = [p.text for p in d0.plains if p.ctx == BODY]
    print('改前：域', len(d0.fields), '正文纯文本', plain0)
    assert plain0 == ['[1]', '[1,2]'], plain0

    xml1, rep = lift_xml(xml0)
    etree.fromstring(xml1.encode('utf-8'))
    d1 = Document(xml1.encode('utf-8'))

    print('lift：上宏', rep['lifted'], '跳过', rep['skipped'])
    print('改后：域', len(d1.fields), '正文纯文本', [p.text for p in d1.plains if p.ctx == BODY])
    assert len(d1.fields) == len(d0.fields) + 2, '域数不对'
    assert not [p for p in d1.plains if p.ctx == BODY], '正文还有纯文本残留'
    assert [p.text for p in d1.plains if p.ctx == TABLE] == ['[3]'], '表格被误伤'
    assert [p.text for p in d1.plains if p.ctx == NOTE] == ['[3]'], '表注被误伤'
    assert [p.text for p in d1.plains if p.ctx == CAPTION] == ['[3]'], '图题被误伤'

    # 可见文字不变
    assert d0.para_text == d1.para_text, '上宏改了可见文字'

    # 合并出来的域
    multi = [f for f in d1.items() if len(f.ids) == 2]
    assert len(multi) == 1, f'应该只有一个双条目域，实际 {len(multi)}'
    m = multi[0]
    items = m.data['citationItems']
    print('双条目域：ids', m.ids, 'position', [i.get('position') for i in items],
          'display', m.display)
    assert [i.get('position') for i in items] == [0, 1]
    for it in items:
        assert it['itemData']['id'] == it['id']
        assert it['uris'][0].endswith('/items/' + {101: 'AAAAAAA1', 102: 'BBBBBBB2'}[it['id']])
    assert m.display == '[1,2]'
    assert m.plain_citation == '[1,2]'

    # citationID 唯一
    ids = [f.data.get('citationID') for f in d1.items()]
    assert len(ids) == len(set(ids)), 'citationID 重复'
    print('PASS')


if __name__ == '__main__':
    main()
