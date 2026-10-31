# Task-021: README.md 目录结构说明与 C/S 运行指南重构

- **状态**：🟢 Completed
- **目标**：
  1. 在 `README.md` 中补充 Git 跟踪文件的完整目录树及各子模块职责说明，让开发者一目了然；
  2. 彻底重构 `## 运行` 小节：引导用户安装 `uv` 并执行 `uv sync`，清理废弃的 `--confirm-api` 参数，明确 `--server-url` 含义；
  3. 提供“零服务依赖本地 Mock 冒烟（单方面可跑）”与“对接外部 Memory Server（C/S 完整跑法）”双轨指南，兼顾初学验证与工业级评测。

## Checklist

- [x] 立项并在 `STATE.md` 挂载当前任务
- [x] 梳理并撰写 `README.md` 项目目录结构（包含 `configs/`、`src/memory_benchmark/` 各子模块及根目录配置文件）
- [x] 重构 `README.md` 运行小节：
  - [x] 安装 `uv` 与环境初始化（`uv sync`）
  - [x] 环境变量配置（`.env` 来自 `.env.example`）
  - [x] 模式 A：零外部依赖快速本地自测（`--method mock`）
  - [x] 模式 B：对接真实 Memory Server 的端到端评测（`--method http` + `--server-url`）
  - [x] 清理废弃参数（如 `--confirm-api`），确保命令行 100% 真实可用
- [x] 运行 `uv run pytest -q` 确保文档路径防漂移测试全绿
- [x] 收口任务，更新 `STATE.md` 与任务状态
