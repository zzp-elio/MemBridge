# Task-032: README.md 双语化改造（英文为主版本，中文为可选版本）

- **状态**：✅ Completed
- **目标**：
  1. 实现双语文档体系：将主入口 [`README.md`](../../README.md) 重构为专业、地道、结构严密的英文版本；
  2. 将原有完备的中文文档提取并沉淀为 [`README_zh.md`](../../README_zh.md)；
  3. 在两个版本顶部均添加清晰的双语导航切换栏：`[English](README.md) | [简体中文](README_zh.md)`；
  4. 扩展自动化文档门禁契约测试 [`tests/test_end_to_end_pipeline.py`](../../tests/test_end_to_end_pipeline.py)，将 `README_zh.md` 纳入 `core_docs` 巡检，确保双语文档中的所有相对链接与代码路径真实存在、不发生漂移；
  5. 沉淀 ADR-028（双语架构文档规范与国际化门禁）至 [`docs/decisions.md`](../decisions.md)；
  6. 运行 `uv run pytest -q` 确保所有 28+ 门禁测试全绿，完成 Git 提交并推送。

## Checklist

- [x] 立项并在 [`STATE.md`](../../STATE.md) 挂载任务卡
- [x] 创建并校验 [`README_zh.md`](../../README_zh.md)（保留现有完备中文内容并添加语言切换栏）
- [x] 重构主入口 [`README.md`](../../README.md) 为高质量全英文版本（保持结构、表格、接口规范与图表完全对齐）
- [x] 在 [`tests/test_end_to_end_pipeline.py`](../../tests/test_end_to_end_pipeline.py) 中将 `README_zh.md` 纳入文档防漂移测试
- [x] 沉淀架构决策 ADR-028 至 [`docs/decisions.md`](../decisions.md)
- [x] 运行 `uv run pytest -q` 验证全部测试通过（包含文档门禁）
- [x] 更新 [`STATE.md`](../../STATE.md) 与本任务卡状态为 Completed
- [ ] 执行 Git commit 与 push
