# -*- coding: utf-8 -*-
"""只读访问 zotero.sqlite：拿 itemID、key、题名，供 repair 做条目重连。

写库是禁止的——这个工具只在 docx 一侧动手。
"""
import os
import shutil
import sqlite3
import tempfile


class Library:
    def __init__(self, db_path):
        self.path = os.path.abspath(db_path)
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)
        self.ids = set()
        self.deleted = set()
        self.key_to_id = {}
        self.titles = {}
        self._load()

    def _load(self):
        tmp = os.path.join(tempfile.gettempdir(), 'zotdocx_lib_ro.sqlite')
        shutil.copy2(self.path, tmp)          # 库可能在用，复制一份只读
        con = sqlite3.connect(tmp)
        try:
            self.ids = {r[0] for r in con.execute('select itemID from items')}
            self.key_to_id = {r[1]: r[0] for r in con.execute('select itemID, key from items')}
            try:
                self.deleted = {r[0] for r in con.execute('select itemID from deletedItems')}
            except sqlite3.Error:
                pass
            self.titles = {r[0]: r[1] for r in con.execute(
                'select i.itemID, v.value from items i '
                'join itemData d on d.itemID = i.itemID '
                'join fields f on f.fieldID = d.fieldID and f.fieldName = "title" '
                'join itemDataValues v on v.valueID = d.valueID')}
        finally:
            con.close()

    # --- repair 用到的四问 ---
    def has(self, i):
        if i is None:
            return False
        try:
            return int(i) in self.ids
        except (TypeError, ValueError):
            return False

    def id_of_key(self, key):
        return self.key_to_id.get(key)

    def key_of(self, item_id):
        for k, v in self.key_to_id.items():
            if v == item_id:
                return k
        return None

    def find_by_title(self, title):
        if not title:
            return []
        t = title.strip().lower()
        return [i for i, s in self.titles.items() if (s or '').strip().lower() == t]

    # --- status 用的分类 ---
    def classify(self, i):
        if i is None:
            return '缺 id'
        if isinstance(i, int) or (isinstance(i, str) and i.isdigit()):
            n = int(i)
            if n in self.ids:
                return '存在'
            return '回收站' if n in self.deleted else '缺失'
        s = str(i)
        key = s.split('/')[-1]
        return '会话号(可解析)' if key in self.key_to_id else '会话号(库中无)'
