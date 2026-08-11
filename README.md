# AI 采购助理（AI Procurement Assistant）

解析供应商报价 → TCO 比价 → LLM 议价策略，一站式采购决策工具。

> 让每一次采购谈判都有数据撑腰。

## 为什么做这个

传统比价只看单价，而采购的真实成本藏在运费、账期、交期、MOQ 里。本工具以**TCO（总拥有成本）**口径统一比价，并调用大模型基于数据生成**可执行的议价策略**——每家供应商的砍价空间、目标价、可交换筹码、风险提示。

## 功能

| 能力 | 说明 |
|---|---|
| 📥 多格式解析 | CSV / Excel / Word / PDF / 邮件文本，中文表头自动识别（含"原料名称""报价（元）"等真实方言） |
| 🧩 一表多商拆分 | 市场调研表（同物料×多供应商）自动按供应商拆分，生成真实的多方比价 |
| ⚖️ TCO 比价 | 单价 × 数量 + 运费分摊 + 账期资金成本（年化5%），逐物料 & 整单双口径 |
| 🧠 LLM 议价顾问 | SiliconFlow API，输出每家供应商：可议价空间（高/中/低+数据理由）、具体砍价点、交换筹码、风险提示、主供/替补策略 |
| 📄 Markdown 报告 | 自动生成完整比价与议价报告 |

## 快速开始

```bash
# 1. 依赖
pip install -r requirements.txt

# 2. 配置密钥（议价功能需要，纯比价可跳过）
export SILICONFLOW_API_KEY=sk-xxxx          # Windows: set SILICONFLOW_API_KEY=sk-xxxx
export PROCUREMENT_LLM=deepseek-ai/DeepSeek-V4-Pro   # 可选，默认即此

# 3. 运行（解析目录内所有报价文件 → 比价 → 议价 → 报告）
python main.py --input sample_data/

# 仅比价，不调 LLM
python main.py --input sample_data/ --no-llm

# 指定输出
python main.py --input 报价单.xlsx --output result.md
```

示例输出见 `output/`，样例数据见 `sample_data/`（CSV + 邮件TXT + XLSX 三种格式）。

## 架构

```
main.py                      # CLI 入口
pac/
├── parser.py                # 多格式报价解析（csv/xlsx/txt邮件）
├── compare.py               # TCO 计算：运费分摊 + 账期资金成本
├── advisor.py               # LLM 议价策略生成（SiliconFlow）
├── report.py                # Markdown 报告
└── models.py                # 数据模型
sample_data/                 # 3家供应商样例（三种格式）
output/                      # 生成的报告
```

## TCO 口径

```
TCO = 货值(单价×数量) + 运费分摊 + 账期资金成本
账期资金成本 = 货值 × 5% × 账期天数 / 360   （未报运费按货值3%估算）
```

## 路线图

- [x] PDF 报价单解析（文字层 + LLM 结构化提取）
- [x] Word 采购记录解析 + 真实世界表头模糊识别 + 一表多商拆分
- [ ] 汇率与多币种支持（跨境采购）
- [ ] 历史报价库：同一供应商多次报价趋势与涨幅预警
- [ ] 议价话术生成：一键生成给供应商的正式还价邮件
- [ ] Web UI（Streamlit）

## 技术栈

Python 3.11 · pandas · openpyxl · requests · SiliconFlow API（DeepSeek-V4-Pro / Kimi）
