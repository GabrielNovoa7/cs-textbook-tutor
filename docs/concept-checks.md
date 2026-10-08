# Concept Checks

New regular sections have two questions (2/2 to pass). Every third section within
a chapter and its last section have four-question checkpoints (3/4 to pass).
Existing saved four-question checks keep their questions and 3/4 threshold;
they are never regenerated just to change their length. Attempts store their
actual question count so history and scores have the correct denominator.
The MVP supports multiple-choice and true/false; question type and grading data
are stored separately so later types can add their own local graders.

## Request flow

1. Complete reading through the existing reading-progress endpoint.
2. `POST /sections/{id}/concept-check` returns a saved quiz if one exists.
3. Otherwise, reuse the lesson page mapper, trim at section headings, and extract
   current-section reading. Scan the chapter locally for question blocks under
   headings such as Self-Test, Review Questions, Problems, and Practice Exercises.
   Only candidate questions, not the chapter's future prose, enter the prompt.
4. Commit a unique `creating` record before making one OpenAI Responses request.
   The request selects answerable textbook candidates first and generates the
   missing questions. Structured output includes options, correct answer indices,
   explanations, review hints, source IDs, and current-reading evidence quotes.
   The same request creates one appropriate application activity, or explicitly
   returns no activity if the reading does not justify another task.
5. Validate the required distinct questions, option/answer consistency, candidate IDs, and
   evidence quotes locally. Save the complete quiz as JSON in SQLite. Public
   responses explicitly include only question IDs, prompts, options, type, and
   limited source labels; they exclude grading data and original question text.
6. `POST /sections/{id}/concept-check/attempts` accepts all question option indices.
   The server compares indices locally, saves an attempt, and marks
   `concept_check_completed` when the score meets that check's threshold. A later failed
   practice attempt does not clear completion. Incorrect answers show review
   hints rather than the answer key.
7. `GET /sections/{id}/concept-check/attempts` returns timestamped scores.
   Refreshing, reopening, submitting, and retrying make no new OpenAI calls.

## Persistence and failure behavior

`concept_checks` holds the status and private quiz JSON keyed uniquely by section.
`concept_check_attempts` holds submitted answers, feedback, score, pass/fail, and
timestamps. Attempts and completion are committed in the same transaction.

The SQLite reservation prevents concurrent creation across requests/processes.
SDK retries are disabled. A failed request or invalid response does not
automatically issue another request. Error categories are saved and displayed
without exposing provider bodies, secrets, or private answers. Returned responses
are saved before validation; after a validator fix, a normal Start can recover a
saved response with zero API calls. Evidence matching normalizes PDF ligatures,
soft hyphens and wrapped words while still requiring the quote in current reading.
Reading extraction preserves PDF text-block order so marginal glossary labels do
not get visually sorted into body sentences. Old saved responses that fail
validation are also checked against a fresh extraction of the same mapped section;
this recovery does not generate questions or make an API request. Wrapped compound
hyphens and word-break hyphens are checked as exact alternatives, not fuzzy matches.

If recovery is impossible, the UI offers **Retry Quiz Creation (new API request)**.
Only this explicit action sends another request for a failed creation; normal
Start clicks do not. This is an exception to the original strict lifetime
one-request limit for failure recovery, with the potential API charge disclosed
before clicking. Successfully created quizzes never regenerate through this
option. Reading and attempt records are preserved. A server crash leaving a
`creating` record still requires investigation; active generation cannot be
reset by clicking retry.

Learning Path rebuilds now update matching textbook/chapter/section numbers in
place. If the parser would remove a section with progress or quiz records, the
whole rebuild rolls back. Logical numbering changes need an explicit migration.
Matching by number also assumes numbering continues to identify the same lesson;
substantial content changes may require a future quiz-versioning design.

## Extraction limits

Question discovery is heuristic, not OCR. Candidate text is capped at 24,000
characters, with nearby questions preferred. Reading above 65,000 characters or
80 pages is rejected instead of silently truncating the section. Missing section
headings or insufficient extracted text stop generation. If the next heading
cannot be found on its mapped boundary page, that page is excluded so future
material cannot enter the reading. This can omit a current-section continuation.

Exact evidence validation checks provenance; it does not prove that the model's
answer or its judgment of a textbook question is educationally correct. Review
real generated quizzes as part of manual testing. Automated open-ended/code
grading and a separate chapter mastery assessment remain future work.

## Activities and navigation

`GET /sections/{id}/activity` unlocks after passing the section questions. It
returns an explicit public field allowlist, excluding correct order and accepted
output strings. `POST` saves a draft or checks completion. Ordering and output
prediction use local deterministic comparisons. Coding, scenario, comparison,
and explanation tasks require a written solution plus a self-review checklist;
the UI explicitly says this is not automatic correctness grading. Java can run
through the existing local development runner; other languages are editable only.
Activity drafts and completion persist in `activity_submissions`. Completing a
task updates activity/section completion in the same transaction. A reading for
which generation explicitly chose no activity completes after passing questions.

Older saved quizzes receive a small teach-back activity using their existing
question text; this local compatibility fallback requires zero new API calls.
Previously passed legacy lessons remain complete; their teach-back activity is
optional practice. Required activities apply to lessons created with the new
activity-aware schema. Roadmap labels distinguish Questions Remaining and Activity
Remaining instead of labeling every unfinished lesson Available.
Activities for new sections are created in the original single request and have
their own evidence validation and textbook/generated provenance.

Lessons offer Previous Section, Next Section, and Next Chapter navigation in
textbook order. Browsing ahead does not mark skipped lessons completed. Sidebar
Learning Path returns to book selection; Library returns to the library. The
roadmap can open any section and shows persisted chapter/overall completion.
Heading matching tolerates merged/split OCR words, but still requires the exact
section number and identical title characters (apart from spacing/punctuation).

## Validation

Run `python -m unittest backend.test_concept_check -v` from the repository root.
Tests use temporary databases/PDFs and mocked generation, with no paid requests.
Run `npm run build` and `npm run lint` from `frontend`.
