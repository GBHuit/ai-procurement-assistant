#!/usr/bin/env python3
"""AI采购助理 - PDF报价单解析：文字层直提 / 扫描版OCR → LLM结构化 → SupplierQuote"""
from __future__ import annotations
import json, os, re, time
import pymupdf
from .models import LineItem, SupplierQuote

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
OCR_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
STRUCT_MODEL = os.environ.get("PROCUREMENT_LLM", "deepseek-ai/DeepSeek-V4-Pro")

STRUCT_PROMPT = """你是一个采购数据抽取引擎。从以下PDF报价单文本中提取标准化报价信息，输出JSON。

输出格式（严格按此JSON结构）：
{
  "supplier": "供应商公司名（从文本中提取，若找不到用文件名）",
  "items": [
    {"item": "品名", "spec": "规格（含尺寸/克重/型号）", "qty": 整数, "unit_price": 数字}
  ],
  "moq": "起订量（原样文本）",
  "lead_time": "交期（原样文本）",
  "payment": "付款条件/账期（原样文本）",
  "freight": "运费金额或'含运费'字样（原样文本）",
  "validity": "报价有效期（原样文本）",
  "notes": "其他关键条款"
}

规则：
- 只输出JSON，不要任何解释文字
- 物料行的品名、规格、数量、单价必须一一对应
- 若文本中找不到某字段，填null
- 金额数字保留原始精度（如4.20不要简化成4.2）"""


def _call_llm(messages: list, api_key: str, model: str, timeout: int = 180) -> str:
    import requests
    resp = requests.post(
        API_URL,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": 3000, "temperature": 0.1},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _extract_text_layer(path: str) -> tuple[str, int]:
    """pymupdf提取所有页文本，返回(全文, 页数)"""
    doc = pymupdf.open(path)
    text = "\n".join(f"--- 第{i+1}页 ---\n{page.get_text()}" for i, page in enumerate(doc))
    n = len(doc)
    doc.close()
    return text.strip(), n


def _has_text_layer(path: str, sample_pages: int = 4) -> bool:
    """采样判定是否有文字层"""
    doc = pymupdf.open(path)
    n = len(doc)
    idxs = sorted(set([0, n // 2, n - 1]))[:sample_pages]
    has = any(len(doc[i].get_text().strip()) > 50 for i in idxs)
    doc.close()
    return has


def _ocr_page(pdf_path: str, page_num: int, api_key: str) -> str:
    """单页OCR（base64图片 → Qwen3-VL）"""
    import base64, io, requests
    doc = pymupdf.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpg", jpg_quality=85)
    b64 = base64.b64encode(img_bytes).decode()
    doc.close()
    resp = requests.post(
        API_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={
            "model": OCR_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": "请逐行输出这张报价单上的全部文本内容，包括表格中的所有数据。不要遗漏任何数字和文字。不要总结，只输出原文。"},
                ],
            }],
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _ocr_all_pages(pdf_path: str, api_key: str) -> str:
    doc = pymupdf.open(pdf_path)
    total = len(doc)
    doc.close()
    texts = []
    for i in range(total):
        t = _ocr_page(pdf_path, i, api_key)
        texts.append(f"--- 第{i+1}页 ---\n{t}")
        if i < total - 1:
            time.sleep(0.5)
    return "\n".join(texts)


def _parse_llm_json(raw: str) -> dict:
    """从LLM响应中提取JSON（容错：去掉markdown代码块）"""
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError(f"LLM未返回有效JSON: {raw[:200]}")
    return json.loads(m.group())


def parse_pdf(path: str) -> SupplierQuote:
    """解析PDF报价单（自动分流文字层/扫描版）"""
    api_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未设置 SILICONFLOW_API_KEY，PDF解析需要该密钥")

    supplier_fallback = os.path.splitext(os.path.basename(path))[0]

    # 判定文字层/扫描版
    if _has_text_layer(path):
        text, pages = _extract_text_layer(path)
        source_hint = f"文字层{pages}页"
    else:
        print(f"    -> 扫描版，启动OCR（{os.path.getsize(path)/1e6:.1f}MB）…")
        text = _ocr_all_pages(path, api_key)
        source_hint = f"扫描版OCR"

    # LLM结构化
    raw = _call_llm(
        [{"role": "user", "content": f"{STRUCT_PROMPT}\n\nPDF文件名：{supplier_fallback}\nPDF内容：\n{text[:8000]}"}],
        api_key, STRUCT_MODEL,
    )
    data = _parse_llm_json(raw)

    # 构建 SupplierQuote
    q = SupplierQuote(
        supplier=data.get("supplier", "") or supplier_fallback,
        source_file=os.path.basename(path),
        moq=data.get("moq"),
        lead_time=data.get("lead_time"),
        payment=data.get("payment"),
        validity=data.get("validity"),
    )
    # 运费处理
    freight_raw = data.get("freight")
    if freight_raw:
        if "含" in str(freight_raw):
            q.freight_inc = True
        else:
            try:
                q.freight = float(re.sub(r"[^\d.]", "", str(freight_raw)))
            except ValueError:
                pass

    for it in data.get("items", []):
        try:
            q.items.append(LineItem(
                item=str(it.get("item", "")),
                spec=str(it.get("spec", "")),
                qty=int(it.get("qty", 0)),
                unit_price=float(it.get("unit_price", 0)),
            ))
        except (ValueError, TypeError):
            continue

    # 保留原文供后续参考
    q.raw_text = f"来源: {source_hint}"
    return q
