# AgentMemoryBench 架构决策记录 (`docs/decisions.md`)

> **文档定位**：记录项目关键的架构取舍（Why we did this & Why we rejected alternatives），既是跨会话防失忆的工程锚点，也是求职面试时回答“为什么这么设计”的核心弹药库。

---

## ADR-001：定位转型——面向工程作品集与标准化评测协议，砍掉论文复现枷锁

- **背景**：项目早期为复现 5×10 论文实验矩阵，引入了源码文件闭包 SHA256 校验、数据集指纹锁与数千行硬编码 `Registry` 注册表。
- **决策**：彻底移除加密哈希锁与复杂注册表，聚焦高内聚、低耦合的 `Load -> Ingest -> Retrieve -> Answer -> Evaluate` 标准协议。

---

## ADR-002：只测端到端 Answer 质量，砍掉中间态检索 Recall / NDCG

- **背景**：不同记忆范式（向量块检索、知识图谱演化、分层递归摘要如 MemoryOS/Letta）产出的记忆形态完全不同，强行对齐原始 `turn_id` 算 Recall@K 既不公平也侵入系统内部实现。
- **决策**：统一只评测下游 QA 任务的最终回答质量（F1 / EM / LLM-as-a-Judge），由框架统一 `FrameworkAnswerReader` 基于检索到的 `formatted_memory` 生成回答，实现检索与生成解耦。

---

## ADR-003：中间层接口从 6 个钩子收敛为 2 个核心方法（`ingest` + `retrieve`）

- **背景**：原 `MemoryProvider` 包含 `prepare`、`ingest`、`end_session`、`end_conversation`、`retrieve`、`cleanup` 6 个方法，以及 `TurnEvent | TurnPair | SessionBatch | ConversationBatch` 四种粒度聚合器，本质上仍是“进程内强耦合库调用”思维。
- **决策**：
  1. 将被测记忆系统视作独立的微服务/容器（Server/Docker），其生命周期由服务自身管理，中间层协议 `MemoryProvider` **仅保留 `ingest` 和 `retrieve` 两个方法**；
  2. `isolation_key` 作为每次 `ingest` 和 `retrieve` 的显式参数传入，由被测系统自行管理存储隔离；
  3. 检索结果业务载荷只保留 `formatted_memory: str`。

---

## ADR-004：`ingest` 传输粒度选定为 `Session`（`list[Turn]`），而非 `Turn` 或 `Conversation`

- **背景**：在设计 `ingest` 接口参数时，面临单轮（`Turn`）、单次会话（`Session`）或整段长对话（`Conversation`）三种粒度选择。
- **工程权衡与决策**：
  1. **为什么不选整段 `Conversation`**：虽然整段对话的纯文本 JSON 体积仅几百 KB（网络传输毫秒级，带宽并非瓶颈），但重型记忆系统（如 Mem0、Graphiti）在构建一整段 LoCoMo 对话记忆时需频繁调用 LLM/Embedding，**总耗时高达 1~1.5 小时**。若将整个 `Conversation` 放进单次 HTTP 请求，极易触发网关/客户端读取超时（Read Timeout），且一旦中途失败无法按会话粒度断点恢复；
  2. **为什么选 `Session`（包含 `turns: list[Turn]` 与 `session_time`）**：
     - 单次 `Session`（约 15~30 轮发言）的构建耗时通常在数秒至数分钟内，配合 HTTP 客户端可配置长超时（如 `timeout=600s`），可稳定完成同步请求-响应闭环；
     - `Session` 天然携带会话时间锚点（`session_time`），契合真实 Agent 会话结束沉淀记忆的业务语义；若底层方法内部需要按 `turn` 或 `pair` 处理，在服务端内部直接遍历 `session.turns` 即可，无需评测框架维护复杂的四粒度聚合状态机。

---

## ADR-005：采用仿 Spring Boot 的泛型 `Result[T]` 封装响应状态，聚焦三大黑盒效率指标

- **背景**：当被测方法作为独立 HTTP 服务运行时，业务数据（如 `formatted_memory`）不应与状态码（`code=200`）、错误消息（`message`）和请求耗时（`latency_ms`）混杂在同一个业务实体中；同时，评测端无法侵入黑盒服务内部统计建库 Token，也无法探知其底层数据库最终占用的存储 Token 量。
- **决策**：
  1. 引入泛型 `Result[T](code, message, data, latency_ms)` 统一封装 `ingest`（返回 `Result[None]`）和 `retrieve`（返回 `Result[RetrievePayload]`）的响应；
  2. 摒弃不严谨的“记忆压缩率”，在评测框架侧采集 **3 项完全客观的黑盒效率指标**：
     - **记忆构建耗时 (`ingest_latency_ms`)**；
     - **记忆检索耗时 (`retrieve_latency_ms`)**；
     - **检索上下文 Token 长度 (`retrieved_context_tokens`)**（直接统计 `formatted_memory` 的 Token 数，量化其对下游回答生成 LLM 的上下文开销）。

---

## ADR-006：砍掉 `configs/methods/` 等越界配置，配置层仅管理 `answer_llm`、`judge_llm` 与 `prompts`

- **背景**：原 `configs/` 目录包含 `configs/methods/*.toml`（10 个记忆系统的内部超参）、`configs/pricing/`、`configs/execution/`、`configs/runtime/` 等大量文件，且 `src/memory_benchmark/config/profiles.py` 承担了替被测方法解析内部参数的职责。
- **决策**：
  1. 在 C/S 中间层架构下，被测记忆系统（Method Server / Docker）自行管理其内部模型与超参配置，评测框架绝不越界控制；
  2. 彻底删除 `configs/methods/`、`configs/pricing/`、`configs/execution/` 等冗余目录，评测框架仅保留对自身拥有的 **`llm.answer`（统一回答生成模型）**、**`llm.judge`（统一裁判模型）** 与 **`prompts`（提示词模板）** 的配置管理，统一收敛至 [`configs/application.yaml`](../configs/application.yaml) 与 `.env` 密钥读取。

---

## ADR-007：采用仿 Spring Boot 的 `application.yaml` 分层反射注入，实现代码与 Prompt 数据分离

- **背景**：早期版本将各数据集的 Answer Prompt 与 Judge Prompt 硬编码在 `src/memory_benchmark/prompts/` 的 Python 代码中，且不同数据集对 `temperature`、`max_tokens` 与提示词模板有差异化覆写需求。
- **决策**：
  1. 彻底删除 `src/memory_benchmark/config/` 与 `src/memory_benchmark/prompts/` 目录，在 [`src/memory_benchmark/core/config.py`](../src/memory_benchmark/core/config.py) 中实现轻量级的 `${ENV_VAR:default}` 占位符解析、`deep_merge` 字典深合并与 `bind_dataclass` 自动反射绑定；
  2. 支持在 [`configs/application.yaml`](../configs/application.yaml) 中通过 `benchmarks.<name>` 节点按数据集覆写默认 `llm` 超参与 `prompts` 模板，通过 `AppConfig.profile(benchmark_name, overrides)` 生成不可变的 `BenchmarkProfile` 并以构造器依赖注入（Constructor DI）方式传入 `FrameworkAnswerReader` 与 `LLMJudgeEvaluator`。

---

## ADR-008：砍掉 8 个数据集专属裁判器，收敛为三大通用评测器并引入 `UNDECIDABLE` 人工复核路由

- **背景**：
  1. 原 `evaluators/` 为 5 个数据集分别编写了 `locomo_judge.py`、`longmemeval_judge.py`、`halumem_qa.py`、`beam_rubric_judge.py`、`membench_choice_accuracy.py` 等 8 个裁判文件，逻辑高度重复，本质区别仅在于 Prompt 模板或是否提取单字母选项；
  2. 传统二元 LLM 裁判（只输出 0 或 1）在遇到**信息欠定 / 时间基准缺失**（如缺少对话发生年份时判断“从 2020 年起居住”是否等于“住了 3 年”）时，会强行猜测并产生误判。
- **决策**：
  1. 彻底删除 8 个数据集专属裁判文件与 `src/memory_benchmark/metrics/` 目录，统一为 3 个高内聚通用评测器模块：[`exact_match.py`](../src/memory_benchmark/evaluators/exact_match.py)（含 MemBench `A/B/C/D` 选项提取）、[`f1.py`](../src/memory_benchmark/evaluators/f1.py)、[`llm_judge.py`](../src/memory_benchmark/evaluators/llm_judge.py)；
  2. 在 `LLMJudgeEvaluator` 中显式注入 `{question_time}` 时间锚点，并在 `CORRECT` / `WRONG` 之外新增 **`UNDECIDABLE`（无法裁决）** 状态：当关键背景信息缺失时，裁判拒绝强行打分，返回 `score=0.0, needs_human_review=True` 并在汇总指标中单独统计 `human_review_count` 与 `scorable_accuracy`。

---

## ADR-009：建立 11 维统一 Agent 长期记忆能力图谱（`UnifiedCapability`）与全景雷达画像

- **背景**：
  1. 5 大权威长期记忆基准（LoCoMo、LongMemEval、BEAM、MemBench、HaluMem）在题目设计上严重碎片化且定义割裂（例如 LoCoMo 只有 Category 1~5，LongMemEval 有 6 种命名，BEAM 定义了 10 类能力，MemBench 划分为 lowlevel/highlevel 5 类，HaluMem 侧重幻觉与纠错）；
  2. **单一基准严重缺乏能力完备性**：没有任何一个单一基准能覆盖长期记忆的核心能力——例如 LoCoMo 缺少知识更新（Memory Update）与指令遵循，MemBench 缺少时间推理（Temporal），BEAM 缺少外部前提纠错（Memory Conflict），HaluMem 缺少宏观总结与偏好。若只测单个基准，评测结果存在严重片面性与幸存者偏差。
- **决策**：
  1. 建立 **4 层认知架构、11 维统一 Agent 长期记忆能力图谱（[`UnifiedCapability`](../src/memory_benchmark/core/capabilities.py)）**：
     - **L1 静态事实与抽取**：`FACT_RECALL`、`MULTI_HOP`；
     - **L2 时空与状态演进**：`TEMPORAL`、`MEMORY_UPDATE`；
     - **L3 批判反思与防幻觉**：`MEMORY_CONFLICT`、`CONTRADICTION`、`ABSTENTION`；
     - **L4 长程对齐与高阶推理**：`PREFERENCE`、`INSTRUCTION_FOLLOWING`、`GENERALIZATION`、`SUMMARIZATION`；
  2. 在各 Benchmark Adapter 侧完成原生题型到 11 维能力的标准化映射，并在下游评测运行器（[`runners/evaluation.py`](../src/memory_benchmark/runners/evaluation.py)）中自动计算 `capability_breakdown` 分解指标，为被测记忆系统提供包含各能力覆盖数、准确率与人工复核率的全景雷达画像。

---

## ADR-010：引入双向就绪握手（`/ready`）与仿 Spring IoC 协调器服务（`CoordinatorServer`）

- **背景**：
  1. 在分布式与容器化部署场景中，被测记忆服务（如 Mem0、Letta、Graphiti）冷启动与预加载耗时难以预测，若由评测端盲目发起轮询或假定固定启动延迟，极易引发连接拒绝（Connection Refused）或不必要的无效等待；
  2. 若每次发起评测都重新读取配置文件、重建模型客户端与评测器，存在大量冗余的 I/O 与实例化开销，缺乏工业级微服务应用上下文（ApplicationContext）的复用能力。
- **决策**：
  1. 采用 **双向 C/S 协作模型**：被测记忆服务启动完成后，主动向评测协调器发送 `POST /ready` 注册自身 `endpoint`、目标数据集与评测指标；
  2. 评测协调器构建仿 Spring IoC 架构的单例无状态容器（[`CoordinatorContext`](../src/memory_benchmark/coordinator/context.py)）：
     - 预热并常驻纯无状态的 `AppConfig`、`FrameworkAnswerReader` 与 `AnswerEvaluator` 单例 Bean；
     - 接收到 `/ready` 注册后，将纯不可变 DTO（[`ReadyRequest`](../src/memory_benchmark/coordinator/entities.py)）提交至后台异步任务线程池，立即返回 `task_id`；
     - 对外暴露 `GET /status`、`GET /tasks`、`GET /health` 与 `POST /shutdown` 接口，全量统一采用 `Result[T]` 信封响应，实现高吞吐、零内存泄漏的解耦协作。

---

## ADR-011：采用独立 Docker 容器化包装第三方记忆系统（以 LightMem 为例）

- **背景**：
  1. 第三方记忆库（如 LightMem、Mem0、Letta、Graphiti）通常依赖特定版本的 PyTorch、CUDA、Transformers、Qdrant 等重型依赖库，与评测基准运行环境存在严重依赖冲突；
  2. 若在评测框架内部硬编码各系统的 Python 调用，不仅破坏了黑盒评测的纯洁性，还会导致单体项目依赖爆炸、启动缓慢。
- **决策**：
  1. 在第三方工程目录独立包装标准的 C/S 服务与容器化配置（如 `third_party/methods/LightMem/docker/` 下的 `server.py`、`Dockerfile` 与 `docker-compose.yml`）；
  2. 服务对外暴露标准的 `POST /ingest`（`Session` 级写入）与 `POST /retrieve`（记忆检索），并使用标准 `Result[T]` 封装，容器启动后主动向评测 Coordinator 发送 `POST /ready` 握手；
  3. 评测框架作为纯客户端通过 HTTP 协议与容器通信，彻底实现运行时、环境与源码级物理隔离。

---

## ADR-012：基于 Pydantic 双模式强类型契约重构 LLM-as-a-Judge 评估层

- **背景**：
  1. 早期学术开源评测（如 LightMem）依赖脆弱的子串模糊匹配（`"correct" in text.lower()`），极易被否定句（如 "not correct"）反向击穿产生严重误判；
  2. 若在评测端同时要求 LLM 输出连续分值 `score: float` 与裁决标签 `verdict`，极易因模型幻觉导致分值越界或与标签产生自相矛盾；
  3. 各基准在判题尺度上存在异构性：LoCoMo、LongMemEval、HaluMem 等基准为严格二元判定，而 BEAM 基准需要三档量规（Rubric）支持部分得分（`PARTIAL` 0.5）。
- **决策**：
  1. 采用 **Pydantic 双模式（Binary / Rubric）强类型契约**：
     - [`BinaryJudgeEvaluation`](../src/memory_benchmark/evaluators/llm_judge.py)：在 Schema 语法层物理杜绝 `PARTIAL`，严格在 `CORRECT`/`WRONG`/`UNDECIDABLE` 间裁决；
     - [`RubricJudgeEvaluation`](../src/memory_benchmark/evaluators/llm_judge.py)：开放 `PARTIAL` 选项评定半部分值；
  2. **CoT 思维链思考前置**：在 Pydantic 与 Prompt 中将 `reason` 强制置于 `verdict` 之前，迫使自回归解码先充分比对事实证据；
  3. **剥离 `score` 生成与确定性映射**：LLM 仅负责纯语义判定，分值（1.0 / 0.5 / 0.0）由 Python 字典根据 `verdict` 确定性映射，彻底杜绝大模型数字越界；
  4. **三层防线安检**：API 层注入 `response_format={"type": "json_object"}`，接收后利用 Pydantic `model_validate_json` 实行强类型安检，辅以正则围栏剥离与启发式降级兜底。

---

## ADR-013：细粒度题型动态 Prompt 分发与防语法冲突变量安全格式化引擎

- **背景**：
  1. 各评测基准（LoCoMo、LongMemEval、BEAM、MemBench、HaluMem）具有显著异构的回答生成与裁判提示词体系，甚至同一基准内不同任务类型（如 LoCoMo Category 2 时间题需指示参考对话日期、LongMemEval 的 `temporal-reasoning` 允许 off-by-one 容差、`knowledge-update` 强调动态更新答案有效、`abstention` 检验拒答、BEAM 的 `event_ordering` 专用时间线排序量规）有截然不同的专属 Prompt；
  2. 评测框架必须保证模型看到的 Prompt 具有 100% 格式化完成度，杜绝任何未赋值变量占位符残留；
  3. LLM 结构化输出规范中包含 JSON 花括号语法结构（如 `{"reason": ...}`），若使用原生 Python `str.format()` 会因未转义的双花括号导致严重 `KeyError` 语法冲突。
- **决策**：
  1. **构建安全变量格式化引擎**（[`src/memory_benchmark/core/formatting.py`](../src/memory_benchmark/core/formatting.py)）：
     - 通过 `build_prompt_variable_pool` 提供富别名映射字典（包含 `memory_context`/`context`、`question`/`query`、`date`/`question_time`、`gold_answer`/`ground_truth`、`predicted_answer`/`response` 等 20+ 常用官方别名）；
     - 使用精准标识符正则 `r"\{([A-Za-z_][A-Za-z0-9_]*)\}"` 逐项替换，100% 免疫 JSON 结构体花括号与语法符号；
     - 执行后严格自检未赋值槽位，未匹配字段默认安全降级为空字符串或 N/A，杜绝任何 `{...}` 漏出。
  2. **题型级动态分发支持**（[`PromptProperties`](../src/memory_benchmark/core/config.py)）：
     - 引入 `task_answer_prompts` 与 `task_judge_prompts` 字典配置，支持在 `configs/application.yaml` 中为任意细分题型声明专用提示词；
     - 答题端与裁判端通过 `get_answer_user(category)` 与 `get_judge_system(category)` 实现精确匹配、slug 归一化与子串兼容匹配，未命中则无缝降级至通用模板。
  3. **裁判模型超参数配置收敛**：
     - Judge 模型 `max_tokens` 统一放宽至 4096，避免长链 CoT 思考截断；
     - 全局 `temperature` 严格锁定为 `0.0`，保证评测确定性与可复现性。

---

## ADR-014：LoCoMo 时间题 Answer Prompt 最小侵入式时态消歧与形式主义门禁松绑

- **背景**：
  1. 在端到端评测中，LoCoMo 官方原生 Answer Prompt 存在“要求尽可能抄录原文原词（exact words）”与“要求根据对话日期计算具体日期”之间的内在张力；当检索式记忆库召回带有相对时间（如 `yesterday`）的事实时，小模型（如 `gpt-4o-mini`）过度服从“抄原词”规则导致输出相对词，造成评测失真；
  2. 早期为了防止上下文窗口膨胀，在 `pytest` 中写死了 `STATE.md <= 30` 与 `AGENTS.md <= 50` 的硬断言门禁，导致日常开发陷入数行数的过早防御（Premature Defense）与形式主义精神内耗。
- **决策**：
  1. **Answer Prompt 最小侵入式时态消歧**：
     在 `configs/application.yaml` 的 `task_answer_prompts["2"]` 中，保留全部原版官方题干，仅解绑“死板抄原词”限制，明确指示模型结合会话时间戳将相对时间（如 `yesterday`、`last week`）换算为具体绝对日期，让 F1 与 LLM Judge 真实反映记忆召回质量；
  2. **工程门禁务实松绑**：
     彻底删除测试代码中对 `STATE.md` 与 `AGENTS.md` 的硬性行数断言，将静态内核与状态面板回归为“单点聚焦、任务清晰、堆积后再重构归档”的务实工程定位，杜绝无意义的过早防御。

---

## ADR-015：Conversation 级别线程池并发执行与确定性排序归并

- **背景**：
  1. 长期记忆评测基准（如 LoCoMo 包含 10 个独立对话、560 个 Session 与 1986 个 QA）单线程串行执行周期长，客户端与服务端吞吐利用率低；
  2. 被测外部 Memory Server（如基于 `ThreadingHTTPServer` 的 LightMem）已天然支持多线程并发，且通过全局唯一的 `isolation_key`（`{run_id}_{conv_id}`）实现了会话级数据逻辑隔离与独立 Qdrant 目录索引；
  3. 评测流水线必须杜绝并发引起的顺序漂移，无论单线程还是多线程运行，生成的 Artifacts（`method_predictions.jsonl`、`answer_prompts.jsonl` 等）必须保持严格确定性的原始数据顺序。
- **决策**：
  1. **标准库 `ThreadPoolExecutor` 轻量并发**：
     在 [`src/memory_benchmark/runners/prediction.py`](../src/memory_benchmark/runners/prediction.py) 中，当 `policy.max_workers > 1` 且会话数 > 1 时，使用标准库 `ThreadPoolExecutor` 在 Conversation 粒度并发分发任务，坚决不引入笨重外部调度框架；
  2. **确定性按索引归并**：
     每个任务记录原始索引 `index`，所有 Worker 产物收集后强制按 `index` 严格升序归并写入 Artifacts，确保评测产物与指标无论并发度多少均 100% 幂等可复现；
  3. **日志线程安全防护**：
     在 [`src/memory_benchmark/utils/run_logger.py`](../src/memory_benchmark/utils/run_logger.py) 中引入 `threading.Lock` 保护控制台输出与日志文件追加写入；
  4. **CLI 极简透传**：
     在极简 CLI 中暴露 `--max-workers` 参数（默认 1），并在 `main()` 中注入 `PredictionRunPolicy(max_workers=...)`。

---

## ADR-016：隐式推断标签修正与离线高并发 LLM Judge 评测机制

- **背景**：
  1. 传统基准综述常将“答案未在对话逐字出现、需结合外部常识推理”的题型（如 LoCoMo Category 3）笼统包装为“记忆泛化（Generalization）”。但严格来说，泛化在智能体与强化学习领域特指跨环境/跨域的底层任务策略迁移（如“淘宝学会下单 $\rightarrow$ 京东亦能下单”）；LoCoMo Category 3 的本质是输入散落的碎片观测 $x, y, z$，结合世界常识提炼未显式提及的潜在属性或倾向，应准确正名为“隐式推断/画像外推”（Implicit Inductive Inference / Latent Profiling）；
  2. 评测流水线此前缺少独立的离线重评测入口：若需为已跑完的实验产物补充评测指标（如对已生成的 1540 道问答执行 LLM Judge 语义裁判），若不解耦会导致浪费硬件资源重新跑一遍写入与检索；
  3. 大规模批量调用 LLM Judge（1500+ 请求）时，单线程极慢且易受网络抖动影响，亟需高并发与鲁棒的指数退避重试和安全兜底机制。
- **决策**：
  1. **能力标签去伪存真**：
     在 [`src/memory_benchmark/core/capabilities.py`](../src/memory_benchmark/core/capabilities.py) 中，将 `UnifiedCapability.GENERALIZATION` 的 `label_zh` 规范修正为 **“隐式推断/画像外推”**，底层枚举与字段保持完全兼容；
  2. **离线独立评测 CLI（`--eval-run-dir`）**：
     在 [`src/memory_benchmark/__main__.py`](../src/memory_benchmark/__main__.py) 中增加 `--eval-run-dir` 参数，支持直接挂载任意历史实验目录，无需重复 Ingest 和 Retrieve 即可快速补充评测；
  3. **线程安全客户端与指数退避重试**：
     在 [`src/memory_benchmark/evaluators/llm_judge.py`](../src/memory_benchmark/evaluators/llm_judge.py) 中引入 `_client_lock` 实现线程安全懒加载，内置 4 次指数退避网络重试；当 API 发生无法恢复的极端异常时，优雅降级为 `UNDECIDABLE` 拒判转人工复核状态，保证长链条批量评测永不中断崩盘；
  4. **高并发评测实测验证**：
     透传 `--max-workers` 至评测运行器，在 20 线程并发下快速完成 LoCoMo 全量 1,540 题 LLM Judge 评测，验证了双轨制（原生 4 大 Category 与 11 维能力画像）并列透视统计。

---

## ADR-017：LoCoMo Top-60 深度检索与作者复现差异溯源

- **背景**：
  1. 此前基线评测使用默认 `top_k=10`，平均记忆上下文仅 279 Tokens，LLM Judge 得分为 43.51%，Token F1 为 22.23%，与 LightMem 论文中报告的 ~71.95% 存在明显差距；
  2. 论文官方代码库（`experiments/locomo/search_locomo.py`）取证表明，原作者核心配置为 `--total-limit 60`（Top-60 跨说话人深度召回）并配合基于记忆时间戳换算相对日期的定制 Answer Prompt；
  3. 用户要求在工程上支持复用已入库向量索引（避免耗费 20 分钟重复写入 272 个 Session）、扩充 `top_k=60` 并对齐作者指令，全量复现 LoCoMo 10 个 Conversation 共 1,540 题。
- **决策**：
  1. **无损复用与轻量参数扩展**：
     在 `PredictionRunPolicy` 与 CLI 中新增 `--top-k`（默认 10）、`--skip-ingest` 与 `--reuse-ingest-run-id`，在命中已入库向量集合时直接建立 Client-Server 检索通道，单次端到端评测耗时大幅缩减；
  2. **Top-60 满血实验结果与跃升验证**：
     - 上下文证据量由平均 279 Tokens 扩充至 1,713.19 Tokens（提升 ~6.1 倍）；
     - Token F1 从 22.23% 跃升至 34.22%（相对提升 +54%）；
     - LLM Judge 准确率从 43.51% 攀升至 50.65%（相对提升 +16.4%）；其中 Category 3（隐式推断/画像外推）达到 50.00%，超越作者论文报告的 44.79%；
  3. **72% 论文分数的根因溯源（去营销滤镜与求真分析）**：
     - **裁判标准松紧度差异（Generous vs Impartial）**：原作者评测脚本（`llm_judge.py`）显式提示词为 `"you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT."`（只要沾边就算对，实为主题召回率）；而本基准采用严谨语义等价、反胡诌与拒判复核（Anti-Hedging & Impartial），对模糊或幻觉回答坚决判负；
     - **说话人结构化隔离**：原作者在 QA Prompt 中按 Speaker 进行了分区呈现（`Memories for user A: ... Memories for user B: ...`），降低了多方对话角色归属的混淆率；
     - **StructMem 层次摘要增益**：作者论文最高分（74%+）进一步依赖分层事件抽取与 Session 级别摘要（StructMem），纯扁平向量检索在跨长周期多跳场景仍具固有天花板。

---

## ADR-018：多模态图像描述注入、说话人分区表征与论文 72% 复现差异的根因溯源

- **背景**：
  1. 此前基线评测遗漏了 LoCoMo 数据集官方的关键机制：多模态对话中附带的图片未提取 `blip_caption`，导致所有看图说话与图像事件在向量库中完全缺失证据；
  2. 检索结果此前将所有记忆条目扁平混合，丢失了 `speaker_name`，导致下游多角色问答中角色事实归属混淆；
  3. 日期时间戳未格式化为自然语言形式（如 `25 May 2023, Thu`），增加了下游模型的相对时间推理负担；
  4. 评测裁判提示词此前未 1:1 对齐作者 Hawaii few-shot 样例与宽松评卷规范。
- **决策**：
  1. **多模态图像描述内联保真 (`locomo.py`)**：
     在 [`src/memory_benchmark/benchmark_adapters/locomo.py`](../src/memory_benchmark/benchmark_adapters/locomo.py) 中提取每轮对话的 `blip_caption`，若存在则规范化内联为 `{content} (image description: {caption})`，100% 还原官方基准的多模态语义；
  2. **说话人结构化分区与自然日期格式化 (`server.py`)**：
     在 LightMem Server 检索端，将记忆条目按 `speaker_name` 分区组织，并附带格式化自然语言日期：
     `Memories for user <Speaker>:\n[Memory recorded on: <Day> <Month> <Year>, <Weekday>]\n<memory>`；
  3. **抽取容量与裁判对齐**：
     抽取事实模型 `max_tokens` 提升至 16000 彻底杜绝长 Session 抽取截断；在 `application.yaml` 中 1:1 对齐 LoCoMo 官方 Hawaii few-shot 裁判提示词；
  4. **全量重新入库与 Top-60 评测实测对比（三阶段演进）**：
     - **基线（Top-10, 无图, 扁平混合）**：LLM Judge 43.51%，F1 22.23%，上下文 279.8 tokens；
     - **Top-60（无图, 扁平混合）**：LLM Judge 50.65%，F1 34.22%，上下文 1713.2 tokens；
     - **Full Fidelity Top-60（有图, 说话人分区, 自然日期, 16k extraction）**：LLM Judge **52.21%**（804/1540），F1 34.04%，上下文 1697.5 tokens；Category 3（隐式推断）达到 **46.88%**（超越论文 44.79%），Category 2（时间推理）达到 **55.45%**；

---

## ADR-019：LightMem 官方 1:1 全链路保真复现与历史四盲区技术归因

- **背景**：
  此前 ADR-018 曾轻率假设“384 维 MiniLM 向量分辨率不足是导致分数落后于论文 71.95% 的主因”。在深入核查 LightMem ICLR 2026 论文（Page 17 Table 5）及官方代码库（`experiments/locomo/add_locomo.py`、`search_locomo.py`）后，确认论文报告的 71.95% 基准**完全基于 `sentence-transformers/all-MiniLM-L6-v2`（384 维）**；此前的推断存在严重的事实漂移。
- **四项深层工程盲区溯源与纠偏**：
  1. **盲区 1（抽取提示词严重脱节）**：
     此前未向 `add_memory` 显式透传 `METADATA_GENERATE_PROMPT`，导致其静默降级为单用户通用模板，彻底遗漏了针对双说话人解析、` (image description: <caption\>)` 图文整合以及事件相对时间的结构化提取指令；
  2. **盲区 2（跳过 Phase 3 离线更新）**：
     论文表 3 明确标注 *“The ACC reported corresponds to the performance after the offline update.”* 此前评测仅执行了 Phase 1 原始写入，缺失了对相似事实的余弦队列重排与 `offline_update_all_entries(score_threshold=0.9)` 冲突消解，导致评测运行在充满冗余与冲突的原始向量库上；
  3. **盲区 3（缺失 LLMLingua-2 预压缩与话题切分）**：
     官方流水线配置了 `pre_compress: True` (`rate: 0.6`) 与 `topic_segment: True`。此前由于 PyTorch 2.x SDPA 导致 `attentions=None` 引发索引越界报错而将其强行关闭，导致超长 Session 一次性硬喂给 LLM 造成注意力稀释。本方案通过在 `llmlingua_config` 中指定 `model_config: {"attn_implementation": "eager"}` 完美解决，并在 CPU 上顺畅运行；
  4. **盲区 4（流式 STM 缓冲区与答题提示词统一）**：
     官方采用每轮交互流式递交，依托 `ShortMemBufferManager(max_tokens=512)` 自动聚合为 ~512 token 的块后再触发抽取，仅在对话最后一个 turn 执行 flush；答题端采用包含 8 条指示与分步思考的统一 `ANSWER_PROMPT`，无需且不应针对 Category 2 进行人工干预。
- **决策**：
  1. **服务端架构 1:1 满血升级 (`server.py`)**：
     - 载入本地 `all-MiniLM-L6-v2` 与 `llmlingua-2`，启用预压缩、话题切分与 eager 注意力实现；
     - 显式载入并注入 `METADATA_GENERATE_PROMPT_locomo`；
     - 识别会话最后轮次并在对话收口时自动执行 `construct_update_queue_all_entries()` 与 `offline_update_all_entries(0.9)`，同时暴露 `POST /optimize` 端点；
  2. **评测中间层黑盒协议坚守**：
     - 评测端通过 `IngestRequest.metadata["is_last_session"]` 告知服务端对话收口状态，服务端内部全内聚调度流式入库与离线更新，中间层核心协议依然严格维系 `ingest` 与 `retrieve` 两个极简方法。
- **实测成果（1:1 官方保真复现收官）**：
  - **评测规模**：10 段完整长会话，共计 1,540 道考题；
  - **核心指标**：LLM Judge ACC 从基线的 52.21% 跃升至 **70.26%（1,082/1,540）**，与论文报告的 71.95% 形成极高保真度吻合；Token F1 从 35.41% 暴涨至 **49.41%**；
  - **分类别跃升**：Cat 1 (多跳推理) 达 64.54%（前 43.6%），Cat 2 (时间推理) 达 72.90%（前 49.8%），Cat 3 (隐式推断) 达 44.79%，Cat 4 (事实抽取) 达 74.08%（前 57.1%）；
  - **架构结论**：彻底澄清了此前对 MiniLM 向量维度的归因偏差，确立了多说话人元数据精准提取与 Phase 3 离线语义去重更新对长程记忆推理的决定性作用。

---

## ADR-020：11 类能力图谱收成 6 类评测类型

- **背景**：ADR-009 的 11 类把做对时该回答不同的题放进了同一把尺子，也把只有一家基准、约 40 题的类型抬成了跨基准维度。
- **决策**：`UnifiedCapability` 只保留 6 类：事实回忆、多证据综合、时间与顺序、记忆更新、拒答、个性化。个性化只包含已经说过的偏好。错误前提纠正、内部矛盾、指令遵循、开放域常识、没说破的偏好、新情境应用和长期总结不再映射进这 6 类，`map_native_task_to_capability` 对它们返回 `None`。

---

## ADR-021：评测流水线阶段解耦（Subcommand 架构）、--smoke 一键封装与协议去侵入化

- **背景**：
  1. 此前命令行采用扁平 flags，导致不同阶段的参数严重耦合（如离线打分参数 `--eval-run-dir` 强依赖 `--metrics`，若漏传则容易产生非预期隐式行为）；
  2. 遗留的 `--top-k` 试图替外部记忆系统决定返回条数，但不同记忆系统（向量库、知识图谱、分层摘要树）拥有完全不同的内部检索策略与截断打法，向评测端暴露 `top_k` 属于严重破坏黑盒契约与抽象泄漏；
  3. 遗留的 `--server`（Coordinator 监听服务）让评测端反向开启 HTTP 监听外部容器握手，角色定位混乱；
  4. 底层零散的 `--max-conversations`、`--max-sessions`、`--max-questions` 暴露给初次使用者极易因参数配错导致系统异常或巨额 Token 浪费。
- **决策**：
  1. **彻底移除 `--top-k`**：坚守评测中间层黑盒契约，评测端只负责传递 query 并消费返回的 `formatted_memory`，具体检索多少条、如何去重重排完全属于 Memory Server 内部策略；
  2. **彻底移除 `--server` / `--host` / `--port`**：坚守评测端作为纯粹 C/S 客户端打流发起方的定位，不承担反向服务监听；
  3. **重构为清晰的阶段解耦子命令架构**：
     - `run`：一站式全流程评测（默认子命令，向后完全兼容）；
     - `ingest`：阶段一，仅写入长对话历史到 Memory Server；
     - `query`：阶段二，仅检索记忆并生成回答；
     - `eval`：阶段三，仅离线读取产物重打分，参数空间独立并严格校验必填项（`--run-dir` 与 `--metrics`）；
  4. **一键冒烟 `--smoke` 安全封装**：隐藏底层微调参数，在顶层及子命令暴露 `--smoke`，自动安全截取微量数据秒级跑通全链路验证。

---

## ADR-022：--smoke 极简微抽样（1 会话 1 Session 1 题）与真实 C/S 连通性测试边界

- **背景**：
  此前 ADR-021 将 `--smoke` 设定为「1 个会话、5 道考题」。但在 LoCoMo 等重型长对话数据集中，单个 Conversation 依然包含多达 35 个 Session（~1540 轮发言）。若被测 Memory Server 为重型知识图谱或多阶段抽取系统（如 LightMem/Mem0），仅写入这 35 个 Session 就需耗时 15~30 分钟，违背了“秒级连通性冒烟验证”的初衷。此外，用户容易混淆 `mock` 模式与真实网络连通性的职责边界。
- **决策**：
  1. **缩紧 `--smoke` 采样边界为最小原子测试单元**：
     - 固定锁定为 **1 个 Conversation + 1 个 Session + 1 道 Question**；
     - 使得端到端评测退化为 **单次 `POST /ingest` + 单次 `POST /retrieve`**，将冒烟耗时从数十分钟压缩至 1~3 秒以内；
  2. **基准选择策略**：
     - 默认使用 `locomo`（代表最标准的日常对话轮次）；
     - 允许通过 `-b / --benchmark` 切换至任意其他基准（如 `longmemeval`, `membench` 等），以便针对特定基准的 Schema 适配器与数据格式进行单题冒烟；
  3. **明确 `mock` 与 `http` 的职责分工**：
     - `mock`（内存桩）：验证客户端内部环境、依赖加载、Prompt 矩阵、打分器数学运算与产物写入（解决 CI/CD 与离线无外部依赖的可测性）；
     - `http`（真实网络客户端）：验证外部 Memory Server 的真实 HTTP 连通性、网络可达性、路由响应与入库反序列化（配合 `--smoke` 实现秒级服务探活）。

---

## ADR-023：彻底收敛评测端为纯粹 HTTP 客户端，移除公开 mock 模式，规范接口实体与并发契约

- **背景**：
  1. 此前 CLI 保留了 `--method mock`，导致初次使用者产生严重混淆（误以为 `mock` 能够测试外部服务连通性），且作为一个标准的 C/S 架构评测中间层，公开暴露本地内存测试桩破坏了评测中间层的角色定位；
  2. 评测框架开启多线程并发（如 `-w 10`）时，流量直接打向外部 Memory Server。若外部服务端未做会话隔离、或使用全局共享单例变量、或连接池过小，极易发生跨会话数据污染、数据库死锁与服务崩溃；
  3. 外部开发者接入时亟需清晰精确的接口 DTO 实体结构与 JSON 请求/响应规范。
- **决策**：
  1. **收敛评测端定位与 CLI 参数**：
     - `--server-url` 成为核心连接参数（缺省默认 `http://127.0.0.1:8002`）；
     - 彻底从公开帮助（`--help`）与 `README.md` 中移除 `--method` 和 `mock`，默认 100% 运行为面向外部 HTTP Memory Server 的客户端打流器（内部测试仅保留隐藏兼容）；
  2. **规范化 C/S 两大核心端点实体结构**：
     - 在文档中完整公布 `POST /ingest`（`IngestRequest`: `isolation_key`, `session: Session(session_id, session_time, turns: list[Turn])`）与 `POST /retrieve`（`RetrieveRequest`: `isolation_key`, `query`, `question_time`）的标准化 JSON 格式，统一响应信封 `Result[T]`；
  3. **确立服务端并发支撑契约**：
     - 明确要求 Memory Server 必须将 `isolation_key` 作为数据库/向量索引的分区主键（Partition Key），严禁全局共享状态；
     - 推荐生产级 ASGI 异步部署（`uvicorn server:app --workers 4`）与连接池调优；
     - 评测端默认采用 `--max-workers 1` 安全兜底，确保对单线程简陋 Demo 的 100% 兼容。

---

## ADR-024：客户端防作弊客观时钟度量、分层时间降级与同会话严格顺序传递契约

- **背景**：
  1. 此前协议中被测服务端响应体包含 `latency_ms`。但服务端自报耗时存在严重的造假风险；
  2. 长会话记忆具有强烈的因果时序性。若并发评测打乱了同一个对话内的 Session 顺序，记忆库将发生因果倒置；
  3. 各基准在时间字段（`turn_time` vs `session_time`）与说话人（`speaker` 角色 vs 人名）上存在异构性。
- **决策**：
  1. **耗时度量客户端化（Cheat-Proof Client Timing）**：
     - 响应体中的 `latency_ms` 降级为完全可选字段；评测框架一律通过客户端纳秒级高精度时钟 `time.perf_counter()` 采集端到端实际耗时；
     - 在同一局域网或 Localhost 环回网络下（RTT ~0.05ms），网络扰动 < 0.01%，真实量化了下游感知延迟；
  2. **同会话严格同步保序递交（In-Order Delivery）**：
     - 同一 `isolation_key` 内的 Session 严格串行、同步递交，前序 Session 收到 `200 OK` 后方可发送后序；多线程并发（`-w`）仅在跨 Conversation 间进行；
  3. **分层时间降级策略**：
     - `Turn` 实体显式携带 `turn_time: str | null`，`Session` 携带 `session_time: str | null`；
     - 服务端推荐降级消费：`timestamp = turn.turn_time or session.session_time`，兼容全量基准；
  4. **明确 Speaker 的双重语义**：
     - 包含标准角色（`"user"` / `"assistant"` / `"agent"`）与自然人名（如 LoCoMo 的 `"Alice"` / `"Bob"`），服务端可直接作为主语标签入库。

---

## ADR-025：README 叙事结构重构、双轨延迟记录对比与学术级全景架构图资产落地

- **背景**：
  1. 此前 `README.md` 直接以技术协议细节开篇，缺乏宏观全局概览与自顶向下的认知脚手架；
  2. 论文级开源项目需要一张高亲和力、结构严谨的学术系统全景架构图作为视觉锚点；
  3. `latency_ms` 此前的“防作弊”表述过于说教，需调整为专业客观的“双轨延迟度量（Dual Latency Tracking）”：客户端测量端到端往返耗时，若服务端返回内部耗时则共同沉淀，支持网络损耗对比与性能剖析。
- **决策**：
  1. **重构 README 章节叙事动线**：
     按照「项目定位 $\rightarrow$ 系统整体架构图 $\rightarrow$ 评测题与 6 类能力图谱 $\rightarrow$ 目录结构与模块职责 $\rightarrow$ 接口实体规范 $\rightarrow$ 服务端并发指南 $\rightarrow$ 运行指南 $\rightarrow$ 参数表 $\rightarrow$ 实战 Cookbook」标准流水线重构，认知层级由浅入深；
  2. **沉淀 16:9 暖色手账风学术全景架构图**：
     生成并保存为 `assets/architecture.png`，在 `.gitignore` 中解除忽略并纳入 Git 版本控制；
  3. **双轨延迟客观呈现**：
     评测端始终通过客户端 `time.perf_counter()` 采集端到端实际耗时；若服务端在响应中返回了 `latency_ms`，评测框架一并持久化记录，提供服务端内部计算耗时与客户端感知延迟的双向对照。

---

## ADR-026：剔除 README 压缩 Mermaid、泛化外部记忆黑盒抽象与 Token-Level F1 评测基线

- **背景**：
  1. GitHub 对包含多子图的横向宽幅 Mermaid 流程图（`flowchart LR`）存在自适应压缩缺陷，在移动端与小屏视口下字号极小无法阅读；且上方已有高清学术全景架构图（`assets/architecture.png`），Mermaid 造成双重视觉冗余；
  2. 原架构图与说明中在被测端标注“知识图谱”、“向量数据库”，过度具体化了外部服务的实现技术栈，违背了基准“对被测记忆范式保持完全中立与黑盒解耦”的宪章初衷；
  3. 需要在问答打分中确立无需外部模型 API 调用的 Token-Level F1 标准离线基线，与语义级 LLM-Judge 形成高低搭配。
- **决策**：
  1. **移除形变 Mermaid，转为简洁分层说明**：
     彻底删除 `README.md` 中的 Mermaid 图，保留 16:9 高清手绘架构图作为统一视觉入口，并在正文以 3 层列表形式精炼说明数据层、中间层与服务层的职责解耦；
  2. **泛化外部记忆服务抽象（Black-Box Decoupling）**：
     架构图与文档中移除狭义的“知识图谱/向量数据库”技术绑定，将其泛化为“自定义记忆引擎（Custom Memory Engine）”与“黑盒内部演化与存储”。无论被测系统内部使用向量检索、知识图谱、分层摘要（MemGPT/Letta）还是自定义 KV/混合策略，只要遵循 `POST /ingest` 与 `POST /retrieve` 协议均可接入；
  3. **固化标准 Token-Level F1 评测基线**：
     采用标准 SQuAD 式词袋 Token 级别的 Precision、Recall 与调和平均数 $F_1$，配合先验文本归一化（小写、去标点、去冠词、合并空白），作为零 API 成本、可完全确定性复现的离线客观打分基准。

---

## ADR-027：项目品牌全面升级为 MemBridge（C/S 解耦网关与中间件定位）

- **背景**：
  1. 原项目名称 `AgentMemoryBench` 遵循传统的“X-Bench”命名范式，在开源与学术社区同质化严重，且容易被误解为封闭的数据集评测脚本包，未能凸显其作为“C/S 解耦架构评测网关与中间层”的核心系统工程价值；
  2. 针对公开 GitHub 仓库门面，需要一个发音清晰、更具现代工业级系统辨识度的品牌名称。
- **决策**：
  1. **品牌升级为 MemBridge**：
     - 英文全称：**MemBridge: Standardized C/S Evaluation Middleware & Gateway for AI Agent Long-Term Memory Systems**；
     - 寓意：作为一座标准的桥梁（Bridge），连接多元的长对话评测基准数据与异构的外部独立记忆微服务；
  2. **仓库与配置同步更名**：
     - GitHub 仓库重命名为 `zzp-elio/MemBridge`，本地远程地址无缝切换；
     - `pyproject.toml` 包名更新为 `membridge`，保留 `memory-benchmark` 与新增 `membridge` 双 CLI 命令入口；
     - 核心文档（`README.md`、`AGENTS.md`、`docs/architecture.md`、`STATE.md`）全面对齐品牌升级。

---

## ADR-028：双语架构文档规范与国际化门禁（主英文 + 可选中文本）

- **背景**：
  1. 随着项目品牌升级为 MemBridge 并面向国际开源与学术社区，GitHub 默认首屏 `README.md` 需要以专业、地道、结构严谨的英文呈现；
  2. 原有的详尽中文文档涵盖了细致的 6 类能力图谱、C/S 实体规范、并发运维指南与用例，是中文母语开发者与国内团队的重要参考资产，不应废弃；
  3. 双语文档极易随代码迭代发生事实性漂移（例如一方更新了 CLI 参数或接口实体，另一方漏更），需要通过自动化测试保障双向有效性。
- **决策**：
  1. **主英文 + 可选中文的物理分离结构**：
     - [`README.md`](../README.md)：全英文版本作为 GitHub 仓库默认主入口；
     - [`README_zh.md`](../README_zh.md)：完整中文版本作为可选语言版本；
     - 两个文档顶部均放置统一的双语切换导航栏（分别链接至 [`README.md`](../README.md) 与 [`README_zh.md`](../README_zh.md)）；
  2. **双语内容与结构严格对齐**：
     - 系统整体架构、6 类能力图谱、关键模块职责、C/S API 规范（`IngestRequest` / `RetrieveRequest` / `Result[T]`）、服务端并发指南、CLI 命令参考及 Cookbook 用例保持 1:1 章节镜像对齐；
  3. **自动化测试纳入双语文档防漂移门禁**：
     - 扩展 `tests/test_end_to_end_pipeline.py` 中的 `test_documentation_links_and_paths_never_drift`，将 `README_zh.md` 纳入 `core_docs` 与 `active_doc` 检查范围；
     - 校验双语 README 中出现的所有相对链接和代码路径必须在磁盘上真实存在，漏改或失效则在 CI / Pre-commit 阶段立即拦截。

---

## ADR-029：系统全景架构图双语化资产对齐（英文独立手绘插图）

- **背景**：
  1. 在 ADR-028 建立双语文档体系后，英文主文档 [`README.md`](../README.md) 仍引用包含全中文文字标签的原架构图（`assets/architecture.png`），导致英文读者的视觉阅读体验断层；
  2. 国际社区与海外学术同行需要视觉元素、模块名称与数据流完全一致的全英文手绘架构图。
- **决策**：
  1. **建立双语架构图像资产**：
     - 保留原中文架构图为 [`assets/architecture.png`](../assets/architecture.png)，供 [`README_zh.md`](../README_zh.md) 呈现；
     - 新增全英文架构全景图 [`assets/architecture_en.png`](../assets/architecture_en.png)，供主入口 [`README.md`](../README.md) 呈现；
  2. **严格保持视觉风格与架构语义 1:1 对齐**：
     - 延续【暖色手账/白板手绘风】（米白细网格底、深炭墨水线、奶黄便签、暖橙标题、薄荷绿状态标）；
     - 三层解耦（Benchmark Data Tier -> MemBridge Evaluation Middleware -> External Memory Service）；
     - 通用黑盒解耦（Custom Memory Engine，不捆绑特定具体数据库）；
     - 数据流（`POST /ingest`、`POST /retrieve`、`formatted_memory`）保持标准 C/S 接口定义。

---

## ADR-030：实验目录不可静默覆盖，失败样本与裁判故障分开计分

- **背景**：
  1. README 写默认 `run_id` 自动生成，代码却固定为 `{benchmark}_{method}`。本地目录和远端 `isolation_key` 都会在下一次运行时撞车；
  2. ADR-008 要求 `UNDECIDABLE` 的记录分为 0，并单独给出可评分准确率。裁判 API 失败被塞进同一个 `UNDECIDABLE`，而且失败分支本身会因为非法字段再抛 `TypeError`；
  3. 没有预测结果的题被评测器跳过，均分只除以成功题，失败越多分母越小；
  4. ADR-025 要求同时保留客户端墙钟和服务端 `latency_ms`，runner 在服务端耗时大于 0 时丢掉墙钟；
  5. 有人提议给 `MemoryProvider` 增加删除命名空间的方法。这和 ADR-003 的两方法契约冲突。
- **决策**：
  1. 缺省 `run_id` 带 UTC 时间戳和 8 位随机后缀。目录非空时，没有 `--resume` 或 `--force` 就拒绝运行；
  2. 裁判调用或解析失败记为 `JUDGE_ERROR`，`is_correct=None`，不进入自动均分。`UNDECIDABLE` 仍按 ADR-008 在单题记录里记 0 分，同样不进入 `mean_score` / `scorable_mean_score`；
  3. 公开题里没有预测的题按 0 分进入 `mean_score`。`conditional_mean_score` 只平均那些真正产出了可评分预测的题，并同时写出 `completion_rate`；
  4. `retrieve_latency_ms` 与汇总里的 Mean / P50 / P95 用客户端墙钟。服务端 `latency_ms` 另存在 `server_*` 字段；
  5. 每次 ingest 附带 `idempotency_key = {isolation_key}:{session_id}`。Mock 对同一键不重复写入。外部服务不识别该键时，重复 POST 仍可能双写；
  6. 不新增第三个 `MemoryProvider` 方法，因此不做 `DELETE /namespace`。默认 HTTP 超时保持 1800 秒，只增加 `--timeout-seconds`。













