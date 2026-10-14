# CS Textbook Tutor: audit and first-pass roadmap

This is an existing learning application with a useful foundation. Keep React, FastAPI, SQLite and Chroma; the immediate work is reliability and completing the UI around functionality that already exists. This pass changes no hosting or deployment configuration and makes no paid OpenAI requests.

## Scope and evidence

Reviewed application modules, frontend components, database schema/migrations, PDF extraction and quiz validation, tests, desktop profile/packaging code, dependency manifests, and project documentation. Ran the local frontend/backend, inspected the real library and saved Java chat in Edge through Playwright, and exercised controlled browser failure fixtures. Destructive lifecycle tests use disposable SQLite databases, PDFs and Chroma collections.

Development data at audit time:

| Data | Count |
|---|---:|
| Textbooks | 4 |
| SQLite chunks | 7,311 |
| Chroma vectors | 9,021 |
| Vectors belonging to absent textbook IDs | 1,710 |
| Chats / messages | 3 / 16 |
| Chapters / sections | 58 / 970 |
| Quizzes | 7 ready, 1 failed |

SQLite `quick_check` returned `ok`; foreign-key checks returned no violations. The existing orphan vectors were **not deleted**. A later repair should first produce a dry-run report and retain a recoverable backup. No existing quiz was regenerated or user textbook deleted.

## Current architecture

| Folder/module | Responsibility |
|---|---|
| `frontend/src/App.tsx` | Library, course navigation, PDF reading, chat, chat code playground; component-local navigation state |
| `ConceptCheck.tsx`, `LessonActivity.tsx`, `StudyTools.tsx` | Section quizzes, application activities, progress, notes/bookmarks, chapter reviews/assignments |
| `DesktopSetup.tsx`, `ProfilePreferences.tsx`, `desktop.ts` | Desktop onboarding, preferences, backend URL and token injection |
| `CodeEditor.tsx`, `LocalCodeEditor.tsx` | Lazy, locally bundled Monaco editor and worker |
| `backend/main.py` | FastAPI routes, upload/deletion coordination, request validation |
| `database.py` | SQLite persistence and additive migrations; foreign keys and cascades |
| `pdf_processor.py`, `lesson_source.py`, `text_chunker.py` | Page text, bookmark/printed contents parsing, printed-page mapping, page-aware overlapping chunks |
| `vector_store.py` | One persistent Chroma collection filtered by textbook ID |
| `tutor.py` | Responses API chat generation and safe provider errors |
| `concept_check.py` | Material discovery, one-request quiz/activity creation, evidence validation, cache and deterministic grading |
| `lesson_activity.py`, `learning_tools.py` | Local activity grading/self-review, reviews, notes and dashboard |
| `code_runner.py` | Java/Python/C++ execution in temporary directories |
| `desktop/` | Electron process lifecycle, encrypted API keys, profile isolation, installer build and smoke tests |
| `docs/`, `backend/test_*.py` | Learning workflow documentation and regressions |

Development storage is under `backend/`: `tutor.db`, `uploads/`, `vector_store/`. Desktop storage uses separate profile directories under the Windows app-data directory. SQLite stores books/chunks, chats/messages, chapter/section structure, progress, quiz creation state/private answers/attempts, activities, notes, reviews and assignments. Chroma duplicates chunk text for retrieval and stores embeddings with textbook, chunk and physical-page metadata. Embeddings use Chroma's default local model; uploading does not use OpenAI embeddings.

Upload flow is PDF validation/extraction → page-aware chunks → pending SQLite book/chunks → batched Chroma indexing → ready SQLite book. Chat flow is textbook-filtered retrieval → recent conversation plus passages → one Responses request → persisted user/assistant messages. Learning paths come from PDF bookmarks or printed contents heuristics, without AI calls.

## What the app already does

- PDF library with real cover images, duplicate detection, persistent storage and confirmed deletion.
- Persistent textbook chats; the study button resumes the latest chat. Existing chat history renders as Markdown.
- Chapter/section learning paths, PDF reading with physical/printed page mapping, previous/next navigation and saved reading progress.
- Cached section questions, explanations, textbook exercise candidates, answer privacy, local grading and attempt history.
- Regular sections currently have **two questions**; every third section and the last section of a chapter have four. Existing cached checks are preserved.
- Generated application activities share the initial quiz request. Ordering/output activities have local grading; coding/explanation activities use explicit self-review.
- Notes/bookmarks, resume learning, missed-concept review, aggregate progress, cached chapter reviews and case-study assignments.
- Java, Python and C++ local execution; Java requires a JDK, C++ requires the configured compiler.
- Desktop onboarding, isolated profiles, encrypted personal keys, and themes.

These capabilities are established by source inspection and existing/new tests. This pass does **not** establish current API account/model access, live generation quality, every textbook's extraction accuracy, or a newly built Windows installer.

## Findings and fixes

| Priority | Finding | First-pass outcome |
|---|---|---|
| Critical for usability | Monaco CDN script was blocked by the app's own CSP, leaving editor on Loading | Bundled Monaco/worker locally, lazy loaded; preserved restrictive script policy; registered only supported language definitions |
| High | Invalid/scanned PDFs could fail with 500, leave files, or create books without retrieval | Clear 422 errors, 100 MB application limit, cleanup, Windows-safe stream parsing |
| High | Indexing failure left a committed book/chunks; duplicates could report a pending upload as successful | Compensating cleanup and additive `indexing_status`; pending books hidden, pending duplicates return 409 |
| High | Book deletion left vectors; a PDF deletion failure could retain an unsearchable book | Delete book-filtered vectors; retain existing embeddings and a temporary PDF backup for ordinary failure recovery |
| High | Java buffered arbitrary stdout/stderr in backend RAM | Shared file-based runner, timeout/process-tree cleanup, output monitoring and bounded returned text |
| High in untrusted execution | Exercise children inherited the API key and desktop token | Allowlisted runtime environment; still explicitly trusted-only execution |
| Medium | Chat used SDK default retries, provider storage, and unsanitized failure behavior | No automatic retries, 90-second timeout, `store=False`, safe actionable error categories |
| Medium | Chat failure silently lost the submitted question; library failure looked like an empty library | Visible alerts, draft restoration, retry library button, guard against overlapping normal/code tutor requests |
| Medium | Frontend only worked with one exact hostname origin | Explicit localhost and IPv4 loopback origins on port 5173 |
| Medium | Large textbooks could exceed Chroma's add batch limit | Adds split by the runtime's batch limit |
| Medium | Desktop briefly showed new-profile setup before saved profiles loaded; smoke test could fail while still returning exit 0 | Wait for profile listing, truthful failure exit status, extended smoke test to load local desktop Monaco |
| Low | `.env` variants were not ignored | Ignore `.env.*` while permitting example files; retained existing `.env` unchanged |
| Low | Recent Chats was a static, nonfunctional demo; PDF parser contained two unreachable copies | Removed demo card and unreachable parser code |
| Low | Frontend lint failed | Initial library effect uses abortable fetch and asynchronous completion; lint passes |
| Dependency | Monaco's pinned sanitizer dependency had advisories | Override DOMPurify to patched 3.4.17; frontend npm audit reports zero findings |

The upload limit bounds the saved application file, not all multipart-parser spooling or PDF decompression. Output monitoring checks periodically; it is not a hard operating-system disk/CPU quota. Cross-store compensation is not a distributed transaction: process crashes and recovery failures remain a repair-tool concern.

## Remaining issues

### Follow-up: C++ learning path

The Gaddis C++ PDF's detailed contents starts without a readable Contents heading.
The parser now recognizes detailed chapter/section rows, spaced section numbers
and wrapped titles. Damaged chapter headings are recovered only when the summary
and numbered sections corroborate them. Split page-number digits are recovered
only when neighboring section pages corroborate them, preserving numeric title
suffixes such as C++ 17.

Its saved path now contains **21 chapters and 202 recognized sections**. Section
18.4 remains flagged because its page number is OCR-damaged. A local database
backup was made under ignored `.tools/audit-backups/` before creating this path.
Other textbooks' saved work was preserved.

Only **182 of its 1,334 PDF pages have selectable text**. Verified chapter openings
for chapters 1–4 are physical PDF pages 31, 57, 115 and 181. The mapper now requires
printed-page corroboration so preface summaries cannot become lessons. Later
scanned chapters show an OCR message and a full-PDF link rather than guessed page
mappings. The user chose to defer OCR; scanned-chapter retrieval/quiz coverage is
still limited, and damaged section headings can block quiz preflight. No quiz
generation or OCR was run for this follow-up.

Saved paths now expose parsing warnings in the API and UI. Playwright verified
the real C++ path, first-section mapping, warning and scanned-chapter fallback.
The other three textbooks' first lesson mappings were rechecked.

1. **Chat access and evidence:** Chats navigation is a placeholder. Only the latest chat per book is accessible through the main UI. `/ask` returns retrieval metadata, but persistent chat messages store only text; citation page numbers are not structured, clickable evidence. Save source metadata alongside assistant messages before building an evidence drawer. Store excerpts from actual chunks rather than asking the model to reconstruct quotations.
2. **Mastery semantics:** Completion flags and quiz accuracy are not a robust measure of retained understanding. Self-reviewed coding activities can mark mastery without execution tests. Distinguish reading completion, practice completion, self-review and demonstrated skill.
3. **Four questions:** Current two/four checkpoint policy differs from the desired roughly four questions per section. Change generation policy for new quizzes after agreeing on question variety and preserve old attempts/caches.
4. **Recovery:** A crashed quiz can remain `creating`; a crashed upload can remain `indexing`. Need explicit diagnosis/recovery with leases or timestamps. Do not silently retry paid quiz creation. Existing failed quiz was preserved.
5. **Storage drift:** 1,710 pre-existing orphan vectors remain. SQLite/Chroma startup is eager; there is no audited repair/reindex/backup tool. Add indexes and batched dashboard queries if measured latency warrants it; dashboard currently issues multiple queries per book/section.
6. **Concurrency:** Chat user/assistant messages commit separately; simultaneous API requests can interleave, even though this pass blocks ordinary overlapping UI sends. Add one atomic exchange write and per-chat in-flight handling. Lesson/path requests can resolve out of order after fast navigation; cancellation should extend beyond initial library loading.
7. **Extraction:** Printed-page mapping can repeatedly scan the PDF. Last-section page-range display can stop too early, and same-page section boundaries need care. Candidate exercises are heuristic, often adapted into choice questions rather than shown verbatim. Scanned PDFs need OCR outside the upload flow.
8. **API efficiency:** Quizzes already cache and grade locally; notes, reviews, progress and code execution use zero AI calls. Chat creates a new SDK client each time, sends up to ten messages without a total character budget, and has no explicit output cap. Add connection reuse, bounded input/output and usage accounting before expanding AI features. Avoid an extra AI request just to classify each exercise.
9. **UI polish:** Long filenames are used as titles; chapter headers can say Start Here after completion; library progress can stay stale after upload/deletion until remount. Improve meaningful empty states, keyboard/focus handling and contrast. Current mobile library has no horizontal overflow at 390 px; this is not a comprehensive accessibility audit.
10. **Security/build hygiene:** Browser backend lacks authentication/Host enforcement/rate limiting for public use. Code execution can still access files/network with the Windows user's permissions. Root npm audit reports eight moderate dependency entries in the desktop build chain, rooted in a `sprintf-js` advisory. Do not apply a broad forced downgrade; update/test build tooling deliberately. Python requirements are unpinned; `pip check` verifies compatibility, not vulnerability freedom.
11. **Tests:** Initial 37 backend tests were useful but omitted uploads/vector lifecycle and chat errors. New tests address these. Browser fixtures cover specific regressions, not full end-to-end quiz generation, actual exercise correctness, restart recovery, or complete accessibility. Normal unittest discovery with `-t .` fails because backend is a namespace package; use the explicit modules below.

## Prioritized roadmap

### Critical fixes

- Completed in this pass: editor loading, upload/vector failure cleanup, pending upload visibility, deletion recovery, Java output/environment controls and visible chat errors.
- Next: dry-run storage consistency/recovery tooling with backups; atomic chat exchange persistence; deliberate desktop build-chain dependency remediation.
- Before any public hosting: isolated execution sandbox, authentication/authorization, Host checks, request/resource limits and provider-budget controls. Public hosting remains outside this pass.

### Quick improvements

- Replace filename-only titles with editable metadata; refresh dashboard after library changes.
- Display existing failed/indexing/creating states with safe recovery guidance.
- Add clear empty states and correct chapter status labels.
- Bound chat context and output; reuse SDK connections; display usage safely without logging prompts or secrets.
- Extend abort/stale-response handling to course/chat navigation; preserve unsaved notes when leaving.
- Add repeatable test scripts/CI and lock tested Python dependencies.

### Next major feature

**Complete the saved-chat and textbook-evidence experience.** Build on existing chat tables/routes: list chats by book, create/select/rename sessions, persist verified source metadata, and show clickable physical-page references with actual retrieved excerpts. This closes the current dead Chats navigation and makes textbook grounding inspectable without extra AI requests. Deliver chat browsing first, then evidence display, as independently reviewable increments.

Success: multiple sessions per book can be resumed after restart; older history remains intact; new answers expose stored source evidence; switching sessions never sends an AI request.

### Later improvements

- Evolve each section into reading → roughly four relevant questions → applied task → recap, preserving cached work.
- Java exercises with saved editor drafts, tested starter programs, expected-output/test cases and local deterministic checks. Keep hints optional and cache generated exercise material.
- Better textbook-exercise discovery and provenance; guided solutions offered progressively rather than immediately.
- Chapter quizzes, spaced review and topic-level mastery based on repeated performance; clearly separate self-review from automated verification.
- PDF excerpt reader/OCR support, improved page mapping, accessibility and richer library design.
- Only when needed: modularize large App/main modules, streaming chat, installer updates and optional sync. No wholesale rewrite is justified by this audit.

## Validation and how to repeat it

Final results: **63 backend tests passed**, frontend lint passed, production build passed, extended desktop smoke passed, controlled Playwright smoke passed, and the real saved Java course/chat/local-execution smoke passed. `pip check` and `git diff --check` passed. Frontend npm audit reported zero advisories; root build-tool audit retained the eight moderate entries described above. Expected test logs exercise failed generation/deletion recovery with synthetic inputs.

Existing development counts remained 4 books, 3 chats, 16 messages and 8 quizzes; all four books are ready after the additive migration. The native embedded PDF's URL/page mapping and reader frame were checked; complete native PDF painting was not conclusively verified from the captured screenshot. No paid generation was revalidated.

```powershell
npm --prefix frontend run build
npm --prefix frontend run lint
.\backend\venv\Scripts\python.exe -m unittest backend.test_desktop backend.test_learning_tools backend.test_concept_check backend.test_pdf_processor backend.test_api backend.test_code_runner backend.test_tutor
.\backend\venv\Scripts\python.exe -m pip check
.\backend\venv\Scripts\python.exe scripts/check_secrets.py
npm run desktop:test
npm --prefix frontend audit
```

With the Vite frontend running on `http://127.0.0.1:5173`:

```powershell
npx --yes --package @playwright/cli playwright-cli -s=tutor-smoke open http://127.0.0.1:5173 --browser msedge
npx --yes --package @playwright/cli playwright-cli -s=tutor-smoke run-code --filename frontend/scripts/browser-smoke.js
npx --yes --package @playwright/cli playwright-cli -s=tutor-smoke close
```

Browser fixtures intercept backend calls: library retry, locally bundled Java editor, run-button output rendering, quota error/draft preservation, one request per send, demo removal and mobile layout. Actual Java execution, compile failures, timeouts and output limits are exercised in backend tests. Screenshots are ignored under `output/playwright/`.

Build passes with a warning about the large, lazy-loaded Monaco chunk (~2.72 MB uncompressed / 699 KB gzip). It loads when the editor opens, not on the initial library screen. Desktop smoke covers onboarding, encrypted test keys, authenticated local API, profile separation/switching and file-based local Monaco rendering; it does not build or install an installer.

Secret checks found no OpenAI-key patterns in tracked files or reachable Git blobs, and no tracked/history `.env` paths. This pattern scan is not proof that every kind of credential is absent. No secret values are printed by the scanner. See the separate security report for remaining local execution and hosting risks.
