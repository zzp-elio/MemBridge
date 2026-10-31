# 任务单 Task-016: LoCoMo 多模态图像描述与说话人保真度端到端重构

## 1. 任务背景与核心目标
- **背景**：
  此前评测遗漏了 LoCoMo 数据集官方的两个决定性机制：
  1. 多模态对话中的 `blip_caption` 未拼接进文本，导致记忆系统缺失所有图片事件证据（如日出画作）；
  2. 记忆检索回传时丢失了 `speaker_name`，导致下游多角色事实混淆；
  3. 时间戳格式未转为自然语言日期；
  4. 裁判提示词未 1:1 对齐作者宽松评分规范。
- **目标**：
  1. 在 `src/memory_benchmark/benchmark_adapters/locomo.py` 中将 `blip_caption` 注入 `turn.content`；
  2. 在 `third_party/methods/LightMem/docker/server.py` 中将 `/retrieve` 结果按 `speaker_name` 分区并格式化自然语言日期；
  3. 在 `configs/application.yaml` 中 1:1 对齐 LoCoMo 官方 Judge Prompt；
  4. 全量重新入库 10 个 Conversation（覆盖旧缓存），重新执行 Top-60 满血答题与双轨 LLM Judge 评测；
  5. 验证是否达到原论文 70%~72% 水平并更新所有架构与决策文档。

## 2. 修改边界与红线守则
- **协议兼容**：保持 `MemoryProvider` 接口 (`ingest` / `retrieve`) 签名完全不变，检索结果仍为 `formatted_memory: str`。
- **Docs-as-Code**：任务收口时同步更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md` (ADR-018)。

## 3. Checklist
- [x] 修改 `src/memory_benchmark/benchmark_adapters/locomo.py`，将 `blip_caption` 拼接入 `turn.content`。
- [x] 修改 `third_party/methods/LightMem/docker/server.py`，检索时按 `speaker_name` 分区组织记忆并格式化日期。
- [x] 修改 `configs/application.yaml`，完善 LoCoMo 的 Judge Prompt（对齐作者宽松评卷标准）。
- [x] 运行 `uv run pytest -q` 确保全套回归测试通过。
- [x] 重启 LightMem Server，重新执行全量入库与 Top-60 答题（Run ID: `locomo_full_fidelity_top60`）。
- [x] 执行高并发 LLM Judge 评测并输出最终成绩。
- [x] 更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md`。
