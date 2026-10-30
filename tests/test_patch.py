# -*- coding: utf-8 -*-
"""patch 的回归测试：用合成 omni.ja（假 Zotero 包），不碰真实安装。

覆盖：
  * auto_patch 在 setText 开头插入调用、末尾追加片段，参数名跟着原文走；
  * 写回后条目不增不减，其他部件逐字节不变；
  * 已经打过的、找不到 setText 的、没有标记的输入，一律拒绝。
"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from zotdocx.patch import (INNER, MARKER, apply_patch, auto_patch,  # noqa: E402
                           inspect, omni_path, sha)

FAKE = (
    '// fake integration.js\n'
    'Zotero.Integration.TextDocument.prototype = {\n'
    '\tsetText: function (text, mode) {\n'
    '\t\tthis.text = text;\n'
    '\t\treturn mode;\n'
    '\t},\n'
    '\tother: function () { return 1; }\n'
    '};\n'
)


def make_omni(path, inner_text):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('chrome/content/moz.build', 'FILES += []')
        z.writestr(INNER, inner_text)
        z.writestr('defaults/preferences/zotero.js', 'pref("a", 1);')


def main():
    work = os.path.join(HERE, 'fixtures', 'fakezotero', 'app')
    os.makedirs(work, exist_ok=True)
    omni = omni_path(os.path.dirname(work))
    make_omni(omni, FAKE)

    st0 = inspect(omni, MARKER)
    print('打前：', st0['entries'], '条目', st0['inner_size'], 'B，标记在：', st0['has_marker'])
    assert not st0['has_marker']

    patched = auto_patch(FAKE.encode('utf-8'))
    text = patched.decode('utf-8')
    assert 'text = _zoteroPlainCitationFix(text);' in text, '没有插入调用'
    assert text.count('function _zoteroPlainCitationFix') == 1, '片段应只追加一次'
    assert '\t\tthis.text = text;' in text, '原文件内容被改坏了'
    print('auto_patch：', len(FAKE), 'B ->', len(patched), 'B')

    bak = apply_patch(omni, patched, MARKER)
    print('备份：', os.path.basename(bak), '存在：', os.path.exists(bak))

    st1 = inspect(omni, MARKER)
    print('打后：', st1['entries'], '条目', st1['inner_size'], 'B，标记在：', st1['has_marker'])
    assert st1['has_marker'] and st1['entries'] == st0['entries']
    assert st1['inner_sha'] == sha(patched)
    with zipfile.ZipFile(omni) as z:
        assert z.testzip() is None
        assert z.read('chrome/content/moz.build') == b'FILES += []', '其他部件被改动了'

    for label, blob in (('已打过', patched), ('没有 setText', b'var a = 1;\n')):
        try:
            auto_patch(blob)
            raise AssertionError('%s 的输入应该被拒绝' % label)
        except ValueError as e:
            print('拒绝（%s）：' % label, e)

    try:
        apply_patch(omni, b'no marker here', MARKER)
        raise AssertionError('应该拒绝没有标记的补丁')
    except ValueError as e:
        print('拒绝无标记输入：', e)

    print('PASS')


if __name__ == '__main__':
    main()
