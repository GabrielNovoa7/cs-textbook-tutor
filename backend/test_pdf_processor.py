import tempfile
import unittest
from pathlib import Path

import pymupdf

from backend.pdf_processor import extract_printed_table_of_contents, analyze_table_of_contents


class PrintedContentsTests(unittest.TestCase):
    def test_contents_stops_before_running_headers_and_joins_titles(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "book.pdf"
            with pymupdf.open() as document:
                for text in (
                    "Contents\n1 Software Development 1\n1.1 Analysis 4\n"
                    "2 Long Chapter Title\nand More Words 20\n2.1 Objects 21",
                    "Contents\nAppendixes\nA Reference 100",
                    "Contents\nIndex 120",
                    "CHAPTER CONTENTS\nChapter Objectives\n1.1 Analysis 5\n"
                    "Chapter 1 Software Development 3",
                ):
                    document.new_page().insert_text((40, 40), text)
                document.save(path)
            entries = extract_printed_table_of_contents(path)
            self.assertEqual(len(entries), 4)
            self.assertEqual(entries[0]["book_page"], 1)
            self.assertEqual(entries[1]["book_page"], 4)
            self.assertEqual(entries[2]["title"], "Long Chapter Title and More Words")

    def extract(self, contents):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "book.pdf"
            with pymupdf.open() as document:
                page = document.new_page()
                page.insert_text((40, 40), contents)
                document.save(path)
            return analyze_table_of_contents(extract_printed_table_of_contents(path))

    def test_numeric_chapter_titles(self):
        result = self.extract(
            "Contents\n1 Software Development 1\n"
            "1.1 Problem Analysis and Specification 4\n1.2 Design 6\n"
            "2 Abstract Data Types 45\n2.1 Implementations 46\nAppendix A 100\nIndex 120"
        )
        self.assertEqual([c["number"] for c in result["chapters"]], ["1", "2"])
        self.assertEqual(result["chapters"][0]["sections"][0]["title"], "Problem Analysis and Specification")
        self.assertEqual(result["chapters"][1]["sections"][0]["book_page"], 46)

    def test_existing_chapter_word_format(self):
        result = self.extract(
            "Contents\nChapter 1 Introduction 1\n1.1 Objects 2\n"
            "Chapter 2 Methods 20\n2.1 Calls 21\nAppendix A 100\nIndex 120"
        )
        self.assertEqual(len(result["chapters"]), 2)
        self.assertEqual(result["chapters"][0]["title"], "Introduction")


if __name__ == "__main__":
    unittest.main()
