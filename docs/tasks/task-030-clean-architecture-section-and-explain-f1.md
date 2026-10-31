# Task-030: 清理 README 压缩 Mermaid、解耦外部记忆抽象与 Token-Level F1 评测机理解析

- **状态**：✅ Completed
- **目标**：
  1. 移除 `README.md` 架构章节中导致 GitHub 压缩形变、字号过小的 Mermaid 宽流程图，聚焦高清 16:9 学术架构图与结构化 3 层解耦文字阐述；
  2. 泛化外部记忆服务抽象：架构图与文档中彻底剔除具体的“知识图谱/向量数据库”狭义标签，强调评测端对外部记忆内部演化与存储策略的“完全黑盒与范式无关性”（支持任意图谱、向量、层次摘要、时序工作记忆等）；
  3. 深入解析 Token-Level F1 分数在问答评测中的计算全流程（痛感先行、文本归一化、查准率 Precision、查全率 Recall、调和平均、边界用例与局限性），与 `src/memory_benchmark/evaluators/f1.py` 源码 1:1 机械锚定；
  4. 保持代码与文档契约防漂移测试全绿，提交并推送到 GitHub 远程仓库。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 移除 `README.md` 中冗余形变的 Mermaid 流程图，泛化三层解耦说明（强调黑盒记忆引擎）
- [x] 重新生成并替换 `assets/architecture.png`（右侧外部记忆服务解耦为通用记忆引擎，不出现具体库名）
- [x] 沉淀架构决策至 `docs/decisions.md` (ADR-026)
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 提交并推送到 GitHub 远程分支
- [x] 收口任务，更新 `STATE.md`
- [x] 向用户详细讲解 Token-Level F1 指标的底层计算全流程与工程机理
