import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import type { SectionProgress } from "./App";

const API_BASE = "http://127.0.0.1:8000";
type Activity = {
  activity_type: string; title: string; prompt: string; items: string[];
  starter_code: string; language: string; checklist: string[];
  source_type: string; evidence_page: number;
};

export default function LessonActivity({ sectionId, onProgress }: {
  sectionId: number; onProgress: (progress: SectionProgress) => void;
}) {
  const [activity, setActivity] = useState<Activity | null>(null);
  const [response, setResponse] = useState("");
  const [order, setOrder] = useState<number[]>([]);
  const [reviewed, setReviewed] = useState<number[]>([]);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [output, setOutput] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/sections/${sectionId}/activity`).then(async (result) => {
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail || "Could not load activity.");
      if (!active) return;
      setActivity(data.activity);
      setCompleted(data.completed);
      setResponse(data.submission?.response ?? data.activity?.starter_code ?? "");
      setOrder(data.submission?.order?.length ? data.submission.order : data.activity?.items.map((_: string, i: number) => i) ?? []);
      setReviewed(data.submission?.reviewed ?? []);
      setMessage(data.submission?.feedback ?? "");
      onProgress(data.progress);
    }).catch((error) => { if (active) setError(error.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [sectionId, onProgress]);

  async function save(complete: boolean) {
    setBusy(true); setError("");
    try {
      const result = await fetch(`${API_BASE}/sections/${sectionId}/activity`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ response, order, reviewed: [...reviewed].sort((a, b) => a - b), complete }),
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail || "Could not save activity.");
      setCompleted(data.completed); setMessage(data.feedback); onProgress(data.progress);
    } catch (error) { setError(error instanceof Error ? error.message : "Could not save activity."); }
    finally { setBusy(false); }
  }

  async function runActivityCode() {
    setBusy(true);
    setOutput(activity?.language === "cpp" ? "Compiling C++… The first run can take a few minutes." : "Running…");
    try {
      const result = await fetch(`${API_BASE}/run-code`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: response, language: activity?.language }) });
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail || "Could not run code.");
      setOutput(data.output || data.stderr || data.stdout || JSON.stringify(data));
    } catch (error) { setError(error instanceof Error ? error.message : "Could not run code."); }
    finally { setBusy(false); }
  }

  if (loading) return <section className="lesson-next-card">Loading section activity…</section>;
  if (!activity) return <section className="lesson-next-card"><p role="status">{error || "✓ Section complete. No additional activity is needed for this reading."}</p></section>;
  const selfReview = !["ordering", "predict_output"].includes(activity.activity_type);
  return <section className="lesson-next-card lesson-activity">
    <p className="eyebrow">{activity.activity_type.replaceAll("_", " ")} · {completed ? "Completed ✓" : "Section Activity"}</p>
    <h3>{activity.title}</h3>
    {completed && <p>This section is complete. You can use this activity for additional practice.</p>}
    <p className="activity-prompt">{activity.prompt}</p>
    <p>{activity.source_type === "textbook" ? "📖 From a textbook exercise" : "✨ Based on this section"} · PDF page {activity.evidence_page}</p>
    {activity.activity_type === "ordering" ? <ol className="activity-order">
      {order.map((item, position) => <li key={item}><span>{activity.items[item]}</span>
        <button disabled={busy || position === 0} aria-label={`Move item ${position + 1} up`} onClick={() => setOrder((previous) => {
          const next = [...previous]; [next[position - 1], next[position]] = [next[position], next[position - 1]]; return next;
        })}>↑</button>
        <button disabled={busy || position === order.length - 1} aria-label={`Move item ${position + 1} down`} onClick={() => setOrder((previous) => {
          const next = [...previous]; [next[position + 1], next[position]] = [next[position], next[position + 1]]; return next;
        })}>↓</button>
      </li>)}
    </ol> : activity.activity_type === "coding" ? <>
      <Editor height="300px" language={activity.language === "cpp" ? "cpp" : activity.language} theme="vs-dark"
        value={response} onChange={(value) => setResponse(value ?? "")} options={{ minimap: { enabled: false } }} />
      {["java", "cpp", "python"].includes(activity.language) && <button className="start-concept-button" disabled={busy} onClick={runActivityCode}>Run {activity.language === "cpp" ? "C++" : activity.language} Locally</button>}
      {output && <pre className="activity-output">{output}</pre>}
    </> : <>
      {activity.starter_code && <pre className="activity-output">{activity.starter_code}</pre>}
      <label className="activity-answer-label">Your {activity.activity_type === "predict_output" ? "predicted output" : "response"}
        <textarea value={response} maxLength={20000} onChange={(event) => setResponse(event.target.value)} rows={6} />
      </label>
    </>}
    {selfReview && <fieldset className="activity-review"><legend>Self-review checklist</legend>
      <p>Completion records your self-review; it does not automatically verify your solution.</p>
      {activity.checklist.map((item, index) => <label key={index}><input type="checkbox" checked={reviewed.includes(index)}
        onChange={(event) => setReviewed((previous) => event.target.checked ? [...previous, index] : previous.filter((value) => value !== index))} />{item}</label>)}
    </fieldset>}
    {error && <p className="path-error" role="alert">{error}</p>}
    {message && <p role="status">{message}</p>}
    <div className="activity-actions">
      <button className="path-back-button" disabled={busy} onClick={() => void save(false)}>Save Draft</button>
      <button className="start-concept-button" disabled={busy} onClick={() => void save(true)}>{selfReview ? "Complete Self-Review" : "Check Activity"}</button>
    </div>
  </section>;
}
