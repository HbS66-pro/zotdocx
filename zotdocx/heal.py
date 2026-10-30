# -*- coding: utf-8 -*-
"""heal：修 Zotero 刷新报错的两个结构性病根。

① 引注域跨段落（域的 end 掉进下一段）→ 把域尾收回本段；
② 域内存的编号（plainCitation / formattedCitation）与显示编号不一致 → 以显示为准同步。
书目域（ZOTERO_BIBL）本就跨段，跳过不动。

只做这两件事；不动文字、不动编号含义、不碰表格与文献表。
"""
import json
import re

RUN_OPEN = re.compile(r'<w:r(?: [^>]*)?>')
BEGIN = '<w:fldChar w:fldCharType="begin"/>'
END = '<w:fldChar w:fldCharType="end"/>'
SEP = '<w:fldChar w:fldCharType="separate"/>'
PPR = re.compile(r'<w:pPr>.*?</w:pPr>', re.S)
POPEN = re.compile(r'<w:p(?: [^>]*)?>')
CITE = re.compile(r'CSL_CITATION\s*(\{.*\})\s*$', re.S)


def field_spans(xml):
    """每个域的字符区间 [run 起点, run 终点)，按文档顺序。"""
    marks = [(m.start(), m.group(1)) for m in
             re.finditer(r'<w:fldChar w:fldCharType="(begin|end)"/>', xml)]
    out, stack = [], []
    for pos, kind in marks:
        if kind == 'begin':
            stack.append(pos)
        elif stack:
            b = stack.pop()
            rs = [m.start() for m in RUN_OPEN.finditer(xml, 0, b)][-1]
            out.append((rs, xml.index('</w:r>', pos) + len('</w:r>')))
    out.sort()
    return out


def instr_of(seg):
    return ''.join(re.findall(r'<w:instrText[^>]*>(.*?)</w:instrText>', seg, re.S))


def visible_of(seg):
    return ''.join(re.findall(r'<w:t(?: [^>]*)?>(.*?)</w:t>', seg, re.S))


def _close_span(seg):
    """把跨段域的域尾并回本段；返回 (新 seg, 是否改动)。"""
    if '</w:p>' not in seg:
        return seg, False
    k = seg.index('</w:p>')
    left, right = seg[:k], seg[k:]
    m = PPR.search(right)
    start_in = m.end() if m else (POPEN.search(right).end() if POPEN.search(right) else 0)
    tail = right[start_in:]
    if tail.count(END) != 1:
        raise ValueError('尾块 end 标记不为 1，拒绝改动')
    texts = re.findall(r'<w:t(?: [^>]*)?>(.*?)</w:t>', tail, re.S)
    if any(t.strip() for t in texts):
        raise ValueError('尾块含非空白文字 %r，拒绝改动' % texts)
    return left + tail + right[:start_in], True


def _sync_citation(seg):
    """域内编号与显示不一致时，以显示为准同步；返回 (新 seg, 旧号, 新号) 或 (seg, None, None)。"""
    instr = instr_of(seg)
    m = CITE.search(instr.strip())
    if not m:
        return seg, None, None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return seg, None, None
    pc = data.get('properties', {}).get('plainCitation')
    sm, em = seg.find(SEP), seg.find(END)
    disp = visible_of(seg[sm + len(SEP):em]).strip() if 0 <= sm < em else ''
    if not pc or not disp or disp == pc:
        return seg, None, None
    old = '"plainCitation":"%s"' % pc
    if old not in seg:
        return seg, None, None
    seg = seg.replace(old, '"plainCitation":"%s"' % disp, 1)
    fc = data['properties'].get('formattedCitation')
    if isinstance(fc, str) and fc.startswith('\\super'):
        oldfc = '"formattedCitation":"%s"' % json.dumps(fc)[1:-1]
        newfc = '"formattedCitation":"%s"' % json.dumps('\\super %s\\nosupersub{}' % disp)[1:-1]
        if oldfc in seg:
            seg = seg.replace(oldfc, newfc, 1)
    return seg, pc, disp


def heal_xml(xml):
    """返回 (新 xml, 报告)。纯函数，不落盘。"""
    report = {'moved': 0, 'synced': 0, 'skipped_bibl': 0, 'problems': []}
    for rs, re_ in reversed(field_spans(xml)):
        seg = xml[rs:re_]
        instr = instr_of(seg)
        if 'ZOTERO_BIBL' in instr:
            report['skipped_bibl'] += 1
            continue
        try:
            seg2, moved = _close_span(seg)
        except ValueError as e:
            report['problems'].append(str(e))
            continue
        seg3, old, new = _sync_citation(seg2)
        if seg3 != seg:
            xml = xml[:rs] + seg3 + xml[re_:]
        if moved:
            report['moved'] += 1
        if old is not None:
            report['synced'] += 1
            report.setdefault('pairs', []).append((old, new))
    return xml, report
