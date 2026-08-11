#!/usr/bin/env python3
"""AI采购助理 - 数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineItem:
    """一行物料报价"""
    item: str            # 品名
    spec: str            # 规格
    qty: int             # 数量
    unit_price: float    # 单价（人民币）
    note: str = ""

    @property
    def subtotal(self) -> float:
        return self.qty * self.unit_price


@dataclass
class SupplierQuote:
    """一家供应商的完整报价"""
    supplier: str
    source_file: str
    items: list[LineItem] = field(default_factory=list)
    moq: Optional[str] = None          # 起订量
    lead_time: Optional[str] = None    # 交期
    payment: Optional[str] = None      # 账期/付款条件
    freight: Optional[float] = None    # 运费总额（单独计价）
    freight_inc: bool = False          # 单价是否已含运费
    tax_rate: float = 0.0              # 税率（0.13 = 13%）
    validity: Optional[str] = None     # 报价有效期
    raw_text: str = ""                 # 原始文本（邮件等，供LLM参考）

    @property
    def item_total(self) -> float:
        return sum(i.subtotal for i in self.items)


@dataclass
class ComparisonRow:
    """同一物料在多家供应商间的比价行"""
    item: str
    spec: str
    qty: int
    quotes: dict[str, dict] = field(default_factory=dict)
    # quotes: {supplier: {unit_price, subtotal, freight_share, tco}}
