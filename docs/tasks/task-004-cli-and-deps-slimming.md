# Task-004: 极简入口收敛与 `pyproject.toml` 僵尸依赖彻底清理

- **状态**：✅ Completed (2026-10-12)
- **前置任务**：[`task-003-deep-slimming.md`](task-003-deep-slimming.md)
- **核心目标**：
  1. **砍掉冗余的 `src/memory_benchmark/cli/` 目录（441 行）**：移除 `list-methods`、`list-benchmarks`、`list-evaluators` 等过渡期子命令及 4 个多余的 Command 包装类，在 [`src/memory_benchmark/__main__.py`](../../src/memory_benchmark/__main__.py) 中浓缩为约 120 行的单文件极简命令行入口；
  2. **彻底清理 [`pyproject.toml`](../../pyproject.toml) 中的 35 个僵尸依赖**：删除原 10 个本地第三方记忆库遗留的数据库、向量库与重型 NLP 依赖（如 `neo4j`、`qdrant-client`、`chromadb`、`lancedb`、`faiss-cpu`、`redis`、`spacy`、`transformers`、`llmlingua` 等），仅保留评测中间层实际使用的 7 个核心轻量包（`ijson`、`nltk`、`openai`、`python-dotenv`、`requests`、`rich`、`tiktoken`）。

---

## 执行步骤 Checklist

- [x] **Step 1：将极简 CLI 入口内聚至 `src/memory_benchmark/__main__.py` 并删除 `src/memory_benchmark/cli/`**
  - 支持直接通过 `uv run memory-benchmark --benchmark locomo --method mock --metrics f1`（或指定 `--server-url http://localhost:8000`）一键跑通 `Load -> Ingest -> Retrieve -> Answer & Evaluate`。
- [x] **Step 2：移除 `locomo_f1.py` 对 `numpy` 的唯一调用，并瘦身 `pyproject.toml` 依赖表**
  - 用原生 `sum(x) / len(x)` 替代 `np.mean(x)`；
  - 将 `pyproject.toml` 的 `dependencies` 从 42 项缩减为 7 项核心依赖，移除 `en-core-web-sm` 外部 wheel 源。
- [x] **Step 3：更新端到端测试 `tests/test_end_to_end_pipeline.py` 与文档（`README.md`、`STATE.md`）**
  - 运行 `uv run pytest -q` 验证 100% 通过。
