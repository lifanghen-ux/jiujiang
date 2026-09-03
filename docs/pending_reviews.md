# 待复核事项

## 成员 B 梁雨珊

- [ ] 正式 CSV 输出时间、目录和版本；
- [ ] `weekly_snapshot.csv` 最终字段、类型与主键；
- [ ] `risk_events.csv` 是否完整包含 evidence、severity、category、week；
- [ ] `upgrade_label` 是否由脚本严格按 t+1 至 t+3 生成；
- [ ] rolling window、SLA、延期和关键人员字段的原始数据支持情况。

## 赵文雅

- [ ] Evidence PASS/FAIL 的确定性规则；
- [ ] `rectify_id` 与 `evidence_id` 的证据表达；
- [ ] Agent Trace 的最小必要字段、脱敏和权限；
- [ ] 中高风险人工确认与业务门禁；
- [ ] RAG 制度文件、处置规则的来源和授权范围。

## 全组

- [ ] 是否新增 `upgrade_probability: float [0,1]`；
- [ ] `risk_level` 生成方、阈值和红线规则；
- [ ] “管理”是否加入正式风险类别；
- [ ] `agent_judge_log` 与 `agent_reason_log` 的职责；
- [ ] 正式 Agent JSON schema 版本。

