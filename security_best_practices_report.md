# Security review: CS Textbook Tutor

Reviewed October 13, 2026. The app is suitable for further **personal, trusted local** development, with the limitations below. This pass did not deploy, expose credentials, modify the existing `.env`, or call OpenAI. No whole-application security certification is implied.

## High severity when untrusted code or remote users are involved

**SEC-01 — Code execution is not a sandbox.** `backend/code_runner.py:54` and `backend/main.py:760` execute programs with the user's OS permissions. Impact: untrusted programs can read/write files and access the network. This pass removes backend credentials from inherited environment variables and shares bounded-output/process-tree handling across Java/Python/C++; it does not restrict filesystem or network access. Use trusted exercise programs. A real isolation boundary is required before public or untrusted multi-user operation.

**SEC-02 — Browser-mode API has no public-user access controls.** `backend/main.py:115` only authenticates when a desktop token is configured. Browser development binds loopback, but lacks per-user authentication, Host enforcement and quotas. CORS limits browser-readable cross-origin responses; it is not authentication. Keep local-only. Before public hosting, add appropriate auth/authorization, Host protection, request limits and execution isolation. [FastAPI's CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/) explains exact origin configuration.

## Medium severity / resource and privacy controls

**SEC-03 — Input/output resource controls improved, not OS-hard quotas.** Uploads now reject files above 100 MB and reject unreadable/empty text PDFs (`backend/main.py:560`). Parsing runs in a worker thread. Multipart spooling and compressed PDF expansion remain separate concerns. Runner output is monitored periodically and returned text is capped; output can exceed the capture threshold between checks. CPU, disk, network and child-process restrictions still need OS-level controls for untrusted use.

**SEC-04 — Provider data and error handling improved.** `backend/tutor.py:31` sends `store=False`, uses a 90-second timeout and disables automatic retries. Provider error bodies are never returned. Quiz generation already used no retries, provider-storage opt-out, cached validation and safe categories. `store=False` is a response-storage setting, not a claim that every provider retention mechanism is disabled. New chat input rejects blank/oversized questions; a total history/output budget remains recommended.

**SEC-05 — Dependency advisories need continued maintenance.** Frontend npm audit is clear after overriding DOMPurify to 3.4.17. Root npm audit reports eight moderate entries in Electron build tooling, rooted in `sprintf-js` [GHSA-hp3w-g68c-fv3c](https://github.com/advisories/GHSA-hp3w-g68c-fv3c). They are not eight distinct demonstrated runtime exploits. Packaging dependencies were not broadly downgraded or force-updated. Python `pip check` passes; a Python advisory scan and tested version lock remain outstanding.

## Low severity / hygiene

**SEC-06 — Secret-file ignore coverage improved.** `.gitignore:9` ignores `.env` and `.env.*`, permitting example files. Existing `backend/.env` is ignored and unchanged. No `.env` path was found in tracked files/reachable history; the key-pattern scanner found no OpenAI-style keys in 58 tracked files or 122 reachable Git blobs at the time it ran. No finding currently establishes the need to rotate the key. This is a limited pattern scan, not a guarantee that all credential formats were checked.

**SEC-07 — Local Monaco preserves script restrictions.** `frontend/src/LocalCodeEditor.tsx:1` imports the editor locally, avoiding a CDN script previously blocked by CSP. `frontend/index.html:7` permits self/blob workers while keeping script sources local. Markdown does not enable raw HTML. [Monaco React's local-package integration guidance](https://github.com/suren-atoyan/monaco-react#use-monaco-editor-as-an-npm-package) supports configuring the loader with an imported Monaco instance.

## Existing protections retained

- Parameterized SQLite queries, foreign keys and deletion cascades.
- Random stored PDF filenames and path containment checks on delete/cover routes.
- Desktop random session tokens, timing-safe comparison and loopback binding.
- Electron context isolation, sandboxed renderer, no Node integration, restricted navigation and IPC sender checks.
- API keys encrypted with Electron safeStorage, separate from profile metadata/browser storage/installer contents.
- Quiz answer keys remain server-side; deterministic grading avoids repeated provider calls.

The filesystem/database/vector-store deletion compensation protects ordinary recoverable exceptions, not abrupt crashes across all stores. Recovery tools and backups remain part of the roadmap. The full architecture and prioritized feature roadmap are in `docs/project-audit-2026-10-13.md`.
