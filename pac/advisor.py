#!/usr/bin/env python3
"""AI采购助理 - LLM议价顾问：基于比价数据生成谈判策略"""
from __future__ import annotations
import json
import os

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = os.environ.get("PROCUREMENT_LLM", "deepseek-ai/DeepSeek-V4-Pro")

SYSTEM_PROMPT = """你是资深采购谈判顾问，服务过世界五百强制造企业，精通供应商管理、成本拆解与议价策略。
你的任务：基于多供应商报价数据，输出可执行的议价方案。要求：
1. 数据说话：所有判断必须引用报价数据（单价、MOQ、交期、账期、运费），不许空谈
2. 结构清晰：每家供应商分别给出——可议价空间判断（高/中/低+理由）、具体砍价点、可交换筹码、风险提示
3. 最后给出整体策略：主供/替补分配建议、下单节奏、二次询价建议
4. 用中文输出，markdown 格式，简洁专业，不寒暄"""


def build_prompt(quotes_json: str, compare_json: str) -> str:
    return f"""以下是本次采购的报价数据：

【各供应商完整报价】
{quotes_json}

【比价与TCO计算】
{compare_json}

请生成议价要点报告。"""


def _call_llm(prompt: str, api_key: str, timeout: int = 120) -> str:
    import requests
    resp = requests.post(
        API_URL,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def advise(quotes: list, rows: list, totals: dict) -> str:
    """生成议价报告。quotes/rows/totals 为 parser/compare 产物"""
    api_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if not api_key:
        return "> ⚠️ 未设置 SILICONFLOW_API_KEY，跳过LLM议价（仅输出比价）。"

    quotes_json = json.dumps(
        [{
            "供应商": q.supplier,
            "来源文件": q.source_file,
            "物料": [{"品名": i.item, "规格": i.spec, "数量": i.qty,
                       "单价": i.unit_price, "小计": round(i.subtotal, 2)}
                      for i in q.items],
            "起订量": q.moq, "交期": q.lead_time, "账期": q.payment,
            "运费": q.freight, "报价有效期": q.validity,
        } for q in quotes],
        ensure_ascii=False, indent=1,
    )
    compare_json = json.dumps(
        [{
            "物料": r.item, "规格": r.spec, "数量": r.qty,
            "各家": {k: v for k, v in r.quotes.items()},
        } for r in rows] + [{"整单汇总(TCO)": totals}],
        ensure_ascii=False, indent=1,
    )
    try:
        return _call_llm(build_prompt(quotes_json, compare_json), api_key)
    except Exception as e:
        return f"> ⚠️ LLM调用失败（{e}），仅输出比价结果。"
