"""全流程端到端契约测试：Dataset -> Ingest(Session) -> Retrieve -> Answer -> Evaluate Answer。"""

from __future__ import annotations

from pathlib import Path

import pytest

from memory_benchmark.__main__ import main as cli_main
from memory_benchmark.core import (
    Conversation,
    Dataset,
    GoldAnswerInfo,
    IngestRequest,
    MemoryProvider,
    MockMemoryProvider,
    Question,
    Result,
    RetrievePayload,
    RetrieveRequest,
    Session,
    Turn,
    create_provider,
    list_methods,
)
from memory_benchmark.evaluators import create_evaluator, list_evaluators
from memory_benchmark.readers import FakeAnswerLLMClient, FrameworkAnswerReader
from memory_benchmark.runners.evaluation import run_artifact_evaluation
from memory_benchmark.runners.prediction import run_predictions
from memory_benchmark.storage import RunContext


def _sample_dataset() -> Dataset:
    return Dataset(
        dataset_name="locomo",
        conversations=[
            Conversation(
                conversation_id="conv-1",
                sessions=[
                    Session(
                        session_id="sess-1",
                        session_time="2026-05-01T10:00:00",
                        turns=[
                            Turn(
                                turn_id="t1",
                                speaker="Alice",
                                content="I adopted a golden retriever named Mango.",
                                normalized_role="user",
                            ),
                            Turn(
                                turn_id="t2",
                                speaker="Bob",
                                content="Mango is a lovely name for a golden retriever!",
                                normalized_role="assistant",
                            ),
                        ],
                    )
                ],
                questions=[
                    Question(
                        question_id="q1",
                        conversation_id="conv-1",
                        text="What is the name of Alice's dog?",
                        category="single-hop",
                    )
                ],
                gold_answers={
                    "q1": GoldAnswerInfo(
                        question_id="q1",
                        answer="Mango",
                    )
                },
            )
        ],
    )


def test_end_to_end_prediction_and_answer_evaluation(tmp_path: Path) -> None:
    """验证 Ingest(Session) -> Retrieve -> Answer -> Evaluate Answer 四阶段闭环与三大黑盒效率指标。"""
    dataset = _sample_dataset()

    provider = create_provider("mock")
    assert isinstance(provider, MockMemoryProvider)

    fake_client = FakeAnswerLLMClient("Mango")
    reader = FrameworkAnswerReader(client=fake_client)

    run_ctx = RunContext.create(
        run_id="smoke_run",
        benchmark_name="locomo",
        method_name="mock",
        model_name="fake-answer-llm",
        output_root=tmp_path / "outputs",
    )
    pred_summary = run_predictions(
        dataset=dataset,
        provider=provider,
        run_context=run_ctx,
        answer_reader=reader,
    )
    assert len(fake_client.calls) == 1
    assert "Mango" in fake_client.calls[0]["prompt"]

    assert pred_summary.total_conversations == 1
    assert pred_summary.completed_conversations == 1
    assert pred_summary.total_questions == 1
    assert pred_summary.completed_questions == 1
    assert pred_summary.failed_count == 0

    # 验证三大客观黑盒效率指标已采集
    eff = pred_summary.efficiency_metrics
    assert "total_ingest_latency_ms" in eff
    assert "mean_retrieve_latency_ms" in eff
    assert eff["mean_retrieved_context_tokens"] > 0

    evaluator = create_evaluator("f1", benchmark_name="locomo")
    eval_summary = run_artifact_evaluation(
        run_dir=run_ctx.run_dir,
        evaluator=evaluator,
        expected_benchmark="locomo",
    )

    assert eval_summary.total_questions == 1
    assert eval_summary.mean_score == 1.0


def test_runner_raises_on_non_200_result_code(tmp_path: Path) -> None:
    """验证当被测记忆服务返回 code != 200 时，Runner 立即捕获并报错阻断。"""

    class FailingServerProvider(MemoryProvider):
        def ingest(self, request: IngestRequest) -> Result[None]:
            return Result.fail(code=504, message="Session ingest timed out")

        def retrieve(self, request: RetrieveRequest) -> Result[RetrievePayload]:
            return Result.ok(RetrievePayload(formatted_memory="unused"))

    run_ctx = RunContext.create(
        run_id="fail_run",
        benchmark_name="locomo",
        method_name="http",
        model_name="fake-answer-llm",
        output_root=tmp_path / "outputs",
    )
    with pytest.raises(RuntimeError, match="code=504"):
        run_predictions(
            dataset=_sample_dataset(),
            provider=FailingServerProvider(),
            run_context=run_ctx,
        )


def test_streamlined_main_entrypoint(tmp_path: Path) -> None:
    """验证单文件极简命令行入口 (__main__.py) 支持一键跑通评测与参数校验。"""
    import json

    assert set(list_methods()) == {"mock", "http"}
    assert "f1" in list_evaluators()

    sample_file = tmp_path / "data" / "locomo" / "locomo10.json"
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text(
        json.dumps(
            [
                {
                    "sample_id": "conv-cli-1",
                    "conversation": {
                        "speaker_a": "Alice",
                        "speaker_b": "Bob",
                        "session_1_date_time": "2026-05-01 10:00",
                        "session_1": [
                            {"speaker": "Alice", "dia_id": "D1:1", "text": "I live in Paris."},
                            {"speaker": "Bob", "dia_id": "D1:2", "text": "Paris is wonderful!"},
                        ],
                    },
                    "qa": [
                        {
                            "question": "Where does Alice live?",
                            "answer": "Paris",
                            "category": 1,
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = cli_main(
        [
            "--project-root",
            str(tmp_path),
            "--benchmark",
            "locomo",
            "--method",
            "mock",
            "--run-id",
            "cli_smoke",
            "--metrics",
            "f1",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "outputs" / "cli_smoke" / "artifacts" / "method_predictions.jsonl").is_file()
    assert (tmp_path / "outputs" / "cli_smoke" / "summaries" / "summary.f1.json").is_file()


def test_spring_boot_style_yaml_config_and_evaluators() -> None:
    """验证 application.yaml 占位符解析、Dataclass 自动反射注入、选择题 ExactMatch 及 Judge UNDECIDABLE 路由。"""
    from memory_benchmark.core import (
        AnswerResult,
        LLMProperties,
        bind_dataclass,
        load_app_config,
        resolve_placeholders,
    )

    # 1. 验证嵌套占位符 ${A:${B:default}} 解析与反射注入
    env = {"OPENAI_API_KEY": "sk-test-env", "JUDGE_LLM_MODEL": "claude-opus-4"}
    raw = {
        "api_key": "${ANSWER_LLM_API_KEY:${OPENAI_API_KEY:}}",
        "model": "${JUDGE_LLM_MODEL:gpt-4o-mini}",
        "temperature": "0.2",
    }
    resolved = resolve_placeholders(raw, env=env)
    props = bind_dataclass(LLMProperties, resolved)
    assert props.api_key == "sk-test-env"
    assert props.model == "claude-opus-4"
    assert props.temperature == 0.2

    # 2. 验证从项目 configs/application.yaml 按 Benchmark 层级覆盖 prompts 与 llm 参数（如 max_tokens / temperature）
    app_cfg = load_app_config(".")
    default_prof = app_cfg.profile("default")
    membench_prof = app_cfg.profile("membench")
    beam_prof = app_cfg.profile(
        "beam",
        overrides={
            "llm": {"answer": {"temperature": 0.35}, "judge": {"temperature": 0.1}},
            "prompts": {"judge_system": "Custom Beam Judge Rubric"},
        },
    )
    assert default_prof.answer_llm.max_tokens == 512
    assert membench_prof.answer_llm.max_tokens == 16
    assert "A, B, C, or D" in membench_prof.prompts.answer_system
    # 未在 membench 中覆盖的 judge_system 自动继承自顶层 prompts 默认值
    assert membench_prof.prompts.judge_system == default_prof.prompts.judge_system
    # 运行时 overrides 进一步覆盖 beam 的 temperature 与 judge_system
    assert beam_prof.answer_llm.max_tokens == 1024
    assert beam_prof.answer_llm.temperature == 0.35
    assert beam_prof.judge_llm.temperature == 0.1
    assert beam_prof.prompts.judge_system == "Custom Beam Judge Rubric"

    # 3. 验证通用 ExactMatchEvaluator 直接支持 MemBench 选择题判分
    em_eval = create_evaluator("exact_match")
    q = Question(question_id="mc-1", conversation_id="c-1", text="Which city?")
    gold_mc = GoldAnswerInfo(
        question_id="mc-1",
        answer="B. Paris",
        metadata={"ground_truth": "B"},
    )
    res_ok = em_eval.evaluate(q, AnswerResult(conversation_id="c-1", question_id="mc-1", answer="(B)"), gold_mc)
    assert res_ok.score == 1.0
    assert res_ok.is_correct is True

    # 4. 验证通用 LLMJudgeEvaluator 支持 UNDECIDABLE 拒判转人工复核状态
    judge_eval = create_evaluator(
        "llm_judge",
        completion_fn=lambda **_: '{"verdict": "UNDECIDABLE", "score": 0.0, "reason": "Missing year anchor"}',
    )
    res_undecidable = judge_eval.evaluate(
        q,
        AnswerResult(conversation_id="c-1", question_id="mc-1", answer="Since 2020"),
        GoldAnswerInfo(question_id="mc-1", answer="3 years"),
    )
    assert res_undecidable.details["verdict"] == "UNDECIDABLE"
    assert res_undecidable.details["needs_human_review"] is True


def test_documentation_links_and_paths_never_drift() -> None:
    """硬门禁：防止重构代码后忘记同步架构文档（自动校验核心 Markdown 链接有效性与架构文档覆盖度）。"""
    import re

    repo_root = Path(__file__).resolve().parents[1]
    core_docs = [
        repo_root / "AGENTS.md",
        repo_root / "STATE.md",
        repo_root / "README.md",
        repo_root / "README_zh.md",
        repo_root / "docs" / "architecture.md",
        repo_root / "docs" / "decisions.md",
    ]
    # 匹配形如 [`label`](path) 或 [label](path) 的真实 Markdown 链接（排除 `Result[T](code, ...)` 这类函数签名）
    link_pattern = re.compile(r"(?<![A-Za-z0-9_])\[[^\]]+\]\(([^)#\s]+)(?:#[^)]*)?\)")

    for doc_path in core_docs:
        assert doc_path.exists(), f"Missing core document: {doc_path}"
        content = doc_path.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            raw_target = match.group(1).strip()
            if raw_target.startswith(("http://", "https://", "mailto:", "file://")):
                continue
            resolved = (doc_path.parent / raw_target).resolve()
            assert resolved.exists(), (
                f"Stale link in {doc_path.relative_to(repo_root)} -> '{raw_target}' "
                f"(resolved to non-existent {resolved})"
            )

    # Active 架构文档（README.md 与 docs/architecture.md）中出现的 `src/memory_benchmark/...` 路径必须真实存在
    code_path_pattern = re.compile(r"`((?:src/memory_benchmark|configs)/[A-Za-z0-9_./-]+)`")
    for active_doc in (
        repo_root / "README.md",
        repo_root / "README_zh.md",
        repo_root / "docs" / "architecture.md",
    ):
        text = active_doc.read_text(encoding="utf-8")
        for match in code_path_pattern.finditer(text):
            rel_path = match.group(1)
            assert (repo_root / rel_path).exists(), (
                f"Stale code path `{rel_path}` in {active_doc.relative_to(repo_root)} does not exist on disk!"
            )

    # AGENTS.md 与 STATE.md 基础存在性与非空校验（不卡死硬性行数）
    assert len((repo_root / "AGENTS.md").read_text(encoding="utf-8").strip()) > 0
    assert len((repo_root / "STATE.md").read_text(encoding="utf-8").strip()) > 0


def test_retain_scored_cohort_drops_unmapped_questions() -> None:
    """没有统一类型的题不进入评测数据集，空对话一并去掉。"""
    from memory_benchmark.benchmark_adapters.base import retain_scored_cohort
    from memory_benchmark.core import (
        Conversation,
        Dataset,
        GoldAnswerInfo,
        Question,
        Session,
        Turn,
        UnifiedCapability,
    )

    dataset = Dataset(
        dataset_name="locomo",
        conversations=[
            Conversation(
                conversation_id="keep",
                sessions=[Session(session_id="s", turns=[Turn("t", "user", "hi")])],
                questions=[
                    Question(
                        question_id="q-keep",
                        conversation_id="keep",
                        text="name?",
                        capability=UnifiedCapability.FACT_RECALL,
                    ),
                    Question(
                        question_id="q-drop",
                        conversation_id="keep",
                        text="guess?",
                        category="3",
                    ),
                ],
                gold_answers={
                    "q-keep": GoldAnswerInfo("q-keep", "Ada"),
                    "q-drop": GoldAnswerInfo("q-drop", "no"),
                },
            ),
            Conversation(
                conversation_id="only-unmapped",
                sessions=[Session(session_id="s", turns=[Turn("t", "user", "hi")])],
                questions=[
                    Question(
                        question_id="q-only",
                        conversation_id="only-unmapped",
                        text="mood?",
                        category="highlevel",
                    )
                ],
                gold_answers={"q-only": GoldAnswerInfo("q-only", "calm")},
            ),
        ],
    )

    dropped = retain_scored_cohort(dataset)
    assert dropped == 2
    assert [conversation.conversation_id for conversation in dataset.conversations] == ["keep"]
    assert [question.question_id for question in dataset.conversations[0].questions] == ["q-keep"]
    assert set(dataset.conversations[0].gold_answers) == {"q-keep"}
    assert dataset.metadata["scored_question_count"] == 1


def test_real_benchmarks_load_into_six_type_cohort() -> None:
    """五个基准都能读入，且读入后的题都落在 6 类里。"""
    from pathlib import Path

    from memory_benchmark.benchmark_adapters import get_adapter

    root = Path(__file__).resolve().parents[1]
    required = [
        root / "data/locomo/locomo10.json",
        root / "data/longmemeval/longmemeval_s_cleaned.json",
        root / "data/halumem/HaluMem-Medium.jsonl",
        root / "data/BEAM/beam_dataset/100K",
        root / "data/membench/Membenchdata/data2test/0-10k",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("local benchmark data is not present")

    specs = [
        ("locomo", None, None),
        ("longmemeval", "s_cleaned", None),
        ("halumem", "medium", 1),
        ("beam", "100k", 1),
        ("membench", "0_10k", 1),
        ("membench", "0_10k", None),
    ]
    for name, variant, limit in specs:
        dataset = get_adapter(name, root, variant=variant).load(limit=limit)
        assert dataset.conversations
        for conversation in dataset.conversations:
            assert conversation.questions
            for question in conversation.questions:
                assert question.unified_capability is not None

    locomo = get_adapter("locomo", root).load()
    assert sum(len(conversation.questions) for conversation in locomo.conversations) == 1444
    assert locomo.metadata["excluded_unmapped_question_count"] == 96


def test_unified_6_capabilities_taxonomy_mapping() -> None:
    """验证 6 类记忆评测类型，以及不能并进这 6 类的原生题返回空。"""
    from memory_benchmark.core import (
        Question,
        UnifiedCapability,
        map_native_task_to_capability,
    )

    assert len(UnifiedCapability) == 6
    assert UnifiedCapability.FACT_RECALL.label_zh == "事实回忆"
    assert UnifiedCapability.MULTI_HOP.label_zh == "多证据综合"
    assert UnifiedCapability.TEMPORAL.label_zh == "时间与顺序"
    assert UnifiedCapability.MEMORY_UPDATE.label_zh == "记忆更新"
    assert UnifiedCapability.ABSTENTION.label_zh == "拒答"
    assert UnifiedCapability.PREFERENCE.label_zh == "个性化"

    assert map_native_task_to_capability("locomo", "1") == UnifiedCapability.MULTI_HOP
    assert map_native_task_to_capability("locomo", "2") == UnifiedCapability.TEMPORAL
    assert map_native_task_to_capability("locomo", "3") is None
    assert map_native_task_to_capability("locomo", "4") == UnifiedCapability.FACT_RECALL
    assert map_native_task_to_capability("locomo", "5") is None

    assert map_native_task_to_capability("longmemeval", "single_session_user") == UnifiedCapability.FACT_RECALL
    assert map_native_task_to_capability("longmemeval", "multi_session") == UnifiedCapability.MULTI_HOP
    assert map_native_task_to_capability("longmemeval", "temporal_reasoning") == UnifiedCapability.TEMPORAL
    assert map_native_task_to_capability("longmemeval", "dynamic_knowledge_update") == UnifiedCapability.MEMORY_UPDATE
    assert map_native_task_to_capability("longmemeval", "preference_switch") == UnifiedCapability.PREFERENCE
    assert map_native_task_to_capability("longmemeval", "multi_session_abs") == UnifiedCapability.ABSTENTION

    assert map_native_task_to_capability("beam", "information_extraction") == UnifiedCapability.FACT_RECALL
    assert map_native_task_to_capability("beam", "event_ordering") == UnifiedCapability.TEMPORAL
    assert map_native_task_to_capability("beam", "preference_following") == UnifiedCapability.PREFERENCE
    assert map_native_task_to_capability("beam", "contradiction_resolution") is None
    assert map_native_task_to_capability("beam", "instruction_following") is None
    assert map_native_task_to_capability("beam", "summarization") is None

    assert map_native_task_to_capability("membench", "simple") == UnifiedCapability.FACT_RECALL
    assert map_native_task_to_capability("membench", "aggregative") == UnifiedCapability.MULTI_HOP
    assert map_native_task_to_capability("membench", "knowledge_update") == UnifiedCapability.MEMORY_UPDATE
    assert map_native_task_to_capability("membench", "highlevel") is None
    assert map_native_task_to_capability("membench", "post_processing") is None
    assert map_native_task_to_capability("membench", "noisy") is None

    assert map_native_task_to_capability("halumem", "basic_fact") == UnifiedCapability.FACT_RECALL
    assert map_native_task_to_capability("halumem", "memory_conflict") is None
    assert map_native_task_to_capability("halumem", "memory_boundary") == UnifiedCapability.ABSTENTION
    assert map_native_task_to_capability("halumem", "generalization") is None

    # 3. 验证 Question 实体属性与解析
    q = Question(
        question_id="q-test",
        conversation_id="c-test",
        text="What did Bob say?",
        capability=UnifiedCapability.FACT_RECALL,
    )
    assert q.unified_capability == UnifiedCapability.FACT_RECALL

    q_str = Question(
        question_id="q-str",
        conversation_id="c-test",
        text="Where is Alice?",
        capability="temporal",
    )
    assert q_str.unified_capability == UnifiedCapability.TEMPORAL


def test_end_to_end_capability_breakdown_in_evaluation(tmp_path: Path) -> None:
    """验证预测到评测全流程中自动持久化 capability 并生成 6 类分解报告 (capability_breakdown)。"""
    import json
    from memory_benchmark.core import (
        Conversation,
        Dataset,
        GoldAnswerInfo,
        Question,
        Session,
        Turn,
        UnifiedCapability,
        create_provider,
    )
    from memory_benchmark.evaluators import create_evaluator
    from memory_benchmark.readers import FakeAnswerLLMClient, FrameworkAnswerReader
    from memory_benchmark.runners.evaluation import run_artifact_evaluation
    from memory_benchmark.runners.prediction import run_predictions
    from memory_benchmark.storage import RunContext

    # 构造跨越多个不同能力维度的测试数据集
    dataset = Dataset(
        dataset_name="locomo",
        conversations=[
            Conversation(
                conversation_id="conv-cap-1",
                sessions=[
                    Session(
                        session_id="s1",
                        turns=[
                            Turn(turn_id="t1", speaker="Alice", content="My dog is Mango.", normalized_role="user"),
                        ],
                    )
                ],
                questions=[
                    Question(
                        question_id="q-fact",
                        conversation_id="conv-cap-1",
                        text="What is dog's name?",
                        capability=UnifiedCapability.FACT_RECALL,
                    ),
                    Question(
                        question_id="q-temp",
                        conversation_id="conv-cap-1",
                        text="When was Mango adopted?",
                        capability=UnifiedCapability.TEMPORAL,
                    ),
                ],
                gold_answers={
                    "q-fact": GoldAnswerInfo(question_id="q-fact", answer="Mango"),
                    "q-temp": GoldAnswerInfo(question_id="q-temp", answer="Yesterday"),
                },
            )
        ],
    )

    provider = create_provider("mock")
    fake_client = FakeAnswerLLMClient("Mango")
    reader = FrameworkAnswerReader(client=fake_client)

    run_ctx = RunContext.create(
        run_id="cap_eval_run",
        benchmark_name="locomo",
        method_name="mock",
        model_name="fake-llm",
        output_root=tmp_path / "outputs",
    )
    run_predictions(
        dataset=dataset,
        provider=provider,
        run_context=run_ctx,
        answer_reader=reader,
    )

    evaluator = create_evaluator("f1", benchmark_name="locomo")
    summary = run_artifact_evaluation(
        run_dir=run_ctx.run_dir,
        evaluator=evaluator,
        expected_benchmark="locomo",
    )

    summary_file = Path(summary.summary_path)
    assert summary_file.is_file()
    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))

    assert "capability_breakdown" in summary_data
    breakdown = summary_data["capability_breakdown"]
    assert len(breakdown) == 2

    by_cap = {item["capability"]: item for item in breakdown}
    assert "fact_recall" in by_cap
    assert "temporal" in by_cap

    fact_item = by_cap["fact_recall"]
    assert fact_item["label_zh"] == "事实回忆"
    assert fact_item["layer"] == "事实"
    assert fact_item["question_count"] == 1
    assert fact_item["mean_score"] == 1.0
    assert fact_item["human_review_count"] == 0

    temp_item = by_cap["temporal"]
    assert temp_item["label_zh"] == "时间与顺序"
    assert temp_item["layer"] == "变化"
    assert temp_item["question_count"] == 1
    assert temp_item["mean_score"] == 0.0


def test_coordinator_server_ready_handshake_and_task_execution(tmp_path: Path) -> None:
    """验证 Coordinator Server 的 HTTP /ready 双向握手、异步任务池调度及 Result[T] 响应契约。"""
    import json
    import time
    import requests
    from memory_benchmark.coordinator import (
        CoordinatorContext,
        CoordinatorServer,
        TaskState,
    )
    from memory_benchmark.core import load_app_config

    # 1. 准备本地基准测试数据
    sample_file = tmp_path / "data" / "locomo" / "locomo10.json"
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text(
        json.dumps(
            [
                {
                    "sample_id": "conv-coord-1",
                    "conversation": {
                        "speaker_a": "Alice",
                        "speaker_b": "Bob",
                        "session_1_date_time": "2026-05-01 10:00",
                        "session_1": [
                            {"speaker": "Alice", "dia_id": "D1:1", "text": "I like reading novels."},
                            {"speaker": "Bob", "dia_id": "D1:2", "text": "Novels are great!"},
                        ],
                    },
                    "qa": [
                        {
                            "question": "What does Alice like?",
                            "answer": "novels",
                            "category": 4,
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    app_cfg = load_app_config(str(tmp_path))
    ctx = CoordinatorContext(app_config=app_cfg)

    # 2. 启动 CoordinatorServer (port=0 动态端口)
    with CoordinatorServer(ctx, host="127.0.0.1", port=0) as server:
        base_url = server.base_url

        # 3. 探活测试 GET /health
        res_health = requests.get(f"{base_url}/health", timeout=5)
        assert res_health.status_code == 200
        health_json = res_health.json()
        assert health_json["code"] == 200
        assert health_json["data"]["status"] == "UP"

        # 4. 模拟外部记忆系统发送 POST /ready
        ready_payload = {
            "method_name": "mock",
            "endpoint": "http://127.0.0.1:9099",
            "benchmark": "locomo",
            "run_id": "coord_test_run",
            "metrics": ["f1"],
            "max_conversations": 1,
            "max_questions_per_conversation": 1,
        }
        res_ready = requests.post(f"{base_url}/ready", json=ready_payload, timeout=5)
        assert res_ready.status_code == 200
        ready_json = res_ready.json()
        assert ready_json["code"] == 200
        task_id = ready_json["data"]["task_id"]
        assert task_id

        # 5. 轮询 GET /status 等待后台工作线程异步完成评测
        completed = False
        for _ in range(30):
            time.sleep(0.1)
            res_status = requests.get(f"{base_url}/status?task_id={task_id}", timeout=5)
            assert res_status.status_code == 200
            status_json = res_status.json()
            if status_json["data"]["status"] == TaskState.COMPLETED.value:
                completed = True
                summary = status_json["data"]["result_summary"]
                assert summary is not None
                assert "prediction" in summary
                assert "evaluations" in summary
                break
            elif status_json["data"]["status"] == TaskState.FAILED.value:
                pytest.fail(f"Task failed: {status_json['data']['error_message']}")

        assert completed, "Task did not complete within timeout"

        # 6. 验证 GET /tasks 返回任务大盘
        res_tasks = requests.get(f"{base_url}/tasks", timeout=5)
        assert res_tasks.status_code == 200
        tasks_json = res_tasks.json()
        assert len(tasks_json["data"]) >= 1

        # 7. 异常分支校验：不存在的 task_id -> 404
        res_not_found = requests.get(f"{base_url}/status?task_id=nonexistent", timeout=5)
        assert res_not_found.status_code == 404
        assert res_not_found.json()["code"] == 404


def test_lightmem_server_protocol_integration() -> None:
    """验证 LightMem Docker 服务端实现标准 /ingest 与 /retrieve 协议并支持 HttpMemoryProvider 调用。"""
    import sys
    import threading
    import requests
    from http.server import ThreadingHTTPServer
    from memory_benchmark.core import (
        HttpMemoryProvider,
        IngestRequest,
        RetrieveRequest,
        Session,
        Turn,
    )

    repo_root = Path(__file__).resolve().parents[1]
    lightmem_docker_dir = repo_root / "third_party" / "methods" / "LightMem" / "docker"
    if not lightmem_docker_dir.is_dir():
        pytest.skip("LightMem docker server is not part of this checkout")
    if str(lightmem_docker_dir) not in sys.path:
        sys.path.insert(0, str(lightmem_docker_dir))

    from server import LightMemHTTPHandler

    # 1. 启动轻量 LightMem 服务端（ephemeral port）
    server = ThreadingHTTPServer(("127.0.0.1", 0), LightMemHTTPHandler)
    server_port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        provider = HttpMemoryProvider(base_url=f"http://127.0.0.1:{server_port}")

        # 2. 验证 Session 写入 Ingest 契约
        ingest_req = IngestRequest(
            isolation_key="iso-lightmem-test",
            session=Session(
                session_id="s1",
                session_time="2026-05-01 10:00",
                turns=[
                    Turn(
                        turn_id="t1",
                        speaker="Alice",
                        content="I adopted a rescue cat named Mochi.",
                        normalized_role="user",
                    )
                ],
            ),
        )
        ingest_res = provider.ingest(ingest_req)
        assert ingest_res.is_success
        assert ingest_res.code == 200

        # 3. 验证 carries metadata is_last_session 与 /optimize 端点
        ingest_last = IngestRequest(
            isolation_key="iso-lightmem-test",
            session=Session(
                session_id="s2",
                session_time="2026-05-02 11:00",
                turns=[
                    Turn(
                        turn_id="t2",
                        speaker="Bob",
                        content="Mochi loves tuna treats.",
                        normalized_role="user",
                    )
                ],
            ),
            metadata={"is_last_session": True},
        )
        assert provider.ingest(ingest_last).is_success

        opt_res = requests.post(
            f"http://127.0.0.1:{server_port}/optimize",
            json={"isolation_key": "iso-lightmem-test"},
            timeout=5,
        )
        assert opt_res.status_code == 200
        assert opt_res.json()["code"] == 200

        # 4. 验证检索 Retrieve 契约
        ret_req = RetrieveRequest(
            isolation_key="iso-lightmem-test",
            query="What is the name of Alice's cat?",
            top_k=5,
        )
        ret_res = provider.retrieve(ret_req)
        assert ret_res.is_success
        assert ret_res.code == 200
        assert ret_res.data is not None
        assert "Mochi" in ret_res.data.formatted_memory

    finally:
        server.shutdown()
        server.server_close()


def test_dual_schema_llm_judge_pydantic_enforcement() -> None:
    """验证 Pydantic 双模式 (Binary / Rubric) 强类型裁判模型、自动路由与确定性打分映射。"""
    import pytest
    from pydantic import ValidationError
    from memory_benchmark.evaluators import (
        BinaryJudgeEvaluation,
        RubricJudgeEvaluation,
        create_evaluator,
        parse_judge_response,
    )
    from memory_benchmark.core import Question, AnswerResult, GoldAnswerInfo

    # 1. 验证 Pydantic Schema 定义与字段非空校验
    # 空白 reason 会被拦截
    with pytest.raises(ValidationError):
        BinaryJudgeEvaluation(reason="   ", verdict="CORRECT")

    # 二元 Schema 物理杜绝 PARTIAL（字段类型校验失败）
    with pytest.raises(ValidationError):
        BinaryJudgeEvaluation(reason="Partially correct", verdict="PARTIAL")  # type: ignore[arg-type]

    # Rubric Schema 允许 PARTIAL
    rubric_obj = RubricJudgeEvaluation(reason="Got 1 out of 2 cities", verdict="PARTIAL")
    assert rubric_obj.verdict == "PARTIAL"

    # 2. 验证 parse_judge_response 结合模式与确定性打分映射
    # Binary 模式：CORRECT -> 1.0, WRONG -> 0.0, UNDECIDABLE -> 0.0 (needs_review)
    dec_bin_ok = parse_judge_response('{"reason": "Fully matches", "verdict": "CORRECT"}', mode="binary")
    assert dec_bin_ok.score == 1.0
    assert dec_bin_ok.is_correct is True

    dec_bin_wrong = parse_judge_response('{"reason": "Completely wrong", "verdict": "WRONG"}', mode="binary")
    assert dec_bin_wrong.score == 0.0
    assert dec_bin_wrong.is_correct is False

    dec_bin_undecidable = parse_judge_response('{"reason": "Missing year anchor", "verdict": "UNDECIDABLE"}', mode="binary")
    assert dec_bin_undecidable.score == 0.0
    assert dec_bin_undecidable.needs_human_review is True

    # 3. 验证 Rubric 模式支持 PARTIAL 获得 0.5 分
    dec_rubric_partial = parse_judge_response(
        '{"reason": "Recalled 1 entity out of 2", "verdict": "PARTIAL"}',
        mode="rubric",
    )
    assert dec_rubric_partial.score == 0.5
    assert dec_rubric_partial.verdict == "PARTIAL"

    # 4. 验证 create_evaluator 工厂自动根据 benchmark 注入 mode
    # locomo -> binary 模式
    eval_locomo = create_evaluator(
        "llm_judge",
        benchmark_name="locomo",
        completion_fn=lambda **_: '{"reason": "Perfect match", "verdict": "CORRECT"}',
    )
    assert getattr(eval_locomo, "mode") == "binary"

    # beam -> rubric 模式
    eval_beam = create_evaluator(
        "llm_judge",
        benchmark_name="beam",
        completion_fn=lambda **_: '{"reason": "Partial coverage", "verdict": "PARTIAL"}',
    )
    assert getattr(eval_beam, "mode") == "rubric"

    q = Question(conversation_id="conv-beam", question_id="q-beam", text="Cities visited?")
    ans = AnswerResult(conversation_id="conv-beam", question_id="q-beam", answer="Paris")
    gold = GoldAnswerInfo(question_id="q-beam", answer="Paris and Lyon")
    res_beam = eval_beam.evaluate(q, ans, gold)
    assert res_beam.score == 0.5
    assert res_beam.details["verdict"] == "PARTIAL"
    assert res_beam.details["mode"] == "rubric"


def test_task_prompt_matrix_and_safe_variable_formatting() -> None:
    """验证变量安全注入引擎（无残留未赋值变量）、细分题型针对性 Prompt 派发与 Judge 超参。"""
    from memory_benchmark.core import (
        Question,
        AnswerResult,
        GoldAnswerInfo,
        RetrievePayload,
        PromptProperties,
        load_app_config,
        build_prompt_variable_pool,
        format_prompt_template,
    )
    from memory_benchmark.readers.answer import FrameworkAnswerReader, FakeAnswerLLMClient
    from memory_benchmark.evaluators import create_evaluator

    cfg = load_app_config()

    # 1. 验证 Judge 超参：放宽至 4096，temperature 为 0.0
    for bench in ("locomo", "longmemeval", "beam", "membench", "halumem"):
        prof = cfg.profile(bench)
        assert prof.judge_llm.max_tokens >= 4096
        assert prof.judge_llm.temperature == 0.0

    # 2. 验证 format_prompt_template 零残留且免疫 JSON 花括号
    raw_template = """Return JSON: {"reason": "ok", "verdict": "CORRECT"}
[Context]: {memory_context}
[Date]: {date}
[Question]: {question}
[Gold]: {gold_answer}
[Prediction]: {predicted_answer}"""

    variables = build_prompt_variable_pool(
        question_text="What is the capital?",
        memory_context="France capital is Paris.",
        question_time="2026-05-01",
        gold_answer="Paris",
        predicted_answer="Paris",
    )
    rendered = format_prompt_template(raw_template, variables)
    # 保证所有业务变量均已赋值
    assert "France capital is Paris." in rendered
    assert "2026-05-01" in rendered
    assert "What is the capital?" in rendered
    assert "Paris" in rendered
    # 保证 JSON 结构体中的花括号与字段名未被破坏
    assert '{"reason": "ok", "verdict": "CORRECT"}' in rendered
    # 保证无任何未赋值的 {identifier} 残留
    import re
    remaining_vars = re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", rendered)
    assert remaining_vars == [], f"Unexpected unassigned variables left in prompt: {remaining_vars}"

    # 3. 验证细分题型针对性 Prompt 派发能力（task_answer_prompts）
    matrix_prompts = PromptProperties(
        answer_user="{memory_context}\n\nQuestion: {question}\n\nAnswer:",
        task_answer_prompts={
            "2": (
                "{memory_context}\n\nQuestion: {question}\n\n"
                "Use DATE of CONVERSATION to answer with an approximate date and "
                "resolve them using the conversation timestamp into a specific date.\n\nAnswer:"
            )
        },
    )
    matrix_reader = FrameworkAnswerReader(client=FakeAnswerLLMClient("dummy"), prompts=matrix_prompts)
    
    q_cat2 = Question(conversation_id="conv-1", question_id="q-time", text="Where was John before Seattle?", category="2")
    payload = RetrievePayload(formatted_memory="John was in Chicago.")
    prompt_res_cat2 = matrix_reader.build_prompt(q_cat2, payload)
    cat2_text = prompt_res_cat2.prompt_messages[1].content
    assert "Use DATE of CONVERSATION to answer with an approximate date" in cat2_text
    assert "resolve them using the conversation timestamp into a specific date" in cat2_text
    assert "{memory_context}" not in cat2_text
    assert "{question}" not in cat2_text

    q_cat1 = Question(conversation_id="conv-1", question_id="q-multi", text="Common hobbies?", category="1")
    prompt_res_cat1 = matrix_reader.build_prompt(q_cat1, payload)
    cat1_text = prompt_res_cat1.prompt_messages[1].content
    assert "Use DATE of CONVERSATION" not in cat1_text

    # 4. 验证 LongMemEval 裁判端任务分发（temporal-reasoning, knowledge-update, preference, abstention）
    captured_judge_prompts: dict[str, str] = {}
    def _mock_lme_judge(system_prompt: str, user_prompt: str) -> str:
        # 记录根据 category 选出的 system_prompt
        return '{"reason": "Correct", "verdict": "CORRECT"}'

    eval_lme = create_evaluator("llm_judge", benchmark_name="longmemeval", completion_fn=lambda system_prompt, user_prompt: '{"reason": "ok", "verdict": "CORRECT"}')
    for cat, keyword in [
        ("temporal-reasoning", "off-by-one"),
        ("knowledge-update", "updated answer"),
        ("preference", "personal information"),
        ("abstention", "unanswerable"),
    ]:
        captured_sys = []
        ev = create_evaluator(
            "llm_judge",
            benchmark_name="longmemeval",
            completion_fn=lambda system_prompt, user_prompt, cs=captured_sys: cs.append(system_prompt) or '{"reason": "ok", "verdict": "CORRECT"}',
        )
        q = Question(conversation_id="c", question_id=f"q-{cat}", text="sample", category=cat)
        ev.evaluate(q, AnswerResult(conversation_id="c", question_id=f"q-{cat}", answer="ans"), GoldAnswerInfo(question_id=f"q-{cat}", answer="gold"))
        assert any(keyword in p for p in captured_sys), f"Expected '{keyword}' in judge prompt for category {cat}"

    # 5. 验证 BEAM event_ordering 裁判端专用 prompt
    beam_captured_sys = []
    ev_beam = create_evaluator(
        "llm_judge",
        benchmark_name="beam",
        completion_fn=lambda system_prompt, user_prompt, cs=beam_captured_sys: cs.append(system_prompt) or '{"reason": "ok", "verdict": "CORRECT"}',
    )
    q_beam_order = Question(conversation_id="c", question_id="q-order", text="Order events", category="event_ordering")
    ev_beam.evaluate(q_beam_order, AnswerResult(conversation_id="c", question_id="q-order", answer="1, 2, 3"), GoldAnswerInfo(question_id="q-order", answer="1, 2, 3"))
    assert any("event-ordering" in p for p in beam_captured_sys), "Expected event-ordering rubric in BEAM judge prompt"


def test_concurrent_conversation_prediction_runner(tmp_path: Path) -> None:
    """验证多 Worker 并发运行器（ThreadPoolExecutor）对多 Conversation 的确定性并发处理与 CLI 兼容性。"""
    from memory_benchmark.__main__ import _build_parser
    from memory_benchmark.core import (
        Conversation,
        Dataset,
        GoldAnswerInfo,
        MockMemoryProvider,
        Question,
        Session,
        Turn,
    )
    from memory_benchmark.readers.answer import FakeAnswerLLMClient, FrameworkAnswerReader
    from memory_benchmark.runners.prediction import PredictionRunPolicy, run_predictions
    from memory_benchmark.storage import RunContext, read_jsonl

    # 1. 验证 CLI 参数已正确注册
    parser = _build_parser()
    args = parser.parse_args(["--max-workers", "4"])
    assert args.max_workers == 4

    # 2. 构造 3 个完全独立的 Conversation
    conversations = []
    for i in range(3):
        cid = f"conv-{i}"
        sessions = [
            Session(session_id=f"s-{i}-1", turns=[Turn(turn_id=f"t-{i}-1", speaker="user", content=f"Hello from {cid} session 1")]),
            Session(session_id=f"s-{i}-2", turns=[Turn(turn_id=f"t-{i}-2", speaker="user", content=f"Fact from {cid} session 2")]),
        ]
        questions = [
            Question(question_id=f"q-{i}-1", conversation_id=cid, text=f"Question 1 for {cid}?"),
            Question(question_id=f"q-{i}-2", conversation_id=cid, text=f"Question 2 for {cid}?"),
        ]
        gold_answers = {
            f"q-{i}-1": GoldAnswerInfo(question_id=f"q-{i}-1", answer=f"Answer 1 for {cid}"),
            f"q-{i}-2": GoldAnswerInfo(question_id=f"q-{i}-2", answer=f"Answer 2 for {cid}"),
        }
        conversations.append(Conversation(conversation_id=cid, sessions=sessions, questions=questions, gold_answers=gold_answers))

    dataset = Dataset(dataset_name="test_concurrent", conversations=conversations)

    # 3. 分别用单线程与 3 线程并发运行预测
    reader = FrameworkAnswerReader(client=FakeAnswerLLMClient("mock answer"))

    run_ctx_serial = RunContext.create("run_serial", "test_concurrent", "mock", "fake", tmp_path / "serial")
    run_ctx_parallel = RunContext.create("run_parallel", "test_concurrent", "mock", "fake", tmp_path / "parallel")

    summary_serial = run_predictions(
        dataset,
        MockMemoryProvider(),
        run_ctx_serial,
        policy=PredictionRunPolicy(max_workers=1),
        answer_reader=reader,
    )

    summary_parallel = run_predictions(
        dataset,
        MockMemoryProvider(),
        run_ctx_parallel,
        policy=PredictionRunPolicy(max_workers=3),
        answer_reader=reader,
    )

    # 4. 验证并发与串行的统计及产物记录完全一致（确定性排序保障）
    assert summary_parallel.total_conversations == 3
    assert summary_parallel.completed_conversations == 3
    assert summary_parallel.total_questions == 6
    assert summary_parallel.completed_questions == 6

    records_serial = read_jsonl(summary_serial.prediction_path)
    records_parallel = read_jsonl(summary_parallel.prediction_path)

    assert len(records_serial) == len(records_parallel) == 6
    for s_rec, p_rec in zip(records_serial, records_parallel):
        assert s_rec["conversation_id"] == p_rec["conversation_id"]
        assert s_rec["question_id"] == p_rec["question_id"]
        assert s_rec["answer"] == p_rec["answer"]


def test_cli_eval_run_dir_and_open_domain_stays_unmapped(tmp_path: Path) -> None:
    """验证 --eval-run-dir 离线评测，以及 LoCoMo 开放域题不进入 6 类。"""
    import json
    from memory_benchmark.__main__ import main
    from memory_benchmark.core import map_native_task_to_capability

    assert map_native_task_to_capability("locomo", "3") is None

    # 2. 复用已有 prediction 产物测试 CLI --eval-run-dir
    dataset = Dataset(
        dataset_name="locomo",
        conversations=[
            Conversation(
                conversation_id="c1",
                sessions=[Session(session_id="s1", turns=[Turn("t1", "user", "I collect comic books.")])],
                questions=[
                    Question(
                        question_id="q1",
                        conversation_id="c1",
                        text="What does user collect?",
                        category="3",
                        capability="generalization",
                    )
                ],
                gold_answers={"q1": GoldAnswerInfo("q1", "comic books")},
            )
        ],
    )
    run_ctx = RunContext.create("run_eval_cli", "locomo", "mock", "fake", tmp_path / "eval_cli")
    reader = FrameworkAnswerReader(client=FakeAnswerLLMClient("comic books"))
    run_predictions(dataset, MockMemoryProvider(), run_ctx, answer_reader=reader)

    # 3. 使用 main() 执行离线独立评估
    exit_code = main([
        "--eval-run-dir", str(run_ctx.run_dir),
        "--benchmark", "locomo",
        "--metrics", "f1",
        "--max-workers", "2",
    ])
    assert exit_code == 0

    # 4. 验证生成的 summary.f1.json 包含修正后的能力标签与原生 category
    summary_path = run_ctx.run_dir / "summaries" / "summary.f1.json"
    assert summary_path.is_file()
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_data["category_breakdown"][0]["category"] == "3"
    assert summary_data["capability_breakdown"][0]["label_zh"] == "generalization"


def test_subcommand_pipeline_and_smoke(tmp_path: Path) -> None:
    """验证阶段解耦子命令 (run, ingest, query, eval) 与 --smoke 一键冒烟。"""
    from memory_benchmark.__main__ import _build_parser, _slice_dataset, main
    from memory_benchmark.core import Conversation, Dataset, GoldAnswerInfo, Question, Session, Turn

    # 1. 验证 --smoke 极简微裁剪：截取 1 个会话，1 个 Session，1 道题
    convs = [
        Conversation(
            conversation_id=f"c{i}",
            sessions=[
                Session(session_id=f"s{i}_1", turns=[Turn(f"t{i}_1", "user", f"content {i} 1")]),
                Session(session_id=f"s{i}_2", turns=[Turn(f"t{i}_2", "user", f"content {i} 2")]),
            ],
            questions=[Question(question_id=f"q{i}_{j}", conversation_id=f"c{i}", text=f"Q {i}_{j}?") for j in range(10)],
            gold_answers={f"q{i}_{j}": GoldAnswerInfo(f"q{i}_{j}", f"Ans {i}_{j}") for j in range(10)},
        )
        for i in range(3)
    ]
    ds = Dataset("test_smoke", convs)
    sliced = _slice_dataset(ds, smoke=True)
    assert len(sliced.conversations) == 1
    assert len(sliced.conversations[0].sessions) == 1
    assert len(sliced.conversations[0].questions) == 1
    assert len(sliced.conversations[0].gold_answers) == 1

    # 2. 验证子命令解析与默认 fallback
    parser = _build_parser()
    args_default = parser.parse_args(["--smoke"])
    assert args_default.subcommand == "run"
    assert args_default.smoke is True

    args_ingest = parser.parse_args(["ingest", "--smoke"])
    assert args_ingest.subcommand == "ingest"
    assert args_ingest.smoke is True

    args_query = parser.parse_args(["query", "--smoke"])
    assert args_query.subcommand == "query"
    assert args_query.smoke is True

    args_eval = parser.parse_args(["eval", "--run-dir", str(tmp_path), "--metrics", "f1,exact_match"])
    assert args_eval.subcommand == "eval"
    assert args_eval.run_dir == str(tmp_path)
    assert args_eval.metrics == "f1,exact_match"

    # 3. 用临时数据集跑通子命令，不依赖本机才有的 data/locomo。
    import json

    sample_root = tmp_path / "project"
    sample_file = sample_root / "data" / "locomo" / "locomo10.json"
    sample_file.parent.mkdir(parents=True)
    sample_file.write_text(
        json.dumps(
            [
                {
                    "sample_id": "conv-cli-1",
                    "conversation": {
                        "speaker_a": "Alice",
                        "speaker_b": "Bob",
                        "session_1_date_time": "2026-05-01 10:00",
                        "session_1": [
                            {"speaker": "Alice", "dia_id": "D1:1", "text": "I live in Paris."},
                            {"speaker": "Bob", "dia_id": "D1:2", "text": "Paris is wonderful!"},
                        ],
                    },
                    "qa": [
                        {
                            "question": "Where does Alice live?",
                            "answer": "Paris",
                            "category": 1,
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    root = str(sample_root)
    ret_ingest = main([
        "ingest", "--smoke", "-b", "locomo", "-m", "mock",
        "--run-id", "pipeline_smoke", "--force", "--project-root", root,
    ])
    assert ret_ingest == 0

    ret_query = main([
        "query", "--smoke", "-b", "locomo", "-m", "mock", "--mock-llm",
        "--run-id", "pipeline_smoke", "--project-root", root,
    ])
    assert ret_query == 0

    ret_run = main([
        "run", "--smoke", "-b", "locomo", "-m", "mock", "--mock-llm",
        "--metrics", "f1", "--project-root", root,
    ])
    assert ret_run == 0




