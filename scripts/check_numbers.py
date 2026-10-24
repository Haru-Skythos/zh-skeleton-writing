#!/usr/bin/env python3
"""门禁脚本：数字白名单检查。

从草稿中提取所有数字（含 "a-b" 区间与千分位），与白名单比对。
表/图/式/第/节 等引导的编号自动放行。

用法: python check_numbers.py <草稿.md> <whitelist.txt>
退出码: 0 = 通过, 1 = 存在白名单外数字
"""
import re
import sys
import argparse

# 提取：普通数、小数、千分位、区间（0-3 / 100~2000 / 5–25 dB）
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?(?:\s*[-–~]\s*\d[\d,]*(?:\.\d+)?)?")
# 上下文放行：表 4 / 图 4(f) / 式 (3) / 第 1 行 / 第 1, 2 行（逗号列表中的后续数字）/ 4.2 节标题
CTX_OK = re.compile(r"[表图式第节]\s*$|第\s*[\d,\s]*$|\(\s*[a-z]\s*\)$")


def norm(tok: str) -> str:
    return tok.replace(" ", "").replace(",", "")


def extract(text: str):
    """返回 [(行号, 数字token, 是否上下文放行)]"""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # 章节标题（如 "## 4.2 ..."）里的编号放行
        heading = stripped.startswith("#")
        for m in NUM_RE.finditer(line):
            tok = m.group(0)
            prefix = line[: m.start()]
            ok = heading or CTX_OK.search(prefix)
            out.append((lineno, tok, ok))
    return out


def check(draft: str, whitelist: str) -> int:
    with open(draft, encoding="utf-8") as f:
        text = f.read()
    with open(whitelist, encoding="utf-8") as f:
        allowed = {norm(l.strip()) for l in f if l.strip()}

    fails, seen = [], set()
    for lineno, tok, ok in extract(text):
        if ok:
            continue
        n = norm(tok)
        seen.add(n)
        if n not in allowed:
            fails.append((lineno, tok))

    print(f"== 数字白名单检查: {draft} ==")
    print(f"    白名单 {len(allowed)} 项，正文实际用到 {len(seen & allowed)} 项")
    if fails:
        print(f"[FAIL] 白名单外数字 {len(fails)} 处（回 brief 核对，禁止现场改数）:")
        for lineno, tok in fails:
            print(f"  L{lineno}: {tok}")
        return 1
    print("[PASS] 所有数字均在白名单内")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("whitelist")
    args = ap.parse_args()
    sys.exit(check(args.draft, args.whitelist))
