# -*- coding: utf-8 -*-
"""总的自查脚本：不变量 + 幂等 + 只改 document.xml。

对每个写命令，在合成稿副本上跑：
  1. 只有 word/document.xml 变了，其余部件逐字节一致；
  2. 连跑两次，第二次 0 改动（幂等）；
  3. 跑完再体检，状态符合预期。
"""
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from make_fixture import build                       # noqa: E402
from zotdocx.analyze import BODY, Document           # noqa: E402
from zotdocx.docxfile import DOC, Docx               # noqa: E402
from zotdocx.heal import heal_xml                    # noqa: E402
from zotdocx.lift import lift_xml                    # noqa: E402
from zotdocx.renumber import renumber_xml            # noqa: E402

FIX = os.path.join(HERE, 'fixtures')
DOCX = DOC


def parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def run(fn, src, dst, **kw):
    with Docx(src) as z:
        xml = z.text(DOCX)
        new, rep = fn(xml, **kw)
        z.save_as(dst, new)
    return rep


def only_xml_changed(a, b):
    pa, pb = parts(a), parts(b)
    assert set(pa) == set(pb), '部件列表变了'
    bad = [n for n in pa if n != DOCX and pa[n] != pb[n]]
    return bad


def main():
    ok = True
    base = build(os.path.join(FIX, 'audit_base.docx'), plain_body=True)

    # ---- heal ----
    src = base
    d1 = os.path.join(FIX, 'audit_heal1.docx')
    rep = run(heal_xml, src, d1)
    bad = only_xml_changed(src, d1)
    print(f'heal     改动={rep["moved"]}+{rep["synced"]}  非 document.xml 变动={bad}')
    ok &= not bad
    rep2 = run(heal_xml, d1, os.path.join(FIX, 'audit_heal2.docx'))
    print(f'heal 二次 改动={rep2["moved"]}+{rep2["synced"]}（应为 0+0）')
    ok &= (rep2['moved'] == 0 and rep2['synced'] == 0)

    # ---- lift ----
    d3 = os.path.join(FIX, 'audit_lift1.docx')
    rep3 = run(lift_xml, src, d3)
    bad = only_xml_changed(src, d3)
    print(f'lift     上宏={len(rep3["lifted"])} 跳过={len(rep3["skipped"])}  非 document.xml 变动={bad}')
    ok &= not bad and len(rep3['lifted']) == 2
    rep4 = run(lift_xml, d3, os.path.join(FIX, 'audit_lift2.docx'))
    print(f'lift 二次 上宏={len(rep4["lifted"])}（应为 0）')
    ok &= len(rep4['lifted']) == 0

    # ---- renumber（在上宏后的稿子上） ----
    d5 = os.path.join(FIX, 'audit_renum1.docx')
    rep5 = run(renumber_xml, d3, d5)
    bad = only_xml_changed(d3, d5)
    print(f'renumber 域改动={rep5["fields"]} 纯文本={rep5["plain"]}  非 document.xml 变动={bad}')
    ok &= not bad
    rep6 = run(renumber_xml, d5, os.path.join(FIX, 'audit_renum2.docx'))
    print(f'renumber 二次 域改动={rep6["fields"]} 纯文本={rep6["plain"]}（应为 0）')
    ok &= (rep6['fields'] == 0 and not rep6['plain'])

    # ---- 上宏后的终态 ----
    with Docx(d5) as z:
        d = Document(z.text(DOCX).encode('utf-8'))
    body_plain = [p.text for p in d.plains if p.ctx == BODY]
    cross = sum(1 for f in d.items() if f.cross)
    print(f'终态     正文纯文本={body_plain} 跨段引注={cross} 域={len(d.fields)}')
    ok &= not body_plain and cross == 0

    print('AUDIT', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
