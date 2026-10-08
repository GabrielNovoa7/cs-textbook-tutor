# CS Textbook Tutor

A personal study workspace for computer science textbooks. Upload a PDF, follow its chapters and sections, practice what you read, and ask an AI tutor questions grounded in the book.

This actively developed learning project uses React/Vite, FastAPI, SQLite, ChromaDB, PyMuPDF, and OpenAI, with an Electron Windows desktop application.

## Features

- PDF library with real cover previews, duplicate detection, and deletion with two confirmations.
- Textbook learning paths, saved reading progress, and resume studying.
- At least two concept questions per section; four questions at selected checkpoints.
- Cached quizzes, local grading, saved attempts, and red/green answer feedback.
- Varied activities, coding exercises, chapter reviews, and self-reviewed assignments.
- Java, Python, and C++ code execution with time limits and bounded output.
- Previous/next section navigation and a separate next-chapter button.
- Progress dashboard, missed-concept review, notes, and PDF bookmarks.
- Persistent textbook chats supported by page-aware semantic retrieval.
- Four color styles and display-name preferences.
- Desktop profile setup with avatars, live theme previews, learning goals, and an optional personal API key.
- Separate desktop libraries and progress per profile, with encrypted API-key storage.

## Windows desktop

The installed app starts its local backend automatically. No development terminals are needed.

1. Run the Windows installer generated in `desktop-release/`.
2. Open **CS Textbook Tutor** from the desktop or Start menu.
3. Create a profile: name, avatar, theme, and learning goal.
4. Add your own OpenAI API key, or skip and add it later from the profile icon.
5. Upload your textbooks and start studying.

Desktop profiles start fresh. Existing development books and progress remain in `backend/`; automatic import is not implemented. Desktop data is stored under `%APPDATA%/cs-textbook-tutor-desktop/profiles/<profile-id>/`. Switch or create profiles from the profile menu.

API keys are encrypted locally using Electron `safeStorage` and Windows account protection. They are excluded from the installer, profile metadata, and browser storage. Profiles are separate workspaces within one Windows account, rather than password-protected accounts.

AI features require internet access and an OpenAI API account with available usage. A ChatGPT subscription does not include API billing. The first textbook upload may download ChromaDB's embedding model. Without a key, cached material and local tools remain available, but AI generation does not.

The installer bundles the backend, a Python exercise runtime, and the configured Zig C++ compiler. Java exercises require a JDK with `java` and `javac` on `PATH`.

Initial installers are unsigned test builds. Automatic updates, cloud sync, and macOS/Linux installers are not implemented. Install a newer build to update; profile data is stored outside the installation folder and preserved.

## Run from source

Requirements: Node.js/npm and Python 3.13. Windows is required for the current desktop packaging scripts. A JDK is required for Java exercises.

From the repository root:

```powershell
python -m venv backend/venv
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend install
npm ci
```

For browser development, create an untracked `backend/.env`:

```dotenv
OPENAI_API_KEY=your_own_api_key
```

Start the backend in one terminal:

```powershell
.\backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Start the frontend in another:

```powershell
npm --prefix frontend run dev
```

Open `http://localhost:5173`. Development data lives in `backend/tutor.db`, `backend/uploads/`, and `backend/vector_store/`. Do not commit these files or your `.env`.

Run the desktop application from source:

```powershell
npm run desktop
```

Desktop profiles use their own API keys and do not inherit the development `.env`.

## Build a Windows installer

After installing the dependencies above:

```powershell
.\backend\venv\Scripts\python.exe -m pip install -r desktop/requirements-build.txt
powershell -ExecutionPolicy Bypass -File backend/setup_cpp.ps1
npm run desktop:build
```

The build downloads a checksum-verified official Python runtime, packages the backend with PyInstaller, and generates a Windows x64 NSIS installer in `desktop-release/`. Electron and installer tools may download on the first build. Development databases, personal keys, and uploaded PDFs are excluded.

Rerun `npm run desktop:build` after changes. Increment the root `package.json` version for a new release. `npm run desktop:package` only repackages an already-built frontend and backend.

## Validation

```powershell
npm --prefix frontend run build
.\backend\venv\Scripts\python.exe -m unittest backend.test_desktop backend.test_learning_tools backend.test_concept_check backend.test_pdf_processor
npm run desktop:test
```

Desktop integration tests use disposable profiles under `desktop-build/smoke-profiles/` and make no OpenAI requests.

Before a release, check:

- Create two profiles; confirm their libraries, preferences, and progress are separate.
- Skip an API key, then add it through profile settings.
- Upload a PDF, complete a section, and restart to verify saved progress.
- Check quiz feedback, activities, chapter review, notes, bookmarks, and navigation.
- Run a short program in each configured language.
- Close the app and confirm its backend stops; reopen and resume studying.

## Architecture and limitations

PyMuPDF extracts page-aware text. SQLite stores books, chats, learning paths, and progress. ChromaDB stores embeddings for semantic retrieval. Relevant passages and section material support OpenAI explanations and quizzes.

Quizzes are validated against textbook evidence, cached, and graded locally. A generation failure is not a failed student attempt. Explicit retries may send a new API request; repeated ordinary clicks do not silently regenerate a quiz.

PDF quality matters: scanned pages, unusual headings, and inconsistent contents may require extraction fixes. AI-generated material still needs human review. This project is for personal local study; its code runner is not a sandbox suitable for public multi-user hosting.

See [study tools documentation](docs/study-tools.md) for the learning workflow.

## Learning project and AI assistance

I am building this application to learn full-stack development, APIs, databases, retrieval-augmented generation, and AI integration, and to use it for my own computer science studies.

Development uses significant ChatGPT/Codex assistance for planning, implementation, debugging, explanations, review, and documentation. I manage project decisions, review the code, test behavior, and continue improving the application.
