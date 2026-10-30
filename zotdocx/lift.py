# -*- coding: utf-8 -*-
"""lift：把正文里的纯文本引用编号 `[n]` / `[a,b]` 补成 Zotero 活域。

做法（不改动任何既有域）：
  * 从同一份文档里已存在的**单条目域**整块复制，换 citationID；
  * 多条目时，先各复制一个单体块，再把它们的 citationItems 合并成一个域
    （每个 citationItem 都是 Zotero 自己写的，id / uris / itemData 天然对齐）；
  * 显示区文字换成目标编号，rPr 沿用原来那段纯文本的格式。

口径：只处理正文段落；表格、表注、图题、参考文献表一律不动。
"""
import json
import random
import re
import string

from .analyze import BODY, Document, nums_of
from .heal import END, SEP, field_spans, instr_of

RPR = re.compile(r'<w:rPr>.*?</w:rPr>', re.S)
RUN = re.compile(r'<w:r(?: [^>]*)?>.*?</w:r>', re.S)
T = re.compile(r'<w:t(?: [^>]*)?>.*?</w:t>', re.S)
INSTR = re.compile(r'(<w:instrText[^>]*>)(.*?)(</w:instrText>)', re.S)
CITE = re.compile(r'(CSL_CITATION\s*)(\{.*\})(\s*</w:instrText>|$)', re.S)
TOKEN = re.compile(r'<w:t(?: [^>]*)?>(.*?)</w:t>', re.S)
SCAN = re.compile(
    r'<w:p(?: [^>]*)?>|</w:p>|<w:fldChar w:fldCharType="(?:begin|end)"/>'
    r'|<w:r(?: [^>]*)?>|</w:r>|<w:t(?: [^>]*)?>.*?</w:t>', re.S)


def _rand_id(used):
    while True:
        c = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        if c not in used:
            used.add(c)
            return c


def _json_of(seg):
    instr = instr_of(seg)
    m = CITE.search(instr.strip())
    return json.loads(m.group(2)) if m else None


def _display_run(block, token):
    """返回 (run_start, run_end, run_text)；run 内必须恰好一个 w:t。"""
    m = re.search(r'<w:t(?: [^>]*)?>%s</w:t>' % re.escape(token), block)
    if not m:
        return None
    rs = [x.start() for x in re.finditer(r'<w:r(?: [^>]*)?>', block, re.S) if x.start() < m.start()]
    rs = rs[-1] if rs else None
    re_ = block.index('</w:r>', m.end()) + len('</w:r>')
    return rs, re_, block[rs:re_]


def _retarget(block, old_tok, new_tok, rpr):
    """把复制来的块改成目标编号与目标格式。"""
    got = _display_run(block, old_tok)
    if not got:
        raise ValueError('源域里找不到显示文字 %s' % old_tok)
    rs, re_, run = got
    run = re.sub(r'(<w:t[^>]*>)%s(</w:t>)' % re.escape(old_tok),
                 lambda m: m.group(1) + new_tok + m.group(2), run, count=1)
    if rpr:
        if RPR.search(run):
            run = RPR.sub(rpr, run, count=1)
        else:
            run = re.sub(r'(<w:r(?: [^>]*)?>)', r'\1' + rpr, run, count=1)
    return block[:rs] + run + block[re_:]


def _merge_blocks(blocks, newdisp, rpr, used):
    """把多个单条目块合并成一个域：JSON 拼接 + 显示区重建。"""
    first = blocks[0]
    data = _json_of(first)
    items = list(data.get('citationItems', []))
    for b in blocks[1:]:
        d = _json_of(b)
        items.extend(d.get('citationItems', []))
    for i, it in enumerate(items):
        it['position'] = i
    data['citationItems'] = items
    data.setdefault('properties', {})
    data['properties']['plainCitation'] = newdisp
    fc = data['properties'].get('formattedCitation')
    if isinstance(fc, str) and fc.startswith('\\super'):
        data['properties']['formattedCitation'] = '\\super %s\\nosupersub{}' % newdisp
    data['citationID'] = _rand_id(used)

    # 显示区：清掉多余 run，只留第一个文字 run 并写入新编号
    s = first.index(SEP) + len(SEP)
    e = first.index(END)
    region = first[s:e]
    runs = RUN.findall(region)
    keep, done = [], False
    for r in runs:
        txt = ''.join(TOKEN.findall(r))
        if txt.strip() == '':
            keep.append(r)
        elif not done:
            keep.append(re.sub(r'(<w:t[^>]*>).*?(</w:t>)',
                               lambda m: m.group(1) + newdisp + m.group(2),
                               r, count=1, flags=re.S))
            done = True
        elif txt.strip():
            raise ValueError('源域显示区有多个文字 run，拒绝合并（怕丢文字）')
    if not done:
        raise ValueError('源域显示区里没有文字 run')
    body = first[:s] + ''.join(keep) + first[e:]

    # 换 JSON
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    body = INSTR.sub(lambda m: m.group(1) + ' ADDIN ZOTERO_ITEM CSL_CITATION ' + payload + ' ' + m.group(3), body, count=1)
    return body


def lift_xml(xml):
    """返回 (新 xml, 报告)。"""
    doc = Document(xml.encode('utf-8'))
    report = {'lifted': [], 'skipped': [], 'fields_before': len(doc.fields)}

    # 编号 → 条目 id（只信单条目域）
    num2id = {}
    for f in doc.items():
        if len(f.ids) == 1 and len(f.nums) == 1:
            num2id[f.nums[0]] = f.ids[0]

    # 条目 id → 源域块
    used = set(re.findall(r'"citationID":"([^"]*)"', xml))
    src = {}
    for rs, re_ in field_spans(xml):
        seg = xml[rs:re_]
        instr = instr_of(seg)
        if 'ZOTERO_ITEM' not in instr:
            continue
        try:
            d = _json_of(seg)
        except Exception:
            continue
        if d and len(d.get('citationItems', [])) == 1:
            src.setdefault(d['citationItems'][0].get('id'), seg)

    # 找出所有可上宏的纯文本 run（正文段落、域外、run 内只有这一个编号）
    cands = []
    p_idx, depth = -1, 0
    run_start, run_end = None, None
    for m in SCAN.finditer(xml):
        tok = m.group(0)
        if tok.startswith('<w:p'):
            p_idx += 1
        elif tok.startswith('<w:fldChar'):
            depth += 1 if 'begin' in tok else -1
        elif tok.startswith('<w:r'):
            if depth == 0:
                run_start = m.start()
        elif tok == '</w:r>':
            if depth == 0 and run_start is not None:
                text = ''.join(TOKEN.findall(xml[run_start:m.end()])).strip()
                if (p_idx < len(doc.para_ctx) and doc.para_ctx[p_idx] == BODY
                        and re.fullmatch(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', text)):
                    cands.append((run_start, m.end(), text, p_idx))
            run_start = None

    # 从后往前替换，避免位移
    for rs, re_, text, p_idx in reversed(cands):
        nums = nums_of(text[1:-1])
        if not nums or any(n not in num2id for n in nums):
            report['skipped'].append((text, '编号在文档里找不到对应条目'))
            continue
        blocks = []
        missing = False
        for n in nums:
            b = src.get(num2id[n])
            if b is None:
                missing = True
                break
            blocks.append(b)
        if missing:
            report['skipped'].append((text, '缺单条目源域'))
            continue
        run = xml[rs:re_]
        rpr_m = RPR.search(run)
        rpr = rpr_m.group(0) if rpr_m else None
        try:
            if len(blocks) == 1:
                blk = _retarget(blocks[0], text, text, rpr)
                blk = re.sub(r'"citationID":"[^"]*"', '"citationID":"%s"' % _rand_id(used), blk, count=1)
            else:
                blk = _merge_blocks(blocks, text, rpr, used)
        except ValueError as e:
            report['skipped'].append((text, str(e)))
            continue
        xml = xml[:rs] + blk + xml[re_:]
        report['lifted'].append((text, p_idx))

    report['fields_after'] = len(field_spans(xml))
    # 还剩哪些正文纯文本没上宏（通常是被拆成多个 run 的编号），如实报出来
    after = Document(xml.encode('utf-8'))
    report['left'] = [p.text for p in after.plains if p.ctx == BODY]
    return xml, report
