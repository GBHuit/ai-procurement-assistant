#!/usr/bin/env python3
"""AI采购助理 - 命令行入口
用法:
  python main.py --input sample_data/           # 解析+比价+LLM议价+报告
  python main.py --input sample_data/ --no-llm  # 仅比价，不调LLM
  python main.py --input <报价文件或目录> --output report.md
"""
from __future__ import annotations
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pac.parser import parse_any          # noqa: E402
from pac.compare import compare, summarize  # noqa: E402
from pac.advisor import advise            # noqa: E402
from pac.report import build_report       # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="AI采购助理：解析报价→比价→议价策略")
    ap.add_argument("--input", required=True, help="报价文件或目录（支持csv/xlsx/txt）")
    ap.add_argument("--output", default="", help="报告输出路径（默认 output/report_时间戳.md）")
    ap.add_argument("--no-llm", action="store_true", help="跳过LLM议价，仅比价")
    args = ap.parse_args()

    # 收集输入文件
    if os.path.isdir(args.input):
        files = sorted(
            glob.glob(os.path.join(args.input, "*"))
            + glob.glob(os.path.join(args.input, "**", "*"), recursive=True)
        )
        files = [f for f in files if os.path.splitext(f)[1].lower() in (".csv", ".xlsx", ".txt", ".md")]
        files = sorted(set(files))
    else:
        files = [args.input]
    if not files:
        print("错误：未找到报价文件")
        sys.exit(1)

    # 解析
    quotes = []
    for f in files:
        try:
            q = parse_any(f)
            if q.items:
                quotes.append(q)
                print(f"  ✓ {q.supplier}: {len(q.items)}项物料 "
                      f"(货值{sum(i.subtotal for i in q.items):,.2f}元)")
            else:
                print(f"  ⚠ {os.path.basename(f)}: 未解析出物料，跳过")
        except Exception as e:
            print(f"  ✗ {os.path.basename(f)}: {e}")
    if not quotes:
        print("错误：所有文件解析失败")
        sys.exit(1)

    # 比价
    rows = compare(quotes)
    totals = summarize(rows)
    print(f"\n比价完成：{len(rows)}项物料，{len(quotes)}家供应商")

    # LLM议价
    advice = ""
    if not args.no_llm:
        print("正在调用LLM生成议价策略…")
        advice = advise(quotes, rows, totals)
        print("  ✓ 议价策略生成")

    # 报告
    out = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "output",
        "report_" + __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S") + ".md",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(build_report(quotes, rows, totals, advice))
    print(f"\n报告已生成：{out}")


if __name__ == "__main__":
    main()
