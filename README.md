# Jiujiang：银行外包供应商动态风险预测与多智能体协同骨架

本仓库是成员 C 李芳痕在接口及安全规则复核前的可运行工程骨架，覆盖：

- LangGraph 多 Agent 协同流程；
- 大模型统一调用、结构化输出校验、重试与 fallback；
- RAG 文档加载、切分、索引与可追溯检索；
- 未来 3 周风险升级标签、特征工程和模型服务接口；
- Mock 数据端到端演示与单元测试。

> 当前状态：`DRAFT / MOCK / UNTRAINED`。本仓库不包含真实银行数据，不代表 `api_contract.md` 已完成团队评审，也不输出可自动执行的正式处置决策。

## 1. 当前边界

可运行部分：

- Coordinator、Risk Identification、Association Analysis、Dynamic Prediction、Evidence、Decision、Human Review 节点；
- mock LLM 和 mock prediction；
- JSON/Pydantic 校验与错误状态；
- Evidence FAIL 阻断 Decision Agent；
- 本地可追溯 RAG 示例；
- 标签窗口、工作流门禁和结构化输出测试。

待成员 B 或赵文雅复核后再固化：

- 正式 CSV schema、rolling feature 口径和模型训练；
- `upgrade_probability` 是否写入正式 API；
- `risk_level` 阈值与风险类别枚举；
- `rectify_id` 与 `evidence_id` 的正式接口表示；
- Evidence PASS/FAIL 规则、日志权限和人工确认制度；
- 正式制度文件及处置规则知识库。

## 2. 快速启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m app.main demo
python -m pytest
```

如需安装机器学习和文档读取依赖：

```powershell
python -m pip install -e ".[ml,docs,dev]"
```

默认 `LLM_PROVIDER=mock`，无需 API Key。切换真实模型前必须通过团队的模型、数据和日志安全复核。

## 3. 命令

```powershell
# 运行端到端 mock 工作流
python -m app.main demo

# 创建并查询测试知识库
python -m app.main rag-demo

# 校验未来三周标签示例
python -m app.main label-demo

# 执行测试
python -m pytest
```

## 4. 目录结构

```text
app/
├─ agents/       # 各专业 Agent 节点
├─ common/       # 日志和通用异常
├─ llm/          # LLM provider 与结构化调用
├─ prediction/   # 数据、标签、特征、模型和解释接口
├─ rag/          # 文档加载、切分、索引和检索
├─ schemas/      # DRAFT 工作流结构体
└─ workflow/     # LangGraph 状态与编排
data/
├─ knowledge/    # 仅放已授权知识文档
├─ mock/         # 虚构测试数据
└─ index/        # 本地索引（默认不提交）
tests/           # 单元及端到端测试
```

## 5. 安全设计

- 结构化模型负责风险标签和概率；LLM 不直接生成风险分值；
- Evidence FAIL 时 Decision Agent 被强制跳过；
- Decision Agent 只生成候选建议，状态为 `PENDING_HUMAN_REVIEW`；
- 所有正式证据必须带 `evidence_id`，且不得引用未来周；
- 日志不记录 API Key，不默认保存完整内部推理；
- 未审核知识条目标记为 `is_approved=false`；
- mock 数据和输出均明确标识，不与正式数据混用。

## 6. 对接责任

- 成员 B：正式模拟数据、CSV schema、标签生成脚本和后端接口；
- 成员 C：数据验收、特征工程、模型、SHAP、多 Agent、RAG 与 LLM 封装；
- 赵文雅：Evidence 可信校验、安全权限、系统测试和材料复核；
- 全组：正式 API 新字段及业务规则变更。

详细待复核项见 [docs/pending_reviews.md](docs/pending_reviews.md)。

## 7. 免责声明

本仓库仅用于校企金融科技专项赛的虚构模拟原型，不包含真实银行客户、合同、账户、密钥或生产业务数据。

