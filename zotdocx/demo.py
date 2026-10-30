# -*- coding: utf-8 -*-
"""合成演示文档：`zotdocx demo` 用它一条命令跑出可见结果。

只包含假段落和假引用域，不含任何真实论文、真实文献库内容。
故意留了三处毛病，方便演示修复效果：
  * 两个引注域的显示号与首次引用顺序相反；
  * 表格、表注、图题里的编号是纯文本；
  * 正文里有一处编号没上宏。
"""
import os
import zipfile

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

_FIELD = (
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> ADDIN ZOTERO_ITEM CSL_CITATION {json} </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>{disp}</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
)

_CITE = (
    '{{"citationID":"{cid}","properties":{{"plainCitation":"{disp}",'
    '"formattedCitation":"\\\\super {disp}\\\\nosupersub{{}}","noteIndex":0}},'
    '"citationItems":[{{"id":{iid},"uris":["http://zotero.org/users/0/items/{key}"],'
    '"itemData":{{"id":{iid},"type":"article-journal","title":"Demo item {iid}"}}}}],'
    '"schema":"https://github.com/citation-style-language/schema/raw/master/csl-citation.json"}}'
)

_BIBL = (
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> ADDIN ZOTERO_BIBL {}</w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>[1] Demo item 101. 2020.</w:t></w:r>'
    '<w:r><w:t>[2] Demo item 102. 2021.</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/'
    'vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    '</Types>'
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
    'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/extended-properties" Target="docProps/app.xml"/>'
    '</Relationships>'
)

_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)

_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:styles xmlns:w="%s">'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/></w:style>'
    '</w:styles>' % W
)

_CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
    'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    '<dc:title>zotdocx demo</dc:title><dc:creator>zotdocx</dc:creator>'
    '<cp:lastModifiedBy>zotdocx</cp:lastModifiedBy>'
    '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:modified>'
    '</cp:coreProperties>'
)

_APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
    'extended-properties"><Application>zotdocx</Application></Properties>'
)


def _t(text):
    return '<w:r><w:t>%s</w:t></w:r>' % text


def _sup(text):
    return '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>%s</w:t></w:r>' % text


def _p(*runs):
    return '<w:p>%s</w:p>' % ''.join(runs)


def _cite(disp, iid, key):
    return _FIELD.format(
        json=_CITE.format(cid='c%d' % iid, disp=disp, iid=iid, key=key), disp=disp)


def document():
    body = ''.join([
        _p(_t('这份文件由 zotdocx demo 生成，只用于演示，不含任何真实文献。')),
        _p(_t('合成段落一，引用 '), _cite('[2]', 101, 'DEMO0001'), _t('。')),
        _p(_t('合成段落二，引用 '), _cite('[1]', 102, 'DEMO0002'), _t('。')),
        _p(_t('合成段落三，这里的 '), _sup('[1]'), _t(' 是纯文本，还没上宏。')),
        '<w:tbl><w:tr><w:tc>%s</w:tc></w:tr></w:tbl>' % _p(_t('[2]')),
        _p(_t('注：表中 [2] 为纯文本，不上宏。')),
        _p(_t('图1 合成图题 [1]')),
        _p(_t('参考文献')),
        _p(_BIBL),
    ])
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="%s"><w:body>%s<w:sectPr/></w:body></w:document>' % (W, body))


def build(path):
    """写出演示文档，返回路径。生成的包是完整 docx，可以直接用 Word 打开。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', _RELS)
        z.writestr('word/_rels/document.xml.rels', _DOC_RELS)
        z.writestr('word/document.xml', document())
        z.writestr('word/styles.xml', _STYLES)
        z.writestr('docProps/core.xml', _CORE)
        z.writestr('docProps/app.xml', _APP)
    return path
