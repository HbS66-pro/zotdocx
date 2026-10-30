# -*- coding: utf-8 -*-
"""repair：修断链——引用域指向的条目在库里不存在时，把它重新连到正确条目上。

三种修法，按可靠性排序：
  1. uris 里的 item key 在库里 → 直接用该 key 对应的 itemID（最可靠）；
  2. key 不在、但 itemData 里的题名在库里**唯一**命中 → 用它，并把 uris 改成该条目；
  3. 都对不上 → 不动，列入 unrecoverable，交给人。

不写数据库、不新建条目：越界的事不做。
"""
import json
import re

from .heal import field_spans, instr_of

CITE = re.compile(r'CSL_CITATION\s*(\{.*\})\s*$', re.S)
JSON_IN_INSTR = re.compile(r'(CSL_CITATION\s*)(\{.*\})(\s*</w:instrText>)', re.S)
URI_TPL = 'http://zotero.org/users/0/items/%s'


def _relink(item, lib):
    """返回 (新 id, 依据) 或 (None, 原因)。"""
    key = ((item.get('uris') or [''])[0]).rsplit('/', 1)[-1]
    nid = lib.id_of_key(key)
    if nid is not None:
        return nid, 'key'
    title = (item.get('itemData') or {}).get('title', '')
    cands = lib.find_by_title(title)
    if len(cands) == 1:
        return cands[0], 'title'
    return None, ('题名多义' if len(cands) > 1 else '库里找不到')


def repair_xml(xml, lib):
    report = {'ok': 0, 'relinked': [], 'unrecoverable': [], 'problems': []}
    for rs, re_ in reversed(field_spans(xml)):
        seg = xml[rs:re_]
        instr = instr_of(seg)
        if 'ZOTERO_ITEM' not in instr:
            continue
        m = CITE.search(instr.strip())
        if not m:
            report['problems'].append('引注域 JSON 解析失败')
            continue
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            report['problems'].append('JSON 坏：%s' % e)
            continue

        changed = False
        for item in data.get('citationItems', []):
            if lib.has(item.get('id')):
                report['ok'] += 1
                continue
            old = item.get('id')
            nid, why = _relink(item, lib)
            if nid is None:
                report['unrecoverable'].append((old, why, (item.get('itemData') or {}).get('title', '')[:30]))
                continue
            item['id'] = nid
            if why == 'title':
                key = lib.key_of(nid)
                if key:
                    item['uris'] = [URI_TPL % key]
            data.setdefault('itemData', {})
            if isinstance(item.get('itemData'), dict):
                item['itemData']['id'] = nid
            report['relinked'].append((old, nid, why))
            changed = True

        if changed:
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            seg2 = JSON_IN_INSTR.sub(
                lambda mm: mm.group(1) + payload + mm.group(3), seg, count=1)
            if seg2 == seg:
                report['problems'].append('改完 JSON 没能写回 instrText')
                continue
            xml = xml[:rs] + seg2 + xml[re_:]
    return xml, report
