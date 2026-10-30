# -*- coding: utf-8 -*-
"""patch 的回归测试：用合成 omni.ja（假 Zotero 包），不碰真实安装。"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from zotdocx.patch import INNER, apply_patch, inspect, omni_path  # noqa: E402

MARK = 'plainCitationFix'


def make_omni(path, inner_text):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('chrome/content/moz.build', 'FILES += []')
        z.writestr(INNER, inner_text)
        z.writestr('defaults/preferences/zotero.js', 'pref("a", 1);')


def main():
    work = os.path.join(HERE, 'fixtures', 'fakezotero', 'app')
    os.makedirs(work, exist_ok=True)
    omni = omni_path(os.path.dirname(work))
    make_omni(omni, 'function setText(t){ return t; }')
    patched = os.path.join(HERE, 'fixtures', 'patched_integration.js')
    with open(patched, 'w', encoding='utf-8') as f:
        f.write('function _%s(t){ return t; }\nfunction setText(t){ return _%s(t); }\n' % (MARK, MARK))

    st0 = inspect(omni, MARK)
    print('打前：', st0['entries'], '条目', st0['inner_size'], 'B，标记在：', st0['has_marker'])
    assert not st0['has_marker']

    with open(patched, 'rb') as f:
        data = f.read()
    bak = apply_patch(omni, data, MARK)
    print('备份：', os.path.basename(bak), '存在：', os.path.exists(bak))

    st1 = inspect(omni, MARK)
    print('打后：', st1['entries'], '条目', st1['inner_size'], 'B，标记在：', st1['has_marker'])
    assert st1['has_marker'] and st1['entries'] == st0['entries']
    assert st1['inner_sha'] == __import__('zotdocx.patch', fromlist=['sha']).sha(data)
    with zipfile.ZipFile(omni) as z:
        assert z.testzip() is None
        assert z.read('chrome/content/moz.build') == b'FILES += []', '其他部件被改动了'

    # 拒绝没有标记的文件
    try:
        apply_patch(omni, b'no marker here', MARK)
        raise AssertionError('应该拒绝没有标记的补丁')
    except ValueError as e:
        print('拒绝无标记输入：', e)

    print('PASS')


if __name__ == '__main__':
    main()
