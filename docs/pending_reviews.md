# 待复核事项

## 成员 B 梁雨珊

- [ ] 确认 2026-09-07 收到的 7 张 CSV 是否作为正式模拟数据 V1；成员 C 自检已通过；
- [ ] 确认 `weekly_snapshot.csv` 当前 7 个字段是否为最终接口版本；成员 C 已验证 `(supplier_id, week)` 无重复；
- [ ] 确认 `risk_events.csv` 当前 7 个字段是否为最终接口版本；现有 evidence、severity、category、week 均非空；
- [ ] 复核 `upgrade_label` 生成口径；成员 C 按 t+1 至 t+3 全量重算，10,400 行零差异；
- [ ] 决定是否补充 SLA、延期和关键人员等原始字段；当前数据只能实现事件、分值、整改和业务暴露相关特征。

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
