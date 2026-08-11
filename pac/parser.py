#!/usr/bin/env python3
"""AI采购助理 - 多格式报价解析：CSV / 邮件文本TXT / Excel XLSX -> SupplierQuote"""
from __future__ import annotations
import csv
import os
import re
from .models import LineItem, SupplierQuote

# 常见中文表头 -> 标准字段
HEADER_MAP = {
    "品名": "item", "物料名称": "item", "产品名称": "item", "名称": "item",
    "规格": "spec", "型号": "spec",
    "数量": "qty", "采购数量": "qty", "需求数量": "qty",
    "单价": "unit_price", "含税单价": "unit_price", "报价": "unit_price", "价格": "unit_price",
    "起订量": "moq", "最小起订量": "moq",
    "交期": "lead_time", "交货期": "lead_time", "交期(天)": "lead_time",
    "账期": "payment", "付款条件": "payment", "付款方式": "payment",
    "运费": "freight", "物流费": "freight",
    "有效期": "validity", "报价有效期": "validity",
}


def _norm_header(h: str) -> str:
    h = h.strip().lower()
    return HEADER_MAP.get(h, h)


def parse_csv(path: str) -> SupplierQuote:
    """解析结构化CSV：第一行为表头（中文亦可）"""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f))
    headers = list(rows[0].keys()) if rows else []
    cols = {_norm_header(h): h for h in headers}
    supplier = os.path.splitext(os.path.basename(path))[0]
    q = SupplierQuote(supplier=supplier, source_file=os.path.basename(path))
    for r in rows:
        try:
            item = r.get(cols.get("item", ""), "")
            spec = r.get(cols.get("spec", ""), "")
            qty = int(float(str(r.get(cols.get("qty", ""), "0")).replace(",", "")))
            price = float(str(r.get(cols.get("unit_price", ""), "0")).replace(",", ""))
            if item and price > 0:
                q.items.append(LineItem(item=item, spec=spec, qty=qty, unit_price=price))
        except (ValueError, TypeError):
            continue
    # 附加字段（若表中有）
    for k, v in [("moq", "moq"), ("lead_time", "交期"), ("payment", "账期"),
                 ("freight", "运费"), ("validity", "有效期")]:
        if k in cols and rows and rows[0].get(cols[k]):
            val = rows[0][cols[k]]
            if k == "freight":
                if "含" in val:
                    q.freight_inc = True
                else:
                    try:
                        q.freight = float(val)
                    except ValueError:
                        pass
            else:
                setattr(q, k, val.strip())
    return q


def parse_xlsx(path: str) -> SupplierQuote:
    """解析Excel报价单（pandas + openpyxl），兼容多sheet取第一个有数据的"""
    import pandas as pd
    supplier = os.path.splitext(os.path.basename(path))[0]
    q = SupplierQuote(supplier=supplier, source_file=os.path.basename(path))
    df = pd.read_excel(path, sheet_name=None, dtype=str)
    for sheet, data in df.items():
        data = data.dropna(how="all")
        if data.empty:
            continue
        headers = [str(c).strip() for c in data.columns]
        cols = {_norm_header(h): h for h in headers}
        if "item" not in cols and "unit_price" not in cols:
            continue
        for _, r in data.iterrows():
            try:
                item = str(r.get(cols.get("item", ""), "") or "")
                spec = str(r.get(cols.get("spec", ""), "") or "")
                qty = int(float(str(r.get(cols.get("qty", ""), "0")).replace(",", "")))
                price = float(str(r.get(cols.get("unit_price", ""), "0")).replace(",", ""))
                if item and item != "nan" and price > 0:
                    q.items.append(LineItem(item=item, spec=spec, qty=qty, unit_price=price))
            except (ValueError, TypeError):
                continue
        if q.items:
            break
    # 附加字段（若表中有）
    for k, v in [("moq", "moq"), ("lead_time", "交期"), ("payment", "账期"),
                 ("freight", "运费"), ("validity", "有效期")]:
        if k in cols and len(data) and data.iloc[0].get(cols[k]) is not None:
            val = str(data.iloc[0][cols[k]]).strip()
            if k == "freight":
                if "含" in val:
                    q.freight_inc = True
                else:
                    try:
                        q.freight = float(val)
                    except ValueError:
                        pass
            else:
                setattr(q, k, val)
    return q


def parse_txt_email(path: str) -> SupplierQuote:
    """解析非结构化邮件文本：正则抓供应商名、物料行、交易条款"""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    supplier = os.path.splitext(os.path.basename(path))[0]
    # 去掉邮件头
    q = SupplierQuote(supplier=supplier, source_file=os.path.basename(path), raw_text=text)

    # 供应商名（"XX公司"或"XX实业"等）——取最长匹配，避免匹配到主题行短名
    names = re.findall(r"([\u4e00-\u9fa5A-Za-z0-9]{2,15}(?:公司|实业|包装|纸业|集团|厂))", text)
    if names:
        q.supplier = max(names, key=len)

    # 交易条款
    m = re.search(r"起订量[量为:：]?\s*(\d+[万k个件]*)", text)
    if m:
        q.moq = m.group(1)
    m = re.search(r"交期[为:：]?\s*(\d+[-~至]?\d*\s*天)", text)
    if m:
        q.lead_time = m.group(1)
    m = re.search(r"(?:账期|月结|付款方式)[为:：]?\s*([^\n，。;；]{2,20})", text)
    if m:
        q.payment = m.group(1).strip()
    m = re.search(r"运费[为:：]?\s*(?:约|大概)?\s*(\d+(?:\.\d+)?)\s*元", text)
    if m:
        q.freight = float(m.group(1))
    m = re.search(r"有效期[为:：]?\s*([^\n。;；]{2,15})", text)
    if m:
        q.validity = m.group(1).strip()

    # 物料行：匹配「名称+规格+数量+单价」组合
    # 例：五层瓦楞纸箱 60*40*40cm 10000个 单价4.20元
    blacklist = ("起订", "交期", "运费", "有效期", "报价", "含税", "单价", "数量")
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z]{2,20}?)\s*"
        r"([0-9*×xX\-–—.]{3,20}cm|[\u4e00-\u9fa5]{1,6}克|[\u4e00-\u9fa5]{1,6}层)?\s*"
        r"(\d[\d,]*)\s*(?:个|只|件|套|pcs|PCS)?\s*"
        r"(?:单价|价格|报价)?[为:：]?\s*([1-9]\d*(?:\.\d+)?)\s*元",
        text,
    ):
        item, spec, qty, price = m.group(1), m.group(2) or "", m.group(3), m.group(4)
        if any(b in item for b in blacklist):
            continue
        q.items.append(LineItem(
            item=item, spec=spec,
            qty=int(qty.replace(",", "")),
            unit_price=float(price),
        ))
    return q


def parse_any(path: str) -> SupplierQuote:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return parse_csv(path)
    if ext == ".xlsx":
        return parse_xlsx(path)
    if ext in (".txt", ".md", ".eml"):
        return parse_txt_email(path)
    raise ValueError(f"不支持的文件格式: {ext}")
