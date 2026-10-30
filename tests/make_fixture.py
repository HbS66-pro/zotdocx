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


LABELS = {
    'zh': {
        'body1': '合成段落一，引用',
        'body2': '合成段落二，引用',
        'plain1': '纯文本引用段',
        'plain2': '纯文本多引用段',
        'end': '结束。',
        'note': '注：表中 %s 为纯文本，不上宏。',
        'caption': '图1 合成图题 %s',
        'biblio': '参考文献',
    },
    'en': {
        'body1': 'Synthetic paragraph one, cite ',
        'body2': 'Synthetic paragraph two, cite ',
        'plain1': 'Plain-text citation ',
        'plain2': 'Multiple plain-text citations ',
        'end': '.',
        'note': 'Note: %s in the table stays plain text.',
        'caption': 'Table 1 Synthetic caption %s.',
        'fig': 'Figure 2 Synthetic caption %s.',
        'biblio': 'References',
    },
}


def document(swapped=False, plain_body=False, lang='zh'):
    """swapped=True：两个域的显示号故意对调，用来测 renumber 的纠错与纯文本同步。
    plain_body=True：再加两段正文纯文本引用，用来测 lift。
    lang='en'：图题、表注、参考文献标题换成英文写法。"""
    L = LABELS[lang]
    d1, d2 = ('[2]', '[1]') if swapped else ('[1]', '[2]')
    table_n, note_n, cap_n = ('[2]', '[1]', '[1]') if swapped else ('[3]', '[3]', '[3]')
    extra = ''
    if plain_body:
        extra = (
            '<w:p><w:r><w:t>%s</w:t></w:r>' % L['plain1'] +
            '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>[1]</w:t></w:r>'
            '<w:r><w:t>%s</w:t></w:r></w:p>' % L['end'] +
            '<w:p><w:r><w:t>%s</w:t></w:r>' % L['plain2'] +
            '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>[1,2]</w:t></w:r>'
            '<w:r><w:t>%s</w:t></w:r></w:p>' % L['end']
        )
    caps = '<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % (L['caption'] % cap_n)
    if L.get('fig'):
        caps += '<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % (L['fig'] % cap_n)
    body = (
        '<w:p><w:r><w:t>%s</w:t></w:r>' % L['body1'] + cite(d1, 101, 'AAAAAAA1') +
        '</w:p>'
        '<w:p><w:r><w:t>%s</w:t></w:r>' % L['body2'] + cite(d2, 102, 'BBBBBBB2') +
        '<w:r><w:t>%s</w:t></w:r></w:p>' % L['end']
        + extra +
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>%s</w:t></w:r></w:p></w:tc></w:tr></w:tbl>' % table_n +
        '<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % (L['note'] % note_n) +
        caps +
        '<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % L['biblio'] +
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


def build(path, swapped=False, plain_body=False, lang='zh'):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('word/document.xml', document(swapped, plain_body, lang))
    return path


if __name__ == '__main__':
    import sys
    print(build(sys.argv[1] if len(sys.argv) > 1 else 'fixtures/synthetic.docx'))
