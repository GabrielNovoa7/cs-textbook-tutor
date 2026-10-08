import { useEffect, useState } from "react";
import { starters } from "./codeSamples";

const API = "http://127.0.0.1:8000";
async function api(path: string, method = "GET", body?: object) {
  const response = await fetch(API + path, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not save your work.");
  return data;
}
type Destination = { textbook_id: number; section_id: number };
type DashboardData = {
  resume: (Destination & { section_number: string; title: string }) | null;
  books: { id: number; filename: string; total: number; completed: number; reading: number; pending_activities: number; chapter_reviews: number; assignments: number }[];
  missed: (Destination & { filename: string; section_number: string; prompt: string; hint: string; pdf_page: number })[];
  quiz_score: number; quiz_total: number; attempts: number;
};

export function StudyDashboard({ onOpen, compact = false }: { onOpen: (destination: Destination) => void; compact?: boolean }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; api("/study-dashboard").then(d => { if (active) setData(d); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading learning progress…</p>;
  return <div className="study-tools">
    {data.resume && <section className="lesson-next-card"><p className="eyebrow">Pick up where you left off</p><h3>Section {data.resume.section_number} · {data.resume.title}</h3><button className="start-concept-button" onClick={() => onOpen(data.resume!)}>Continue Learning →</button></section>}
    {!compact && <>
      <section className="lesson-next-card"><h3>Your learning progress</h3><p>{data.attempts} quiz attempts · {data.quiz_total ? Math.round(data.quiz_score / data.quiz_total * 100) : 0}% accuracy across attempts</p>
        {!data.books.length && <p>Add a textbook to begin.</p>}
        {data.books.map(b => <article className="study-progress-book" key={b.id}><h4>{b.filename}</h4><progress max={b.total || 1} value={b.completed} /><p>{b.completed}/{b.total} sections complete · {b.reading} readings complete · {b.pending_activities} unfinished activities</p><p>{b.chapter_reviews} chapter reviews passed · {b.assignments} assignments completed</p></article>)}
      </section>
      <section className="lesson-next-card"><h3>Review missed concepts</h3><p>Questions missed on your latest attempt in each section. Answering them correctly removes them from this list.</p>
        {!data.missed.length && <p>No missed questions to review.</p>}
        {data.missed.map((m, i) => <article className="missed-concept" key={`${m.section_id}:${i}`}><p className="eyebrow">{m.filename} · Section {m.section_number}</p><strong>{m.prompt}</strong><p>{m.hint}</p><a href={`${API}/textbooks/${m.textbook_id}/pdf#page=${m.pdf_page}`} target="_blank" rel="noreferrer">Read PDF page {m.pdf_page}</a><button className="start-concept-button" onClick={() => onOpen(m)}>Practice this section</button></article>)}
      </section>
      <CodePlayground />
    </>}
  </div>;
}

export function SectionNotes({ sectionId, textbookId, startPage }: { sectionId: number; textbookId: number; startPage: number }) {
  const [note, setNote] = useState(""); const [bookmarks, setBookmarks] = useState<number[]>([]); const [page, setPage] = useState(startPage);
  const [message, setMessage] = useState(""); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  useEffect(() => { let active = true; api(`/sections/${sectionId}/notes`).then(d => { if (active) { setNote(d.note); setBookmarks(d.bookmarks); } }).catch(e => { if (active) setMessage(e.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [sectionId]);
  async function save(next = bookmarks) { setBusy(true); try { const d = await api(`/sections/${sectionId}/notes`, "PUT", { note, bookmarks: next }); setBookmarks(d.bookmarks); setMessage("Notes and bookmarks saved."); } catch (e) { setMessage(e instanceof Error ? e.message : "Could not save."); } finally { setBusy(false); } }
  return <section className="lesson-next-card study-tools"><h3>My notes and bookmarks</h3><label>Section notes<textarea disabled={loading || busy} maxLength={20000} rows={5} value={note} onChange={e => setNote(e.target.value)} /></label>
    <button className="start-concept-button" disabled={loading || busy} onClick={() => void save()}>Save Notes</button>
    <div className="bookmark-controls"><label>PDF page <input type="number" min={1} value={page} onChange={e => setPage(Number(e.target.value))} /></label><button disabled={loading || busy || !Number.isInteger(page) || page < 1} onClick={() => void save([...bookmarks, page])}>Bookmark Page</button></div>
    <ul>{bookmarks.map(p => <li key={p}><a href={`${API}/textbooks/${textbookId}/pdf#page=${p}`} target="_blank" rel="noreferrer">PDF page {p}</a> <button disabled={busy} aria-label={`Remove bookmark page ${p}`} onClick={() => void save(bookmarks.filter(x => x !== p))}>Remove</button></li>)}</ul><p role="status">{message}</p>
  </section>;
}

type ChapterData = { title: string; passing_score: number; questions: { key: string; prompt: string; options: string[]; section_number: string }[]; history: { score: number; total: number; passed: number; created_at: string }[]; assignment_prompt: string; assignment: { response: string; completed: number } | null };
type ReviewResult = { score: number; total: number; passed: boolean; feedback: { key: string; correct: boolean; feedback: string }[] };
export function ChapterReview({ chapterId }: { chapterId: number }) {
  const [data, setData] = useState<ChapterData | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [answers, setAnswers] = useState<Record<string, number>>({}); const [result, setResult] = useState<ReviewResult | null>(null);
  const [response, setResponse] = useState(""); const [reviewed, setReviewed] = useState(false); const [message, setMessage] = useState("");
  async function load() { setBusy(true); setError(""); try { const d = await api(`/chapters/${chapterId}/review`); setData(d); setResponse(d.assignment?.response ?? ""); } catch (e) { setError(e instanceof Error ? e.message : "Could not open review."); } finally { setBusy(false); } }
  async function submit() { setBusy(true); setError(""); try { const d: ReviewResult = await api(`/chapters/${chapterId}/review`, "POST", { answers }); setResult(d); setData(previous => previous ? { ...previous, history: [{ score: d.score, total: d.total, passed: Number(d.passed), created_at: new Date().toISOString() }, ...previous.history] } : previous); } catch (e) { setError(e instanceof Error ? e.message : "Could not grade review."); } finally { setBusy(false); } }
  async function save(complete: boolean) { setBusy(true); setError(""); try { await api(`/chapters/${chapterId}/assignment`, "PUT", { response, complete, reviewed }); setMessage(complete ? "Assignment completed through self-review." : "Assignment draft saved."); if (complete) setData(d => d ? { ...d, assignment: { response, completed: 1 } } : d); } catch (e) { setError(e instanceof Error ? e.message : "Could not save assignment."); } finally { setBusy(false); } }
  return <section className="chapter-review study-tools"><button className="start-concept-button" disabled={busy} onClick={() => void load()}>Chapter Review & Assignment</button><p>Unlocks when every section is complete. Reviews reuse your saved quiz questions.</p>{error && <p role="alert">{error}</p>}
    {data && <><h3>{data.title} · Chapter Review</h3><p>Pass with {data.passing_score}/{data.questions.length}.</p>
      {data.questions.map(q => { const f = result?.feedback.find(f => f.key === q.key); return <fieldset className={`quiz-question ${f ? f.correct ? "question-correct" : "question-incorrect" : ""}`} key={q.key} disabled={busy || !!result}><legend>{q.prompt}</legend><p>Section {q.section_number}</p>{q.options.map((o, i) => <label className="quiz-option" key={i}><input type="radio" name={`${chapterId}-${q.key}`} checked={answers[q.key] === i} onChange={() => setAnswers(a => ({ ...a, [q.key]: i }))} />{o}</label>)}{f && <p>{f.correct ? "✓ Correct" : "✕ Review needed"} · {f.feedback}</p>}</fieldset>; })}
      {!result ? <button disabled={busy || Object.keys(answers).length !== data.questions.length} onClick={() => void submit()}>Submit Chapter Review</button> : <div><p>{result.score}/{result.total} · {result.passed ? "Passed" : "Try again"}</p><button onClick={() => { setResult(null); setAnswers({}); }}>Practice Again</button></div>}
      {!!data.history.length && <p>Saved attempts: {data.history.map(h => `${h.score}/${h.total}${h.passed ? " ✓" : ""}`).join(" · ")}</p>}
      <h3>Chapter Assignment {data.assignment?.completed ? "· Completed ✓" : ""}</h3><p>{data.assignment_prompt}</p><textarea value={response} maxLength={20000} rows={8} onChange={e => setResponse(e.target.value)} />
      <label><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I connected the chapter concepts, included a worked example, checked it, and cited textbook pages.</label><p>This is a self-reviewed assignment, not an automatically graded solution.</p>
      <button disabled={busy} onClick={() => void save(false)}>Save Assignment Draft</button> <button disabled={busy || !reviewed || !data.history.some(h => h.passed)} onClick={() => void save(true)}>Complete Assignment</button><p role="status">{message}</p>
    </>}
  </section>;
}

export function CodePlayground() {
  const [language, setLanguage] = useState<keyof typeof starters>("python"); const [code, setCode] = useState<Record<keyof typeof starters, string>>(starters); const [output, setOutput] = useState(""); const [busy, setBusy] = useState(false);
  async function run() { setBusy(true); setOutput(language === "cpp" ? "Compiling C++… The first run can take a few minutes." : "Running…"); try { const d = await api("/run-code", "POST", { language, code: code[language] }); setOutput(`${d.status}\n${d.output || "Program finished with no output."}`); } catch (e) { setOutput(e instanceof Error ? e.message : "Could not run code."); } finally { setBusy(false); } }
  return <section className="lesson-next-card study-tools"><h3>Code Playground</h3><p>Runs code locally on your computer. Run code you trust; interactive input is not supported.</p><label>Language <select value={language} onChange={e => { setLanguage(e.target.value as keyof typeof starters); setOutput(""); }}><option value="java">Java</option><option value="cpp">C++</option><option value="python">Python</option></select></label><textarea aria-label={`${language} code`} spellCheck={false} rows={9} maxLength={20000} value={code[language]} onChange={e => setCode(c => ({ ...c, [language]: e.target.value }))} /><button className="start-concept-button" disabled={busy} onClick={() => void run()}>{busy ? "Running…" : "Run Code"}</button>{output && <pre className="activity-output">{output}</pre>}</section>;
}
