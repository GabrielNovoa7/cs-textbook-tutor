from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel

import shutil


from backend.pdf_processor import (
    extract_pages_from_pdf,
    extract_table_of_contents,
    extract_printed_table_of_contents,
    extract_page_text_range,
    analyze_table_of_contents,
)

from backend.text_chunker import chunk_pages

from backend.database import (
    init_db,
    get_textbook_by_hash,
    get_textbook,
    save_textbook,
    get_textbooks,
    get_section_context,
    save_learning_path,
    get_learning_path,
    learning_path_exists,
    create_chat,
    get_chats,
    get_chat,
    save_message,
    get_messages,
    get_section_progress,
    mark_reading_complete,
)

from backend.lesson_source import build_section_source

from backend.vector_store import add_textbook_chunks, search_textbook

from backend.tutor import generate_tutor_response

from backend.code_runner import run_java_code

# =====================================================
# REQUEST MODELS
# =====================================================


class AskRequest(BaseModel):
    question: str


class CreateChatRequest(BaseModel):
    title: str


class CodeRunRequest(BaseModel):
    code: str


# =====================================================
# APP SETUP
# =====================================================


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"

UPLOAD_FOLDER.mkdir(exist_ok=True)


init_db()


# =====================================================
# HELPER FUNCTIONS
# =====================================================


def calculate_file_hash(file_path):
    file_hash = sha256()

    with file_path.open("rb") as pdf_file:
        while True:
            block = pdf_file.read(1024 * 1024)

            if not block:
                break

            file_hash.update(block)

    return file_hash.hexdigest()


# =====================================================
# HOME
# =====================================================


@app.get("/")
def home():
    return {"message": ("CS Textbook Tutor API is running")}


# =====================================================
# TEXTBOOKS
# =====================================================


@app.get("/textbooks")
def list_textbooks():
    return get_textbooks()


# =====================================================
# TABLE OF CONTENTS
# =====================================================


@app.get("/textbooks/{textbook_id}/toc")
def get_textbook_toc(textbook_id: int):
    textbook = get_textbook(textbook_id)

    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook was not found.")

    file_path = UPLOAD_FOLDER / textbook["stored_filename"]

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=("The textbook PDF file " "could not be found.")
        )

    # First try real PDF bookmarks.
    contents = extract_table_of_contents(file_path)

    source = "pdf_bookmarks"

    # If there are no useful bookmarks,
    # fall back to scanning the printed TOC.
    if not contents:
        contents = extract_printed_table_of_contents(file_path)

        source = "printed_toc_scan"

    # OCR recovery is only needed for
    # the printed TOC scanner.
    analysis = analyze_table_of_contents(
        contents, file_path=(file_path if source == "printed_toc_scan" else None)
    )

    return {
        "textbook_id": textbook_id,
        "filename": textbook["filename"],
        "source": source,
        "entries_found": len(analysis["entries"]),
        "chapters_found": len(analysis["chapters"]),
        "recovered_sections": len(analysis["recovered_sections"]),
        "warnings_found": len(analysis["warnings"]),
        "warnings": analysis["warnings"],
        "chapters": analysis["chapters"],
    }


# =====================================================
# LEARNING PATH
# =====================================================


@app.post("/textbooks/{textbook_id}/learning-path/rebuild")
def rebuild_learning_path(textbook_id: int):
    textbook = get_textbook(textbook_id)

    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook was not found.")

    file_path = UPLOAD_FOLDER / textbook["stored_filename"]

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=("The textbook PDF file " "could not be found.")
        )

    # -----------------------------------------
    # METHOD 1:
    # Try real PDF bookmarks first.
    # -----------------------------------------

    contents = extract_table_of_contents(file_path)

    source = "pdf_bookmarks"

    # -----------------------------------------
    # METHOD 2:
    # Fall back to printed TOC scanning.
    # -----------------------------------------

    if not contents:
        contents = extract_printed_table_of_contents(file_path)

        source = "printed_toc_scan"

    # -----------------------------------------
    # ANALYZE / CLEAN
    #
    # Only give file_path to the analyzer
    # when using printed TOC extraction.
    # -----------------------------------------

    analysis = analyze_table_of_contents(
        contents, file_path=(file_path if source == "printed_toc_scan" else None)
    )

    # If absolutely no chapters could be
    # detected, don't save a broken path.
    if not analysis["chapters"]:
        return {
            "saved": False,
            "textbook_id": textbook_id,
            "filename": textbook["filename"],
            "source": source,
            "reason": ("No usable chapters " "could be detected."),
            "warnings_found": len(analysis["warnings"]),
            "warnings": analysis["warnings"],
        }

    # Save even if there are minor warnings.
    # A book does not need to have a perfectly
    # sequential TOC to have a Learning Path.
    result = save_learning_path(textbook_id=textbook_id, chapters=analysis["chapters"])

    return {
        "saved": True,
        "textbook_id": textbook_id,
        "filename": textbook["filename"],
        "source": source,
        "recovered_sections": len(analysis["recovered_sections"]),
        "chapters_saved": result["chapters_saved"],
        "sections_saved": result["sections_saved"],
        "warnings_found": len(analysis["warnings"]),
        "warnings": analysis["warnings"],
    }


@app.get("/textbooks/{textbook_id}/learning-path")
def read_learning_path(textbook_id: int):
    textbook = get_textbook(textbook_id)

    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook was not found.")

    if not learning_path_exists(textbook_id):
        return {
            "textbook_id": textbook_id,
            "filename": textbook["filename"],
            "built": False,
            "chapters": [],
        }

    chapters = get_learning_path(textbook_id)

    return {
        "textbook_id": textbook_id,
        "filename": textbook["filename"],
        "built": True,
        "chapters_found": len(chapters),
        "chapters": chapters,
    }


@app.get("/textbooks/{textbook_id}/pdf")
def get_textbook_pdf(textbook_id: int):
    textbook = get_textbook(textbook_id)

    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook was not found.")

    file_path = UPLOAD_FOLDER / textbook["stored_filename"]

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Textbook PDF was not found.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=textbook["filename"],
        content_disposition_type="inline",
    )


@app.get("/sections/{section_id}/lesson-source")
def get_section_lesson_source(section_id: int):
    context = get_section_context(section_id)

    if not context:
        raise HTTPException(status_code=404, detail="Section was not found.")

    file_path = UPLOAD_FOLDER / context["stored_filename"]

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Textbook PDF was not found.")

    source = build_section_source(file_path=file_path, section_context=context)

    return {
        "section_id": (context["section_id"]),
        "section_number": (context["section_number"]),
        "section_title": (context["section_title"]),
        "chapter_id": (context["chapter_id"]),
        "chapter_number": (context["chapter_number"]),
        "chapter_title": (context["chapter_title"]),
        "textbook_id": (context["textbook_id"]),
        "filename": (context["filename"]),
        "pdf_url": (f"/textbooks/" f"{context['textbook_id']}" f"/pdf"),
        **source,
    }


@app.get("/sections/{section_id}/progress")
def read_section_progress(section_id: int):
    context = get_section_context(section_id)

    if not context:
        raise HTTPException(status_code=404, detail="Section was not found.")

    return get_section_progress(section_id)


@app.post("/sections/{section_id}/progress/reading-complete")
def complete_section_reading(section_id: int):
    progress = mark_reading_complete(section_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Section was not found.")

    return {"message": "Reading completed.", "progress": progress}


# =====================================================
# DEBUG PDF PAGES
# =====================================================


@app.get("/textbooks/{textbook_id}/debug-pages")
def debug_textbook_pages(textbook_id: int, start_page: int = 10, end_page: int = 40):
    textbook = get_textbook(textbook_id)

    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook was not found.")

    file_path = UPLOAD_FOLDER / textbook["stored_filename"]

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=("The textbook PDF " "could not be found.")
        )

    pages = extract_page_text_range(file_path, start_page, end_page)

    return {
        "textbook_id": textbook_id,
        "start_page": start_page,
        "end_page": end_page,
        "pages": pages,
    }


# =====================================================
# UPLOAD TEXTBOOK
# =====================================================


@app.post("/upload-textbook")
async def upload_textbook(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail=("Only PDF textbooks are " "currently supported.")
        )

    original_filename = Path(file.filename).name

    stored_filename = f"{uuid4().hex}.pdf"

    file_path = UPLOAD_FOLDER / stored_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = calculate_file_hash(file_path)

    existing_textbook = get_textbook_by_hash(file_hash)

    if existing_textbook:
        file_path.unlink(missing_ok=True)

        return {
            "message": ("This textbook has already " "been uploaded."),
            "textbook_id": (existing_textbook["id"]),
            "filename": (existing_textbook["filename"]),
            "already_exists": True,
        }

    pages, page_count = extract_pages_from_pdf(file_path)

    chunks = chunk_pages(pages)

    characters_extracted = sum(len(page["text"]) for page in pages)

    textbook_id = save_textbook(
        filename=original_filename,
        stored_filename=stored_filename,
        file_hash=file_hash,
        page_count=page_count,
        characters_extracted=(characters_extracted),
        chunks=chunks,
    )

    add_textbook_chunks(textbook_id=textbook_id, chunks=chunks)

    return {
        "textbook_id": textbook_id,
        "filename": original_filename,
        "pages": page_count,
        "characters_extracted": (characters_extracted),
        "chunks_created": len(chunks),
        "already_exists": False,
    }


# =====================================================
# SEMANTIC SEARCH
# =====================================================


@app.get("/textbooks/{textbook_id}/search")
def search_textbook_chunks(textbook_id: int, query: str):
    results = search_textbook(textbook_id=textbook_id, query=query)

    return {"query": query, "textbook_id": textbook_id, "results": results}


# =====================================================
# TEXTBOOK QUESTION
# =====================================================


@app.post("/textbooks/{textbook_id}/ask")
def ask_textbook(textbook_id: int, request: AskRequest):
    passages = search_textbook(
        textbook_id=textbook_id, query=request.question, results=5
    )

    if not passages:
        raise HTTPException(
            status_code=404, detail=("No relevant textbook " "content was found.")
        )

    answer = generate_tutor_response(question=request.question, passages=passages)

    sources = [
        {
            "page_number": (passage["page_number"]),
            "chunk_id": (passage["chunk_id"]),
            "distance": (passage["distance"]),
        }
        for passage in passages
    ]

    return {"question": request.question, "answer": answer, "sources": sources}


# =====================================================
# CHATS
# =====================================================


@app.post("/textbooks/{textbook_id}/chats")
def create_textbook_chat(textbook_id: int, request: CreateChatRequest):
    chat_id = create_chat(textbook_id=textbook_id, title=request.title)

    return {"chat_id": chat_id, "textbook_id": textbook_id, "title": request.title}


@app.get("/textbooks/{textbook_id}/chats")
def list_textbook_chats(textbook_id: int):
    return get_chats(textbook_id)


@app.get("/chats/{chat_id}/messages")
def list_chat_messages(chat_id: int):
    return get_messages(chat_id)


@app.post("/chats/{chat_id}/ask")
def ask_chat(chat_id: int, request: AskRequest):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat was not found.")

    history = get_messages(chat_id)

    search_query = request.question

    previous_user_messages = [
        message["content"] for message in history if message["role"] == "user"
    ]

    if previous_user_messages:
        search_query = (
            f"{previous_user_messages[-1]}\n"
            f"Follow-up question: "
            f"{request.question}"
        )

    passages = search_textbook(
        textbook_id=(chat["textbook_id"]), query=search_query, results=5
    )

    if not passages:
        raise HTTPException(
            status_code=404, detail=("No relevant textbook " "content was found.")
        )

    answer = generate_tutor_response(
        question=request.question, passages=passages, chat_history=history
    )

    save_message(chat_id=chat_id, role="user", content=request.question)

    save_message(chat_id=chat_id, role="assistant", content=answer)

    return {"chat_id": chat_id, "question": request.question, "answer": answer}


# =====================================================
# JAVA CODE RUNNER
# =====================================================


@app.post("/run-code")
def run_code(request: CodeRunRequest):
    if len(request.code) > 20000:
        raise HTTPException(status_code=400, detail="Code is too large.")

    return run_java_code(request.code)
