# Task-029: README 章节结构逻辑调优、延迟对比呈现与学术级架构图生成

- **状态**：✅ Done
- **目标**：
  1. 优化 `README.md` 整体阅读结构，从「定位 -> 架构图 -> 评测题 -> 目录结构 -> 接口实体规范 -> 并发处理 -> 运行与参数 -> 场景示例」自然展开；
  2. 移除 `latency_ms` 的防作弊说辞，改为客观事实阐述：客户端本地记录网络往返耗时，若服务端返回内部耗时则共同记录，便于双向对比与网络分析；
  3. 使用 AI 生图（`image-generator`）生成学术级【暖色手账/白板手绘风】16:9 全景系统架构示意图，存放于 `assets/` 目录并纳入 Git 版本追踪；
  4. 保持代码与文档契约防漂移测试全绿，收口提交并推送到 GitHub 远程仓库。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 调用 `image-generator` 智能体并发生成 16:9 暖色手账风学术全景架构图
- [x] 创建 `assets/` 目录，将生成的架构图保存为 `assets/architecture.png`
- [x] 修改 `.gitignore` 允许跟踪 `!assets/` 与 `!assets/**`
- [x] 重构 `README.md` 章节顺序，嵌入架构图，更新延迟对比说明
- [x] 沉淀架构决策至 `docs/decisions.md` (ADR-025)
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 收口任务，更新 `STATE.md`
