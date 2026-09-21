"""Run:  python -m unittest test_exit_ticket_import -v

Tests the importer's reading of answer sheets using made-up text, so it doesn't need PowerPoint files.
"""
import unittest

import exit_ticket_import as I
import exit_ticket_logic as L


def ans(text, qtype="x"):
    return {"qtype": qtype, "prompt": "P", "answer": text}


class HelperTests(unittest.TestCase):
    def test_split_alternatives(self):
        self.assertEqual(I._split_alternatives("Counter (Program Counter)."), ["Counter", "Program Counter"])
        self.assertEqual(I._split_alternatives("CPU / processor"), ["CPU", "processor"])
        self.assertEqual(I._split_alternatives("control unit or CU"), ["control unit", "CU"])
        self.assertEqual(I._split_alternatives("execute"), ["execute"])

    def test_assign_pairs_hints_with_descriptions_by_shared_words(self):
        terms = ["ALU", "Cache"]
        hints = ["arithmetic/logic", "frequently used data"]
        descs = ["Frequently used data kept close to the CPU", "Carries out arithmetic and logical operations"]
        order, confident = I._assign(terms, hints, descs)
        self.assertEqual(order, [1, 0])
        self.assertTrue(confident)

    def test_assign_reports_when_it_is_only_guessing(self):
        _, confident = I._assign(["a", "b"], ["zzz", "qqq"], ["one", "two"])
        self.assertFalse(confident)

    def test_marks_are_one_each_with_explain_four_and_total_ten(self):
        qs = [{"qtype": t, "data": {}} for t in ("mcq", "truefalse", "fill", "match", "order", "short", "explain")]
        self.assertTrue(I.allocate_marks(qs))
        self.assertEqual([q["marks"] for q in qs], [1.0] * 6 + [4.0])
        self.assertFalse(I.allocate_marks(qs[:5]))      # a shorter ticket is not 10 marks


class BuildQuestionTests(unittest.TestCase):
    def build(self, raw, answer):
        warn = []
        return I.build_question(raw, ans(answer), warn), warn

    def test_mcq_reads_the_correct_letter(self):
        q, w = self.build({"qtype": "mcq", "prompt": "Q?", "options": ["a", "b", "c"]}, "Correct answer: C - because.")
        self.assertEqual((q["data"]["correct"], w), (2, []))

    def test_truefalse_ignores_explanations_and_full_stops(self):
        raw = {"qtype": "truefalse", "prompt": "", "statements": ["s1", "s2", "s3"]}
        q, w = self.build(raw, "True  ·  False (that describes an OR gate)  ·  True.")
        self.assertEqual([s["answer"] for s in q["data"]["statements"]], [True, False, True])
        self.assertEqual(w, [])

    def test_truefalse_count_mismatch_is_reported_not_guessed(self):
        q, w = self.build({"qtype": "truefalse", "prompt": "", "statements": ["s1", "s2"]}, "True · False · True")
        self.assertIsNone(q)
        self.assertTrue(w)

    def test_fill_pairs_answers_with_blanks_and_keeps_alternatives(self):
        raw = {"qtype": "fill", "prompt": "", "sentences": ["The ____ does A.", "The Program ____ does B."]}
        q, w = self.build(raw, "(1) Control Unit    (2) Counter (Program Counter).")
        blanks = [s["blanks"] for s in q["data"]["sentences"]]
        self.assertEqual(blanks, [[["Control Unit"]], [["Counter", "Program Counter"]]])
        self.assertEqual(w, [])

    def test_fill_wrong_number_of_answers_is_reported(self):
        q, w = self.build({"qtype": "fill", "prompt": "", "sentences": ["A ____ b ____ c"]}, "(1) only one")
        self.assertIsNone(q)
        self.assertTrue(w)

    def test_match_uses_position_when_the_answer_sheet_shortens_the_names(self):
        raw = {"qtype": "match", "prompt": "", "terms": ["Patterns", "Abstraction"],
               "descriptions": ["Removing unnecessary detail", "Spotting similarities between problems"]}
        q, w = self.build(raw, "Pattern recognition-spotting similarities  ·  Abstraction-removing detail.")
        pairs = {p["left"]: p["right"] for p in q["data"]["pairs"]}
        self.assertEqual(pairs, {"Patterns": "Spotting similarities between problems", "Abstraction": "Removing unnecessary detail"})
        self.assertEqual(w, [])

    def test_order_matches_abbreviated_steps_to_the_full_ones(self):
        raw = {"qtype": "order", "prompt": "", "items": ["Apply each gate's rule in turn", "Read the input values", "Combine the results into the final output"]}
        q, w = self.build(raw, "Order: 1 Read the input values  ·  2 Apply each gate's rule  ·  3 Combine into the final output.")
        self.assertEqual(q["data"]["items"], ["Read the input values", "Apply each gate's rule in turn", "Combine the results into the final output"])

    def test_explain_keeps_the_model_answer_and_splits_marking_points(self):
        q, w = self.build({"qtype": "explain", "prompt": "Explain."}, "Model: registers hold data; the ALU operates; the result is stored.")
        self.assertEqual(q["data"]["marking_points"], ["registers hold data", "the ALU operates", "the result is stored"])
        self.assertIn("registers hold data", q["data"]["model_answer"])

    def test_a_missing_answer_sheet_entry_is_reported(self):
        warn = []
        q = I.build_question({"qtype": "mcq", "prompt": "Q", "options": ["a", "b"]}, None, warn)
        self.assertIsNone(q)
        self.assertTrue(any("answer sheet" in w for w in warn))

    def test_every_built_question_passes_the_editors_rules(self):
        q, _ = self.build({"qtype": "mcq", "prompt": "Q?", "options": ["a", "b"]}, "Correct answer: B")
        q["marks"] = 1.0
        self.assertEqual(L.clean_question(q)["data"]["correct"], 1)


if __name__ == "__main__":
    unittest.main()
