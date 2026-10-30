# -*- coding: utf-8 -*-
"""最小 docx 读写层：只碰 word/document.xml，其余部件逐字节不动。

设计原则（来自被验证过的旧脚本）：
  * 读取用 lxml 解析，便于按结构判断；
  * 落盘时按原条目顺序重建 zip，保留压缩方式与时间戳；
  * 写之前先序列化再回读校验，校验不过就放弃。
"""
import os
import shutil
import zipfile

DOC = 'word/document.xml'


class Docx:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)
        self._zf = zipfile.ZipFile(self.path)
        self.names = self._zf.namelist()

    def read(self, name=DOC):
        return self._zf.read(name)

    def text(self, name=DOC):
        return self.read(name).decode('utf-8')

    def close(self):
        self._zf.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def save_as(self, out_path, xml_text, name=DOC):
        """按原条目顺序重建 zip，只替换 name 这一个部件。"""
        data = xml_text.encode('utf-8')
        tmp = out_path + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zo:
            for it in self._zf.infolist():
                body = data if it.filename == name else self._zf.read(it.filename)
                nzi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
                nzi.compress_type = it.compress_type
                nzi.external_attr = it.external_attr
                nzi.internal_attr = it.internal_attr
                nzi.create_system = it.create_system
                zo.writestr(nzi, body)
        # 回读校验：条目数一致、目标部件一致
        with zipfile.ZipFile(tmp) as z:
            if len(z.namelist()) != len(self.names) or z.read(name) != data:
                os.remove(tmp)
                raise RuntimeError('重建包自检未通过，已放弃')
        shutil.move(tmp, out_path)
