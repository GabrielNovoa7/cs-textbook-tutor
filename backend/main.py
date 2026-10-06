from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import shutil

from backend.pdf_processor import extract_text_from_pdf


app = FastAPI()

UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)


@app.get("/")
def home():
    return {"message": "CS Textbook Tutor API is running"}


@app.post("/upload-textbook")
async def upload_textbook(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF textbooks are currently supported."
        )

    safe_filename = Path(file.filename).name
    file_path = UPLOAD_FOLDER / safe_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text, page_count = extract_text_from_pdf(file_path)

    return {
        "filename": safe_filename,
        "pages": page_count,
        "characters_extracted": len(text),
        "preview": text[:500]
    }