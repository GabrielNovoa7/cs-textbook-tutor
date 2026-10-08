# Study tools

The library shows **Continue Learning** after a section has been opened. Visits are
saved separately from completion so browsing does not mark a lesson finished.

**Progress** shows completed sections, readings, pending activities and quiz
accuracy across attempts. Its missed-concept list uses the latest quiz attempt
per section. Practice the section again to update that list. Textbook links use
physical PDF page numbers.

Each lesson has **My notes and bookmarks**. Save Notes saves the text explicitly;
adding or removing a bookmark also saves the current note. Notes and bookmarks
are stored in SQLite and survive restart. Deleting a book removes these records
along with its other learning data.

Each expanded chapter has **Chapter Review & Assignment**. Complete every section
first. Reviews combine up to twelve saved questions, taking at most two per section,
and require 75% to pass. Grading stays on the server; private answer indices are
not sent before submission. Review attempts are saved separately from section
attempts. The assignment is a case study connecting the chapter's section topics.
Drafts are saved, and completion requires a passed review, a substantive response
and confirmation of self-review. This is not automatic grading. These tools make
no additional OpenAI requests.

The Progress page's playground and coding activities support Java, C++ and Python.
Java requires the existing JDK. Python uses the backend interpreter. C++ uses g++
or clang++ from PATH, or the pinned portable Zig compiler in `.tools`.

To set up the portable compiler on another Windows checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/setup_cpp.ps1
```

The script downloads from Zig's official site, checks SHA256 against its release
index and extracts only inside the project's ignored `.tools` directory.

Execution is local, not a security sandbox: use code you trust. Programs have a
five-second execution limit, no interactive stdin and bounded displayed output.
C++ compilation has a three-minute limit to accommodate its first library build.

Validation:

```powershell
.\backend\venv\Scripts\python.exe -m unittest backend.test_learning_tools backend.test_concept_check backend.test_pdf_processor
cd frontend
npm run build
```
