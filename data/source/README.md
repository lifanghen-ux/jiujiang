# 模拟数据源

本目录保存成员 B 交付的 200 家虚构供应商模拟数据，导入日期为 2026-09-07。

数据仅用于竞赛原型、模型训练和系统测试，不包含真实银行业务数据。成员 B 原始交付的七张 CSV 属于同一批次：

- `suppliers.csv`
- `contracts.csv`
- `projects.csv`
- `bank_systems.csv`
- `risk_events.csv`
- `rectify_records.csv`
- `weekly_snapshot.csv`

经独立复算，10,400 条周度记录的事件数量、风险分数、整改状态和未来三周升级标签与上游生成规则一致。

成员 C 另行增加 `leading_indicators.csv`，用于验证“如果银行能提供风险发生前的 SLA、延期、人员、工单、可用率、投诉和舆情数据，模型能否利用这些信号”。它不修改原始七张表，全部记录均标记为 `is_simulated=true`，版本为 `LEADING-SIM-V0.1`。

该文件由以下命令确定性生成：

```powershell
python scripts/generate_leading_indicators.py
```

这些指标是模拟场景假设，不得解释为银行真实数据或真实效果。
