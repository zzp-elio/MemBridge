"""评测结果可信度：实验隔离、分数口径、协议失败与断点。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_benchmark.__main__ import _prepare_run_directory, generate_run_id
from memory_benchmark.core import (
    AnswerResult,
    ConfigurationError,
    Conversation,
    Dataset,
    GoldAnswerInfo,
    HttpMemoryProvider,
    IngestRequest,
    MemoryProvider,
    MockMemoryProvider,
    PromptProperties,
    Question,
    Result,
    RetrievePayload,
    RetrieveRequest,
    Session,
    Turn,
    UnifiedCapability,
)
from memory_benchmark.evaluators import create_evaluator
from memory_benchmark.evaluators.llm_judge import LLMJudgeEvaluator
from memory_benchmark.readers import FakeAnswerLLMClient, FrameworkAnswerReader
from memory_benchmark.runners.evaluation import run_artifact_evaluation
from memory_benchmark.runners.prediction import PredictionRunPolicy, run_predictions
from memory_benchmark.storage import RunContext, read_jsonl


def _dataset() -> Dataset:
    return Dataset(
        dataset_name="locomo",
        conversations=[
            Conversation(
                conversation_id="conv-1",
                sessions=[
                    Session(
                        session_id="sess-1",
                        turns=[Turn(turn_id="t1", speaker="Alice", content="Mango the dog")],
                    )
                ],
                questions=[
                    Question(
                        question_id="q1",
                        conversation_id="conv-1",
                        text="What is the dog's name?",
                        category="temporal-reasoning",
                        capability=UnifiedCapability.ABSTENTION,
                        metadata={"choices": {"A": "Mango", "B": "Other"}},
                    ),
                    Question(
                        question_id="q2",
                        conversation_id="conv-1",
                        text="Where?",
                        category="single-hop",
                    ),
                ],
                gold_answers={
                    "q1": GoldAnswerInfo(question_id="q1", answer="Mango"),
                    "q2": GoldAnswerInfo(question_id="q2", answer="Paris"),
                },
            )
        ],
    )


def _run(tmp_path: Path, provider: MemoryProvider, *, policy: PredictionRunPolicy | None = None, run_id: str = "run-a") -> RunContext:
    run_ctx = RunContext.create(
        run_id=run_id,
        benchmark_name="locomo",
        method_name="mock",
        model_name="fake-answer-llm",
        output_root=tmp_path / "outputs",
    )
    run_predictions(
        _dataset(),
        provider,
        run_ctx,
        policy=policy,
        answer_reader=FrameworkAnswerReader(client=FakeAnswerLLMClient("Mango")),
        benchmark_variant="s_cleaned",
        manifest_extra={"answer_model": "answer-model", "judge_model": "judge-model"},
    )
    return run_ctx


def test_generate_run_id_is_unique_and_existing_directory_is_refused(tmp_path: Path) -> None:
    first = generate_run_id("locomo", "http")
    second = generate_run_id("locomo", "http")
    assert first != second
    assert first.startswith("locomo_http_")

    run_dir = tmp_path / "locomo_http"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="already exists"):
        _prepare_run_directory(tmp_path, "locomo_http", resume=False, force=False)


def test_exact_match_does_not_take_the_first_character() -> None:
    evaluator = create_evaluator("exact_match")
    question = Question(question_id="mc", conversation_id="c", text="Which?")
    gold = GoldAnswerInfo(question_id="mc", answer="Paris", metadata={"ground_truth": "A"})
    apple = evaluator.evaluate(
        question,
        AnswerResult(question_id="mc", conversation_id="c", answer="Apple"),
        gold,
    )
    explicit = evaluator.evaluate(
        question,
        AnswerResult(question_id="mc", conversation_id="c", answer="A."),
        gold,
    )
    assert apple.score == 0.0
    assert apple.details["choice_parse_status"] == "invalid_choice"
    assert explicit.score == 1.0


def test_judge_failure_is_judge_error_not_a_second_exception() -> None:
    def _boom(**kwargs: object) -> str:
        raise RuntimeError("api down")

    evaluator = LLMJudgeEvaluator(
        prompt_props=PromptProperties(
            task_judge_prompts={
                "temporal-reasoning": "TEMPORAL PROMPT",
                "abstention": "ABSTENTION PROMPT {question}",
            }
        ),
        completion_fn=_boom,
    )
    question = Question(
        question_id="q",
        conversation_id="c",
        text="color?",
        category="temporal-reasoning",
        capability=UnifiedCapability.ABSTENTION,
    )
    result = evaluator.evaluate(
        question,
        AnswerResult(question_id="q", conversation_id="c", answer="blue"),
        GoldAnswerInfo(question_id="q", answer="blue"),
    )
    assert result.details["verdict"] == "JUDGE_ERROR"
    assert result.details["error_message"] == "api down"
    assert result.is_correct is None


def test_abstention_capability_uses_abstention_prompt() -> None:
    seen: list[str] = []

    def _complete(*, system_prompt: str, user_prompt: str) -> str:
        seen.append(system_prompt)
        return '{"reason": "ok", "verdict": "CORRECT"}'

    evaluator = LLMJudgeEvaluator(
        prompt_props=PromptProperties(
            judge_system="DEFAULT",
            task_judge_prompts={
                "temporal-reasoning": "TEMPORAL PROMPT",
                "abstention": "ABSTENTION PROMPT",
            },
        ),
        completion_fn=_complete,
    )
    evaluator.evaluate(
        Question(
            question_id="q",
            conversation_id="c",
            text="color?",
            category="temporal-reasoning",
            capability=UnifiedCapability.ABSTENTION,
        ),
        AnswerResult(question_id="q", conversation_id="c", answer="blue"),
        GoldAnswerInfo(question_id="q", answer="blue"),
    )
    assert seen == ["ABSTENTION PROMPT"]


def test_missing_prediction_counts_as_zero_in_the_overall_mean(tmp_path: Path) -> None:
    run_ctx = _run(tmp_path, MockMemoryProvider())
    path = run_ctx.run_dir / "artifacts" / "method_predictions.jsonl"
    kept = [row for row in read_jsonl(path) if row["question_id"] == "q1"]
    path.write_text(json.dumps(kept[0], ensure_ascii=False) + "\n", encoding="utf-8")
    summary = run_artifact_evaluation(
        run_ctx.run_dir,
        create_evaluator("f1"),
        expected_benchmark="locomo",
    )
    assert summary.total_questions == 2
    assert summary.missing_questions == 1
    assert summary.completion_rate == 0.5
    assert summary.conditional_mean_score == 1.0
    assert summary.mean_score == 0.5


def test_mock_ingest_idempotency_key_does_not_duplicate_turns() -> None:
    provider = MockMemoryProvider()
    session = Session(
        session_id="sess-1",
        turns=[Turn(turn_id="t1", speaker="Alice", content="once")],
    )
    request = IngestRequest(
        isolation_key="iso",
        session=session,
        idempotency_key="iso:sess-1",
    )
    assert provider.ingest(request).is_success
    second = provider.ingest(request)
    assert second.message == "duplicate ingest ignored"
    assert provider.turns_by_key["iso"] == ["Alice: once"]


def test_retrieve_without_formatted_memory_is_a_protocol_error() -> None:
    def transport(url: str, payload: dict, timeout: float | None) -> dict:
        return {"code": 200, "data": {"memory": "hidden"}, "latency_ms": 3.0}

    provider = HttpMemoryProvider(base_url="http://memory.local", transport=transport)
    result = provider.retrieve(
        RetrieveRequest(isolation_key="iso", query="name?")
    )
    assert result.code == 502
    assert result.data is None


def test_client_and_server_latency_are_both_kept(tmp_path: Path) -> None:
    class SlowReport(MemoryProvider):
        def ingest(self, request: IngestRequest) -> Result[None]:
            assert request.idempotency_key == "run-a_conv-1:sess-1"
            assert request.metadata["is_last_session"] is False
            return Result.ok(None, latency_ms=10_000.0)

        def retrieve(self, request: RetrieveRequest) -> Result[RetrievePayload]:
            assert "choices" not in request.metadata
            return Result.ok(RetrievePayload(formatted_memory="Mango"), latency_ms=10_000.0)

    run_ctx = _run(
        tmp_path,
        SlowReport(),
        policy=PredictionRunPolicy(dataset_was_truncated=True),
    )
    rows = read_jsonl(run_ctx.run_dir / "artifacts" / "method_predictions.jsonl")
    assert rows
    metadata = rows[0]["metadata"]
    assert metadata["server_retrieve_latency_ms"] == 10_000.0
    assert metadata["client_retrieve_latency_ms"] < 1_000.0
    manifest = json.loads((run_ctx.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["benchmark_variant"] == "s_cleaned"
    assert manifest["answer_model"] == "answer-model"
    assert manifest["judge_model"] == "judge-model"
    summary = json.loads((run_ctx.run_dir / "summaries" / "summary.json").read_text(encoding="utf-8"))
    assert "p50_retrieve_latency_ms" in summary["efficiency_metrics"]
    assert "p95_retrieve_latency_ms" in summary["efficiency_metrics"]
    assert summary["efficiency_metrics"]["mean_server_retrieve_latency_ms"] == 10_000.0


def test_query_reuses_ingest_run_and_still_retrieves(tmp_path: Path) -> None:
    calls = {"retrieve": 0}

    class Counting(MemoryProvider):
        def ingest(self, request: IngestRequest) -> Result[None]:
            return Result.ok(None, latency_ms=1.0)

        def retrieve(self, request: RetrieveRequest) -> Result[RetrievePayload]:
            calls["retrieve"] += 1
            assert request.isolation_key == "exp_locomo_01_conv-1"
            return Result.ok(RetrievePayload(formatted_memory="Mango"), latency_ms=1.0)

    run_ctx = RunContext.create(
        run_id="exp_locomo_01",
        benchmark_name="locomo",
        method_name="http",
        model_name="fake-answer-llm",
        output_root=tmp_path / "outputs",
    )
    provider = Counting()
    run_predictions(
        _dataset(),
        provider,
        run_ctx,
        policy=PredictionRunPolicy(skip_retrieval=True, resume=True),
        answer_reader=FrameworkAnswerReader(client=FakeAnswerLLMClient("Mango")),
    )
    assert calls["retrieve"] == 0
    run_predictions(
        _dataset(),
        provider,
        run_ctx,
        policy=PredictionRunPolicy(skip_ingest=True, resume=True),
        answer_reader=FrameworkAnswerReader(client=FakeAnswerLLMClient("Mango")),
    )
    assert calls["retrieve"] == 2
    _prepare_run_directory(tmp_path / "outputs", "exp_locomo_01", resume=False, force=False, allow_existing=True)


def test_resume_skips_completed_conversation(tmp_path: Path) -> None:
    calls = {"ingest": 0}

    class Counting(MemoryProvider):
        def ingest(self, request: IngestRequest) -> Result[None]:
            calls["ingest"] += 1
            return Result.ok(None, latency_ms=1.0)

        def retrieve(self, request: RetrieveRequest) -> Result[RetrievePayload]:
            return Result.ok(RetrievePayload(formatted_memory="Mango"), latency_ms=1.0)

    provider = Counting()
    run_ctx = _run(tmp_path, provider)
    assert calls["ingest"] == 1
    run_predictions(
        _dataset(),
        provider,
        run_ctx,
        policy=PredictionRunPolicy(resume=True),
        answer_reader=FrameworkAnswerReader(client=FakeAnswerLLMClient("Mango")),
    )
    assert calls["ingest"] == 1
    progress = read_jsonl(run_ctx.run_dir / "checkpoints" / "conversation_progress.jsonl")
    assert progress[-1]["status"] == "completed"
