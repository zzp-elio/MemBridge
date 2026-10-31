# 任务单 Task-017: 100% 官方保真度 LightMem LoCoMo 全链路重构与复现评测

## 1. 任务背景与核心目标
- **背景**：
  此前评测与 LightMem 官方代码库（`experiments/locomo/`）及 ICLR 2026 论文（Page 17 Table 5, Page 6 Table 3）存在 4 大严重配置脱节：
  1. 抽取提示词漏传，回退为单用户通用 Prompt，丢失双说话人、图片描述融合与相对时间提取指令；
  2. 缺失 Phase 3 离线更新（`construct_update_queue_all_entries` + `offline_update_all_entries`），评测运行在未去重冲突的原始内存中；
  3. 关停了 `llmlingua-2` 预压缩与话题切分（`pre_compress: True`, `rate: 0.6`, `topic_segment: True`），长会话一次性硬喂导致注意力稀释；
  4. 答题与裁判提示词被拆解，未能 1:1 对齐官方的统一 `ANSWER_PROMPT` 与 Hawaii few-shot 裁判模板。
- **目标**：
  1. 在 `third_party/methods/LightMem/docker/server.py` 中 1:1 接入官方配置：
     - 使用本地 `models/llmlingua-2-bert-base-multilingual-cased-meetingbank` 开启预压缩与话题切分；
     - 显式注入 `METADATA_GENERATE_PROMPT_locomo`；
     - 按 turn 粒度流式推进，触发 512 阈值自然提取，在会话完成或显式调用时执行 `offline_update_all_entries(0.9)`；
  2. 在 `src/memory_benchmark/runners/prediction.py` 中，在 `ingest` 会话的最后一个 Session 标记 `is_last_session`，并在入库完成时触发离线更新优化；
  3. 在 `configs/application.yaml` 中，1:1 对齐官方统一 `ANSWER_PROMPT` 与二元裁判 `ACCURACY_PROMPT`；
  4. 清空旧数据库，执行 10 个 Conversation 全量入库与 Top-60 答题及 LLM Judge 评测（Run ID: `locomo_official_parity_top60`）；
  5. 记录实验对比，同步更新 `docs/architecture.md`、`docs/decisions.md` (ADR-019) 与 `STATE.md`。

## 2. 修改边界与红线守则
- **协议兼容**：严格维系 `MemoryProvider.ingest` 与 `retrieve` 签名，返回标准 `Result[T]`；
- **Zero Sycophancy**：以实测磁盘数据为准，不粉饰不造假；
- **Docs-as-Code**：保持 `STATE.md` <= 30 行，`AGENTS.md` <= 50 行，测试门禁全绿。

## 3. Checklist
- [x] 编写 `docs/tasks/task-017-lightmem-official-full-parity-reproduction.md` 并在 `STATE.md` 挂载指针。
- [x] 升级 `third_party/methods/LightMem/docker/server.py`：
  - [x] 载入本地 `llmlingua-2`，配置 `pre_compress: True` (`rate: 0.6`, `model_config: {'attn_implementation': 'eager'}`) 与 `topic_segment: True`；
  - [x] 载入本地 `all-MiniLM-L6-v2` (384 维)，设置 `th=512` STM 缓冲；
  - [x] 抽取时强制注入 `METADATA_GENERATE_PROMPT_locomo`；
  - [x] 增加 `POST /optimize` 接口（并在最后一个 session `is_last_session=True` 时自动执行 `construct_update_queue_all_entries()` + `offline_update_all_entries(score_threshold=0.9)`）。
- [x] 在 `src/memory_benchmark/runners/prediction.py` 中透传 `is_last_session`，并在 `_retrieve_and_answer_question` 中增加对上游内容审查拦截的容错重试保护。
- [x] 在 `configs/application.yaml` 中，1:1 对齐官方 `ANSWER_PROMPT`（统一全题型，无额外 Category 2 分支）。
- [x] 运行 `uv run pytest -q` 确保所有既有回归测试全绿通过（24/24 passed）。
- [x] 重启 LightMem Server，执行全量 10 对话官方保真入库与 Top-60 评测（Run ID: `locomo_official_parity_top60`）。
- [x] 运行 20 线程高并发 LLM Judge 并产出最终指标。
- [x] 更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md`。

## 4. 实测验证数据与论文对比 (Empirical Results)
- **评测规模**：10 段完整长会话，共计 1,540 道考题。
- **评测环境**：本地 LightMem (MiniLM-L6-v2 + LLMLingua-2) + Qdrant + GPT-4o-mini (Answer & Judge)。
- **核心对比指标**：
  | 评测维度 | 历史基线 (失真配置) | 官方保真复现 (Task-017) | LightMem 官方论文 (ICLR 2026) |
  | :--- | :--- | :--- | :--- |
  | **全量 LLM Judge ACC** | 52.21% (804/1540) | **70.26% (1082/1540)** | **71.95%** (Table 5 MiniLM) |
  | **Token F1 分数** | 35.41% | **49.41%** | - |
  | **Cat 1 (多跳推理)** | 43.6% | **64.54% (182/282)** | ~67% |
  | **Cat 2 (时序推理)** | 49.8% | **72.90% (234/321)** | ~74% |
  | **Cat 3 (隐式推断)** | 36.5% | **44.79% (43/96)** | ~45% |
  | **Cat 4 (事实抽取)** | 57.1% | **74.08% (623/841)** | ~76% |
  | **平均检索耗时** | 68.2 ms | **51.8 ms** (客户端总往返) | ~50 ms |

