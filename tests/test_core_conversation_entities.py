"""测试核心数据实体与公私数据物理隔离契约。"""

import unittest

import pytest

from memory_benchmark.core import (
    AnswerResult,
    Conversation,
    Dataset,
    GoldAnswerInfo,
    ImageRef,
    Question,
    Session,
    Turn,
)


pytestmark = pytest.mark.unit


class CoreConversationEntitiesTest(unittest.TestCase):
    """验证核心 dataclass 的最小行为与公私隔离。"""

    def test_question_does_not_contain_gold_answer(self):
        """Question 只能包含公开问题字段，不能出现 answer。"""

        question = Question(
            question_id="q1",
            conversation_id="conv1",
            text="What does Alice like?",
            category="single-hop",
        )

        self.assertFalse(hasattr(question, "answer"))
        self.assertEqual(question.conversation_id, "conv1")

    def test_session_public_dict_omits_private_metadata(self):
        """private_metadata 只留在评测端，不进入写入请求。"""

        session = Session(
            session_id="s1",
            turns=[Turn(turn_id="t1", speaker="user", content="hello")],
            private_metadata={"source_format": "halumem_session"},
        )

        public = session.to_dict()
        self.assertNotIn("private_metadata", public)
        self.assertEqual(session.private_metadata["source_format"], "halumem_session")

    def test_conversation_keeps_gold_answers_separate(self):
        """Conversation 用 questions 和 gold_answers 分离 public/private 数据。"""

        question = Question(question_id="q1", conversation_id="conv1", text="What?")
        gold = GoldAnswerInfo(question_id="q1", answer="Alice likes tea.")
        conversation = Conversation(
            conversation_id="conv1",
            sessions=[
                Session(
                    session_id="session_1",
                    session_time="2024-01-01",
                    turns=[Turn(turn_id="t1", speaker="Alice", content="I like tea.")],
                )
            ],
            questions=[question],
            gold_answers={"q1": gold},
        )

        self.assertEqual(conversation.questions[0].text, "What?")
        self.assertEqual(conversation.gold_answers["q1"].answer, "Alice likes tea.")

    def test_conversation_public_dict_excludes_gold_answers(self):
        """method 可见导出不能包含 GoldAnswerInfo 或标准答案文本。"""

        question = Question(question_id="q1", conversation_id="conv1", text="What?")
        conversation = Conversation(
            conversation_id="conv1",
            sessions=[],
            questions=[question],
            gold_answers={
                "q1": GoldAnswerInfo(
                    question_id="q1",
                    answer="Alice likes tea.",
                )
            },
        )

        public_payload = conversation.to_public_dict()
        public_text = str(public_payload)

        self.assertNotIn("gold_answers", public_payload)
        self.assertNotIn("GoldAnswerInfo", public_text)
        self.assertNotIn("Alice likes tea.", public_text)

    def test_image_ref_can_be_attached_to_turn(self):
        """Turn 支持可选 ImageRef。"""

        image = ImageRef(image_id="img1", path="/tmp/a.jpg", caption="a whiteboard")
        turn = Turn(turn_id="t1", speaker="Lena", content="Look at this.", images=[image])

        self.assertEqual(turn.images[0].caption, "a whiteboard")

    def test_answer_result_only_stores_prediction(self):
        """AnswerResult 保存预测输出，不保存 gold answer。"""

        result = AnswerResult(question_id="q1", conversation_id="conv1", answer="tea")

        self.assertEqual(result.answer, "tea")
        self.assertFalse(hasattr(result, "gold_answer"))

    def test_dataset_serializes_conversations(self):
        """Dataset.to_dict 能保留 conversation 层级。"""

        dataset = Dataset(
            dataset_name="dummy",
            conversations=[Conversation(conversation_id="conv1")],
        )

        payload = dataset.to_dict()

        self.assertEqual(payload["dataset_name"], "dummy")
        self.assertEqual(payload["conversations"][0]["conversation_id"], "conv1")


if __name__ == "__main__":
    unittest.main()
