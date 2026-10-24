#!/usr/bin/env python3
"""门禁脚本：禁用词检查。查自造词、口语比喻、英文直译句式、英文技术词残留。

用法: python check_words.py <草稿.md>
退出码: 0 = 通过(或仅提示项), 1 = 存在硬违规
"""
import re
import sys
import argparse

# 硬违规：自造词（被项目用成术语、范文里找不到）
BANNED_WORDS = {
    "口径": "指标定义 / 测量结果 / 测量条件 / 阶段",
    "兑现": "显现 / 出现 / 生效",
    "锚定": "定位 / 确定 / 扣住",
    "回撞": "承接",
    "闭环": "完整流程 / 前后接上",
    "落盘": "写入文件 / 保存",
    "赋能": "删除",
    "收车": "训练结束",
    "糊化": "相邻谐波落入同一子带、无法区分",
    "崩至": "降至",
    "拖垮": "受损",
    "猜回": "恢复",
    "贴线": "接近上限",
    "贴边": "接近上限",
    "跑稳": "稳定运行",
}

# 硬违规：英文直译句式（正则）
BANNED_PATTERNS = [
    (r"唯一变量是", "只改变… / 除…外其余条件不变"),
    (r"推进到(第?[一二三1-3]?\s*阶段|Stage)", "进入… / 转到…"),
    (r"需要单独排序", "要单独考察 / 分别比较"),
    (r"测的是", "反映的是"),
    (r"被用于", "用于 / 借助"),
    (r"进行了[^，。；]{0,12}的分析", "分析了…"),
    (r"在[^，。；]{1,12}方面[，,，]?", "直接说具体对象"),
    (r"Stage\s*[12]", "第一阶段 / 第二阶段"),
    (r"\d+k\s*步", "数字写全，如 30,000 步"),
    (r"\d+k\s*参数", "数字写全"),
    (r"：", "冒号展开（卡片记号渗入正文）→ 拆成完整句：其中/即/分别为/分号列举"),
    (r"做(?!出|法|到|好)", "口语动词「做」（范文零次）→ 流程用『进行+N』，瞬时用直接动词"),
    (r"(搞|弄)", "口语动词（范文零次）→ 换具体动词"),
    (r"跑(一|个|了|完|出)", "口语动词「跑」→ 训练/运行"),
]

# 提示项：视上下文决定，不自动判死
REVIEW_WORDS = {
    "维度": "作『方面/指标』讲时禁用；数学空间维度含义可保留",
    "它": "中文论文指代技术对象用『其』，检查此处指代",
    "值得注意的是": "后面必须跟非显然的具体结论，否则删",
    "不难发现": "多数情况删除",
    "给出": "范文 0 次，倾向『如表 N 所示』『实验结果表明』",
    "加入": "组件/机制进入训练用『引入』；信号与噪声物理混合可保留",
}


def check(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    hard, review = [], []
    # 段首锚点：起句应含这些叙事性起点（承接/条件/指表/操作）
    OPEN_ANCHOR = re.compile(r"(表|图|通过|对比|在|当|由于|为了|为此|因此|其中|另外|此外|随着|针对|经|若|然而|但|尽管|综合|总体上|具体而言|上述|上一|近年来|本文|所提|该|实验|仿真|训练|定义|记|设)")
    VERDICT = re.compile(r"(表明|说明|可见|证明|验证了|没有|不再|无法|仍是|优于|高于|低于|消失|补不回|确定|成立)")
    in_para = False
    verdict_count = 0
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            in_para = False
            continue
        first_of_para = not in_para
        in_para = True
        if stripped.startswith((">", "---", "|", "#")):
            continue
        for word, fix in BANNED_WORDS.items():
            for m in re.finditer(re.escape(word), line):
                hard.append((lineno, m.group(0), f"自造词 → {fix}"))
        for pat, fix in BANNED_PATTERNS:
            for m in re.finditer(pat, line):
                hard.append((lineno, m.group(0), f"直译/英文残留 → {fix}"))
        for word, note in REVIEW_WORDS.items():
            for m in re.finditer(re.escape(word), line):
                review.append((lineno, m.group(0), note))
        # 信息流启发式 1：段首裸主张（短句、句首无叙事锚点、含判断词）
        if first_of_para:
            first_sent = re.split(r"[。；:：]", stripped)[0]
            if (
                len(first_sent) < 35
                and VERDICT.search(first_sent)
                and not OPEN_ANCHOR.match(stripped[:12])
            ):
                review.append((lineno, first_sent[:20] + "…", "疑似裸主张段首（[结论]+[支持] 是英文写法）：改成起句在前、判断句末兑现"))
            elif re.search(r"[，,][^，。]*?(给出了依据|提供了依据|提供了证据|提供了支持|是其[^，。]*?(依据|证据))", stripped[:80]):
                review.append((lineno, stripped[:20] + "…", "疑似[结论]+[证据]句式（判断先行、证据垫后）：证据先行，判断句末兑现"))
        # 信息流启发式 2：逐条小结论密度
        for m in re.finditer(r"这(表明|说明)|由此可见|可见[，,]", line):
            verdict_count += 1

    print(f"== 禁用词检查: {path} ==")
    if hard:
        print(f"[FAIL] 硬违规 {len(hard)} 处:")
        for lineno, text, fix in hard:
            print(f"  L{lineno}: 「{text}」 {fix}")
    else:
        print("[PASS] 无自造词、直译句式、英文技术词残留")
    if verdict_count >= 3:
        print(f"[REVIEW] 「这表明/由此可见」共 {verdict_count} 处：逐条裁决是英文 PEEL 痕迹，全段一次裁决留给结算句")
    if review:
        print(f"[REVIEW] 需人工确认 {len(review)} 处:")
        for lineno, text, note in review:
            print(f"  L{lineno}: 「{text}」 {note}")
    return 1 if hard else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="待检查的草稿/定稿 markdown")
    args = ap.parse_args()
    sys.exit(check(args.file))
