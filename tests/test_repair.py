# -*- coding: utf-8 -*-
"""repair 的回归测试（合成 docx + 假库，不接触真实 zotero.sqlite）。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lxml import etree                       # noqa: E402
from make_fixture import build               # noqa: E402
from zotdocx.analyze import Document         # noqa: E402
from zotdocx.docxfile import Docx, DOC       # noqa: E402
from zotdocx.repair import repair_xml        # noqa: E402


class StubLib:
    ids = {101, 102}
    key_to_id = {'AAAAAAA1': 101, 'BBBBBBB2': 102}
    titles = {101: 'Fixture 101', 102: 'Fixture 102'}

    def has(self, i):
        try:
            return int(i) in self.ids
        except (TypeError, ValueError):
            return False

    def id_of_key(self, key):
        return self.key_to_id.get(key)

    def key_of(self, i):
        for k, v in self.key_to_id.items():
            if v == i:
                return k
        return None

    def find_by_title(self, t):
        return [i for i, s in self.titles.items() if s == t]


def one(xml):
    with Docx(build(os.path.join(HERE, 'fixtures', 'synthetic.docx'))) as z:
        return z.text(DOC)


def main():
    base = one(None)
    lib = StubLib()

    # 情形 1：id 不存在，但 uris 里的 key 在库里 → 按 key 重连
    bad_key = base.replace('"id":101,"uris"', '"id":999,"uris"', 1)
    xml1, rep1 = repair_xml(bad_key, lib)
    etree.fromstring(xml1.encode('utf-8'))
    d1 = Document(xml1.encode('utf-8'))
    print('情形1 重连', rep1['relinked'], '不可修', rep1['unrecoverable'])
    assert rep1['relinked'] == [(999, 101, 'key')]
    assert d1.items()[0].ids == [101]

    # 情形 2：key 也不认识，但题名唯一命中 → 按题名重连，并把 uris 改对
    xml2 = base.replace('"id":101,"uris":["http://zotero.org/users/0/items/AAAAAAA1"]',
                        '"id":999,"uris":["http://zotero.org/users/0/items/ZZZZZZZZ"]', 1)
    xml2 = xml2.replace('"itemData":{"id":101', '"itemData":{"id":999', 1)
    xml3, rep2 = repair_xml(xml2, lib)
    d2 = Document(xml3.encode('utf-8'))
    print('情形2 重连', rep2['relinked'], '不可修', rep2['unrecoverable'])
    assert rep2['relinked'] == [(999, 101, 'title')]
    it = d2.items()[0].data['citationItems'][0]
    assert it['id'] == 101 and it['uris'][0].endswith('AAAAAAA1')
    assert it['itemData']['id'] == 101

    # 情形 3：key 与题名都认不出 → 不动，报不可修
    xml4 = base.replace('"id":101,"uris":["http://zotero.org/users/0/items/AAAAAAA1"]',
                        '"id":999,"uris":["http://zotero.org/users/0/items/ZZZZZZZZ"]', 1)
    xml4 = xml4.replace('"title":"Fixture 101"', '"title":"不存在的题名"', 1)
    xml5, rep3 = repair_xml(xml4, lib)
    print('情形3 重连', rep3['relinked'], '不可修', rep3['unrecoverable'])
    assert not rep3['relinked'] and rep3['unrecoverable']
    assert xml5 == xml4, '不能修的域被改动了'

    # 正常稿：一个都不动
    xml6, rep4 = repair_xml(base, lib)
    print('正常稿：重连', rep4['relinked'], '正常条目', rep4['ok'])
    assert xml6 == base and rep4['ok'] == 2
    print('PASS')


if __name__ == '__main__':
    main()
