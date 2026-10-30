# -*- coding: utf-8 -*-
"""demo 命令：生成的合成文档可读、可修；干跑不落盘，--apply 后能过复检。

断言：
  * demo 写出文档并返回 0，同一路径二次运行被拒绝（返回 2）；
  * 对生成的文档 status 返回 1（故意留了编号不符）；
  * renumber 干跑不改文件字节；
  * renumber --apply 备份原文件，之后 status 返回 0。
"""
import hashlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from zotdocx.analyze import Document                            # noqa: E402
from zotdocx.cli import main                                   # noqa: E402
from zotdocx.docxfile import DOC, Docx                         # noqa: E402


def digest(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def run():
    d = tempfile.mkdtemp(prefix='zotdocx_demo_')
    out = os.path.join(d, 'demo.docx')

    assert main(['demo', '--out', out]) == 0, 'demo 未返回 0'
    assert os.path.isfile(out), 'demo 没有生成文档'
    assert main(['demo', '--out', out]) == 2, '已存在的文件应被拒绝覆盖'

    with Docx(out) as z:
        doc = Document(z.text(DOC).encode('utf-8'))
    assert len(doc.items()) == 2 and len(doc.fields) == 3, '演示文档的域结构不对'

    assert main(['status', out]) == 1, '故意留着的编号不符应让 status 返回 1'

    before = digest(out)
    assert main(['renumber', out]) == 0, '干跑应返回 0'
    assert digest(out) == before, '干跑改动了文件'

    assert main(['renumber', out, '--apply']) == 0, '写入应返回 0'
    assert digest(out) != before, '写入后文件没变化'
    baks = [n for n in os.listdir(d) if '.bak_' in n]
    assert baks, '没有生成备份'

    assert main(['status', out]) == 0, '修完再体检应返回 0'
    print(f'演示 {out}：域 3 个，干跑不改盘，写入后复检通过')
    print('PASS')


if __name__ == '__main__':
    run()
