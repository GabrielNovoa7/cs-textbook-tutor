"""Run with python -m unittest backend.test_concept_check (no paid API calls)."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

import pymupdf
from fastapi import HTTPException

from backend import database as db
from backend import concept_check as quiz


class ConceptCheckTests(unittest.TestCase):
    def test_punctuation_spacing_is_typography_not_paraphrase(self):
        self.assertTrue(quiz.evidence_matches("Change to CT new.", "Change to CT new ."))
        self.assertFalse(quiz.evidence_matches("Change to CT old.", "Change to CT new ."))

    def test_image_section_number_on_mapped_printed_page(self):
        self.assertIsNotNone(quiz.printed_title_position("Previous text\nIII Design\nCurrent text", "Design"))
        self.assertIsNone(quiz.printed_title_position("The design is important.", "Design"))

    def test_delete_book_cascades_and_removes_pdf(self):
        from backend import main
        self.create()
        chat = db.create_chat(self.textbook, "Test chat")
        with patch.object(main, "UPLOAD_FOLDER", self.folder):
            self.assertTrue(main.delete_textbook(self.textbook)["deleted"])
        self.assertFalse((self.folder / "test.pdf").exists())
        self.assertIsNone(db.get_textbook(self.textbook))
        self.assertIsNone(db.get_section_context(self.section))
        self.assertIsNone(db.get_chat(chat))
        from contextlib import closing
        with closing(db.get_connection()) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM concept_checks").fetchone()[0], 0)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        patcher = patch.object(db, "DB_PATH", self.folder / "test.db")
        patcher.start()
        self.addCleanup(patcher.stop)
        db.init_db()
        self.textbook = db.save_textbook("test.pdf", "test.pdf", "hash", 3, 1000, [])
        self.chapters = [{"number": "1", "title": "Basics", "toc_pdf_page": 1,
                          "sections": [{"number": "1.1", "title": "Objects", "toc_pdf_page": 1},
                                       {"number": "1.2", "title": "Future", "toc_pdf_page": 2}]}]
        db.save_learning_path(self.textbook, self.chapters)
        self.section = db.get_learning_path(self.textbook)[0]["sections"][0]["id"]
        db.mark_reading_complete(self.section)
        self.questions = [{"id": i, "question_type": "multiple_choice", "prompt": f"Question {i}",
                           "options": ["A", "B", "C", "D"], "grading": {"correct_index": 0},
                           "explanation": "Correct explanation", "review_hint": "Reread PDF page 1",
                           "source": {"source_type": "generated", "section_number": "1.1",
                                      "source_page": 1, "evidence_page": 1}}
                          for i in range(1, 5)]
        (self.folder / "test.pdf").touch()

    def create(self):
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", return_value=self.questions) as generate:
            result = quiz.load_or_create(self.section, self.folder)
            return result, generate.call_count

    def test_creation_cache_and_answer_privacy(self):
        result, calls = self.create()
        self.assertEqual(calls, 1)
        self.assertEqual(len(result["questions"]), 4)
        serialized = json.dumps(result)
        for private in ("correct_index", "explanation", "review_hint", "original_question", "evidence_quote"):
            self.assertNotIn(private, serialized)
        with patch.object(quiz, "generate_questions", side_effect=AssertionError("API called")):
            self.assertEqual(quiz.load_or_create(self.section, self.folder), result)

    def test_all_scores_history_and_sticky_completion(self):
        self.create()
        with patch.object(quiz, "generate_questions", side_effect=AssertionError("API called")):
            for score in range(5):
                result = quiz.submit_attempt(self.section, {str(i): 0 if i <= score else 1 for i in range(1, 5)})
                self.assertEqual(result["score"], score)
                self.assertEqual(result["passed"], score >= 3)
                self.assertEqual(result["progress"]["concept_check_completed"], int(score >= 3))
            quiz.submit_attempt(self.section, {str(i): 1 for i in range(1, 5)})
        self.assertEqual(db.get_section_progress(self.section)["concept_check_completed"], 1)
        self.assertEqual(len(quiz.attempt_history(self.section)), 6)

    def test_invalid_answers_do_not_save_attempt(self):
        self.create()
        for answers in ({}, {str(i): 9 for i in range(1, 5)}, {str(i): True for i in range(1, 5)}):
            with self.assertRaises(HTTPException):
                quiz.submit_attempt(self.section, answers)
        self.assertEqual(quiz.attempt_history(self.section), [])

    def test_reading_gate(self):
        other = db.get_learning_path(self.textbook)[0]["sections"][1]["id"]
        with patch.object(quiz, "generate_questions") as generate:
            with self.assertRaises(HTTPException) as error:
                quiz.load_or_create(other, self.folder)
            self.assertEqual(error.exception.status_code, 409)
            generate.assert_not_called()

    def test_two_question_grading_and_history(self):
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", return_value=self.questions[:2]):
            result = quiz.load_or_create(self.section, self.folder)
        self.assertEqual(result["passing_score"], 2)
        self.assertEqual(result["total_questions"], 2)
        self.assertFalse(quiz.submit_attempt(self.section, {"1": 0, "2": 1})["passed"])
        self.assertTrue(quiz.submit_attempt(self.section, {"1": 0, "2": 0})["passed"])
        self.assertEqual(quiz.attempt_history(self.section)[0]["total_questions"], 2)

    def test_questions_and_activity_share_one_creation_request(self):
        from backend.lesson_activity import load_activity, save_activity
        evidence = "Objects store state and support behavior."
        draft = {"questions": [{"question_type": "multiple_choice", "prompt": f"Question {i}",
                                 "options": ["A", "B", "C", "D"], "correct_index": 0,
                                 "explanation": "An explanation", "review_hint": "Reread page 1",
                                 "candidate_id": None, "evidence_page": 1,
                                 "evidence_quote": evidence} for i in range(2)],
                 "activity": {"activity_type": "predict_output", "title": "Predict output",
                              "prompt": "Predict the output", "items": [], "correct_order": [],
                              "accepted_answers": ["Hello"], "starter_code": "print('Hello')",
                              "language": "python", "checklist": ["Trace each statement", "Check output"],
                              "candidate_id": None, "evidence_page": 1, "evidence_quote": evidence}}
        client = Mock()
        client.with_options.return_value.responses.create.return_value = SimpleNamespace(output_text=json.dumps(draft))
        with patch.dict("sys.modules", {"backend.tutor": SimpleNamespace(client=client)}), \
                patch.object(quiz, "collect_material", return_value=(
                    [{"pdf_page": 1, "text": evidence}], [], {"pdf_start_page": 1})):
            result = quiz.load_or_create(self.section, self.folder)
            self.assertEqual(result["total_questions"], 2)
            quiz.submit_attempt(self.section, {"1": 0, "2": 0})
            activity = load_activity(self.section)
            self.assertNotIn("accepted_answers", json.dumps(activity))
            self.assertFalse(save_activity(self.section, "Wrong", [], [], True)["completed"])
            self.assertTrue(save_activity(self.section, "Hello", [], [], True)["completed"])
            quiz.load_or_create(self.section, self.folder)
            client.with_options.return_value.responses.create.assert_called_once()

    def test_explicit_no_activity_completes_section_after_questions(self):
        from backend.lesson_activity import load_activity
        self.create()
        connection = db.get_connection()
        connection.execute("UPDATE concept_checks SET response_json=? WHERE section_id=?",
                           (json.dumps({"output_text": json.dumps({"activity": None})}), self.section))
        connection.commit()
        connection.close()
        quiz.submit_attempt(self.section, {str(i): 0 for i in range(1, 5)})
        result = load_activity(self.section)
        self.assertIsNone(result["activity"])
        self.assertEqual(result["progress"]["mastery_completed"], 1)

    def test_checkpoint_policy(self):
        self.chapters[0]["sections"] += [
            {"number": "1.3", "title": "Three", "toc_pdf_page": 3},
            {"number": "1.4", "title": "Four", "toc_pdf_page": 4},
        ]
        db.save_learning_path(self.textbook, self.chapters)
        sections = db.get_learning_path(self.textbook)[0]["sections"]
        self.assertEqual([quiz.assessment_size(db.get_section_context(s["id"])) for s in sections], [2, 2, 4, 4])

    def test_heading_matching_tolerates_ocr_spacing_but_not_other_titles(self):
        text = "Previous exercises\n1.3.\nThe Class String\nCurrent material"
        position = quiz.heading_position(text, "1.3", "THECLASS String")
        self.assertIsNotNone(position)
        self.assertTrue(text[position:].startswith("1.3"))
        self.assertIsNone(quiz.heading_position(text, "1.2", "THECLASS String"))
        self.assertIsNone(quiz.heading_position(text, "1.3", "The Class Integer"))
        self.assertIsNotNone(quiz.heading_position("1.2\nExpressions and Assignment Statements", "1.2", "EXPRESSIONSAND ASSIGNMENT STATEMENTS"))

    def test_legacy_completion_is_preserved_without_completing_new_activity(self):
        self.create()
        quiz.submit_attempt(self.section, {str(i): 0 for i in range(1, 5)})
        self.assertEqual(db.get_learning_path(self.textbook)[0]["sections"][0]["mastery_completed"], 1)
        connection = db.get_connection()
        connection.execute("UPDATE section_progress SET activity_completed=0, mastery_completed=0 WHERE section_id=?", (self.section,))
        connection.execute("UPDATE concept_checks SET response_json=? WHERE section_id=?",
                           (json.dumps({"output_text": json.dumps({"activity": {"activity_type": "coding"}})}), self.section))
        connection.commit()
        connection.close()
        section = db.get_learning_path(self.textbook)[0]["sections"][0]
        self.assertEqual(section["mastery_completed"], 0)
        self.assertEqual(section["concept_check_completed"], 1)

    def test_legacy_activity_draft_self_review_and_mastery(self):
        from backend.lesson_activity import load_activity, save_activity
        self.create()
        with self.assertRaises(HTTPException):
            load_activity(self.section)
        quiz.submit_attempt(self.section, {str(i): 0 for i in range(1, 5)})
        with patch.object(quiz, "generate_questions", side_effect=AssertionError("API called")):
            activity = load_activity(self.section)
            self.assertEqual(activity["activity"]["activity_type"], "explain")
            self.assertNotIn("correct_order", json.dumps(activity))
            save_activity(self.section, "My explanation using the textbook example.", [], [], False)
            self.assertIn("My explanation", load_activity(self.section)["submission"]["response"])
            with self.assertRaises(HTTPException):
                save_activity(self.section, "An incomplete response", [], [], True)
            result = save_activity(self.section, "My explanation using the textbook example.", [], [0, 1, 2], True)
            self.assertTrue(result["completed"])
            self.assertEqual(result["progress"]["mastery_completed"], 1)
            self.assertEqual(db.get_learning_path(self.textbook)[0]["sections"][0]["mastery_completed"], 1)

    def test_ordering_activity_is_graded_locally(self):
        from backend.lesson_activity import load_activity, save_activity
        self.create()
        quiz.submit_attempt(self.section, {str(i): 0 for i in range(1, 5)})
        activity = {"activity_type": "ordering", "title": "Order steps", "prompt": "Put the steps in order",
                    "items": ["Finish", "Start"], "correct_order": [1, 0], "accepted_answers": [],
                    "checklist": [], "starter_code": "", "language": "plaintext", "source_type": "generated", "evidence_page": 1}
        connection = db.get_connection()
        connection.execute("UPDATE concept_checks SET activity_json=? WHERE section_id=?", (json.dumps(activity), self.section))
        connection.commit()
        connection.close()
        self.assertNotIn("correct_order", json.dumps(load_activity(self.section)))
        self.assertFalse(save_activity(self.section, "", [0, 1], [], True)["completed"])
        self.assertTrue(save_activity(self.section, "", [1, 0], [], True)["completed"])

    def test_api_routes_and_request_validation(self):
        from fastapi.testclient import TestClient
        import importlib

        # Keep unrelated vector-store and tutor initialization out of this test.
        with patch.dict("sys.modules", {
            "backend.vector_store": SimpleNamespace(add_textbook_chunks=Mock(), search_textbook=Mock()),
            "backend.tutor": SimpleNamespace(generate_tutor_response=Mock()),
        }):
            main = importlib.import_module("backend.main")
        with patch.object(main, "UPLOAD_FOLDER", self.folder), \
                patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", return_value=self.questions) as generate:
            client = TestClient(main.app)
            path = f"/sections/{self.section}/concept-check"
            response = client.post(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("grading", response.text)
            self.assertEqual(client.post(path).status_code, 200)
            self.assertEqual(client.post(path + "/attempts", json={"answers": {str(i): True for i in range(1, 5)}}).status_code, 422)
            result = client.post(path + "/attempts", json={"answers": {str(i): 0 for i in range(1, 5)}})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()["passed"])
            self.assertEqual(len(client.get(path + "/attempts").json()), 1)
            self.assertEqual(generate.call_count, 1)

    def test_alternative_question_headings_and_numbered_questions(self):
        candidates = quiz.discover_candidates([
            (1, "Practice Exercises\n1.1 What is an operating system?\n1.2 What is memory?"),
            (2, "Problems      1.1 Describe a software process.\n1.2 Describe an object."),
        ])
        self.assertEqual(len(candidates), 4)

    def test_failure_never_automatically_reissues_request(self):
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", side_effect=RuntimeError("failed")) as generate:
            for _ in range(2):
                with self.assertRaises(HTTPException):
                    quiz.load_or_create(self.section, self.folder)
            self.assertEqual(generate.call_count, 1)

    def test_failed_creation_requires_explicit_retry_and_preserves_reading(self):
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", side_effect=RuntimeError("private secret")):
            with self.assertRaises(HTTPException) as error:
                quiz.load_or_create(self.section, self.folder)
            self.assertTrue(error.exception.detail["can_retry_creation"])
            self.assertNotIn("private secret", json.dumps(error.exception.detail))
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", return_value=self.questions) as generate:
            with self.assertRaises(HTTPException):
                quiz.load_or_create(self.section, self.folder)
            generate.assert_not_called()
            self.assertEqual(quiz.load_or_create(self.section, self.folder, retry_failed=True)["total_questions"], 4)
            self.assertEqual(generate.call_count, 1)
            quiz.load_or_create(self.section, self.folder, retry_failed=True)
            self.assertEqual(generate.call_count, 1)
        self.assertEqual(db.get_section_progress(self.section)["reading_completed"], 1)
        self.assertEqual(quiz.attempt_history(self.section), [])

    def test_saved_response_recovery_uses_zero_api_calls(self):
        evidence = "The first software process defines activities."
        draft = {"questions": [{"question_type": "multiple_choice", "prompt": f"Question {i}",
                                 "options": ["A", "B", "C", "D"], "correct_index": 0,
                                 "explanation": "An explanation", "review_hint": "Reread page 1",
                                 "candidate_id": None, "evidence_page": 1,
                                 "evidence_quote": evidence} for i in range(4)]}
        payload = {"output_text": json.dumps(draft), "reading": [{"pdf_page": 1, "text": evidence.replace("first", "\ufb01rst")}],
                   "candidates": [], "source": {"pdf_start_page": 1},
                   "context": {"section_number": "1.1"}}
        connection = db.get_connection()
        connection.execute("INSERT INTO concept_checks(section_id,status,response_json) VALUES (?, 'failed', ?)",
                           (self.section, json.dumps(payload)))
        connection.commit()
        connection.close()
        with patch.object(quiz, "generate_questions", side_effect=AssertionError("API called")):
            self.assertEqual(quiz.load_or_create(self.section, self.folder)["total_questions"], 4)

    def test_returned_response_is_saved_before_validation_fails(self):
        client = Mock()
        client.with_options.return_value.responses.create.return_value = SimpleNamespace(output_text='{"questions": []}')
        save_response = Mock()
        with patch.dict("sys.modules", {"backend.tutor": SimpleNamespace(client=client)}):
            with self.assertRaises(ValueError):
                quiz.generate_questions([{"pdf_page": 1, "text": "Objects represent instances of classes in a program."}], [], {}, {"section_number": "1.1", "section_title": "Objects"},
                                        save_response=save_response)
        save_response.assert_called_once()
        schema = client.with_options.return_value.responses.create.call_args.kwargs["text"]["format"]["schema"]
        for definition in ("DraftQuestion", "DraftActivity"):
            self.assertEqual(schema["$defs"][definition]["properties"]["evidence_quote"]["enum"],
                             ["Objects represent instances of classes in a program."])

    def test_evidence_choices_are_bounded_exact_excerpts(self):
        reading = [{"pdf_page": page, "text": " ".join(
            f"Sentence {i} on page {page} describes a distinct textbook concept." for i in range(30))}
            for page in range(1, 5)]
        excerpts = quiz.evidence_excerpts(reading)
        self.assertEqual(len(excerpts), 40)
        self.assertEqual({x["pdf_page"] for x in excerpts}, {1, 2, 3, 4})
        for item in excerpts:
            self.assertTrue(quiz.evidence_matches(item["quote"], reading[item["pdf_page"] - 1]["text"]))

    def test_pdf_typography_normalization(self):
        self.assertEqual(quiz.normalize_evidence("pro\u00adcess \ufb01rst develop-\nment"),
                         quiz.normalize_evidence("process first development"))
        self.assertNotEqual(quiz.normalize_evidence("not correct"), quiz.normalize_evidence("correct"))
        self.assertTrue(quiz.evidence_matches("a low-level-language program", "a low-level-\nlanguage program"))
        self.assertTrue(quiz.evidence_matches("software development", "software develop-\nment"))
        self.assertFalse(quiz.evidence_matches("The program is correct", "The program is not correct"))

    def test_margin_interleaving_cache_recovers_without_generation(self):
        evidence = "The input program is the source program or source code."
        draft = {"questions": [{"question_type": "multiple_choice", "prompt": f"Question {i}",
                                 "options": ["A", "B", "C", "D"], "correct_index": 0,
                                 "explanation": "An explanation", "review_hint": "Reread page 1",
                                 "candidate_id": None, "evidence_page": 1,
                                 "evidence_quote": evidence} for i in range(4)]}
        payload = {"output_text": json.dumps(draft),
                   "reading": [{"pdf_page": 1, "text": "The input program\nsource code    is the source program or source code."}],
                   "candidates": [], "source": {"pdf_start_page": 1}, "context": {"section_number": "1.1"}}
        connection = db.get_connection()
        connection.execute("INSERT INTO concept_checks(section_id,status,response_json) VALUES (?, 'failed', ?)",
                           (self.section, json.dumps(payload)))
        connection.commit()
        connection.close()
        with patch.object(quiz, "collect_material", return_value=(
            [{"pdf_page": 1, "text": evidence}], [], {"pdf_start_page": 1}
        )), patch.object(quiz, "generate_questions", side_effect=AssertionError("API called")):
            result = quiz.load_or_create(self.section, self.folder)
        self.assertEqual(len(result["questions"]), 4)
        self.assertNotIn("grading", json.dumps(result))
        self.assertEqual(quiz.attempt_history(self.section), [])
        self.assertEqual(db.get_section_progress(self.section)["concept_check_completed"], 0)

    def test_concurrent_creation(self):
        def start():
            try:
                return quiz.load_or_create(self.section, self.folder)
            except HTTPException as error:
                return error.status_code
        with patch.object(quiz, "collect_material", return_value=([], [], {})), \
                patch.object(quiz, "generate_questions", return_value=self.questions) as generate:
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(lambda _: start(), range(4)))
            self.assertEqual(generate.call_count, 1)
            self.assertTrue(any(isinstance(result, dict) for result in results))

    def test_rebuild_preserves_quiz_progress_history(self):
        self.create()
        quiz.submit_attempt(self.section, {str(i): 0 for i in range(1, 5)})
        db.save_learning_path(self.textbook, self.chapters)
        self.assertEqual(db.get_learning_path(self.textbook)[0]["sections"][0]["id"], self.section)
        self.assertEqual(db.get_section_progress(self.section)["concept_check_completed"], 1)
        self.assertEqual(len(quiz.attempt_history(self.section)), 1)
        self.assertEqual(quiz.load_or_create(self.section, self.folder)["total_questions"], 4)
        with self.assertRaises(ValueError):
            db.save_learning_path(self.textbook, [])
        self.assertEqual(len(db.get_learning_path(self.textbook)[0]["sections"]), 2)

    def test_section_boundaries_and_local_question_discovery(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((40, 40), "Earlier material must be excluded.\n1.1. Objects\n" +
                         "Objects store state and support behavior. " * 8 +
                         "\nSelf-Test Questions\n1. What do objects store?")
        page = document.new_page()
        page.insert_text((40, 40), "Current section continuation.\n1.2 Future\nSECRET FUTURE MATERIAL\nReview Questions\n2. What is future material?")
        document.save(self.folder / "test.pdf")
        document.close()
        reading, candidates, _ = quiz.collect_material(self.folder / "test.pdf", db.get_section_context(self.section))
        text = json.dumps(reading)
        self.assertNotIn("Earlier material", text)
        self.assertNotIn("SECRET FUTURE MATERIAL", text)
        self.assertIn("Current section continuation", text)
        self.assertTrue(any("What do objects store" in candidate["text"] for candidate in candidates))

    def test_single_structured_request_and_evidence_validation(self):
        evidence = "Objects store state and support behavior."
        draft = {"questions": [{"question_type": "multiple_choice", "prompt": f"Question {i}",
                                 "options": ["State", "Nothing", "Files", "Pages"], "correct_index": 0,
                                 "explanation": "Objects store state.", "review_hint": "Reread page 1.",
                                 "candidate_id": 7 if i == 0 else None,
                                 "evidence_page": 1, "evidence_quote": evidence} for i in range(4)]}
        client = Mock()
        client.with_options.return_value.responses.create.return_value = SimpleNamespace(output_text=json.dumps(draft))
        with patch.dict("sys.modules", {"backend.tutor": SimpleNamespace(client=client)}):
            questions = quiz.generate_questions([{"pdf_page": 1, "text": evidence}],
                                               [{"id": 7, "pdf_page": 2, "line": 3, "text": "What do objects store?"}],
                                               {"pdf_start_page": 1}, {"section_number": "1.1", "section_title": "Objects"})
            self.assertEqual(questions[0]["source"]["source_type"], "textbook")
            self.assertEqual(sum(q["source"]["source_type"] == "generated" for q in questions), 3)
            client.with_options.return_value.responses.create.assert_called_once()
            self.assertEqual(client.with_options.call_args.kwargs["max_retries"], 0)
            draft["questions"][0]["evidence_quote"] = "Evidence from a future section"
            client.with_options.return_value.responses.create.return_value.output_text = json.dumps(draft)
            with self.assertRaises(ValueError):
                quiz.generate_questions([{"pdf_page": 1, "text": evidence}], [],
                                        {"pdf_start_page": 1}, {"section_number": "1.1", "section_title": "Objects"})


if __name__ == "__main__":
    unittest.main()
