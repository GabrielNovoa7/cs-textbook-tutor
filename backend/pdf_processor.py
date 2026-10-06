import re
import pymupdf


CHAPTER_PATTERN = re.compile(
    r"^\s*Chapter\s*(\d+)\s*[.\-]?\s*(.*?)\s+(\d+)\s*$",
    re.IGNORECASE
)

SECTION_PATTERN = re.compile(
    r"^\s*(\d{1,2})[.\-](\d{1,2})[.]?\s+(.+?)\s+(\d+)\s*$"
)


def extract_pages_from_pdf(file_path):
    document = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        pages.append({
            "page_number": page_number,
            "text": page.get_text()
        })

    page_count = document.page_count

    document.close()

    return pages, page_count


def extract_table_of_contents(file_path):
    document = pymupdf.open(file_path)

    raw_toc = document.get_toc(
        simple=True
    )

    document.close()

    if not raw_toc:
        return []

    entries = []

    chapter_word_pattern = re.compile(
        r"^\s*Chapter\s+(\d+)"
        r"(?:\s*[:.\-]\s*|\s+)?"
        r"(.*?)\s*$",
        re.IGNORECASE
    )

    numeric_chapter_pattern = re.compile(
        r"^\s*(\d+)"
        r"\s*[.:\-]?\s+"
        r"(.+?)\s*$"
    )

    # IMPORTANT:
    # This keeps the entire number:
    #
    # 1.1
    # 1.1.1
    # 2.3.4
    #
    # instead of flattening them all.
    section_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)+)"
        r"\s*[.:\-]?\s*"
        r"(.+?)\s*$"
    )

    seen_sections = set()
    seen_chapters = set()

    for (
        level,
        title,
        pdf_page
    ) in raw_toc:

        cleaned_title = " ".join(
            title.split()
        ).strip()

        if not cleaned_title:
            continue

        # =====================================
        # SECTION / SUBSECTION
        # =====================================

        section_match = (
            section_pattern.match(
                cleaned_title
            )
        )

        if section_match:
            full_number = (
                section_match.group(1)
            )

            section_title = (
                section_match.group(2)
                .strip()
            )

            # Avoid duplicate PDF bookmarks.
            if full_number in seen_sections:
                continue

            seen_sections.add(
                full_number
            )

            entries.append({
                "type": "section",
                "number": full_number,
                "title": section_title,

                # Bookmark page numbers are
                # physical PDF pages.
                "book_page": None,

                "toc_pdf_page": pdf_page,

                "confidence": "direct"
            })

            continue

        # =====================================
        # CHAPTER:
        # Chapter 1 Introduction
        # =====================================

        chapter_match = (
            chapter_word_pattern.match(
                cleaned_title
            )
        )

        if chapter_match:
            chapter_number = (
                chapter_match.group(1)
            )

            chapter_title = (
                chapter_match.group(2)
                .strip()
            )

            if not chapter_title:
                chapter_title = (
                    f"Chapter {chapter_number}"
                )

            if chapter_number in seen_chapters:
                continue

            seen_chapters.add(
                chapter_number
            )

            entries.append({
                "type": "chapter",
                "number": chapter_number,
                "title": chapter_title,
                "book_page": None,
                "toc_pdf_page": pdf_page,
                "confidence": "direct"
            })

            continue

        # =====================================
        # NUMERIC TOP-LEVEL CHAPTER:
        #
        # 1 Introduction
        # 2 Processes
        # =====================================

        if level == 1:
            numeric_match = (
                numeric_chapter_pattern.match(
                    cleaned_title
                )
            )

            if numeric_match:
                chapter_number = (
                    numeric_match.group(1)
                )

                if (
                    chapter_number
                    in seen_chapters
                ):
                    continue

                seen_chapters.add(
                    chapter_number
                )

                entries.append({
                    "type": "chapter",

                    "number": chapter_number,

                    "title": (
                        numeric_match
                        .group(2)
                        .strip()
                    ),

                    "book_page": None,

                    "toc_pdf_page": (
                        pdf_page
                    ),

                    "confidence": "direct"
                })

    return entries
    document = pymupdf.open(file_path)

    raw_toc = document.get_toc(
        simple=True
    )

    document.close()

    if not raw_toc:
        return []

    entries = []

    chapter_word_pattern = re.compile(
        r"^\s*Chapter\s+(\d+)"
        r"(?:\s*[:.\-]\s*|\s+)?"
        r"(.*?)\s*$",
        re.IGNORECASE
    )

    numeric_chapter_pattern = re.compile(
        r"^\s*(\d+)"
        r"\s*[.:\-]?\s+"
        r"(.+?)\s*$"
    )

    section_pattern = re.compile(
        r"^\s*(\d+)\.(\d+)"
        r"(?:\.\d+)*"
        r"\s*[.:\-]?\s*"
        r"(.+?)\s*$"
    )

    for (
        level,
        title,
        pdf_page
    ) in raw_toc:

        cleaned_title = " ".join(
            title.split()
        ).strip()

        if not cleaned_title:
            continue

        # ---------------------------------
        # SECTION
        # Example:
        # 1.1 Introduction
        # ---------------------------------

        section_match = (
            section_pattern.match(
                cleaned_title
            )
        )

        if section_match:
            chapter_number = (
                section_match.group(1)
            )

            section_number = (
                section_match.group(2)
            )

            section_title = (
                section_match.group(3)
                .strip()
            )

            entries.append({
                "type": "section",

                "number": (
                    f"{chapter_number}."
                    f"{section_number}"
                ),

                "title": section_title,

                "book_page": None,

                "toc_pdf_page": pdf_page,

                "confidence": "direct"
            })

            continue

        # ---------------------------------
        # CHAPTER
        # Example:
        # Chapter 1 Introduction
        # ---------------------------------

        chapter_match = (
            chapter_word_pattern.match(
                cleaned_title
            )
        )

        if chapter_match:
            chapter_number = (
                chapter_match.group(1)
            )

            chapter_title = (
                chapter_match.group(2)
                .strip()
            )

            if not chapter_title:
                chapter_title = (
                    f"Chapter {chapter_number}"
                )

            entries.append({
                "type": "chapter",
                "number": chapter_number,
                "title": chapter_title,
                "book_page": None,
                "toc_pdf_page": pdf_page,
                "confidence": "direct"
            })

            continue

        # ---------------------------------
        # SOME BOOKS USE:
        #
        # 1 Introduction
        # 2 Software Processes
        # 3 Requirements
        #
        # Only count these when they are
        # top-level PDF bookmarks.
        # ---------------------------------

        if level == 1:
            numeric_match = (
                numeric_chapter_pattern.match(
                    cleaned_title
                )
            )

            if numeric_match:
                entries.append({
                    "type": "chapter",

                    "number": (
                        numeric_match.group(1)
                    ),

                    "title": (
                        numeric_match.group(2)
                        .strip()
                    ),

                    "book_page": None,

                    "toc_pdf_page": pdf_page,

                    "confidence": "direct"
                })

    return entries

    document = pymupdf.open(file_path)

    raw_toc = document.get_toc(
        simple=True
    )

    document.close()

    if not raw_toc:
        return []

    entries = []

    chapter_word_pattern = re.compile(
        r"^\s*Chapter\s+(\d+)"
        r"(?:\s*[:.\-]\s*|\s+)?"
        r"(.*?)\s*$",
        re.IGNORECASE
    )

    numeric_chapter_pattern = re.compile(
        r"^\s*(\d+)"
        r"\s*[.:\-]?\s+"
        r"(.+?)\s*$"
    )

    section_pattern = re.compile(
        r"^\s*(\d+)\.(\d+)"
        r"(?:\.\d+)*"
        r"\s*[.:\-]?\s*"
        r"(.+?)\s*$"
    )

    for (
        level,
        title,
        pdf_page
    ) in raw_toc:

        cleaned_title = " ".join(
            title.split()
        ).strip()

        if not cleaned_title:
            continue

        # -------------------------
        # SECTION
        # Example:
        # 1.1 What Operating Systems Do
        # -------------------------

        section_match = (
            section_pattern.match(
                cleaned_title
            )
        )

        if section_match:
            chapter_number = (
                section_match.group(1)
            )

            section_number = (
                section_match.group(2)
            )

            section_title = (
                section_match.group(3)
                .strip()
            )

            entries.append({
                "type": "section",

                "number": (
                    f"{chapter_number}."
                    f"{section_number}"
                ),

                "title": section_title,

                # Bookmark page numbers refer to
                # physical PDF pages.
                "book_page": None,

                "toc_pdf_page": pdf_page,

                "confidence": "direct"
            })

            continue

        # -------------------------
        # CHAPTER
        # Example:
        # Chapter 1 Introduction
        # -------------------------

        chapter_match = (
            chapter_word_pattern.match(
                cleaned_title
            )
        )

        if chapter_match:
            chapter_number = (
                chapter_match.group(1)
            )

            chapter_title = (
                chapter_match.group(2)
                .strip()
            )

            if not chapter_title:
                chapter_title = (
                    f"Chapter {chapter_number}"
                )

            entries.append({
                "type": "chapter",
                "number": chapter_number,
                "title": chapter_title,
                "book_page": None,
                "toc_pdf_page": pdf_page,
                "confidence": "direct"
            })

            continue

        # -------------------------
        # SOME BOOKS USE:
        # 1 Introduction
        # 2 Processes
        # etc.
        #
        # Only treat these as chapters
        # when they are top-level bookmarks.
        # -------------------------

        if level == 1:
            numeric_chapter_match = (
                numeric_chapter_pattern.match(
                    cleaned_title
                )
            )

            if numeric_chapter_match:
                entries.append({
                    "type": "chapter",

                    "number": (
                        numeric_chapter_match
                        .group(1)
                    ),

                    "title": (
                        numeric_chapter_match
                        .group(2)
                        .strip()
                    ),

                    "book_page": None,

                    "toc_pdf_page": (
                        pdf_page
                    ),

                    "confidence": "direct"
                })

    return entries


def extract_printed_table_of_contents(
    file_path,
    pages_to_scan=80
):
    document = pymupdf.open(file_path)

    toc_pages = []
    inside_contents = False

    pages_to_check = min(
        pages_to_scan,
        document.page_count
    )

    for page_index in range(pages_to_check):
        text = document[page_index].get_text(
            sort=True
        )

        # Ignore the shorter "Brief Contents" page.
        if "Brief Contents" in text:
            continue

        # Find the detailed table of contents.
        if not inside_contents:
            has_contents_heading = re.search(
                r"\bContents\b",
                text,
                re.IGNORECASE
            )

            has_chapter = re.search(
                r"Chapter\s*1\b",
                text,
                re.IGNORECASE
            )

            has_section = re.search(
                r"\b1[.\-]1[.]?\b",
                text
            )

            if (
                has_contents_heading
                and has_chapter
                and has_section
            ):
                inside_contents = True

        if inside_contents:
            toc_pages.append({
                "pdf_page": page_index + 1,
                "text": text
            })

            # Stop at the end of the detailed TOC.
            if (
                re.search(
                    r"\bIndex\b",
                    text,
                    re.IGNORECASE
                )
                and re.search(
                    r"\bAppendix\b",
                    text,
                    re.IGNORECASE
                )
            ):
                break

    document.close()

    entries = []

    for toc_page in toc_pages:
        lines = toc_page["text"].splitlines()

        for line in lines:
            cleaned = " ".join(
                line.split()
            ).strip()

            if not cleaned:
                continue

            chapter_match = CHAPTER_PATTERN.match(
                cleaned
            )

            if chapter_match:
                entries.append({
                    "type": "chapter",
                    "number": chapter_match.group(1),
                    "title": chapter_match.group(2).strip(),
                    "book_page": int(
                        chapter_match.group(3)
                    ),
                    "toc_pdf_page": toc_page[
                        "pdf_page"
                    ]
                })

                continue

            section_match = SECTION_PATTERN.match(
                cleaned
            )

            if section_match:
                chapter_number = (
                    section_match.group(1)
                )

                section_number = (
                    section_match.group(2)
                )

                entries.append({
                    "type": "section",
                    "number": (
                        f"{chapter_number}."
                        f"{section_number}"
                    ),
                    "title": (
                        section_match.group(3)
                        .strip()
                    ),
                    "book_page": int(
                        section_match.group(4)
                    ),
                    "toc_pdf_page": toc_page[
                        "pdf_page"
                    ]
                })

    return entries


def extract_page_text_range(
    file_path,
    start_page=1,
    end_page=40
):
    document = pymupdf.open(file_path)

    pages = []

    start_index = max(
        start_page - 1,
        0
    )

    end_index = min(
        end_page,
        document.page_count
    )

    for page_index in range(
        start_index,
        end_index
    ):
        text = document[
            page_index
        ].get_text(
            sort=True
        )

        pages.append({
            "pdf_page": page_index + 1,
            "text": text
        })

    document.close()

    return pages


def clean_toc_title(title):
    """
    Removes obvious PDF extraction artifacts
    without guessing what the title should say.
    """

    cleaned = title

    cleaned = cleaned.replace("®", "")
    cleaned = cleaned.replace("\\*", "")
    cleaned = cleaned.replace("*", "")

    cleaned = re.sub(
        r"\s+=\s*$",
        "",
        cleaned
    )

    cleaned = " ".join(
        cleaned.split()
    ).strip()

    return cleaned


def clean_toc_entries(entries):
    cleaned_entries = []

    for entry in entries:
        cleaned_entry = entry.copy()

        cleaned_entry["title"] = clean_toc_title(
            entry["title"]
        )

        cleaned_entry["confidence"] = (
            cleaned_entry.get(
                "confidence",
                "direct"
            )
        )

        cleaned_entries.append(
            cleaned_entry
        )

    return cleaned_entries


def build_toc_structure(entries):
    chapters = []
    current_chapter = None

    for entry in entries:

        if entry["type"] == "chapter":
            current_chapter = {
                "number": entry["number"],
                "title": entry["title"],
                "book_page": entry["book_page"],
                "toc_pdf_page": entry[
                    "toc_pdf_page"
                ],
                "confidence": entry.get(
                    "confidence",
                    "direct"
                ),
                "sections": []
            }

            chapters.append(
                current_chapter
            )

        elif (
            entry["type"] == "section"
            and current_chapter
        ):
            section_chapter_number = (
                entry["number"].split(".")[0]
            )

            if (
                section_chapter_number
                == current_chapter["number"]
            ):
                current_chapter[
                    "sections"
                ].append(
                    entry.copy()
                )

    return chapters


def _extract_uppercase_heading(text):
    """
    Attempts to remove OCR junk before a heading.

    Example:

        'shy BOOLEAN EXPRESSIONS'

    becomes:

        'BOOLEAN EXPRESSIONS'
    """

    text = text.replace("|", " ")

    tokens = text.split()

    for index, token in enumerate(tokens):
        letters = "".join(
            character
            for character in token
            if character.isalpha()
        )

        if len(letters) < 2:
            continue

        if letters != letters.upper():
            continue

        candidate = " ".join(
            tokens[index:]
        ).strip()

        all_letters = [
            character
            for character in candidate
            if character.isalpha()
        ]

        if len(all_letters) < 5:
            continue

        uppercase_count = sum(
            1
            for character in all_letters
            if character.isupper()
        )

        uppercase_ratio = (
            uppercase_count
            / len(all_letters)
        )

        if uppercase_ratio < 0.75:
            continue

        blocked_starts = (
            "TIP",
            "PITFALL",
            "EXAMPLE"
        )

        if candidate.upper().startswith(
            blocked_starts
        ):
            continue

        return clean_toc_title(
            candidate
        )

    return None


def extract_recovery_candidates(
    file_path,
    chapters
):
    """
    Finds lines that look like section headings but
    whose section number was damaged during PDF
    text extraction.
    """

    if not chapters:
        return []

    first_toc_page = min(
        chapter["toc_pdf_page"]
        for chapter in chapters
    )

    last_toc_page = max(
        chapter["toc_pdf_page"]
        for chapter in chapters
    )

    document = pymupdf.open(
        file_path
    )

    candidates = []

    for pdf_page in range(
        first_toc_page,
        last_toc_page + 1
    ):
        page = document[
            pdf_page - 1
        ]

        text = page.get_text(
            sort=True
        )

        for line in text.splitlines():
            cleaned = " ".join(
                line.split()
            ).strip()

            if not cleaned:
                continue

            # Already parsed correctly.
            if SECTION_PATTERN.match(
                cleaned
            ):
                continue

            # Do not treat chapter lines as sections.
            if re.match(
                r"^\s*Chapter\b",
                cleaned,
                re.IGNORECASE
            ):
                continue

            # Ignore common non-section TOC entries.
            if re.match(
                (
                    r"^\s*("
                    r"Chapter Summary|"
                    r"Answers to|"
                    r"Programming Projects|"
                    r"Appendix|"
                    r"Index"
                    r")"
                ),
                cleaned,
                re.IGNORECASE
            ):
                continue

            page_match = re.search(
                r"(\d{1,4})\s*$",
                cleaned
            )

            if not page_match:
                continue

            book_page = int(
                page_match.group(1)
            )

            heading_part = (
                cleaned[
                    :page_match.start()
                ]
                .strip()
            )

            title = _extract_uppercase_heading(
                heading_part
            )

            if not title:
                continue

            candidates.append({
                "title": title,
                "book_page": book_page,
                "toc_pdf_page": pdf_page
            })

    document.close()

    # Remove duplicates.
    unique_candidates = []

    seen = set()

    for candidate in candidates:
        key = (
            candidate["book_page"],
            candidate["title"]
        )

        if key in seen:
            continue

        seen.add(key)

        unique_candidates.append(
            candidate
        )

    return unique_candidates


def _make_recovered_section(
    chapter_number,
    section_number,
    candidate
):
    return {
        "type": "section",
        "number": (
            f"{chapter_number}."
            f"{section_number}"
        ),
        "title": candidate["title"],
        "book_page": candidate[
            "book_page"
        ],
        "toc_pdf_page": candidate[
            "toc_pdf_page"
        ],
        "confidence": "recovered"
    }


def recover_missing_sections(
    file_path,
    chapters
):
    """
    Uses section order and textbook page numbers
    to repair section headings whose numbers were
    damaged by PDF extraction.
    """

    candidates = extract_recovery_candidates(
        file_path,
        chapters
    )

    recovered_sections = []

    for chapter_index, chapter in enumerate(
        chapters
    ):
        chapter_number = chapter["number"]

        chapter_start_page = (
            chapter["book_page"]
        )

        if (
            chapter_index + 1
            < len(chapters)
        ):
            chapter_end_page = chapters[
                chapter_index + 1
            ]["book_page"]
        else:
            chapter_end_page = float(
                "inf"
            )

        chapter_candidates = [
            candidate
            for candidate in candidates
            if (
                chapter_start_page
                < candidate["book_page"]
                < chapter_end_page
            )
        ]

        chapter_candidates.sort(
            key=lambda candidate: (
                candidate["book_page"]
            )
        )

        sections = chapter[
            "sections"
        ]

        sections.sort(
            key=lambda section: int(
                section["number"].split(
                    "."
                )[1]
            )
        )

        existing_pages = {
            section["book_page"]
            for section in sections
        }

        chapter_candidates = [
            candidate
            for candidate in chapter_candidates
            if candidate["book_page"]
            not in existing_pages
        ]

        # If no sections were recognized at all,
        # assign candidates sequentially.
        if not sections:
            for index, candidate in enumerate(
                chapter_candidates,
                start=1
            ):
                recovered = (
                    _make_recovered_section(
                        chapter_number,
                        index,
                        candidate
                    )
                )

                sections.append(
                    recovered
                )

                recovered_sections.append(
                    recovered
                )

            continue

        numbered_sections = [
            (
                int(
                    section[
                        "number"
                    ].split(".")[1]
                ),
                section
            )
            for section in sections
        ]

        numbered_sections.sort(
            key=lambda item: item[0]
        )

        # Recover missing sections before
        # the first recognized section.
        first_number, first_section = (
            numbered_sections[0]
        )

        expected_before = list(
            range(
                1,
                first_number
            )
        )

        candidates_before = [
            candidate
            for candidate in chapter_candidates
            if (
                candidate["book_page"]
                < first_section["book_page"]
            )
        ]

        if (
            expected_before
            and len(candidates_before)
            == len(expected_before)
        ):
            for section_number, candidate in zip(
                expected_before,
                candidates_before
            ):
                recovered = (
                    _make_recovered_section(
                        chapter_number,
                        section_number,
                        candidate
                    )
                )

                sections.append(
                    recovered
                )

                recovered_sections.append(
                    recovered
                )

        # Recover missing sections between
        # recognized sections.
        for index in range(
            len(numbered_sections) - 1
        ):
            current_number, current_section = (
                numbered_sections[index]
            )

            next_number, next_section = (
                numbered_sections[
                    index + 1
                ]
            )

            expected_numbers = list(
                range(
                    current_number + 1,
                    next_number
                )
            )

            if not expected_numbers:
                continue

            candidates_between = [
                candidate
                for candidate in chapter_candidates
                if (
                    current_section["book_page"]
                    < candidate["book_page"]
                    < next_section["book_page"]
                )
            ]

            if (
                len(candidates_between)
                != len(expected_numbers)
            ):
                continue

            for section_number, candidate in zip(
                expected_numbers,
                candidates_between
            ):
                recovered = (
                    _make_recovered_section(
                        chapter_number,
                        section_number,
                        candidate
                    )
                )

                sections.append(
                    recovered
                )

                recovered_sections.append(
                    recovered
                )

        # Also look for a trailing section such as
        # 15.7 when 15.1 through 15.6 were detected.
        last_number, last_section = (
            numbered_sections[-1]
        )

        candidates_after = [
            candidate
            for candidate in chapter_candidates
            if (
                candidate["book_page"]
                > last_section["book_page"]
            )
        ]

        next_section_number = (
            last_number + 1
        )

        for candidate in candidates_after:
            # Skip anything already recovered.
            if candidate["book_page"] in {
                section["book_page"]
                for section in sections
            }:
                continue

            recovered = (
                _make_recovered_section(
                    chapter_number,
                    next_section_number,
                    candidate
                )
            )

            sections.append(
                recovered
            )

            recovered_sections.append(
                recovered
            )

            next_section_number += 1

        sections.sort(
            key=lambda section: int(
                section[
                    "number"
                ].split(".")[1]
            )
        )

    return recovered_sections


def find_toc_warnings(chapters):
    warnings = []

    for chapter in chapters:
        sections = chapter[
            "sections"
        ]

        if not sections:
            warnings.append({
                "type": (
                    "no_sections_found"
                ),
                "chapter": chapter[
                    "number"
                ],
                "message": (
                    "No sections were "
                    "detected for Chapter "
                    f"{chapter['number']}."
                )
            })

            continue

        section_numbers = []

        for section in sections:
            try:
                section_number = int(
                    section[
                        "number"
                    ].split(".")[1]
                )

                section_numbers.append(
                    section_number
                )

            except (
                ValueError,
                IndexError
            ):
                continue

        if not section_numbers:
            continue

        highest_section = max(
            section_numbers
        )

        for expected_number in range(
            1,
            highest_section + 1
        ):
            if (
                expected_number
                not in section_numbers
            ):
                missing_number = (
                    f"{chapter['number']}."
                    f"{expected_number}"
                )

                warnings.append({
                    "type": (
                        "missing_section"
                    ),
                    "chapter": chapter[
                        "number"
                    ],
                    "section": (
                        missing_number
                    ),
                    "message": (
                        f"Section "
                        f"{missing_number} "
                        "may be missing from "
                        "the parsed table of "
                        "contents."
                    )
                })

    return warnings


def analyze_table_of_contents(
    entries,
    file_path=None
):
    cleaned_entries = (
        clean_toc_entries(
            entries
        )
    )

    chapters = (
        build_toc_structure(
            cleaned_entries
        )
    )

    recovered_sections = []

    if file_path:
        recovered_sections = (
            recover_missing_sections(
                file_path,
                chapters
            )
        )

    warnings = find_toc_warnings(
        chapters
    )

    return {
        "entries": cleaned_entries,
        "chapters": chapters,
        "recovered_sections": (
            recovered_sections
        ),
        "warnings": warnings
    }