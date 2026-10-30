# -*- coding: utf-8 -*-
"""生成测试用的**合成** docx（不含任何真实论文或文献库内容）。

结构：
  段0 正文，含一个单条目引注域 [1]
  段1 正文，含一个单条目引注域 [2]
  段2 表格（单元格里是纯文本 [3]）
  段3 表注（注：… [3]）
  段4 图题（图1 …）
  段5 参考文献标题
  段6 书目域 + 一条纯文本条目
"""
import os
import zipfile

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

FIELD = (
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> ADDIN ZOTERO_ITEM CSL_CITATION {json} </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>{disp}</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
)

CITE = (
    '{{"citationID":"{cid}","properties":{{"plainCitation":"{disp}",'
    '"formattedCitation":"\\\\super {disp}\\\\nosupersub{{}}","noteIndex":0}},'
    '"citationItems":[{{"id":{iid},"uris":["http://zotero.org/users/0/items/{key}"],'
    '"itemData":{{"id":{iid},"type":"article-journal","title":"Fixture {iid}"}}}}],'
    '"schema":"https://github.com/citation-style-language/schema/raw/master/csl-citation.json"}}'
)

BIBL = (
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> ADDIN ZOTERO_BIBL {}</w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>[1] Fixture A. 2020.</w:t></w:r>'
    '<w:r><w:t>[2] Fixture B. 2021.</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
)


def cite(disp, iid, key):
    return FIELD.format(json=CITE.format(cid='c%d' % iid, disp=disp, iid=iid, key=key), disp=disp)


def document(swapped=False, plain_body=False):
    """swapped=True：两个域的显示号故意对调，用来测 renumber 的纠错与纯文本同步。
    plain_body=True：再加两段正文纯文本引用，用来测 lift。"""
    d1, d2 = ('[2]', '[1]') if swapped else ('[1]', '[2]')
    table_n, note_n, cap_n = ('[2]', '[1]', '[1]') if swapped else ('[3]', '[3]', '[3]')
    extra = ''
    if plain_body:
        extra = (
            '<w:p><w:r><w:t>纯文本引用段</w:t></w:r>'
            '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>[1]</w:t></w:r>'
            '<w:r><w:t>结束。</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>纯文本多引用段</w:t></w:r>'
            '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>[1,2]</w:t></w:r>'
            '<w:r><w:t>结束。</w:t></w:r></w:p>'
        )
    body = (
        '<w:p><w:r><w:t>合成段落一，引用</w:t></w:r>' + cite(d1, 101, 'AAAAAAA1') +
        '</w:p>'
        '<w:p><w:r><w:t>合成段落二，引用</w:t></w:r>' + cite(d2, 102, 'BBBBBBB2') +
        '<w:r><w:t>。</w:t></w:r></w:p>'
        + extra +
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>%s</w:t></w:r></w:p></w:tc></w:tr></w:tbl>' % table_n +
        '<w:p><w:r><w:t>注：表中 %s 为纯文本，不上宏。</w:t></w:r></w:p>' % note_n +
        '<w:p><w:r><w:t>图1 合成图题 %s</w:t></w:r></w:p>' % cap_n +
        '<w:p><w:r><w:t>参考文献</w:t></w:r></w:p>'
        '<w:p>' + BIBL + '</w:p>'
    )
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="%s"><w:body>%s<w:sectPr/></w:body></w:document>' % (W, body))


CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)


def build(path, swapped=False, plain_body=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('word/document.xml', document(swapped, plain_body))
    return path


if __name__ == '__main__':
    import sys
    print(build(sys.argv[1] if len(sys.argv) > 1 else 'fixtures/synthetic.docx'))
