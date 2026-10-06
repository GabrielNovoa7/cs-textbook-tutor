from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from hashlib import sha256
from uuid import uuid4
from pydantic import BaseModel
import shutil

from backend.pdf_processor import extract_pages_from_pdf
from backend.text_chunker import chunk_pages
from backend.database import (
    init_db,
    get_textbook_by_hash,
    save_textbook,
    get_textbooks,
    create_chat,
    get_chats,
    get_chat,
    save_message,
    get_messages
)
from backend.vector_store import (
    add_textbook_chunks,
    search_textbook
)
from backend.tutor import generate_tutor_response

#connects to the frontend here
from fastapi.middleware.cors import CORSMiddleware
#connecst this endpoint to the code editor/code playground
from backend.code_runner import run_java_code

class AskRequest(BaseModel):
    question: str


class CreateChatRequest(BaseModel):
    title: str

class CodeRunRequest(BaseModel):
    code: str


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

init_db()


def calculate_file_hash(file_path):
    file_hash = sha256()

    with file_path.open("rb") as pdf_file:
        while True:
            block = pdf_file.read(1024 * 1024)

            if not block:
                break

            file_hash.update(block)

    return file_hash.hexdigest()


@app.get("/")
def home():
    return {"message": "CS Textbook Tutor API is running"}


@app.get("/textbooks")
def list_textbooks():
    return get_textbooks()


@app.post("/upload-textbook")
async def upload_textbook(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF textbooks are currently supported."
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
            "message": "This textbook has already been uploaded.",
            "textbook_id": existing_textbook["id"],
            "filename": existing_textbook["filename"],
            "already_exists": True
        }

    pages, page_count = extract_pages_from_pdf(file_path)

    chunks = chunk_pages(pages)

    characters_extracted = sum(
        len(page["text"])
        for page in pages
    )

    textbook_id = save_textbook(
        filename=original_filename,
        stored_filename=stored_filename,
        file_hash=file_hash,
        page_count=page_count,
        characters_extracted=characters_extracted,
        chunks=chunks
    )

    add_textbook_chunks(
        textbook_id=textbook_id,
        chunks=chunks
    )

    return {
        "textbook_id": textbook_id,
        "filename": original_filename,
        "pages": page_count,
        "characters_extracted": characters_extracted,
        "chunks_created": len(chunks),
        "already_exists": False
    }


@app.get("/textbooks/{textbook_id}/search")
def search_textbook_chunks(
    textbook_id: int,
    query: str
):
    results = search_textbook(
        textbook_id=textbook_id,
        query=query
    )

    return {
        "query": query,
        "textbook_id": textbook_id,
        "results": results
    }


@app.post("/textbooks/{textbook_id}/ask")
def ask_textbook(
    textbook_id: int,
    request: AskRequest
):
    passages = search_textbook(
        textbook_id=textbook_id,
        query=request.question,
        results=5
    )

    if not passages:
        raise HTTPException(
            status_code=404,
            detail="No relevant textbook content was found."
        )

    answer = generate_tutor_response(
        question=request.question,
        passages=passages
    )

    sources = [
        {
            "page_number": passage["page_number"],
            "chunk_id": passage["chunk_id"],
            "distance": passage["distance"]
        }
        for passage in passages
    ]

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources
    }


@app.post("/textbooks/{textbook_id}/chats")
def create_textbook_chat(
    textbook_id: int,
    request: CreateChatRequest
):
    chat_id = create_chat(
        textbook_id=textbook_id,
        title=request.title
    )

    return {
        "chat_id": chat_id,
        "textbook_id": textbook_id,
        "title": request.title
    }


@app.get("/textbooks/{textbook_id}/chats")
def list_textbook_chats(textbook_id: int):
    return get_chats(textbook_id)


@app.get("/chats/{chat_id}/messages")
def list_chat_messages(chat_id: int):
    return get_messages(chat_id)


@app.post("/chats/{chat_id}/ask")
def ask_chat(
    chat_id: int,
    request: AskRequest
):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat was not found."
        )

    history = get_messages(chat_id)

    search_query = request.question

    previous_user_messages = [
        message["content"]
        for message in history
        if message["role"] == "user"
    ]

    if previous_user_messages:
        search_query = (
            f"{previous_user_messages[-1]}\n"
            f"Follow-up question: {request.question}"
        )

    passages = search_textbook(
        textbook_id=chat["textbook_id"],
        query=search_query,
        results=5
    )

    if not passages:
        raise HTTPException(
            status_code=404,
            detail="No relevant textbook content was found."
        )

    answer = generate_tutor_response(
        question=request.question,
        passages=passages,
        chat_history=history
    )

    save_message(
        chat_id=chat_id,
        role="user",
        content=request.question
    )

    save_message(
        chat_id=chat_id,
        role="assistant",
        content=answer
    )

    return {
        "chat_id": chat_id,
        "question": request.question,
        "answer": answer
    }

@app.post("/run-code")
def run_code(request: CodeRunRequest):
    if len(request.code) > 20000:
        raise HTTPException(
            status_code=400,
            detail="Code is too large."
        )

    return run_java_code(request.code)