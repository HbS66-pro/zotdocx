# -*- coding: utf-8 -*-
"""zotdocx 命令入口。"""
import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from collections import defaultdict, OrderedDict

from .analyze import Document, CTX_CN
from .docxfile import Docx, DOC
from .heal import heal_xml
from .renumber import renumber_xml
from .lift import lift_xml
from .library import Library
from .repair import repair_xml
from .patch import omni_path, inspect, apply_patch

__version__ = '0.1.1'


# ---------------- status ----------------
def cmd_status(args):
    with Docx(args.docx) as z:
        xml = z.text(DOC)
        names = len(z.names)
        try:
            custom = z.read('docProps/custom.xml').decode('utf-8', 'replace')
        except KeyError:
            custom = ''
    m = re.search(r'zotero\.org/styles/([^"<]+)', custom)
    style = m.group(1) if m else '未记录'
    doc = Document(xml.encode('utf-8'))
    items = doc.items()
    bibl = [f for f in doc.fields if f.kind == 'bibl']
    other = [f for f in doc.fields if f.kind == 'other']

    # 域位置分布
    by_ctx = defaultdict(int)
    for f in items:
        by_ctx[CTX_CN.get(f.ctx, f.ctx)] += 1

    # 条目与编号
    ids_seen = OrderedDict()
    per_id_nums = defaultdict(set)
    for f in items:
        for i in f.ids:
            ids_seen.setdefault(i, len(ids_seen) + 1)
        for n in f.nums:
            pass
    for f in items:
        for i in f.ids:
            if len(f.nums) == 1:
                per_id_nums[i].add(f.nums[0])

    canon = {i: k for k, i in enumerate(ids_seen, 1)}
    mismatch = 0
    multi_mismatch = 0
    for f in items:
        want = sorted(canon[i] for i in f.ids if i in canon)
        got = sorted(f.nums)
        if want != got:
            if len(f.ids) > 1:
                multi_mismatch += 1
            else:
                mismatch += 1

    multi_num_ids = [i for i, s in per_id_nums.items() if len(s) > 1]
    all_nums = sorted({n for f in items for n in f.nums})

    # 纯文本
    plain_by_ctx = defaultdict(int)
    for p in doc.plains:
        plain_by_ctx[CTX_CN.get(p.ctx, p.ctx)] += 1

    # 文献库
    lib = Library(args.zotero_db) if args.zotero_db else None
    id_kinds = defaultdict(int)
    broken = {}
    if lib:
        for i in ids_seen:
            k = lib.classify(i)
            id_kinds[k] += 1
            if k not in ('存在', '会话号(可解析)'):
                broken.setdefault(k, []).append(i)

    # ---------------- 输出 ----------------
    base = os.path.basename(args.docx)
    print(f'{base}')
    print(f'  部件 {names} 个；document.xml {len(xml.encode("utf-8")) / 1048576:.2f} MB')
    print(f'  样式 {style}')
    print()
    print(f'域      {len(doc.fields)} = 引注 {len(items)} + 书目 {len(bibl)} + 其他 {len(other)}')
    print(f'        跨段落：引注 {sum(1 for f in items if f.cross)} · 书目 {sum(1 for f in bibl if f.cross)}')
    print('        位置：' + ' · '.join(f'{k} {v}' for k, v in by_ctx.items()))
    print(f'条目    {len(ids_seen)} 个' + (
        '（' + ' · '.join(f'{k} {v}' for k, v in id_kinds.items()) + '）' if lib else ''))
    print(f'编号   显示 {all_nums[0] if all_nums else 0}–{all_nums[-1] if all_nums else 0}'
          f'；同条目多编号 {len(multi_num_ids)}；单条目编号不符 {mismatch}；多条目编号不符 {multi_mismatch}')
    print('纯文本 ' + ' · '.join(f'{k} {v}' for k, v in plain_by_ctx.items()))

    if broken:
        print()
        print('断链：')
        for k, v in broken.items():
            print(f'  {k} {len(v)} 个：{v[:10]}')

    if args.show_text:
        print()
        print('纯文本引用明细：')
        for p in doc.plains:
            print(f'  段{p.p} [{CTX_CN.get(p.ctx, p.ctx)}] {p.text}  {doc.para_text[p.p][:50]}')
        if multi_num_ids:
            print('同条目多编号的 id：', multi_num_ids[:20])

    if args.json:
        print(json.dumps({
            'file': base,
            'fields': {'total': len(doc.fields), 'item': len(items),
                       'bibl': len(bibl), 'other': len(other)},
            'cross_item': sum(1 for f in items if f.cross),
            'items': len(ids_seen),
            'plain': dict(plain_by_ctx),
            'broken': {k: [str(x) for x in v] for k, v in broken.items()},
        }, ensure_ascii=False, indent=2))

    bad = bool(broken) or mismatch > 0 or any(f.cross for f in items)
    return 1 if bad else 0


def _validate(xml):
    from lxml import etree
    etree.fromstring(xml.encode('utf-8'))


def cmd_heal(args):
    with Docx(args.docx) as z:
        xml = z.text(DOC)
    before = Document(xml.encode('utf-8'))
    new_xml, rep = heal_xml(xml)
    _validate(new_xml)
    after = Document(new_xml.encode('utf-8'))

    print(os.path.basename(args.docx))
    print(f'  跨段引注域：{sum(1 for f in before.items() if f.cross)} → '
          f'{sum(1 for f in after.items() if f.cross)}')
    print(f'  域内编号不一致：{before_problems(before)} → {after_problems(after)}')
    print(f'  收回域尾 {rep["moved"]} 个；同步编号 {rep["synced"]} 处；跳过书目域 {rep["skipped_bibl"]}')
    for pc, disp in rep.get('pairs', []):
        print(f'    域内 {pc!r} → 显示 {disp!r}')
    for p in rep['problems']:
        print(f'    ! {p}')
    if not (rep['moved'] or rep['synced']):
        print('  无需改动')
        return 0
    if not args.apply:
        print('（干跑，未写入；加 --apply 生效）')
        return 0

    out = args.out or args.docx
    if out == args.docx:
        import datetime
        bak = args.docx + datetime.datetime.now().strftime('.bak_%Y%m%d_%H%M%S')
        shutil.copy2(args.docx, bak)
        print(f'  备份：{bak}')
    with Docx(args.docx) as z:
        z.save_as(out, new_xml)
    print(f'  已写入：{out}')
    return 0


def cmd_lift(args):
    with Docx(args.docx) as z:
        xml = z.text(DOC)
    new_xml, rep = lift_xml(xml)
    _validate(new_xml)

    print(os.path.basename(args.docx))
    print(f'  域 {rep["fields_before"]} → {rep["fields_after"]}')
    if rep['lifted']:
        print('  上宏：' + ' '.join(f'{t}(段{p})' for t, p in rep['lifted']))
    if rep.get('left'):
        print(f'  ! 正文还剩 {len(rep["left"])} 处纯文本没上宏（多半是编号被拆成多个 run）：{rep["left"][:6]}')
    for t, why in rep['skipped']:
        print(f'  跳过 {t}：{why}')
    if not rep['lifted']:
        print('  无需改动')
        return 0
    if not args.apply:
        print('（干跑，未写入；加 --apply 生效）')
        return 0
    out = args.out or args.docx
    if out == args.docx:
        import datetime
        bak = args.docx + datetime.datetime.now().strftime('.bak_%Y%m%d_%H%M%S')
        shutil.copy2(args.docx, bak)
        print(f'  备份：{bak}')
    with Docx(args.docx) as z:
        z.save_as(out, new_xml)
    print(f'  已写入：{out}')
    return 0


def cmd_renumber(args):
    with Docx(args.docx) as z:
        xml = z.text(DOC)
    new_xml, rep = renumber_xml(xml, skip_note=args.skip_note)
    _validate(new_xml)
    after = Document(new_xml.encode('utf-8'))
    mismatch = sum(1 for f in after.items()
                   if f.nums and [n for n in f.nums] != sorted(f.nums))

    print(os.path.basename(args.docx))
    print(f'  条目 {rep["canon"]} 个；显示编号改写 {rep["rewritten"]} 处；仅同步域内编号 {rep["sync_only"]} 处')
    if rep['plain']:
        from .analyze import CTX_CN
        print('  纯文本编号同步：' + ' · '.join(
            f'{CTX_CN.get(k, k)} {v}' for k, v in rep['plain'].items()))
    if rep['mapping']:
        pairs = ' '.join(f'{a}→{b}' for a, b in sorted(rep['mapping'].items()) if a != b)
        print(f'  映射（仅列出变动）：{pairs or "无"}')
    if rep.get('unmapped'):
        print(f'  ! 这些纯文本编号在文档里没有对应的单条目域，未同步：{rep["unmapped"]}')
    if rep['ambiguous']:
        print(f'  ! 多条目域里映射不唯一的旧号，已跳过：{rep["ambiguous"]}')
    for p in rep['problems']:
        print(f'  ! {p}')
    print(f'  自查：改写后仍乱序的引注域 {mismatch} 个')

    if rep['fields'] == 0 and not rep['plain']:
        print('  无需改动')
        return 0
    if not args.apply:
        print('（干跑，未写入；加 --apply 生效）')
        return 0
    out = args.out or args.docx
    if out == args.docx:
        import datetime
        bak = args.docx + datetime.datetime.now().strftime('.bak_%Y%m%d_%H%M%S')
        shutil.copy2(args.docx, bak)
        print(f'  备份：{bak}')
    with Docx(args.docx) as z:
        z.save_as(out, new_xml)
    print(f'  已写入：{out}')
    return 0


def before_problems(doc):
    return sum(1 for f in doc.items() if f.plain_citation and f.nums
               and f.plain_citation.replace(' ', '') != f.display.replace(' ', ''))


def after_problems(doc):
    return before_problems(doc)


def cmd_repair(args):
    lib = Library(args.zotero_db)
    with Docx(args.docx) as z:
        xml = z.text(DOC)
    new_xml, rep = repair_xml(xml, lib)
    _validate(new_xml)

    print(os.path.basename(args.docx))
    print(f'  正常条目 {rep["ok"]} 个；重连 {len(rep["relinked"])} 处；无法修复 {len(rep["unrecoverable"])} 处')
    for old, new, why in rep['relinked']:
        print(f'    重连 {old} → {new}（依据：{why}）')
    for old, why, title in rep['unrecoverable']:
        print(f'    ! 无法修复 {old}（{why}）：{title}')
    for p in rep['problems']:
        print(f'    ! {p}')
    if not rep['relinked']:
        print('  无需改动')
        return 0
    if not args.apply:
        print('（干跑，未写入；加 --apply 生效）')
        return 0
    out = args.out or args.docx
    if out == args.docx:
        import datetime
        bak = args.docx + datetime.datetime.now().strftime('.bak_%Y%m%d_%H%M%S')
        shutil.copy2(args.docx, bak)
        print(f'  备份：{bak}')
    with Docx(args.docx) as z:
        z.save_as(out, new_xml)
    print(f'  已写入：{out}（回 Word 里点一次 Refresh 让 Zotero 重新渲染）')
    return 0


def cmd_patch(args):
    import zipfile
    from .patch import sha as _sha
    omni = omni_path(args.zotero_dir)
    if not os.path.isfile(omni):
        print(f'! 找不到 omni.ja：{omni}')
        print(r'  --zotero-dir 应指向 Zotero 程序目录（里面是 app\omni.ja），例如 C:\Program Files\Zotero')
        return 2
    try:
        st = inspect(omni, args.marker)
    except (KeyError, zipfile.BadZipFile, OSError) as e:
        print(f'! 这个包读不出来：{e}')
        return 2
    print(f'包      {st["omni"]}')
    print(f'        大小 {st["size"]:,} B；条目 {st["entries"]}')
    print(f'内层    {st["inner_size"]:,} B  sha256[:16] {st["inner_sha"]}')
    print(f'补丁    标记 {args.marker!r}：{"在" if st["has_marker"] else "不在"}')

    if not args.patched:
        if not st['has_marker']:
            print('  只查模式：当前是原版。要打补丁请加 --patched <已修补的 integration.js>')
        return 0

    with open(args.patched, 'rb') as f:
        patched = f.read()
    print(f'补丁文件 {args.patched}')
    print(f'        {len(patched):,} B  sha256[:16] {_sha(patched)}')
    if st['has_marker'] and not args.force:
        print('  当前已是补丁版；确需覆盖请加 --force')
        return 0
    if not args.apply:
        print('（干跑，未写入；加 --apply 生效）')
        return 0

    bak = apply_patch(omni, patched, args.marker)
    st2 = inspect(omni, args.marker)
    print(f'  备份 {bak}')
    print(f'  已写入：条目 {st2["entries"]}；内层 sha256[:16] {st2["inner_sha"]}；标记在：{st2["has_marker"]}')
    print('  重启 Zotero 才生效')
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog='zotdocx',
        description='Zotero 稿件端质检与修复（只读优先，写操作需 --apply）')
    ap.add_argument('-V', '--version', action='version', version=__version__)
    sub = ap.add_subparsers(dest='cmd')

    p = sub.add_parser('status', help='体检：域结构、条目、编号、纯文本引用')
    p.add_argument('docx')
    p.add_argument('--zotero-db', metavar='PATH', help='zotero.sqlite 路径，给了才做断链判定')
    p.add_argument('--show-text', action='store_true', help='打印纯文本引用所在段落（默认不打印正文）')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_status)

    p = sub.add_parser('heal', help='修跨段落引注域与域内编号不一致（结构修复）')
    p.add_argument('docx')
    p.add_argument('--apply', action='store_true', help='实际写入；默认只干跑')
    p.add_argument('--out', metavar='PATH', help='写到新文件（默认原地写，并自动备份）')
    p.set_defaults(func=cmd_heal)

    p = sub.add_parser('renumber', help='按首次被引顺序统一编号，并同步表格/图题/表注里的纯文本编号')
    p.add_argument('docx')
    p.add_argument('--apply', action='store_true', help='实际写入；默认只干跑')
    p.add_argument('--out', metavar='PATH', help='写到新文件（默认原地写，并自动备份）')
    p.add_argument('--skip-note', action='store_true', help='不动表注图注里的纯文本编号')
    p.set_defaults(func=cmd_renumber)

    p = sub.add_parser('lift', help='把正文里的纯文本引用编号补成 Zotero 活域（多条目自动合并）')
    p.add_argument('docx')
    p.add_argument('--apply', action='store_true', help='实际写入；默认只干跑')
    p.add_argument('--out', metavar='PATH', help='写到新文件（默认原地写，并自动备份）')
    p.set_defaults(func=cmd_lift)

    p = sub.add_parser('repair', help='修断链：把指向不存在条目的引用域重新连到正确条目')
    p.add_argument('docx')
    p.add_argument('--zotero-db', metavar='PATH', required=True, help='zotero.sqlite 路径')
    p.add_argument('--apply', action='store_true', help='实际写入；默认只干跑')
    p.add_argument('--out', metavar='PATH', help='写到新文件（默认原地写，并自动备份）')
    p.set_defaults(func=cmd_repair)

    p = sub.add_parser('patch', help='检查/重打 Zotero 的 omni.ja 补丁（不携带任何 Zotero 代码）')
    p.add_argument('--zotero-dir', metavar='DIR', required=True, help='Zotero 程序目录（含 app/omni.ja）')
    p.add_argument('--patched', metavar='FILE', help='已修补的 integration.js；不给则只查')
    p.add_argument('--marker', default='plainCitationFix', help='补丁标记字符串（默认 plainCitationFix）')
    p.add_argument('--apply', action='store_true', help='实际写入；默认只干跑')
    p.add_argument('--force', action='store_true', help='已是补丁版时仍覆盖')
    p.set_defaults(func=cmd_patch)
    return ap


def _utf8_stdio():
    """管道/重定向时也按 UTF-8 输出，避免中文乱码（控制台本就是 UTF-8）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _utf8_stdio()
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, 'func', None):
        ap.print_help()
        return 2
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f'! 找不到文件：{e}')
        return 2
    except zipfile.BadZipFile:
        print('! 这不是 .docx（zip 打不开），或者文件已损坏')
        return 2
    except KeyError as e:
        print(f'! 包里缺部件：{e}')
        return 2
    except PermissionError as e:
        print(f'! 没有权限或文件被占用：{e}')
        print('  在 Word 里关掉这个文档再试')
        return 2


if __name__ == '__main__':
    sys.exit(main())
