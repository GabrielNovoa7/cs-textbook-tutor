import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "tutor.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    connection = get_connection()

    # -------------------------
    # TEXTBOOKS
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS textbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            page_count INTEGER NOT NULL,
            characters_extracted INTEGER NOT NULL,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -------------------------
    # TEXTBOOK CHUNKS
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            textbook_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,

            FOREIGN KEY (textbook_id)
                REFERENCES textbooks(id)
                ON DELETE CASCADE,

            UNIQUE(
                textbook_id,
                chunk_index
            )
        )
    """)

    # -------------------------
    # LEARNING PATH CHAPTERS
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            textbook_id INTEGER NOT NULL,
            chapter_number TEXT NOT NULL,
            title TEXT NOT NULL,
            book_page INTEGER,
            toc_pdf_page INTEGER,
            confidence TEXT NOT NULL DEFAULT 'direct',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (textbook_id)
                REFERENCES textbooks(id)
                ON DELETE CASCADE,

            UNIQUE(
                textbook_id,
                chapter_number
            )
        )
    """)

    # -------------------------
    # LEARNING PATH SECTIONS
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL,
            section_number TEXT NOT NULL,
            title TEXT NOT NULL,
            book_page INTEGER,
            toc_pdf_page INTEGER,
            confidence TEXT NOT NULL DEFAULT 'direct',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (chapter_id)
                REFERENCES chapters(id)
                ON DELETE CASCADE,

            UNIQUE(
                chapter_id,
                section_number
            )
        )
    """)

    # -------------------------
    # CHATS
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            textbook_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (textbook_id)
                REFERENCES textbooks(id)
                ON DELETE CASCADE
        )
    """)

    # -------------------------
    # CHAT MESSAGES
    # -------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (chat_id)
                REFERENCES chats(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
    CREATE TABLE IF NOT EXISTS section_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER NOT NULL UNIQUE,

        reading_completed INTEGER NOT NULL DEFAULT 0,
        concept_check_completed INTEGER NOT NULL DEFAULT 0,
        activity_completed INTEGER NOT NULL DEFAULT 0,
        mastery_completed INTEGER NOT NULL DEFAULT 0,

        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,

        FOREIGN KEY (section_id)
            REFERENCES sections(id)
            ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()


# =====================================================
# TEXTBOOK FUNCTIONS
# =====================================================


def get_textbook_by_hash(file_hash):
    connection = get_connection()

    textbook = connection.execute(
        """
        SELECT *
        FROM textbooks
        WHERE file_hash = ?
        """,
        (file_hash,),
    ).fetchone()

    connection.close()

    if textbook:
        return dict(textbook)

    return None


def get_textbook(textbook_id):
    connection = get_connection()

    textbook = connection.execute(
        """
        SELECT *
        FROM textbooks
        WHERE id = ?
        """,
        (textbook_id,),
    ).fetchone()

    connection.close()

    if textbook:
        return dict(textbook)

    return None


def save_textbook(
    filename, stored_filename, file_hash, page_count, characters_extracted, chunks
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO textbooks (
                filename,
                stored_filename,
                file_hash,
                page_count,
                characters_extracted
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (filename, stored_filename, file_hash, page_count, characters_extracted),
        )

        textbook_id = cursor.lastrowid

        chunk_rows = [
            (textbook_id, chunk["chunk_id"], chunk["page_number"], chunk["text"])
            for chunk in chunks
        ]

        connection.executemany(
            """
            INSERT INTO chunks (
                textbook_id,
                chunk_index,
                page_number,
                text
            )
            VALUES (?, ?, ?, ?)
            """,
            chunk_rows,
        )

        connection.commit()

        return textbook_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_textbooks():
    connection = get_connection()

    textbooks = connection.execute("""
        SELECT
            id,
            filename,
            page_count,
            characters_extracted,
            uploaded_at
        FROM textbooks
        ORDER BY uploaded_at DESC
        """).fetchall()

    connection.close()

    return [dict(textbook) for textbook in textbooks]


# =====================================================
# LEARNING PATH FUNCTIONS
# =====================================================


def save_learning_path(textbook_id, chapters):
    """
    Saves the cleaned chapter/section structure
    for one textbook.

    Existing chapter/section data for the textbook
    is replaced so the Learning Path can be rebuilt
    later when our parser improves.
    """

    connection = get_connection()

    try:
        # Delete the old structure first.
        # Sections are automatically deleted because
        # sections use ON DELETE CASCADE.
        connection.execute(
            """
            DELETE FROM chapters
            WHERE textbook_id = ?
            """,
            (textbook_id,),
        )

        chapter_count = 0
        section_count = 0

        for chapter in chapters:
            cursor = connection.execute(
                """
                INSERT INTO chapters (
                    textbook_id,
                    chapter_number,
                    title,
                    book_page,
                    toc_pdf_page,
                    confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    textbook_id,
                    chapter["number"],
                    chapter["title"],
                    chapter.get("book_page"),
                    chapter.get("toc_pdf_page"),
                    chapter.get("confidence", "direct"),
                ),
            )

            chapter_id = cursor.lastrowid
            chapter_count += 1

            for section in chapter.get("sections", []):
                connection.execute(
                    """
                    INSERT INTO sections (
                        chapter_id,
                        section_number,
                        title,
                        book_page,
                        toc_pdf_page,
                        confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chapter_id,
                        section["number"],
                        section["title"],
                        section.get("book_page"),
                        section.get("toc_pdf_page"),
                        section.get("confidence", "direct"),
                    ),
                )

                section_count += 1

        connection.commit()

        return {"chapters_saved": (chapter_count), "sections_saved": (section_count)}

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_learning_path(textbook_id):
    connection = get_connection()

    chapter_rows = connection.execute(
        """
        SELECT
            id,
            textbook_id,
            chapter_number,
            title,
            book_page,
            toc_pdf_page,
            confidence
        FROM chapters
        WHERE textbook_id = ?
        ORDER BY
            CAST(chapter_number AS INTEGER)
        """,
        (textbook_id,),
    ).fetchall()

    chapters = []

    for chapter_row in chapter_rows:
        chapter = dict(chapter_row)

        section_rows = connection.execute(
            """
            SELECT
                id,
                chapter_id,
                section_number,
                title,
                book_page,
                toc_pdf_page,
                confidence
            FROM sections
            WHERE chapter_id = ?
            ORDER BY
                book_page ASC,
                id ASC
            """,
            (chapter["id"],),
        ).fetchall()

        chapter["sections"] = [dict(section) for section in section_rows]

        chapters.append(chapter)

    connection.close()

    return chapters


def learning_path_exists(textbook_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM chapters
        WHERE textbook_id = ?
        """,
        (textbook_id,),
    ).fetchone()

    connection.close()

    return result["total"] > 0


def get_section_progress(section_id):
    connection = get_connection()

    progress = connection.execute(
        """
        SELECT
            section_id,
            reading_completed,
            concept_check_completed,
            activity_completed,
            mastery_completed,
            updated_at,
            completed_at
        FROM section_progress
        WHERE section_id = ?
        """,
        (section_id,),
    ).fetchone()

    connection.close()

    if progress:
        return dict(progress)

    return {
        "section_id": section_id,
        "reading_completed": 0,
        "concept_check_completed": 0,
        "activity_completed": 0,
        "mastery_completed": 0,
        "updated_at": None,
        "completed_at": None,
    }


def mark_reading_complete(section_id):
    connection = get_connection()

    section = connection.execute(
        """
        SELECT id
        FROM sections
        WHERE id = ?
        """,
        (section_id,),
    ).fetchone()

    if not section:
        connection.close()
        return None

    connection.execute(
        """
        INSERT INTO section_progress (
            section_id,
            reading_completed
        )
        VALUES (?, 1)

        ON CONFLICT(section_id)
        DO UPDATE SET
            reading_completed = 1,
            updated_at = CURRENT_TIMESTAMP
        """,
        (section_id,),
    )

    connection.commit()
    connection.close()

    return get_section_progress(section_id)


# =====================================================
# CHAT FUNCTIONS
# =====================================================


def create_chat(textbook_id, title):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO chats (
            textbook_id,
            title
        )
        VALUES (?, ?)
        """,
        (textbook_id, title),
    )

    chat_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return chat_id


def get_chats(textbook_id):
    connection = get_connection()

    chats = connection.execute(
        """
        SELECT
            id,
            textbook_id,
            title,
            created_at,
            updated_at
        FROM chats
        WHERE textbook_id = ?
        ORDER BY updated_at DESC
        """,
        (textbook_id,),
    ).fetchall()

    connection.close()

    return [dict(chat) for chat in chats]


def get_chat(chat_id):
    connection = get_connection()

    chat = connection.execute(
        """
        SELECT *
        FROM chats
        WHERE id = ?
        """,
        (chat_id,),
    ).fetchone()

    connection.close()

    if chat:
        return dict(chat)

    return None


def save_message(chat_id, role, content):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (chat_id, role, content),
    )

    message_id = cursor.lastrowid

    connection.execute(
        """
        UPDATE chats
        SET updated_at =
            CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (chat_id,),
    )

    connection.commit()
    connection.close()

    return message_id


def get_messages(chat_id):
    connection = get_connection()

    messages = connection.execute(
        """
        SELECT
            id,
            chat_id,
            role,
            content,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,),
    ).fetchall()

    connection.close()

    return [dict(message) for message in messages]


def get_section_context(section_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            s.id AS section_id,
            s.section_number,
            s.title AS section_title,
            s.book_page AS section_book_page,
            s.toc_pdf_page AS section_toc_pdf_page,

            c.id AS chapter_id,
            c.chapter_number,
            c.title AS chapter_title,
            c.book_page AS chapter_book_page,
            c.toc_pdf_page AS chapter_toc_pdf_page,

            t.id AS textbook_id,
            t.filename,
            t.stored_filename

        FROM sections AS s

        JOIN chapters AS c
            ON s.chapter_id = c.id

        JOIN textbooks AS t
            ON c.textbook_id = t.id

        WHERE s.id = ?
        """,
        (section_id,),
    ).fetchone()

    if not row:
        connection.close()
        return None

    context = dict(row)

    next_section = connection.execute(
        """
        SELECT
            id,
            section_number,
            title,
            book_page,
            toc_pdf_page

        FROM sections

        WHERE
            chapter_id = ?
            AND id > ?

        ORDER BY id ASC

        LIMIT 1
        """,
        (context["chapter_id"], section_id),
    ).fetchone()

    context["next_section"] = dict(next_section) if next_section else None

    next_chapter = connection.execute(
        """
        SELECT
            id,
            chapter_number,
            title,
            book_page,
            toc_pdf_page

        FROM chapters

        WHERE
            textbook_id = ?
            AND CAST(
                chapter_number AS INTEGER
            ) >
            CAST(? AS INTEGER)

        ORDER BY
            CAST(
                chapter_number AS INTEGER
            ) ASC

        LIMIT 1
        """,
        (context["textbook_id"], context["chapter_number"]),
    ).fetchone()

    context["next_chapter"] = dict(next_chapter) if next_chapter else None

    connection.close()

    return context
