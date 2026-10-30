# -*- coding: utf-8 -*-
"""patch：给 Zotero 的 app/omni.ja 打/查本机修复补丁。

本仓库**不携带** Zotero 的任何代码，也不内置补丁内容：
  * 查：读包里的 integration.js，算哈希、看标记；
  * 打：用用户自己提供的已修补 integration.js 替换那一个条目，其余逐字节保留。
"""
import datetime
import hashlib
import os
import re
import shutil
import zipfile

INNER = 'chrome/content/zotero/xpcom/integration.js'
MARKER = 'zoteroPlainCitationFix'
SNIPPET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'plaintext-fix.js')

# setText 的两种写法：属性赋值 `setText: function (text) {` 和方法简写 `setText(text) {`
ANCHORS = (
    re.compile(r'setText\s*:\s*function\s*\(([^)]*)\)\s*\{'),
    re.compile(r'(?<![.\w])setText\s*\(([^)]*)\)\s*\{'),
)


def omni_path(zotero_dir):
    """兼容三种给法：Zotero 程序根目录、它下面的 app 目录、直接给 omni.ja。"""
    p = os.path.join(zotero_dir, 'app', 'omni.ja')
    if os.path.isfile(p):
        return p
    p2 = os.path.join(zotero_dir, 'omni.ja')
    if os.path.isfile(p2):
        return p2
    return p


def sha(b, n=16):
    return hashlib.sha256(b).hexdigest().upper()[:n]


def read_inner(omni):
    """读出包里的 integration.js 原文。"""
    with zipfile.ZipFile(omni) as z:
        if INNER not in z.namelist():
            raise KeyError('包内找不到 %s' % INNER)
        return z.read(INNER)


def snippet_body():
    """片段本体：从 function 到文件末尾，头部注释不带走。"""
    with open(SNIPPET, 'r', encoding='utf-8') as f:
        text = f.read()
    return text[text.index('function _zoteroPlainCitationFix'):].rstrip() + '\n'


def auto_patch(src):
    """在 integration.js 原文里插入调用、追加片段，返回新内容；失败抛 ValueError。"""
    text = src.decode('utf-8')
    if MARKER in text:
        raise ValueError('这份 integration.js 里已经含有补丁标记，可能已经打过')
    hit = None
    for pat in ANCHORS:
        hit = pat.search(text)
        if hit:
            break
    if not hit:
        raise ValueError('找不到 setText 的实现，无法自动插入；请按 docs/integration-patch.md 手工打')
    arg = hit.group(1).split(',')[0].strip()
    if not arg:
        raise ValueError('setText 没有参数，不确定该改写哪一行，已放弃')
    call = '\n  %s = _zoteroPlainCitationFix(%s);' % (arg, arg)
    out = text[:hit.end()] + call + text[hit.end():]
    out = out.rstrip() + '\n\n' + snippet_body()
    if MARKER not in out or '_zoteroPlainCitationFix(' not in out:
        raise ValueError('改写结果自检未通过，已放弃（未改动任何文件）')
    return out.encode('utf-8')


def inspect(omni, marker):
    if not os.path.isfile(omni):
        raise FileNotFoundError(omni)
    with zipfile.ZipFile(omni) as z:
        if INNER not in z.namelist():
            raise KeyError('包内找不到 %s' % INNER)
        inner = z.read(INNER)
        n = len(z.namelist())
    return {'omni': omni, 'size': os.path.getsize(omni), 'entries': n,
            'inner_size': len(inner), 'inner_sha': sha(inner),
            'has_marker': marker.encode() in inner}


def apply_patch(omni, patched_bytes, marker):
    """把 patched_bytes 写进 omni 的 integration.js；返回备份路径。"""
    if marker.encode() not in patched_bytes:
        raise ValueError('提供的文件里没有补丁标记 %r，拒绝写入' % marker)
    tmp = omni + '.new'
    with zipfile.ZipFile(omni) as zin:
        infos = zin.infolist()
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for it in infos:
                data = patched_bytes if it.filename == INNER else zin.read(it.filename)
                zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
                zi.compress_type = it.compress_type
                zi.external_attr = it.external_attr
                zi.internal_attr = it.internal_attr
                zi.create_system = it.create_system
                zout.writestr(zi, data)

    with zipfile.ZipFile(tmp) as z:              # 自检：不损坏、条目数不变、目标内容对
        bad = z.testzip()
        n = len(z.namelist())
        inner = z.read(INNER)
    if bad is not None or n != len(infos) or inner != patched_bytes:
        os.remove(tmp)
        raise RuntimeError('重建包自检未通过，已放弃（未改动任何文件）')

    try:
        f = open(omni, 'r+b')
        f.close()
    except PermissionError:
        os.remove(tmp)
        raise RuntimeError('omni.ja 被占用：请先完全退出 Zotero 再重试')

    bak = '%s.bak_%s' % (omni, datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(omni, bak)
    os.replace(tmp, omni)
    return bak
