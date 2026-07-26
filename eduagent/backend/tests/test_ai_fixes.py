import os
import unittest
from unittest.mock import patch

from agents.llm import LLMJSONClient
from agents.quiz_agent import _is_duplicate_question, _local_questions, _matching_document_excerpt, _relevant_excerpt, _source_sentences
from models.schemas import GenerateQuizRequest
from agents.fallbacks import looks_like_pdf_noise
from agents.study_agent import _normalize_topic_rows, extract_topics, extract_topics_with_llm, is_concrete_topic
from utils.subject import infer_subject, subjects_match


class SubjectFilteringTests(unittest.TestCase):
    def test_dbms_document_is_rejected_for_dsa_quiz(self):
        dbms = "Normalization removes anomalies. SQL joins combine relational tables. Transactions satisfy ACID."
        self.assertEqual(infer_subject("dbms-notes.pdf", dbms), "dbms")
        self.assertFalse(subjects_match("Data Structures and Algorithms - Trees", "dbms-notes.pdf", dbms))
        self.assertEqual(_matching_document_excerpt(dbms, "dbms-notes.pdf", "DSA", "Trees"), "")

    def test_matching_dsa_document_supplies_only_relevant_lines(self):
        dsa = "Arrays support indexed access.\nTrees contain nodes and edges.\nHash tables store key value pairs."
        excerpt = _matching_document_excerpt(dsa, "dsa-syllabus.pdf", "Trees", "Binary Trees")
        self.assertIn("Trees contain", excerpt)
        self.assertNotIn("Hash tables", excerpt)

    def test_no_keyword_match_does_not_fall_back_to_document_prefix(self):
        self.assertEqual(_relevant_excerpt("SQL joins and transactions", "Trees", "Traversal"), "")


class QuizDeduplicationTests(unittest.TestCase):
    def test_nonce_does_not_hide_a_repeated_question(self):
        previous = {"which statement is most accurate about graphs variant abc123"}
        self.assertTrue(_is_duplicate_question("Which statement is most accurate about Graphs? Variant def456.", previous))

    def test_two_local_runs_do_not_repeat_questions(self):
        payload = GenerateQuizRequest(student_id="test", topic="Database Fundamentals", subtopic="Database Fundamentals", difficulty="Medium", count=5)
        first = _local_questions(payload)
        used = {q.question.lower() for q in first}
        second = _local_questions(payload, used)
        self.assertEqual(len(first), 5)
        self.assertEqual(len(second), 5)
        for question in second:
            self.assertFalse(_is_duplicate_question(question.question, used))

    def test_plan_instructions_are_not_academic_source_sentences(self):
        source = "Complete concept questions before writing code or solving schedules. A database schema defines tables, relationships, and constraints."
        rows = _source_sentences(source)
        self.assertFalse(any("Complete concept questions" in row for row in rows))


class TopicExtractionTests(unittest.TestCase):
    def test_audience_and_syllabus_headers_are_rejected(self):
        self.assertTrue(looks_like_pdf_noise("Class XI XII Students Droppers"))
        self.assertTrue(looks_like_pdf_noise("Undergraduate Course Syllabus and Assessment Blueprint"))
        self.assertTrue(looks_like_pdf_noise("1. Understand fundamental data structures and their properties"))
        self.assertFalse(is_concrete_topic("Database Management Systems"))
        self.assertFalse(is_concrete_topic("JEE MATHEMATICS"))

    def test_local_extractor_returns_concepts_not_pdf_headings(self):
        text = """DBMS Course Syllabus\nField Value\nNormalization and functional dependencies.\nTransactions, ACID and concurrency control.\nRelational algebra and SQL."""
        topics = extract_topics(text, "")
        names = [row["name"] for row in topics]
        self.assertIn("Normalization", names)
        self.assertIn("Transactions and Concurrency", names)
        self.assertNotIn("DBMS Course Syllabus", names)

    def test_difficulty_labels_are_never_topics(self):
        rows = [
            {"name": "Easy", "subtopics": ["Beginner"]},
            {"name": "Arrays", "subtopics": ["Traversal"], "difficulty": "Easy"},
            {"name": "Hard", "subtopics": ["Trees"]},
        ]
        topics = _normalize_topic_rows(rows, 2)
        self.assertEqual([row["name"] for row in topics], ["Arrays"])
        self.assertEqual(topics[0]["difficulty"], "Easy")

    @patch("agents.study_agent.LLMJSONClient")
    def test_llm_topics_come_from_content(self, client_type):
        client = client_type.return_value
        client.available = True
        client.complete_json.return_value = [
            {"name": "Normalization", "subtopics": ["First Normal Form"], "difficulty": "Medium"},
            {"name": "Medium", "subtopics": []},
        ]
        topics = extract_topics_with_llm("DBMS covers normalization and relational schemas.", "SQL transactions use ACID.")
        self.assertEqual([row["name"] for row in topics], ["Normalization"])
        client.complete_json.assert_called_once()


class UnifiedBudgetTests(unittest.TestCase):
    def test_unified_budget_overrides_legacy_limit(self):
        with patch.dict(os.environ, {"AI_DAILY_REQUEST_BUDGET": "250", "LLM_DAILY_LIMIT": "10"}, clear=False):
            client = LLMJSONClient()
            self.assertEqual(client.daily_limit, 250)
            status = client.usage_status()
            self.assertEqual(status["budget_scope"], "all_plans")
            self.assertIn("requests_used", status)
            self.assertEqual(status["date"], __import__("datetime").date.today().isoformat())


if __name__ == "__main__":
    unittest.main()
