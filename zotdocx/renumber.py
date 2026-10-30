# -*- coding: utf-8 -*-
"""renumber：把全稿编号统一到「首次被引顺序」，并把表格 / 图题 / 表注里的
**纯文本**编号按同一映射一起改。

关键点：old→new 映射不是写死的，而是从「单条目引注域」现算出来的
（每个单条目域的显示号 ↔ 该条目应有的规范号）。多条目域的编号若该表
覆盖不到，会列入 ambiguous，不动。

口径：参考文献表内的纯文本编号**不改**（那是条目自身序号，不是引用）。
"""
import json
import re

from .analyze import BIBLIO, NOTE, Document
from .heal import END, SEP, field_spans, instr_of

RUN = re.compile(r'<w:r(?: [^>]*)?>.*?</w:r>', re.S)
T = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)
CITE = re.compile(r'CSL_CITATION\s*(\{.*\})\s*$', re.S)

SCAN = re.compile(
    r'<w:p(?: [^>]*)?>|</w:p>|<w:tbl>|</w:tbl>'
    r'|<w:fldChar w:fldCharType="(?:begin|end)"/>'
    r'|<w:t(?: [^>]*)?>.*?</w:t>', re.S)
NUM = re.compile(r'\[\s*(\d+(?:\s*[,，\-–]\s*\d+)*)\s*\]')


def _nums(disp):
    out = []
    for part in re.split(r'[,，]', disp.strip('[] ').replace('–', '-')):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-', 1)
            if a.isdigit() and b.isdigit() and 0 < int(b) - int(a) < 100:
                out.extend(range(int(a), int(b) + 1))
                continue
        if part.isdigit():
            out.append(int(part))
    return out


def _rebuild_display(seg, newdisp):
    s = seg.index(SEP) + len(SEP)
    e = seg.index(END)
    region = seg[s:e]
    runs = RUN.findall(region)
    texts = [''.join(T.findall(r)) for r in runs]
    keep, done = [], False
    for t, r in zip(texts, runs):
        if t.strip() == '':
            keep.append(r)
        elif not done:
            if len(T.findall(r)) != 1:
                raise ValueError('显示区一个 run 里有多个 w:t，拒绝改写')
            keep.append(re.sub(r'(<w:t[^>]*>).*?(</w:t>)',
                               lambda m: m.group(1) + newdisp + m.group(2), r, count=1, flags=re.S))
            done = True
        else:
            raise ValueError('显示区有多个文字 run，拒绝改写（怕丢文字）')
    if not done:
        raise ValueError('显示区里没有文字 run')
    return seg[:s] + ''.join(keep) + seg[e:]


def _sync_json(seg, data, newdisp):
    props = data.get('properties', {})
    pc = props.get('plainCitation')
    if pc and pc != newdisp:
        old = '"plainCitation":"%s"' % pc
        if old in seg:
            seg = seg.replace(old, '"plainCitation":"%s"' % newdisp, 1)
    fc = props.get('formattedCitation')
    if isinstance(fc, str) and fc.startswith('\\super'):
        oldfc = '"formattedCitation":"%s"' % json.dumps(fc)[1:-1]
        newfc = '"formattedCitation":"%s"' % json.dumps('\\super %s\\nosupersub{}' % newdisp)[1:-1]
        if oldfc in seg:
            seg = seg.replace(oldfc, newfc, 1)
    return seg


def renumber_xml(xml, skip_note=False):
    """返回 (新 xml, 报告)。"""
    doc = Document(xml.encode('utf-8'))
    allow = []
    for ctx in doc.para_ctx:
        if ctx == BIBLIO:
            allow.append(False)
        elif ctx == NOTE and skip_note:
            allow.append(False)
        else:
            allow.append(True)

    spans = field_spans(xml)
    canon, data_by_field, changed = {}, {}, 0
    report = {'fields': 0, 'rewritten': 0, 'sync_only': 0, 'plain': {}, 'mapping': {}, 'ambiguous': [], 'unmapped': [], 'problems': []}

    # ---- ① 正文引注域：按首次被引顺序定号，改显示 + 改 JSON ----
    infos = []
    for rs, re_ in spans:
        seg = xml[rs:re_]
        instr = instr_of(seg)
        if 'ZOTERO_ITEM' not in instr:
            infos.append(None)
            continue
        m = CITE.search(instr.strip())
        if not m:
            infos.append(None)
            report['problems'].append('引注域 JSON 解析失败')
            continue
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            infos.append(None)
            report['problems'].append('JSON 坏：%s' % e)
            continue
        ids = [c.get('id') for c in data.get('citationItems', [])]
        for i in ids:
            canon.setdefault(i, len(canon) + 1)
        infos.append((ids, data))

    for (rs, re_), info in zip(reversed(spans), reversed(infos)):
        if info is None:
            continue
        ids, data = info
        want = sorted(canon[i] for i in ids)
        newdisp = '[' + ','.join(str(n) for n in want) + ']'
        seg = xml[rs:re_]
        cur = ''.join(T.findall(seg[seg.index(SEP) + len(SEP):seg.index(END)])).strip()
        pc_now = (data.get('properties') or {}).get('plainCitation') or ''

        # 旧号 → 规范号：单条目一对一；多条目按升序位次配对（数字制显示必升序）。
        # 这一段必须放在所有 continue 之前，否则"本来就对"的域贡献不了映射。
        old = _nums(cur)
        if len(old) == len(want) and old == sorted(old):
            for k, v in zip(old, want):
                if k in report['mapping'] and report['mapping'][k] != v:
                    if k not in report['ambiguous']:
                        report['ambiguous'].append(k)
                else:
                    report['mapping'][k] = v

        if cur == newdisp and pc_now == newdisp:
            continue                      # 已经是对的，一个字节都不动
        if sorted(_nums(cur)) == want:
            # 显示编号本身没错，只是域内存的编号过期 —— 只同步 JSON，不动显示区格式
            seg2 = _sync_json(seg, data, cur or newdisp)
            if seg2 != seg:
                xml = xml[:rs] + seg2 + xml[re_:]
                changed += 1
                report['sync_only'] += 1
            continue
        try:
            seg2 = _rebuild_display(seg, newdisp)
        except ValueError as e:
            report['problems'].append(str(e))
            continue
        seg2 = _sync_json(seg2, data, newdisp)
        if seg2 != seg:
            xml = xml[:rs] + seg2 + xml[re_:]
            changed += 1
            report['rewritten'] += 1
    report['fields'] = changed
    mapping = {k: v for k, v in report['mapping'].items() if k not in report['ambiguous']}

    # ---- ② 表格 / 图题 / 表注里的纯文本编号 ----
    if mapping:
        def fix(m):
            nums = _nums(m.group(0))
            if not nums:
                return m.group(0)
            out = []
            for n in nums:
                if n in mapping:
                    out.append(str(mapping[n]))
                else:
                    if n not in report['unmapped']:
                        report['unmapped'].append(n)
                    out.append(str(n))        # 映射不到的保持原样，不猜
            return '[' + ','.join(out) + ']'

        out, pos, p_idx, depth = [], 0, -1, 0
        for m in SCAN.finditer(xml):
            out.append(xml[pos:m.start()])
            tok = m.group(0)
            if tok.startswith('<w:p'):
                p_idx += 1
            elif tok == '</w:p>':
                pass
            elif tok.startswith('<w:fldChar'):
                depth += 1 if 'begin' in tok else -1
            elif tok.startswith('<w:t'):
                if depth == 0 and 0 <= p_idx < len(allow) and allow[p_idx]:
                    inner = re.sub(r'^<w:t[^>]*>|</w:t>$', '', tok)
                    new_inner = NUM.sub(fix, inner)
                    if new_inner != inner:
                        ctx = doc.para_ctx[p_idx]
                        report['plain'][ctx] = report['plain'].get(ctx, 0) + 1
                        tok = tok.replace(inner, new_inner, 1)
            out.append(tok)
            pos = m.end()
        out.append(xml[pos:])
        xml = ''.join(out)

    report['mapping'] = mapping
    report['canon'] = len(canon)
    return xml, report
