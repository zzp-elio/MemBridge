# Task-006: 11 维统一记忆能力图谱（UnifiedCapability）与评测画像落地

- **状态**：✅ Completed (2026-10-13)
- **前置任务**：[`task-005-yaml-config-and-evaluator-unification.md`](task-005-yaml-config-and-evaluator-unification.md)
- **核心目标**：
  1. **代码化 11 维统一记忆能力图谱**：在 `src/memory_benchmark/core/capabilities.py` 中定义不可变枚举 `UnifiedCapability`，实现将 5 大基准（LoCoMo / LongMemEval / BEAM / MemBench / HaluMem）的原生碎片化题型标准映射为 11 维能力维度；
  2. **适配器注入标准能力标签**：更新 5 大 Benchmark Adapter，在将各数据集解析为标准 `Question` 时，注入对应的 `capability: UnifiedCapability | None`；
  3. **出具 11 维能力雷达分解报告**：升级 `src/memory_benchmark/runners/evaluation.py`，支持在整体 QA 评分的基础上，按 `UnifiedCapability` 自动分组核算，输出各能力的题目覆盖数、准确率与人工复核率；
  4. **契约测试与文档同步**：编写能力映射与聚合测试，跑通 `uv run pytest -q`，并在 [`docs/architecture.md`](../architecture.md) 与 [`docs/decisions.md`](../decisions.md) 沉淀 `ADR-009`。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 严禁破坏现有 `MemoryProvider` 双方法协议与 `Result[T]` 封装；
  - 严禁硬编码修改已被测试验证的 C/S 流水线接口；
  - `Question.category` 继续作为向后兼容字段，新增 `Question.capability` 标准强类型枚举属性。
- **11 维统一能力枚举清单**：
  1. `FACT_RECALL`（事实回顾/信息抽取）
  2. `MULTI_HOP`（多证据/跨会话推理）
  3. `TEMPORAL`（时间与事件顺序）
  4. `MEMORY_UPDATE`（动态记忆更新）
  5. `MEMORY_CONFLICT`（外部错误前提纠错）
  6. `CONTRADICTION`（历史内部矛盾消解）
  7. `PREFERENCE`（个性化/偏好应用）
  8. `INSTRUCTION_FOLLOWING`（长程指令遵循）
  9. `ABSTENTION`（可答性边界/防幻觉拒答）
  10. `GENERALIZATION`（记忆泛化应用）
  11. `SUMMARIZATION`（长程宏观总结）

---

## 2. 执行步骤 Checklist

- [x] **Step 1：创建 `src/memory_benchmark/core/capabilities.py` 定义 `UnifiedCapability` 枚举与映射函数**
- [x] **Step 2：增强 `src/memory_benchmark/core/entities.py` 的 `Question` 实体支持 `capability` 字段**
- [x] **Step 3：更新 5 大 Benchmark 适配器注入标准 `UnifiedCapability` 标签**
- [x] **Step 4：升级 `runners/evaluation.py` 实现按能力分组聚合与全景画像输出**
- [x] **Step 5：编写能力映射与聚合测试，验证 `uv run pytest -q` 全绿并同步 `STATE.md` / `docs/architecture.md` / `docs/decisions.md` (ADR-009)**
