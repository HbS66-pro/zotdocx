# -*- coding: utf-8 -*-
"""上标体检的回归测试（全用合成 docx）。

只看 ZOTERO_ITEM 的域结果 run 有没有 <w:vertAlign w:val="superscript"/>：
  1) 基线：两个数字制引注都是整条上标；
  2) 剥掉 vertAlign：两个都变成整条非上标；
  3) 一个域里补一个普通 run：域内混排。
书目域里的文字不参与统计。
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from make_fixture import build                     # noqa: E402
from zotdocx.analyze import Document               # noqa: E402
from zotdocx.cli import main                       # noqa: E402
from zotdocx.docxfile import DOC, Docx             # noqa: E402

SUP = '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
FIRST_DISPLAY = '<w:t>[1]</w:t></w:r>'


def load(path):
    with Docx(path) as z:
        return z.text(DOC)


def summary(xml):
    return Document(xml.encode('utf-8')).sup_summary()


def main_():
    os.makedirs(os.path.join(HERE, 'fixtures'), exist_ok=True)
    base = build(os.path.join(HERE, 'fixtures', 'synthetic.docx'))
    xml = load(base)

    s = summary(xml)
    print('基线        (引注, 上标, 非上标, 混排) =', s)
    assert s == (2, 2, 0, 0), '基线应当是两个整条上标'

    stripped = xml.replace(SUP, '')
    assert stripped != xml
    s2 = summary(stripped)
    print('剥掉 vertAlign =', s2)
    assert s2 == (2, 0, 2, 0), '剥掉后应当是两个整条非上标'

    # 第一个域的显示区后面再补一个普通 run → 同一个域里一个有上标一个没有
    assert xml.count(FIRST_DISPLAY) == 1
    mixed = xml.replace(FIRST_DISPLAY,
                        FIRST_DISPLAY + '<w:r><w:t>,</w:t></w:r>', 1)
    s3 = summary(mixed)
    print('域内混排      =', s3)
    assert s3 == (2, 1, 0, 1), '第一个域应当算混排'

    # ---- 命令行侧：人读输出与 --json 都要带上标这一项 ----
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(['status', base])
    out = buf.getvalue()
    assert '上标   数字制引注 2 个：整条上标 2' in out, out
    assert '没有上标' not in out, '基线不该提示没有上标'
    print('status 文本：含上标行')

    buf = io.StringIO()
    with redirect_stdout(buf):
        main(['status', base, '--json'])
    data = json.loads(buf.getvalue())
    assert data['superscript'] == {'numeric': 2, 'all': 2, 'none': 0,
                                   'mixed': 0}, data['superscript']
    print('status --json：superscript =', data['superscript'])

    # ---- 去掉上标后应当出现那条提示 ----
    plain = os.path.join(HERE, 'fixtures', 'synthetic_plain_sup.docx')
    with Docx(base) as z:
        z.save_as(plain, stripped)
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(['status', plain])
    out = buf.getvalue()
    assert '整条非上标 2' in out and 'Word 宏' in out, out
    print('去上标后：提示行出现')

    print('PASS')


if __name__ == '__main__':
    main_()
