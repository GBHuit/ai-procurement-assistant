#!/usr/bin/env python3
"""AI采购助理 - Markdown报告生成"""
from __future__ import annotations
import datetime


def _money(x: float) -> str:
    return f"{x:,.2f}"


def build_report(quotes, rows, totals, advice: str = "") -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = [
        "# AI采购助理 · 比价与议价报告",
        "",
        f"> 生成时间：{now}  |  供应商：{', '.join(q.supplier for q in quotes)}",
        "",
        "---",
        "",
        "## 一、整单汇总（TCO口径）",
        "",
        "| 供应商 | 货值合计 | 运费分摊 | 账期资金成本 | **TCO总成本** |",
        "|---|---|---|---|---|",
    ]
    for sup, t in sorted(totals.items(), key=lambda x: x[1]["tco"]):
        L.append(f"| {sup} | {_money(t['total'])} | {_money(t['freight'])} | "
                 f"{_money(t['tco'] - t['total'] - t['freight'])} | **{_money(t['tco'])}** |")
    L += ["", "---", "", "## 二、逐物料比价", ""]
    for r in rows:
        L.append(f"### {r.item} {r.spec}  × {r.qty:,}")
        L.append("")
        L.append("| 供应商 | 单价 | 小计 | 运费分摊 | 账期成本 | TCO |")
        L.append("|---|---|---|---|---|---|")
        for sup, d in sorted(r.quotes.items(), key=lambda x: x[1]["tco"]):
            L.append(f"| {sup} | {_money(d['unit_price'])} | {_money(d['subtotal'])} | "
                     f"{_money(d['freight_share'])} | {_money(d['payment_cost'])} | "
                     f"**{_money(d['tco'])}** |")
        L.append("")
    L += ["---", "", "## 三、供应商详情", ""]
    for q in quotes:
        L.append(f"### {q.supplier}（{q.source_file}）")
        L.append("")
        info = [f"- 起订量：{q.moq or '未注明'}", f"- 交期：{q.lead_time or '未注明'}",
                f"- 账期：{q.payment or '未注明'}", f"- 运费：{q.freight if q.freight else '未单独报价'}",
                f"- 有效期：{q.validity or '未注明'}"]
        L += info + [""]
    if advice:
        L += ["---", "", "## 四、LLM议价策略", "", advice, ""]
    return "\n".join(L)
