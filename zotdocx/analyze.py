# -*- coding: utf-8 -*-
"""解析层：把 docx 里的 Zotero 域、纯文本引用、段落语境一次算清。

所有子命令都只调这里，避免旧脚本那套「每个脚本自己拆一遍 zip」。
只读，不改任何东西。
"""
import json
import re
from dataclasses import dataclass, field

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
_Q = lambda n: '{%s}%s' % (W, n)
TAG_P, TAG_TBL, TAG_FLD = _Q('p'), _Q('tbl'), _Q('fldChar')
TAG_INSTR, TAG_T = _Q('instrText'), _Q('t')

BODY, TABLE, CAPTION, NOTE, BIBLIO = 'body', 'table', 'caption', 'note', 'biblio'
CTX_CN = {BODY: '正文', TABLE: '表格', CAPTION: '图题表题', NOTE: '表注图注', BIBLIO: '参考文献表'}

NUM_RE = re.compile(r'\[\s*(\d+(?:\s*[,，\-–]\s*\d+)*)\s*\]')
CAP_RE = re.compile(r'^\s*(图|表|Table|Figure|Fig\.?|Tab\.)\s*\d', re.I)
NOTE_RE = re.compile(r'^\s*(注|Note|Notes)\s*[:：]', re.I)
BIBLIO_HEAD_RE = re.compile(
    r'^\s*(参考文献|References?|Bibliography|Literature Cited|Works Cited)\s*$', re.I)


@dataclass
class Field:
    idx: int
    kind: str                 # 'item' | 'bibl' | 'other'
    ctx: str
    p0: int
    p1: int
    instr: str
    data: dict = None
    ids: list = field(default_factory=list)
    display: str = ''
    nums: list = field(default_factory=list)

    @property
    def cross(self):
        return self.p0 != self.p1

    @property
    def plain_citation(self):
        return (self.data or {}).get('properties', {}).get('plainCitation')


@dataclass
class Plain:
    ctx: str
    p: int
    text: str
    nums: list


def nums_of(s):
    """'[1, 3-5]' → [1,3,4,5]"""
    out = []
    for part in re.split(r'[,，]', s):
        part = part.strip().replace('–', '-')
        if '-' in part:
            try:
                a, b = part.split('-')
                if 0 < int(b) - int(a) < 100:
                    out.extend(range(int(a), int(b) + 1))
                    continue
            except ValueError:
                pass
        if part.isdigit():
            out.append(int(part))
    return out


def _in_table(el):
    node = el.getparent()
    while node is not None:
        if node.tag == TAG_TBL:
            return True
        node = node.getparent()
    return False


def _json_of(instr):
    m = re.search(r'CSL_CITATION\s*(\{.*\})\s*$', instr.strip(), re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


class Document:
    def __init__(self, xml_bytes):
        self.root = etree.fromstring(xml_bytes)
        self.body = self.root.find('w:body', NS)
        if self.body is None:
            raise ValueError('document.xml 里没有 w:body')
        self._paras = list(self.body.iter(TAG_P))
        self.para_text = []
        self.para_table = []
        self.para_ctx = []
        self.fields = []
        self.plains = []
        self._walk()
        self._classify_paragraphs()
        self._collect_plains()
        self._attach_numbers()

    # ---------- 一次遍历：段落、域、域外文字 ----------
    def _walk(self):
        stack = []
        buf, depth, cur = [], 0, -1
        for el in self.body.iter():
            if el.tag == TAG_P:
                cur += 1
                self.para_text.append([])
                self.para_table.append(_in_table(el))
            elif el.tag == TAG_FLD:
                t = el.get(_Q('fldCharType'))
                if t == 'begin':
                    stack.append({'instr': [], 'disp': [], 'sep': False,
                                  'p0': cur, 'table': _in_table(el)})
                    depth += 1
                elif t == 'separate' and stack:
                    stack[-1]['sep'] = True
                elif t == 'end' and stack:
                    f = stack.pop()
                    depth -= 1
                    instr = ''.join(f['instr'])
                    kind = 'item' if 'ZOTERO_ITEM' in instr else (
                        'bibl' if 'ZOTERO_BIBL' in instr else 'other')
                    data = _json_of(instr) if kind == 'item' else None
                    ids = [c.get('id') for c in (data or {}).get('citationItems', [])]
                    self.fields.append(Field(
                        idx=len(self.fields), kind=kind, ctx=None,
                        p0=f['p0'], p1=cur, instr=instr, data=data, ids=ids,
                        display=''.join(f['disp'])))
            elif el.tag == TAG_INSTR:
                if stack:
                    stack[-1]['instr'].append(el.text or '')
                # 域代码不是可见文字，不进 para_text
            elif el.tag == TAG_T:
                txt = el.text or ''
                if stack and stack[-1]['sep']:
                    stack[-1]['disp'].append(txt)
                if cur >= 0:
                    self.para_text[cur].append(txt)

    # ---------- 段落语境：表格 / 图题表题 / 注 / 参考文献 ----------
    def _classify_paragraphs(self):
        texts = [''.join(t) for t in self.para_text]
        self.para_text = texts
        biblio_from = len(texts)
        for i, t in enumerate(texts):
            if BIBLIO_HEAD_RE.match(t):
                biblio_from = i
                break
        for i, t in enumerate(texts):
            if self.para_table[i]:
                self.para_ctx.append(TABLE)
            elif i >= biblio_from:
                self.para_ctx.append(BIBLIO)
            elif CAP_RE.match(t):
                self.para_ctx.append(CAPTION)
            elif NOTE_RE.match(t):
                self.para_ctx.append(NOTE)
            else:
                self.para_ctx.append(BODY)
        for f in self.fields:
            f.ctx = self.para_ctx[f.p0] if f.p0 < len(self.para_ctx) else BODY

    # ---------- 域外纯文本引用 ----------
    def _collect_plains(self):
        for p, (txt, ctx) in enumerate(zip(self.para_text, self.para_ctx)):
            outside = self._text_outside_fields(p)
            for m in NUM_RE.finditer(outside):
                nums = nums_of(m.group(1))
                if not nums or any(n >= 1000 for n in nums):
                    continue    # 访问日期 [2026-05-17] 之类，不是引用编号
                self.plains.append(Plain(ctx=ctx, p=p, text=m.group(0), nums=nums))

    def _text_outside_fields(self, p_idx):
        """重扫该段落，只取不在域内的文字。"""
        p = self._paras[p_idx]
        out, depth = [], 0
        for el in p.iter():
            if el.tag == TAG_FLD:
                t = el.get(_Q('fldCharType'))
                depth += 1 if t == 'begin' else (-1 if t == 'end' else 0)
            elif el.tag == TAG_T and depth == 0:
                out.append(el.text or '')
        return ''.join(out)

    # ---------- 编号 ----------
    def _attach_numbers(self):
        for f in self.fields:
            if f.kind != 'item':
                continue
            nums = []
            for m in NUM_RE.finditer(f.display or ''):
                nums.extend(nums_of(m.group(1)))
            f.nums = nums

    def items(self):
        return [f for f in self.fields if f.kind == 'item']
