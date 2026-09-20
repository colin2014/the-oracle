"""Regression tests for the AI-marking reply validator (no network, no API key needed).

Run:  python -m unittest test_marking_validation -v

Bug this guards: TestQuestion.marks is a Float, so the prompt asked for "integer 0-2.0",
the model replied {"marks_awarded": 2.0}, and the old isinstance(..., int) check threw
away a correct, confident mark, silently sending it to the teacher queue.
"""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import test_marking


def _question(marks=2.0):
    return SimpleNamespace(
        marks=marks, subtopic_title="A1.1", subtopic_code="A1.1", text="Describe the ALU.",
        marking_guidance="1 mark arithmetic, 1 mark logic", common_mistakes=None,
        ai_checklist=None, if_wrong_explainer=None,
    )


def _run(reply_text, marks=2.0):
    """Call the marker with the model stubbed to return reply_text; also return the prompt it was sent."""
    seen = {}

    def fake_create(**kwargs):
        seen["prompt"] = kwargs["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(text=reply_text)])

    client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
         mock.patch("anthropic.Anthropic", return_value=client), \
         mock.patch.object(test_marking, "_subtopic_descriptor", return_value=None):
        result = test_marking._call_claude_marker(_question(marks), "some answer")
    return result, seen.get("prompt", "")


def _reply(marks, confidence=0.95):
    return '{"marks_awarded": %s, "feedback": "ok", "confidence": %s}' % (marks, confidence)


class MarkingValidatorTests(unittest.TestCase):
    def test_whole_float_from_model_is_accepted(self):
        result, _ = _run(_reply("2.0"))
        self.assertIsNotNone(result)
        self.assertEqual(result["marks_awarded"], 2)
        self.assertIsInstance(result["marks_awarded"], int)

    def test_plain_int_still_accepted(self):
        for m in (0, 1, 2):
            with self.subTest(m=m):
                result, _ = _run(_reply(m))
                self.assertEqual(result["marks_awarded"], m)

    def test_json_fenced_reply_still_parsed(self):
        result, _ = _run("```json\n" + _reply("1.0") + "\n```")
        self.assertEqual(result["marks_awarded"], 1)

    def test_prompt_no_longer_says_integer_0_to_2_point_0(self):
        _, prompt = _run(_reply(2))
        self.assertIn("<integer 0-2>", prompt)
        self.assertNotIn("2.0", prompt)
        self.assertIn("worth 2 marks", prompt)

    def test_singular_mark_wording(self):
        _, prompt = _run(_reply(1), marks=1.0)
        self.assertIn("worth 1 mark.", prompt)

    def test_rejects_fraction_bool_string_and_out_of_range(self):
        for bad in ("1.5", "true", '"2"', "3", "3.0", "-1", "null"):
            with self.subTest(bad=bad):
                result, _ = _run(_reply(bad))
                self.assertIsNone(result)

    def test_confidence_defaults_when_out_of_range(self):
        result, _ = _run(_reply(2, confidence=7))
        self.assertEqual(result["confidence"], 0.5)

    def test_as_whole_helper(self):
        self.assertEqual(test_marking._as_whole(2.0), 2)
        self.assertIsInstance(test_marking._as_whole(2.0), int)
        self.assertEqual(test_marking._as_whole(1.5), 1.5)
        self.assertEqual(test_marking._as_whole(3), 3)


if __name__ == "__main__":
    unittest.main()
