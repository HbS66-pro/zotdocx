# -*- coding: utf-8 -*-
"""一把跑完全部回归测试，输出一行一个结果。

    python tests/run_all.py

全部用合成 docx / 合成 omni.ja，不读真实论文，也不碰真实 Zotero 目录。
子进程统一按 UTF-8 输出，Windows 管道下中文不乱码。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = ['test_heal.py', 'test_renumber.py', 'test_lift.py', 'test_en.py',
         'test_repair.py', 'test_patch.py', 'test_superscript.py',
         'test_demo.py', 'audit.py']


def _stdio():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def main():
    _stdio()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    bad = []
    for name in TESTS:
        p = subprocess.run([sys.executable, os.path.join(HERE, name)],
                           cwd=HERE, env=env, capture_output=True)
        out = (p.stdout + p.stderr).decode('utf-8', 'replace').strip()
        ok = p.returncode == 0
        print(f'{"PASS" if ok else "FAIL"}  {name}')
        if not ok:
            bad.append(name)
            for line in out.splitlines()[-8:]:
                print('        ' + line)
    total = len(TESTS)
    print(f'\n{total - len(bad)}/{total} 通过'
          + ('' if not bad else '；失败：' + '、'.join(bad)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
