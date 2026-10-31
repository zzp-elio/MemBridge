# MemBridge 状态路由面板 (`STATE.md`)

> **面板规范**：单点聚焦与结构清晰，记录定位、核心导航与活跃任务一句话摘要及链接。细节存放在 [`docs/tasks/`](docs/tasks/)。

## 1. 项目定位与核心导航
面向 AI Agent 长期记忆系统的 **C/S 架构标准化端到端 QA 评测中间层**。
- **宪章与红线** 👉 [`AGENTS.md`](AGENTS.md) | **系统架构** 👉 [`docs/architecture.md`](docs/architecture.md) | **架构决策** 👉 [`docs/decisions.md`](docs/decisions.md)

## 2. 任务看板（Task Routing）
- **当前活跃任务（Active）**：
  - 🟢 暂无进行中的活跃任务（准备就绪）。
- **历史已完成任务（Completed）**：
  - ✅ [`docs/tasks/task-034-result-integrity.md`](docs/tasks/task-034-result-integrity.md)：评测结果可信度修复。37 passed。幂等键只保证客户端发送和 Mock 去重；不新增删除命名空间接口。
  - ✅ [`docs/tasks/task-033-english-architecture-diagram.md`](docs/tasks/task-033-english-architecture-diagram.md)：架构全景图英文版制作与双语文档对齐。
  - ✅ [`docs/tasks/task-032-bilingual-readme.md`](docs/tasks/task-032-bilingual-readme.md)：README.md 双语化改造（英文为主版本，中文为可选版本）。
  - ✅ [`docs/tasks/task-031-rebrand-to-membridge.md`](docs/tasks/task-031-rebrand-to-membridge.md)：项目品牌全面升级为 MemBridge 与仓库重命名。
  - ✅ [`docs/tasks/task-030-clean-architecture-section-and-explain-f1.md`](docs/tasks/task-030-clean-architecture-section-and-explain-f1.md)：清理 README 压缩 Mermaid、解耦外部记忆抽象与 Token-Level F1 评测机理解析。
  - ✅ [`docs/tasks/task-029-readme-restructure-and-architecture-visual.md`](docs/tasks/task-029-readme-restructure-and-architecture-visual.md)：README 章节结构逻辑调优、延迟对比呈现与学术级架构图生成。
  - ✅ [`docs/tasks/task-028-fix-mermaid-latency-and-session-ordering.md`](docs/tasks/task-028-fix-mermaid-latency-and-session-ordering.md)：修复 Mermaid 渲染错误、明确客户端防作弊耗时度量与同会话顺序传递保证。
  - ✅ [`docs/tasks/task-027-remove-mock-cli-concurrency-and-entity-docs.md`](docs/tasks/task-027-remove-mock-cli-concurrency-and-entity-docs.md)：彻底废除公开 Mock 模式、补充接口实体规范与服务端并发处理体系。
  - ✅ [`docs/tasks/task-026-ultra-lean-smoke-and-connectivity.md`](docs/tasks/task-026-ultra-lean-smoke-and-connectivity.md)：--smoke 极简微抽样（1 会话 1 Session 1 题）与连通性验证完善。
  - ✅ [`docs/tasks/task-025-subcommand-pipeline-and-smoke.md`](docs/tasks/task-025-subcommand-pipeline-and-smoke.md)：子命令流水线解耦（run / ingest / query / eval）、--smoke 极简封装与参数耦合消除。
  - ✅ [`docs/tasks/task-024-streamline-cli-and-git-commit.md`](docs/tasks/task-024-streamline-cli-and-git-commit.md)：极致精简 CLI 参数与开源门面收口。
  - ✅ [`docs/tasks/task-023-cli-parameter-refinement-and-readme-table.md`](docs/tasks/task-023-cli-parameter-refinement-and-readme-table.md)：CLI 命令行参数精细化分组与 README 完整参数表呈现。
  - ✅ [`docs/tasks/task-022-full-audit-and-defect-fixes.md`](docs/tasks/task-022-full-audit-and-defect-fixes.md)：项目全量体检与潜在缺陷修复（MemBench 截断崩溃、CLI 客户端判定、0 warnings）。
  - ✅ [`docs/tasks/task-021-readme-structure-and-execution-guide.md`](docs/tasks/task-021-readme-structure-and-execution-guide.md)：README.md 目录结构说明与 C/S 运行指南重构。
  - ✅ [`docs/tasks/task-020-env-and-git-scope.md`](docs/tasks/task-020-env-and-git-scope.md)：环境变量改为 API_KEY / BASE_URL / MODEL_NAME，Git 只跟踪评测端。
  - ✅ [`docs/tasks/task-019-cohort-and-benchmark-load.md`](docs/tasks/task-019-cohort-and-benchmark-load.md)：五个基准可加载，总分与 6 类使用同一题集。
  - ✅ [`docs/tasks/task-018-six-capability-types.md`](docs/tasks/task-018-six-capability-types.md)：11 类能力图谱收成 6 类评测类型。
  - ✅ [`docs/tasks/task-017-lightmem-official-full-parity-reproduction.md`](docs/tasks/task-017-lightmem-official-full-parity-reproduction.md)：LightMem 官方 1:1 全要素复现（全量 1540 题实测 ACC 70.26%、F1 49.41%，完美吻合论文 71.95%）。
  - ✅ [`docs/tasks/task-016-locomo-multimodal-and-speaker-fidelity.md`](docs/tasks/task-016-locomo-multimodal-and-speaker-fidelity.md)：LoCoMo 多模态图像描述与说话人保真度端到端重构。
  - ✅ [`docs/tasks/task-015-reproduce-lightmem-locomo-author-parity.md`](docs/tasks/task-015-reproduce-lightmem-locomo-author-parity.md)：LightMem LoCoMo 72% 作者满血配置复现实验。
  - ✅ [`docs/tasks/task-014-locomo-high-concurrency-llm-judge.md`](docs/tasks/task-014-locomo-high-concurrency-llm-judge.md)：LoCoMo 题型隐式推断标签修正与 20 线程高并发 LLM Judge 评测。
  - ✅ [`docs/tasks/task-013-concurrent-conversation-prediction-runner.md`](docs/tasks/task-013-concurrent-conversation-prediction-runner.md)：LoCoMo 10 个独立 Conversation 并发评测运行器与 CLI 支持。
  - ✅ [`docs/tasks/task-011~012`](docs/tasks/)：时间题 Prompt 优化与冒烟测试。
  - ✅ [`docs/tasks/task-005~010`](docs/tasks/)：Prompt 矩阵、双模式 Judge、容器化 HTTP 服务、统一 11 维图谱、反射配置。
  - ✅ [`docs/tasks/task-001~004`](docs/tasks/)：中间层协议、代码深度瘦身、CLI 极简化。
