# Task-031: 项目品牌全面升级为 MemBridge 与仓库重命名

- **状态**：✅ Completed
- **目标**：
  1. 将 GitHub 仓库从 `AgentMemoryBench` 重命名为 `MemBridge`（`zzp-elio/MemBridge`），更新本地 Git Remote URL；
  2. 更新 GitHub About 简介与描述中的品牌名；
  3. 全局更新文档与配置文件中的项目命名标识（`README.md`、`pyproject.toml`、`AGENTS.md`、`docs/architecture.md` 等）；
  4. 重新生成/微调架构图 `assets/architecture.png` 中的品牌标识（AgentMemoryBench -> MemBridge）；
  5. 沉淀 ADR-027（品牌升级与工业级中间件定位）；
  6. 运行全量测试确保全绿并推送至新仓库，可选发布 `v0.1.0` 正式 Release。

## Checklist

- [x] 立项并在 `STATE.md` 挂载任务卡
- [x] 执行 `gh repo rename MemBridge --yes` 并更新本地 `origin` URL
- [x] 更新 `pyproject.toml` 项目名称与包配置（增加 `membridge` 命令）
- [x] 更新 `README.md` 大标题与品牌描述
- [x] 更新 `AGENTS.md`、`docs/architecture.md`
- [x] 重新生成/替换 `assets/architecture.png` 为 MemBridge
- [x] 沉淀架构决策至 `docs/decisions.md` (ADR-027)
- [x] 运行 `uv run pytest -q` 确保所有测试全绿
- [x] Git commit 并推送到 `origin/main`
- [x] 创建 `v0.1.0` GitHub Release
- [x] 收口任务并更新 `STATE.md`
