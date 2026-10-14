# CS Textbook Tutor

A personal computer science study app. Bring your textbook PDF, follow its chapters, practice what you read, and ask a tutor questions grounded in the book.

## What it does

- Textbook library with cover previews and persistent chats with page citations.
- Chapter learning paths, PDF reading, saved progress, notes and bookmarks.
- Cached concept quizzes, local grading, coding activities and chapter reviews.
- Java, Python and C++ code playgrounds.
- Dark study workspace with fluid motion, four accent themes and reduced-motion support.
- Windows desktop profiles with separate libraries and encrypted API-key storage.

## Run locally

Install Python 3.13, Node.js/npm, and a JDK for Java exercises.

```powershell
python -m venv backend/venv
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend install
npm ci
```

Create an untracked `backend/.env` containing `OPENAI_API_KEY=your_own_api_key`. Keep keys and personal data out of Git.

Start these in separate terminals:

```powershell
.\backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

```powershell
npm --prefix frontend run dev
```

Open http://localhost:5173. To run the desktop app, use `npm run desktop`.

Desktop profiles use their own keys and data; they do not inherit the development library or `.env`. See [desktop setup and installer instructions](docs/desktop.md).

## Checks

```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
.\backend\venv\Scripts\python.exe -m unittest backend.test_desktop backend.test_learning_tools backend.test_concept_check backend.test_pdf_processor backend.test_api backend.test_code_runner backend.test_tutor
npm run desktop:test
```

## How it works

React/TypeScript presents the workspace. FastAPI handles processing and learning tools. SQLite stores books, chats and progress; ChromaDB stores textbook embeddings. OpenAI generates tutor responses and practice material. Saved quizzes are reused and graded locally to avoid unnecessary API requests.

Development data lives in `backend/tutor.db`, `backend/uploads/` and `backend/vector_store/`. AI features need internet access and an API account with available usage; a ChatGPT subscription does not include API billing.

PDF uploads are limited to 100 MB and need selectable text. Existing partly scanned books can show chapter paths, but unreadable sections need OCR before quizzes and retrieval can use them. OCR is a planned improvement. The code runner is for trusted local programs; it is not a public multi-user sandbox.

See the [audit and roadmap](docs/project-audit-2026-10-13.md), [study tools](docs/study-tools.md) and [security review](security_best_practices_report.md).

## Learning project

I am building this app to learn full-stack development and AI integration, with ChatGPT/Codex assistance for planning, implementation and debugging. I review decisions and test the application as it develops.
