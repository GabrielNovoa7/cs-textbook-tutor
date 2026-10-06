import re
from difflib import SequenceMatcher

import pymupdf


def normalize_text(text):
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def find_chapter_content_page(
    file_path,
    chapter_number,
    chapter_title,
    chapter_book_page,
    toc_pdf_page
):
    """
    For printed TOCs, find where the actual
    chapter begins inside the physical PDF.

    Example:

        Book page 1
        might actually be PDF page 36.

    If we find Chapter 1 on PDF page 36:

        offset = 36 - 1 = 35
    """

    document = pymupdf.open(
        file_path
    )

    normalized_title = normalize_text(
        chapter_title
    )

    chapter_marker = normalize_text(
        f"Chapter {chapter_number}"
    )

    # Start several pages after the TOC entry
    # so we do not accidentally match the TOC.
    start_index = max(
        (toc_pdf_page or 1) + 4,
        0
    )

    for page_index in range(
        start_index,
        document.page_count
    ):
        text = document[
            page_index
        ].get_text(
            sort=True
        )

        normalized_page = normalize_text(
            text
        )

        # Best case:
        # page contains both "Chapter X"
        # and the chapter title.
        if (
            chapter_marker
            in normalized_page
            and normalized_title
            in normalized_page
        ):
            document.close()

            return page_index + 1

        # Fallback:
        # look for a strong title match.
        lines = text.splitlines()

        for line in lines:
            normalized_line = normalize_text(
                line
            )

            if not normalized_line:
                continue

            similarity = SequenceMatcher(
                None,
                normalized_title,
                normalized_line
            ).ratio()

            if similarity >= 0.90:
                document.close()

                return page_index + 1

    document.close()

    return None


def build_section_source(
    file_path,
    section_context
):
    """
    Converts the saved Learning Path section
    into real physical PDF page numbers.
    """

    section_book_page = section_context[
        "section_book_page"
    ]

    section_pdf_page = section_context[
        "section_toc_pdf_page"
    ]

    next_section = section_context.get(
        "next_section"
    )

    next_chapter = section_context.get(
        "next_chapter"
    )

    # =================================================
    # BOOKMARK-BASED PDF
    #
    # For bookmark books, book_page is None and
    # toc_pdf_page is already the real physical page.
    # =================================================

    if section_book_page is None:
        start_pdf_page = section_pdf_page

        end_pdf_page = start_pdf_page

        if (
            next_section
            and next_section["book_page"] is None
            and next_section["toc_pdf_page"]
        ):
            next_page = next_section[
                "toc_pdf_page"
            ]

            if next_page > start_pdf_page:
                end_pdf_page = (
                    next_page - 1
                )

        elif (
            next_chapter
            and next_chapter["book_page"] is None
            and next_chapter["toc_pdf_page"]
        ):
            next_page = next_chapter[
                "toc_pdf_page"
            ]

            if next_page > start_pdf_page:
                end_pdf_page = (
                    next_page - 1
                )

        return {
            "source_type": "pdf_bookmark",
            "pdf_start_page": start_pdf_page,
            "pdf_end_page": end_pdf_page,
            "book_start_page": None,
            "book_end_page": None,
            "page_offset": None
        }

    # =================================================
    # PRINTED TOC PDF
    #
    # We need to convert printed book pages
    # into physical PDF pages.
    # =================================================

    chapter_content_page = (
        find_chapter_content_page(
            file_path=file_path,

            chapter_number=(
                section_context[
                    "chapter_number"
                ]
            ),

            chapter_title=(
                section_context[
                    "chapter_title"
                ]
            ),

            chapter_book_page=(
                section_context[
                    "chapter_book_page"
                ]
            ),

            toc_pdf_page=(
                section_context[
                    "chapter_toc_pdf_page"
                ]
            )
        )
    )

    if chapter_content_page is None:
        return {
            "source_type": (
                "printed_toc"
            ),

            "pdf_start_page": None,
            "pdf_end_page": None,

            "book_start_page": (
                section_book_page
            ),

            "book_end_page": None,

            "page_offset": None,

            "error": (
                "Could not locate the actual "
                "chapter pages in the PDF."
            )
        }

    chapter_book_page = section_context[
        "chapter_book_page"
    ]

    page_offset = (
        chapter_content_page
        - chapter_book_page
    )

    start_pdf_page = (
        section_book_page
        + page_offset
    )

    book_end_page = None
    end_pdf_page = start_pdf_page

    # Next section gives us the end of
    # the current section.
    if (
        next_section
        and next_section["book_page"]
        is not None
    ):
        book_end_page = (
            next_section[
                "book_page"
            ]
            - 1
        )

        end_pdf_page = (
            book_end_page
            + page_offset
        )

    # If this is the last section,
    # use the beginning of the next chapter.
    elif (
        next_chapter
        and next_chapter["book_page"]
        is not None
    ):
        book_end_page = (
            next_chapter[
                "book_page"
            ]
            - 1
        )

        end_pdf_page = (
            book_end_page
            + page_offset
        )

    return {
        "source_type": "printed_toc",

        "pdf_start_page": (
            start_pdf_page
        ),

        "pdf_end_page": (
            end_pdf_page
        ),

        "book_start_page": (
            section_book_page
        ),

        "book_end_page": (
            book_end_page
        ),

        "page_offset": (
            page_offset
        )
    }