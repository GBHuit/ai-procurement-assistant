#!/usr/bin/env python3
"""AI采购助理 - 比价与TCO（总拥有成本）计算"""
from __future__ import annotations
from .models import LineItem, SupplierQuote, ComparisonRow

ANNUAL_COST_RATE = 0.05  # 资金成本年化5%（账期占用的资金成本）
FREIGHT_FALLBACK = 0.03  # 未单独报运费时，按货值3%估算


def _freight_total(q: SupplierQuote) -> float:
    """整单运费总额：已含运费为0，未含按报价或默认比例"""
    if q.freight_inc:
        return 0.0
    if q.freight is not None and q.freight > 0:
        return q.freight
    return q.item_total * FREIGHT_FALLBACK


def _payment_cost(q: SupplierQuote, amount: float) -> float:
    """账期资金成本：月结N天 -> 占用金额 × 年化 × 天数/360"""
    if not q.payment:
        return 0.0
    m = __import__("re").search(r"(\d+)", q.payment or "")
    if not m:
        return 0.0
    days = float(m.group(1))
    return amount * ANNUAL_COST_RATE * days / 360.0


def compare(quotes: list[SupplierQuote]) -> list[ComparisonRow]:
    """按 品名+规格 归并各供应商报价，计算单价/小计/运费分摊/TCO"""
    # 收集所有物料
    items: dict[tuple[str, str], tuple[str, str, int]] = {}
    for q in quotes:
        for it in q.items:
            items.setdefault((it.item, it.spec), (it.item, it.spec, it.qty))

    # 预计算每家整单运费（按货值比例分摊到各物料，避免重复计数）
    freight_totals = {q.supplier: _freight_total(q) for q in quotes}

    rows: list[ComparisonRow] = []
    for (item, spec, qty) in items.values():
        row = ComparisonRow(item=item, spec=spec, qty=qty)
        for q in quotes:
            it = next((i for i in q.items if i.item == item and i.spec == spec), None)
            if not it:
                continue
            freight_share = (freight_totals[q.supplier] * it.subtotal / q.item_total
                             if q.item_total > 0 else 0.0)
            payment_cost = _payment_cost(q, it.subtotal)
            tco = it.subtotal + freight_share + payment_cost
            row.quotes[q.supplier] = {
                "unit_price": it.unit_price,
                "subtotal": it.subtotal,
                "freight_share": round(freight_share, 2),
                "payment_cost": round(payment_cost, 2),
                "tco": round(tco, 2),
            }
        rows.append(row)
    return rows


def summarize(rows: list[ComparisonRow]) -> dict:
    """整单汇总：每家供应商的总价与TCO"""
    totals: dict[str, dict] = {}
    for row in rows:
        for sup, d in row.quotes.items():
            t = totals.setdefault(sup, {"total": 0.0, "tco": 0.0, "freight": 0.0})
            t["total"] += d["subtotal"]
            t["tco"] += d["tco"]
            t["freight"] += d["freight_share"]
    for t in totals.values():
        t["total"] = round(t["total"], 2)
        t["tco"] = round(t["tco"], 2)
    return totals
