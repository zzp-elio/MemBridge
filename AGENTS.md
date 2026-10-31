# MemBridge 项目内核宪章 (`AGENTS.md`)

> **职责边界**：本文件是系统级宪章，保持精炼，**只保存不可妥协的全局红线与渐进式加载路由（Trigger-Based Links）**。具体任务状态、架构细节与历史决策均保存在独立的 Project Memory（`STATE.md` 与 `docs/`）中，按触发条件渐进式读取。

---

## 1. ⚡ 强制工作流铁律（每次会话必守）

1. **冷启动自举（Zero-Prompt Recovery）**：新窗口启动或上下文压缩后，第一时间静默读取 [`STATE.md`](STATE.md) $\rightarrow$ 打开其中指向的唯一活跃 `docs/tasks/task-*.md` $\rightarrow$ 检查 `git status --short`，用 3 句话向用户汇报当前断点与下一步，严禁失忆反问。
2. **先立项、后施工（Task-First Execution）**：任何架构调整、模块删改或新功能开发前，**必须先在 `docs/tasks/task-xxx.md` 创建独立任务单（明确目标、裁剪边界、Checklist 与验收命令），并在 [`STATE.md`](STATE.md) 挂载指针后，方可动手改代码**。
3. **单点状态与文档同步验货**：任务收口必须同步更新 [`STATE.md`](STATE.md)、对应 `task-xxx.md` 及受影响的 [`docs/architecture.md`](docs/architecture.md) / [`docs/decisions.md`](docs/decisions.md)；宣布完成必须以磁盘实测（`uv run pytest -q` 含文档防漂移门禁全绿 + `git status` 检查）为准。

---

## 2. 🎯 项目唯一定位与 4 条架构禁令

- **核心定位**：面向 AI Agent / 后端实习简历的工业级 **C/S 架构 Agent Memory 端到端 QA 评测中间层**（已彻底停止原论文 5×10 跑分计划）。
- **4 条绝对禁令（严禁后续会话回潮）**：
  1. ❌ **禁硬包第三方记忆库**：被测记忆系统作为独立 HTTP Server / Docker 运行；本仓库绝不内置第三方源码、启动脚本或 `configs/methods/`，只管 [`configs/application.yaml`](configs/application.yaml) 中的 `llm`（`answer` / `judge`）与 `prompts` 模板数据。
  2. ❌ **禁扩充中间层方法**：[`MemoryProvider`](src/memory_benchmark/core/provider_protocol.py) 只保留 **`ingest`（按 `Session` 粒度写入）** 与 **`retrieve`（返回 `formatted_memory`）** 两个方法，统一使用仿 Spring Boot 的泛型 `Result[T](code, message, data, latency_ms)` 封装响应。
  3. ❌ **禁中间态检索召回评测與数据集绑定裁判**：只保留三大通用评测器（`ExactMatch`、`F1`、支持 `UNDECIDABLE` 人工复核路由的 `LLMJudge`）及客户端三大客观黑盒效率指标（`ingest_latency_ms`、`retrieve_latency_ms`、`retrieved_context_tokens`）。
  4. ❌ **禁加密死锁与重型注册表**：严禁引入源码 SHA256 防篡改校验锁及多层 Registry 装饰器。

---

## 3. 🧭 Project Memory 渐进式读写与同步路由（按触发条件按需读取 & 主动同步）

| 触发时机（When to Read & Sync） | 目标文档（Progressive Memory Link） | 承载内容与 AI 主动同步责任 |
| :--- | :--- | :--- |
| **新开窗口 / 切换或完成任务节点时** | 👉 [`STATE.md`](STATE.md) | 唯一活跃任务指针与全局进度面板（保持单点聚焦，状态变更必更） |
| **立项施工 / 推进或勾选具体步骤时** | 👉 [`docs/tasks/`](docs/tasks/) | 独立任务合同（背景、修改边界、Step-by-Step Checklist） |
| **查看或修改核心实体、模块职责、配置与协议时** | 👉 [`docs/architecture.md`](docs/architecture.md) | 系统架构说明书（代码结构或协议演进后必须同步更新） |
| **与用户讨论拍板新设计取舍、推翻旧方案时** | 👉 [`docs/decisions.md`](docs/decisions.md) | 架构决策记录 ADR-001~008（讨论达成新决策后必须同步沉淀） |

