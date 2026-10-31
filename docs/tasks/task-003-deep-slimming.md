# Task-003: 全仓深度瘦身 — 移除 `methods/`、`observability/`、冗余 `config` 与第三方脚本

- **状态**：✅ Completed (2026-10-12)
- **前置任务**：[`task-002-cs-middleware.md`](task-002-cs-middleware.md)
- **核心目标**：在确立 C/S 架构评测中间层定位后，全量扫描并彻底铲除仓库中残留的“进程内硬包第三方记忆库”、“侵入式 Token 计费观测”、“重型配置校验器”以及“第三方源码拉取/打补丁脚本”，让代码库每一行都纯粹服务于 `Load -> Ingest(Session) -> Retrieve -> Answer & Evaluate`。

---

## 1. 深度扫描发现的 4 大冗余重灾区与清理成果

| 序号 | 冗余模块 / 目录 | 原代码量 | 清理动作与最终归宿 |
| :--- | :--- | :--- | :--- |
| **1** | `src/memory_benchmark/methods/` | **3,666 行** | 将 `HttpMemoryProvider`、`MockMemoryProvider` 与 `create_provider` 内聚合并入 `core/provider_protocol.py`，**彻底删除整个 `src/memory_benchmark/methods/` 文件夹**。 |
| **2** | `src/memory_benchmark/observability/` | **2,552 行** | 将轻量的 `RunContext` 移入 `storage/experiment_paths.py`，清理 `evaluators/` 与 `runners/` 中的旧引用，**彻底删除整个 `src/memory_benchmark/observability/` 文件夹**。 |
| **3** | `src/memory_benchmark/config/settings.py` | **778 行** | 重写精简为 **168 行**，仅保留 `PathSettings`、`OpenAISettings`（支持 `answer_llm` / `judge_llm` 角色）与 `AnswerLLMSettings`，直接读取 `configs/llm.toml`。 |
| **4** | `scripts/` 第三方环境脚本、`assets/`、`docs/reference/` | **20+ 文件** | 删除 `scripts/bootstrap_*.sh`、`scripts/fetch_third_party_methods.sh`、`scripts/patches/`、`scripts/requirements/`、空壳 `src/memory_benchmark/assets/` 及旧版进程内配置文档 `docs/reference/`。 |

---

## 2. 执行步骤 Checklist

- [x] **Step 1：内聚 `HttpMemoryProvider` 与 `MockMemoryProvider` 至 `core/provider_protocol.py` 并删除 `src/memory_benchmark/methods/`**
- [x] **Step 2：将轻量 `RunContext` 迁入 `storage/experiment_paths.py` 并删除 `src/memory_benchmark/observability/`**
- [x] **Step 3：重写精简 `src/memory_benchmark/config/settings.py`（778 行 -> 168 行）**
- [x] **Step 4：清理 `scripts/` 下的第三方 Method 构建脚本、`src/memory_benchmark/assets/` 与 `docs/reference/`**
- [x] **Step 5：全仓 Import 巡检、运行 `uv run pytest -q`（14 passed，52 个模块零警告导入）并更新 `STATE.md` / `README.md`**
