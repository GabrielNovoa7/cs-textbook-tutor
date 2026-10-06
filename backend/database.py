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

            UNIQUE(textbook_id, chunk_index)
        )
    """)

    connection.commit()
    connection.close()


def get_textbook_by_hash(file_hash):
    connection = get_connection()

    textbook = connection.execute(
        "SELECT * FROM textbooks WHERE file_hash = ?",
        (file_hash,)
    ).fetchone()

    connection.close()

    if textbook:
        return dict(textbook)

    return None


def save_textbook(
    filename,
    stored_filename,
    file_hash,
    page_count,
    characters_extracted,
    chunks
):
    connection = get_connection()

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
        (
            filename,
            stored_filename,
            file_hash,
            page_count,
            characters_extracted
        )
    )

    textbook_id = cursor.lastrowid

    chunk_rows = [
        (
            textbook_id,
            chunk["chunk_id"],
            chunk["page_number"],
            chunk["text"]
        )
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
        chunk_rows
    )

    connection.commit()
    connection.close()

    return textbook_id


def get_textbooks():
    connection = get_connection()

    textbooks = connection.execute(
        """
        SELECT
            id,
            filename,
            page_count,
            characters_extracted,
            uploaded_at
        FROM textbooks
        ORDER BY uploaded_at DESC
        """
    ).fetchall()

    connection.close()

    return [dict(textbook) for textbook in textbooks]