#!/usr/bin/env python3
"""门禁脚本：括号边界检查。

范文的括号只允许三种：术语定义（纯英文缩写）、数值补值（以数字开头）、
文献编号 [12]/[12,13]。其余括号一律判解释性括号。

用法: python check_parens.py <草稿.md>
退出码: 0 = 通过, 1 = 存在违规
"""
import re
import sys
import argparse

ABBR_RE = re.compile(r"^[A-Za-z0-9&\.\-\+/]{1,20}$")
# 数值补值：以数字开头，只含数字/单位/分隔符，如 "(1.8 dB, 0.123)" "(0.107)" "(24k)"→不允许k
NUM_RE = re.compile(
    r"^\d[\d\.,\s\-–~%×/]*(dB|kHz|Hz|ms|MiB|G|K|s|G/s|kHz)*[\d\.,\s\-–~%×/]*$",
    re.IGNORECASE,
)
CITE_RE = re.compile(r"^[\d,\s\-]+$")


def classify(inner: str) -> str:
    s = inner.strip()
    if not s:
        return "空括号"
    if ABBR_RE.match(s):
        return "ok:术语缩写"
    if NUM_RE.match(s):
        return "ok:数值补值"
    return "解释性括号"


def check(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()

    fails = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith((">", "---", "|")):
            continue
        for m in re.finditer(r"[（(]([^（()）]*)[)）]", line):
            kind = classify(m.group(1))
            if kind.startswith("ok"):
                continue
            fails.append((lineno, m.group(0), kind))
        # 方括号只允许文献编号
        for m in re.finditer(r"\[([^\[\]]*)\]", line):
            if not CITE_RE.match(m.group(1).strip()):
                fails.append((lineno, m.group(0), "方括号内容非文献编号"))
        # 正文不应出现全角括号包裹的非术语内容已在上面覆盖；【】标记不允许出现在正文
        for m in re.finditer(r"【[^】]*】", line):
            fails.append((lineno, m.group(0), "正文出现【】标记"))
        # 嵌套括号：外层必然是解释性的
        if len(re.findall(r"[（(]", line)) >= 2 and re.search(r"[（(][^（）()]*[（(]", line):
            fails.append((lineno, line.strip()[:40], "嵌套括号（外层必为解释性）"))

    print(f"== 括号边界检查: {path} ==")
    if fails:
        print(f"[FAIL] 违规 {len(fails)} 处（解释性内容写进正文；若是骨架没排够，回卡片补节点）:")
        for lineno, text_, kind in fails:
            print(f"  L{lineno}: {text_}  ← {kind}")
        return 1
    print("[PASS] 括号只用于术语缩写、数值补值、文献编号")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="待检查的草稿/定稿 markdown")
    args = ap.parse_args()
    sys.exit(check(args.file))
